from functools import wraps
from os.path import basename
from threading import RLock

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from ..storage import Storage
from ...ex_dir import commented_name


def synchronized(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)

    return wrapped


def _escape(value):
    return value.replace("\\", "\\\\").replace("'", "\\'")


class GDrive(Storage):
    max_workers = 1

    def __init__(self, storage_config: dict, project_name: str):
        self._lock = RLock()
        credentials = service_account.Credentials.from_service_account_file(
            storage_config["key_file_path"]
        ).with_scopes(["https://www.googleapis.com/auth/drive"])
        self.service = build("drive", "v3", credentials=credentials)
        self.base_folder_id = storage_config["base_folder_id"]
        self.project_dir = project_name
        query = (
            f"name = '{_escape(project_name)}' and "
            "mimeType = 'application/vnd.google-apps.folder' and "
            f"'{_escape(self.base_folder_id)}' in parents and trashed = false"
        )
        items = self._list(query)
        if len(items) > 1:
            raise ValueError(
                "Multiple project folders found; resolve duplicate folders first."
            )
        if items:
            self.project_dir_id = items[0]["id"]
        else:
            folder = (
                self.service.files()
                .create(
                    body={
                        "name": project_name,
                        "mimeType": "application/vnd.google-apps.folder",
                        "parents": [self.base_folder_id],
                    },
                    fields="id",
                )
                .execute()
            )
            self.project_dir_id = folder["id"]

    @synchronized
    def _list(self, query):
        items, token = [], None
        while True:
            kwargs = dict(q=query, fields="nextPageToken,files(id,name)", pageSize=1000)
            if token:
                kwargs["pageToken"] = token
            result = self.service.files().list(**kwargs).execute()
            items.extend(result.get("files", []))
            token = result.get("nextPageToken")
            if not token:
                return items

    def get_info(self) -> dict:
        return {"project_dir": self.project_dir, "base_folder_id": self.base_folder_id}

    @synchronized
    def upload_experiment(self, zip_path: str):
        file_id = self._find_file_id(basename(zip_path), required=False)
        media = MediaFileUpload(zip_path, mimetype="application/zip", resumable=True)
        try:
            if file_id is not None:
                self.service.files().update(
                    fileId=file_id, media_body=media, fields="id"
                ).execute()
            else:
                self.service.files().create(
                    body={
                        "name": basename(zip_path),
                        "parents": [self.project_dir_id],
                    },
                    media_body=media,
                    fields="id",
                ).execute()
        finally:
            media.stream().close()

    @synchronized
    def download_experiment(self, zip_path: str):
        file_id = self._find_file_id(basename(zip_path))
        request = self.service.files().get_media(fileId=file_id)
        with open(zip_path, "wb") as stream:
            downloader = MediaIoBaseDownload(stream, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()

    @synchronized
    def get_all_experiment_names(self) -> list[str]:
        query = f"'{_escape(self.project_dir_id)}' in parents and trashed = false"
        return [
            item["name"][:-4]
            for item in self._list(query)
            if item["name"].endswith(".zip")
        ]

    @synchronized
    def remove_experiment(self, ex_name: str):
        file_id = self._find_file_id(ex_name + ".zip")
        self.service.files().delete(fileId=file_id).execute()

    @synchronized
    def change_comment(self, ex_name: str, new_comment: str):
        new_name = commented_name(ex_name, new_comment)
        if new_name == ex_name:
            return
        if self.exist_experiment(new_name):
            raise FileExistsError(new_name)
        self.service.files().update(
            fileId=self._find_file_id(ex_name + ".zip"),
            body={"name": new_name + ".zip"},
            fields="id,name",
        ).execute()

    @synchronized
    def _find_file_id(self, file_name, required=True):
        query = (
            f"'{_escape(self.project_dir_id)}' in parents and trashed = false "
            f"and name = '{_escape(file_name)}'"
        )
        items = self._list(query)
        if len(items) > 1:
            raise ValueError(f"Multiple archives found: {file_name}")
        if items:
            return items[0]["id"]
        if required:
            raise FileNotFoundError(f"Remote experiment does not exist: {file_name}")
        return None
