import json
import time
from threading import RLock
from urllib.parse import quote, urlsplit, urlunsplit

from ...utils import atomic_write, validate_experiment_name
from base64 import urlsafe_b64decode
from os.path import basename
from pathlib import Path

import httpx

from ..storage import Storage

CREDENTIALS_PATH = Path.home() / ".resutil" / "credentials.json"

# Firebase token refresh endpoint
_TOKEN_REFRESH_URL = "https://securetoken.googleapis.com/v1/token"


def _load_credentials() -> dict:
    if not CREDENTIALS_PATH.exists():
        raise FileNotFoundError(
            f"Credentials not found at {CREDENTIALS_PATH}. Run 'resutil login' first."
        )
    with CREDENTIALS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _save_credentials(creds: dict) -> None:
    # mkstemp inside atomic_write creates mode 0600 before any token is written.
    atomic_write(CREDENTIALS_PATH, json.dumps(creds, indent=2))


def normalize_server_url(value):
    parts = urlsplit(value)
    if (
        parts.scheme not in ("http", "https")
        or not parts.hostname
        or parts.username
        or parts.password
        or parts.query
        or parts.fragment
    ):
        raise ValueError("Invalid server URL.")
    host = parts.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    port = parts.port
    if port and (parts.scheme, port) not in (("https", 443), ("http", 80)):
        host += f":{port}"
    return urlunsplit((parts.scheme.lower(), host, parts.path.rstrip("/"), "", ""))


def _decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload without verification (just to read exp claim)."""
    payload_b64 = token.split(".")[1]
    # Add padding
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding
    return json.loads(urlsafe_b64decode(payload_b64))


def _is_token_expired(id_token: str, margin_seconds: int = 300) -> bool:
    """Check if token expires within margin_seconds (default 5 min)."""
    try:
        payload = _decode_jwt_payload(id_token)
        exp = payload.get("exp", 0)
        return time.time() > (exp - margin_seconds)
    except Exception:
        return True


def _refresh_id_token(refresh_token: str, api_key: str) -> tuple[str, str]:
    """Use refresh_token to get a new id_token from Firebase."""
    resp = httpx.post(
        f"{_TOKEN_REFRESH_URL}?key={api_key}",
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["id_token"], data["refresh_token"]


def _ensure_valid_token(creds: dict, force=False) -> dict:
    """Check token expiry and refresh if needed. Returns updated creds."""
    id_token = creds["id_token"]
    refresh_token = creds.get("refresh_token")
    api_key = creds.get("api_key")

    if not force and not _is_token_expired(id_token):
        return creds

    if not refresh_token:
        raise PermissionError(
            "ID token expired and no refresh token available. Run 'resutil login' again."
        )
    if not api_key:
        raise PermissionError(
            "ID token expired but api_key not found in credentials. Run 'resutil login' again."
        )

    new_id_token, new_refresh_token = _refresh_id_token(refresh_token, api_key)
    creds["id_token"] = new_id_token
    creds["refresh_token"] = new_refresh_token
    _save_credentials(creds)
    return creds


class ResutilServerStorage(Storage):
    def __init__(self, storage_config: dict, project_name: str):
        self.server_url = normalize_server_url(storage_config["server_url"])
        self.bucket_name = storage_config["bucket_name"]
        self.project_dir = project_name

        self._auth_lock = RLock()
        creds = _load_credentials()
        if normalize_server_url(creds.get("server_url", "")) != self.server_url:
            raise PermissionError(
                "Credentials belong to a different server. Run 'resutil login' for this server."
            )
        creds = _ensure_valid_token(creds)
        self._creds = creds
        self.id_token = creds["id_token"]

        self._client = httpx.Client(
            base_url=self.server_url,
            timeout=60.0,
        )

    def _api_prefix(self) -> str:
        return f"/api/buckets/{quote(self.bucket_name, safe='')}/projects/{quote(self.project_dir, safe='')}/experiments"

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        with self._auth_lock:
            self._creds = _ensure_valid_token(self._creds)
            self.id_token = self._creds["id_token"]
            token = self.id_token
        headers = dict(kwargs.pop("headers", {}))
        headers["Authorization"] = f"Bearer {token}"
        resp = self._client.request(method, path, headers=headers, **kwargs)
        if resp.status_code == 401:
            with self._auth_lock:
                if self.id_token == token:
                    self._creds = _ensure_valid_token(self._creds, force=True)
                    self.id_token = self._creds["id_token"]
                headers["Authorization"] = f"Bearer {self.id_token}"
            resp = self._client.request(method, path, headers=headers, **kwargs)
        if resp.status_code == 401:
            raise PermissionError(
                "Authentication failed. Your token may have expired. Run 'resutil login' again."
            )
        if resp.status_code == 403:
            raise PermissionError(
                f"Access denied. You don't have permission to access bucket '{self.bucket_name}'.\n"
                "Run 'resutil login' to authenticate."
            )
        resp.raise_for_status()
        return resp

    def get_info(self) -> dict:
        return {
            "server_url": self.server_url,
            "bucket_name": self.bucket_name,
            "project_dir": self.project_dir,
        }

    def upload_experiment(self, zip_path: str):
        ex_name = quote(
            validate_experiment_name(basename(zip_path).removesuffix(".zip")), safe=""
        )
        resp = self._request("POST", f"{self._api_prefix()}/{ex_name}/upload-url")
        signed_url = resp.json()["signed_url"]

        with open(zip_path, "rb") as f:
            upload_resp = httpx.put(
                signed_url,
                content=f,
                headers={"Content-Type": "application/zip"},
                timeout=300.0,
            )
            upload_resp.raise_for_status()

    def download_experiment(self, zip_path: str):
        ex_name = quote(
            validate_experiment_name(basename(zip_path).removesuffix(".zip")), safe=""
        )
        resp = self._request("POST", f"{self._api_prefix()}/{ex_name}/download-url")
        signed_url = resp.json()["signed_url"]

        with httpx.stream("GET", signed_url, timeout=300.0) as stream:
            stream.raise_for_status()
            with open(zip_path, "wb") as f:
                for chunk in stream.iter_bytes():
                    f.write(chunk)

    def get_all_experiment_names(self) -> list[str]:
        resp = self._request("GET", self._api_prefix())
        return resp.json()["experiments"]

    def remove_experiment(self, ex_name: str):
        ex_name = quote(validate_experiment_name(ex_name), safe="")
        self._request("DELETE", f"{self._api_prefix()}/{ex_name}")

    def change_comment(self, ex_name: str, new_comment: str):
        from ...ex_dir import commented_name

        commented_name(ex_name, new_comment)
        ex_name = quote(ex_name, safe="")
        self._request(
            "POST",
            f"{self._api_prefix()}/{ex_name}/rename",
            json={"new_comment": new_comment},
        )

    def exist_experiment(self, ex_name: str) -> bool:
        ex_name = quote(validate_experiment_name(ex_name), safe="")
        resp = self._request("GET", f"{self._api_prefix()}/{ex_name}/exists")
        return resp.json()["exists"]
