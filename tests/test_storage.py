import base64
import importlib
import json
from threading import RLock
from unittest.mock import MagicMock

import httpx
import pytest

from conftest import A

server = importlib.import_module("resutil.storage.server.server")
drive = importlib.import_module("resutil.storage.gdrive.gdrive")


def token(exp=9999999999):
    payload = (
        base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode()).decode().rstrip("=")
    )
    return f"header.{payload}.signature"


@pytest.fixture
def creds(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "CREDENTIALS_PATH", tmp_path / "credentials.json")
    data = {
        "server_url": "https://example.test",
        "id_token": token(),
        "refresh_token": "refresh",
        "api_key": "key",
    }
    server._save_credentials(data)
    return data


def test_credentials_bound_to_server(creds):
    with pytest.raises(PermissionError):
        server.ResutilServerStorage(
            {"server_url": "https://other.test", "bucket_name": "test"}, "test"
        )


def test_expired_token_refresh_on_request(creds, monkeypatch):
    storage = server.ResutilServerStorage(
        {"server_url": creds["server_url"], "bucket_name": "test"}, "project"
    )
    storage._creds["id_token"] = token(1)
    refresh = MagicMock(return_value=(token(), "rotated"))
    monkeypatch.setattr(server, "_refresh_id_token", refresh)
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(200, json={"experiments": []})

    storage._client.close()
    storage._client = httpx.Client(
        base_url=storage.server_url, transport=httpx.MockTransport(handle)
    )
    try:
        assert storage.get_all_experiment_names() == []
        refresh.assert_called_once_with("refresh", "key")
        assert requests[0].headers["Authorization"] == f"Bearer {token()}"
    finally:
        storage._client.close()


def test_401_refresh_and_retry_and_encoded_path(creds, monkeypatch):
    storage = server.ResutilServerStorage(
        {"server_url": creds["server_url"], "bucket_name": "test"}, "project"
    )
    monkeypatch.setattr(
        server, "_refresh_id_token", lambda *args: (token(9999999998), "rotated")
    )
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(401 if len(requests) == 1 else 200, json={})

    storage._client.close()
    storage._client = httpx.Client(
        base_url=storage.server_url, transport=httpx.MockTransport(handle)
    )
    try:
        storage.remove_experiment(A + "#1")
        assert len(requests) == 2
        assert b"%231" in requests[0].url.raw_path
        assert (
            requests[0].headers["Authorization"] != requests[1].headers["Authorization"]
        )
    finally:
        storage._client.close()


def test_credential_permissions(creds):
    import os

    if os.name == "posix":
        assert server.CREDENTIALS_PATH.stat().st_mode & 0o777 == 0o600


def test_drive_folder_scope_and_pagination(monkeypatch):
    service = MagicMock()
    response = service.files.return_value.list.return_value.execute
    response.side_effect = [
        {"files": [{"id": "project", "name": "Project"}]},
        {"files": [{"id": "a", "name": A + ".zip"}], "nextPageToken": "next"},
        {"files": [{"id": "b", "name": "other.zip"}]},
    ]
    monkeypatch.setattr(
        drive.service_account.Credentials, "from_service_account_file", MagicMock()
    )
    monkeypatch.setattr(drive, "build", lambda *args, **kw: service)
    storage = drive.GDrive(
        {"key_file_path": "ignored", "base_folder_id": "parent"}, "Project"
    )
    assert storage.get_all_experiment_names() == [A, "other"]
    calls = service.files.return_value.list.call_args_list
    assert "'parent' in parents" in calls[0].kwargs["q"]
    assert "trashed = false" in calls[0].kwargs["q"]
    assert calls[-1].kwargs["pageToken"] == "next"
    assert storage.max_workers == 1


def test_drive_failed_update_never_deletes(tmp_path, monkeypatch):
    storage = object.__new__(drive.GDrive)
    storage._lock = RLock()
    storage.service = MagicMock()
    storage.project_dir_id = "project"
    monkeypatch.setattr(storage, "_find_file_id", lambda *args, **kw: "existing")
    storage.service.files.return_value.update.return_value.execute.side_effect = (
        OSError("network")
    )
    archive = tmp_path / f"{A}.zip"
    archive.write_bytes(b"archive")
    with pytest.raises(OSError):
        storage.upload_experiment(str(archive))
    storage.service.files.return_value.delete.assert_not_called()
