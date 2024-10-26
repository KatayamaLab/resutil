from os.path import basename
import io


from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from ..storage import Storage


class GDrive(Storage):
    def __init__(self, storage_config: dict, project_name: str):
        key_file_path = storage_config["key_file_path"]
        try:
            credentials = service_account.Credentials.from_service_account_file(
                key_file_path
            ).with_scopes(["https://www.googleapis.com/auth/drive"])

            self.service = build("drive", "v3", credentials=credentials)
            self.base_folder_id = storage_config["base_folder_id"]

        except FileNotFoundError:
            raise ValueError(f"Key file not found at {key_file_path}")

        self.project_dir = project_name

        query = f"name = '{project_name}' and mimeType = 'application/vnd.google-apps.folder'"
        results = (
            self.service.files()
            .list(
                q=query,
                fields="files(id, name)",
            )
            .execute()
        )
        items = results.get("files", [])

        self.experiment_item_cache = items

        for item in items:
            if item["name"] == project_name:
                self.project_dir_id = item["id"]
                break
        else:
            file_metadata = {
                "name": project_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [self.base_folder_id],
            }
            folder = (
                self.service.files().create(body=file_metadata, fields="id").execute()
            )
            self.project_dir_id = folder.get("id")

        self.experiment_item_cache = None
        self.max_workers = 1

    def get_info(self) -> tuple[str, str, str]:
        return {
            "project_dir": self.project_dir,
            "base_folder_id": self.base_folder_id,
        }

    def upload_experiment(self, zip_path: str):
        file_metadata = {
            "name": basename(zip_path),  # アップロードするファイル名
            "parents": [self.project_dir_id],  # アップロード先のフォルダID
        }
        media = MediaFileUpload(zip_path, mimetype="application/zip")

        self.service.files().create(
            body=file_metadata, media_body=media, fields="id"
        ).execute()

    def download_experiment(self, zip_path: str):
        file_id = self._find_file_id(basename(zip_path))

        request = self.service.files().get_media(fileId=file_id)
        fh = io.FileIO(zip_path, "wb")

        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

    def get_all_experiment_names(self) -> list[str]:
        query = f"'{self.project_dir_id}' in parents and trashed = false"
        results = (
            self.service.files()
            .list(
                q=query,
                fields="files(id, name)",
            )
            .execute()
        )
        items = results.get("files", [])

        self.experiment_item_cache = items

        if not items:
            return []
        else:
            filenames = [item["name"] for item in items]
            return [f[:-4] for f in filenames]

    def remove_experiment(self, ex_name: str):
        filename = ex_name + ".zip"

        file_id = self._find_file_id(filename)

        try:
            self.service.files().delete(fileId=file_id).execute()
        except Exception as e:
            print(f"An error occurred: {e}")

    def change_comment(self, ex_name, new_comment):
        new_ex_name = f"{ex_name.split('_')[0]}_{ex_name.split('_')[1]}_{new_comment}"
        old_name = ex_name + ".zip"
        new_name = new_ex_name + ".zip"

        file_id = self._find_file_id(old_name)

        try:
            file_metadata = {"name": new_name}
            updated_file = (
                self.service.files()
                .update(fileId=file_id, body=file_metadata, fields="id, name")
                .execute()
            )
            print(
                f"File ID: {updated_file.get('id')} renamed to {updated_file.get('name')}."
            )
        except Exception as e:
            print(f"An error occurred: {e}")

    def exist_experiment(self, ex_name: str) -> bool:
        return ex_name in self.get_all_experiment_names()

    def _find_file_id(self, file_name):
        if self.experiment_item_cache is None:
            self.get_all_experiment_names()

        for item in self.experiment_item_cache:
            if item["name"] == file_name:
                return item["id"]

        return None
