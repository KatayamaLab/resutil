from os.path import basename, normpath
from os import makedirs
from concurrent.futures import ThreadPoolExecutor, Future

from google.cloud import storage
from google.oauth2 import service_account

from ..storage import Storage


class GS(Storage):
    def __init__(self, storage_config: dict, project_name: str):
        key_file_path = storage_config["key_file_path"]
        backet_name = storage_config["backet_name"]
        try:
            credentials = service_account.Credentials.from_service_account_file(
                key_file_path
            )

            self.client = storage.Client(credentials=credentials)
            self.bucket = self.client.get_bucket(backet_name)
        except FileNotFoundError:
            raise ValueError(f"Key file not found at {key_file_path}")

        self.project_dir = project_name

    def get_info(self) -> tuple[str, str, str]:
        return {
            "project_dir": self.project_dir,
            "bucket_name": self.bucket.name,
        }

    def upload_experiment(self, zip_path: str):
        blob = self.bucket.blob(f"{self.project_dir}/{basename(zip_path)}")
        blob.upload_from_filename(zip_path)

        self.client.folder(self.project_dir.id).upload(zip_path, basename(zip_path))

    def download_experiment(self, zip_path: str):
        blob = self.bucket.blob(f"{self.project_dir}/{basename(zip_path)}")
        blob.download_to_filename(zip_path)

    def get_all_experiment_names(self) -> list[str]:
        blobs = self.client.list_blobs(self.bucket, prefix=self.project_dir + "/")
        return [p.name.split("/")[-1][:-4] for p in blobs]
