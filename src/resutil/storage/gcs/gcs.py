from os.path import basename, normpath
from os import makedirs
from concurrent.futures import ThreadPoolExecutor, Future

from google.cloud import storage
from google.oauth2 import service_account

from ..storage import Storage


class GCS(Storage):
    def __init__(self, storage_config: dict, project_name: str):
        key_file_path = storage_config["key_file_path"]
        backet_name = storage_config["backet_name"]
        try:
            credentials = service_account.Credentials.from_service_account_file(
                key_file_path
            )

            self.client = storage.Client(credentials=credentials)
            self.bucket_name = backet_name
        except FileNotFoundError:
            raise ValueError(f"Key file not found at {key_file_path}")

        self.project_dir = project_name

        self.max_workers = 10

    def get_info(self) -> tuple[str, str, str]:
        return {
            "project_dir": self.project_dir,
            "bucket_name": self.bucket_name,
        }

    def upload_experiment(self, zip_path: str):
        blob = self.client.bucket(self.bucket_name).blob(
            f"{self.project_dir}/{basename(zip_path)}"
        )
        blob = self.client.bucket(self.bucket_name).blob(
            f"{self.project_dir}/{basename(zip_path)}"
        )
        blob.upload_from_filename(zip_path)

    def download_experiment(self, zip_path: str):
        blob = self.client.bucket(self.bucket_name).blob(
            f"{self.project_dir}/{basename(zip_path)}"
        )
        blob.download_to_filename(zip_path)

    def get_all_experiment_names(self) -> list[str]:
        blobs = self.client.list_blobs(self.bucket_name, prefix=self.project_dir + "/")
        return [p.name.split("/")[-1][:-4] for p in blobs]

    def remove_experiment(self, ex_name: str):
        blob = self.client.bucket(self.bucket_name).blob(
            self.project_dir + "/" + ex_name + ".zip"
        )
        blob.delete()

    def change_comment(self, ex_name, new_comment):
        new_ex_name = f"{ex_name.split('_')[0]}_{ex_name.split('_')[1]}_{new_comment}"
        old_name = self.project_dir + "/" + ex_name + ".zip"
        new_name = self.project_dir + "/" + new_ex_name + ".zip"
        old_blob = self.client.bucket(self.bucket_name).blob(old_name)

        self.client.bucket(self.bucket_name).copy_blob(
            old_blob, self.client.bucket(self.bucket_name), new_name
        )
        old_blob.delete()

    def exist_experiment(self, ex_name: str) -> bool:
        return ex_name in self.get_all_experiment_names()
