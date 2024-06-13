from os.path import basename, normpath, isfile, isdir, join, dirname
from os import makedirs
from glob import glob
from concurrent.futures import ThreadPoolExecutor, Future

from google.cloud import storage
from google.oauth2 import service_account


class GSClient:
    def __init__(
        self,
        key_file_path: str,
        backet_name: str,
    ):
        try:
            credentials = service_account.Credentials.from_service_account_file(
                key_file_path
            )

            self.client = storage.Client(credentials=credentials)
            self.bucket = self.client.get_bucket(backet_name)
        except FileNotFoundError:
            raise ValueError(f"Key file not found at {key_file_path}")

    def create_folder(self, name: str, folder_id: str):
        new_folder = self.create_subfolder(name, folder_id)
        return new_folder

    def find_subfolder_by_name(self, name: str, folder_path: str):
        folders = self.get_folders_in(folder_path)
        for folder in folders:
            if folder == name:
                return folder

        return None

    def get_folders_in(self, folder_path: str):
        iter = self.client.list_blobs(
            self.bucket, prefix=folder_path + "/", delimiter="/"
        )
        prefixes = set()
        for page in iter.pages:
            prefixes.update(page.prefixes)
        return [p.split("/")[-2] for p in prefixes]

    def find_folder(self, folder_id: str):
        try:
            return self.client.folder(folder_id).get()
        except BoxAPIException:
            raise ValueError(f"Folder with id {folder_id} not found")

    def upload_recursively(
        self,
        local_dir: str,
        dir_name: str,
        executor: ThreadPoolExecutor,
        futures: list[Future] = [],
    ):

        local_items = glob(local_dir + "/*")
        for local_item in local_items:
            if isdir(local_item):
                subdir_name = f"{dir_name}/{basename(normpath(local_item))}"
                self.upload_recursively(local_item, subdir_name, executor, futures)
            elif isfile(local_item):
                path = f"{dir_name}/{basename(local_item)}"
                future = executor.submit(self.upload_file, local_item, path)
                futures.append(future)

    def upload_file(self, local_file_path: str, path: str) -> None:
        blob = self.bucket.blob(f"{path}")
        blob.upload_from_filename(local_file_path)

    def download_recursively(
        self,
        dir_name: str,
        local_dir: str,
        executor: ThreadPoolExecutor,
        futures: list[Future] = [],
    ):
        blobs = self.bucket.list_blobs(prefix=dir_name)
        for blob in blobs:
            future = executor.submit(self.download_file, blob, local_dir, dir_name)
            futures.append(future)
        return futures

    def download_file(self, blob, local_dir: str, prefix) -> None:
        dir = dirname(join(local_dir, blob.name[len(prefix) + 1 :]))
        makedirs(dir, exist_ok=True)
        blob.download_to_filename(join(local_dir, blob.name[len(prefix) + 1 :]))
