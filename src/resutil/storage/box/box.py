from os.path import basename, join

from boxsdk import Client, JWTAuth, BoxAPIException
from boxsdk.object.folder import Folder

from ..storage import Storage


class Box(Storage):
    def __init__(self, storage_config: dict, project_name: str):
        super().__init__(storage_config, project_name)
        # set up the Box client
        key_file_path = storage_config["key_file_path"]
        try:
            auth = JWTAuth.from_settings_file(key_file_path)
        except FileNotFoundError:
            raise ValueError(f"Key file not found at {key_file_path}")
        self.client = Client(auth)

        # setup base folder
        self.base_folder = self._find_folder(storage_config["base_folder_id"])

        # set up project folder
        self.project_folder = self._find_subfolder_by_name(
            project_name, self.base_folder.id
        )
        if self.project_folder is None:
            self.project_folder = self.client.folder(
                self.base_folder.id
            ).create_subfolder(project_name)

        self.max_workers = 10

    def _find_folder(self, folder_id: str) -> Folder:
        try:
            return self.client.folder(folder_id).get()
        except BoxAPIException:
            raise ValueError(f"Folder with id {folder_id} not found")

    def _find_subfolder_by_name(self, name: str, folder_id: str):
        folders = self._get_folders_in(folder_id)
        for folder in folders:
            if folder.name == name:
                return folder
        return None

    def _get_folders_in(self, folder_id: str) -> list[Folder]:
        items = self.client.folder(folder_id).get_items()
        folders = []
        for item in items:
            if item.type == "folder":
                folders.append(item)
        return folders

    def get_info(self) -> dict:
        return {
            "base_folder_id": self.base_folder.id,
            "project_folder_id": self.project_folder.id,
            "project_folder_name": self.project_folder.name,
        }

    def upload_experiment(self, zip_path: str):
        self.client.folder(self.project_folder.id).upload(zip_path, basename(zip_path))

    def download_experiment(self, zip_path: str):
        filename = basename(zip_path)
        items = self.project_folder.get_items()
        for item in items:
            if item.name != filename:
                continue
            with open(zip_path, "wb") as f:
                f.write(item.content())

    def get_all_experiment_names(self) -> list[str]:
        items = self.client.folder(self.project_folder.id).get_items()
        folders = []
        for item in items:
            if item.type == "file" and item.name[-3:] == "zip":
                folders.append(item.name[:-4])
        return folders

    def remove_experiment(self, ex_name: str):
        items = self.client.folder(self.project_folder.id).get_items()
        for item in items:
            if item.name == ex_name + ".zip":
                self.client.file(item.id).delete()
                return
        raise ValueError(f"Experiment {ex_name} not found")

    def change_comment(self, ex_name, new_comment):
        items = self.client.folder(self.project_folder.id).get_items()
        new_ex_name = f"{ex_name.split('_')[0]}_{ex_name.split('_')[1]}_{new_comment}"

        for item in items:
            if item.name == ex_name + ".zip":
                self.client.file(item.id).rename(new_ex_name + ".zip")
                return
        raise ValueError(f"Experiment {ex_name} not found")

    def exist_experiment(self, ex_name: str) -> bool:
        return ex_name in self.get_all_experiment_names()
