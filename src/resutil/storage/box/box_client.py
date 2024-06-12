from os.path import basename, normpath, isfile, isdir, join
from os import makedirs
from glob import glob
from concurrent.futures import ThreadPoolExecutor, Future

from boxsdk import Client, JWTAuth, BoxAPIException
from boxsdk.object.folder import Folder
from boxsdk.object.item import Item


class BoxClient:
    def __init__(self, key_file_path: str):
        try:
            auth = JWTAuth.from_settings_file(key_file_path)
        except FileNotFoundError:
            raise ValueError(f"Key file not found at {key_file_path}")

        # self.access_token = auth.authenticate_instance()
        self.client = Client(auth)

    def create_folder(self, name: str, folder_id: str) -> Folder:
        new_folder = self.create_subfolder(name, folder_id)
        return new_folder

    def find_subfolder_by_name(self, name: str, folder_id: str) -> Folder:
        folders = self.get_folders_in(folder_id)
        for folder in folders:
            if folder.name == name:
                return folder
        return None

    def get_folders_in(self, folder_id: str) -> list[Folder]:
        items = self.client.folder(folder_id).get_items()
        folders = []
        for item in items:
            if item.type == "folder":
                folders.append(item)
        return folders

    def find_folder(self, folder_id: str) -> Folder:
        try:
            return self.client.folder(folder_id).get()
        except BoxAPIException:
            raise ValueError(f"Folder with id {folder_id} not found")

    def upload_recursively(
        self,
        local_dir: str,
        folder: Folder,
        executor: ThreadPoolExecutor,
        futures: list[Future] = [],
    ):
        local_items = glob(local_dir + "/*")
        for local_item in local_items:
            if isdir(local_item):
                subfolder_name = basename(normpath(local_item))
                subfolder = self.create_subfolder(subfolder_name, folder.id)
                self.upload_recursively(local_item, subfolder, executor, futures)
            elif isfile(local_item):
                future = executor.submit(
                    self.upload_file, local_item, folder.id, basename(local_item)
                )
                futures.append(future)

    def create_subfolder(self, name: str, folder_id: str) -> Folder:
        return self.client.folder(folder_id).create_subfolder(name)

    def upload_file(self, local_file_path: str, folder_id: str, name: str) -> None:
        self.client.folder(folder_id).upload(local_file_path, name)

    def download_recursively(
        self,
        folder: Folder,
        local_dir: str,
        executor: ThreadPoolExecutor,
        futures: list[Future] = [],
    ):
        items = self.client.folder(folder.id).get_items()
        for item in items:
            if item.type == "folder":
                subfolder_name = join(local_dir, item.name)
                makedirs(subfolder_name, exist_ok=True)
                self.download_recursively(item, subfolder_name, executor, futures)
            elif item.type == "file":
                future = executor.submit(self.download_file, item, local_dir)
                futures.append(future)
        return futures

    def download_file(self, item: Item, local_dir: str) -> None:
        with open(join(local_dir, item.name), "wb") as f:
            f.write(item.content())
        return item.name
