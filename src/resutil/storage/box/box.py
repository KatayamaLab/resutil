from os.path import basename, join

from boxsdk import Client, JWTAuth, BoxAPIException
from boxsdk.object.folder import Folder


class Box:
    def __init__(self, storage_config: dict, project_name: str):
        key_file_path = storage_config["key_file_path"]
        try:
            auth = JWTAuth.from_settings_file(key_file_path)
        except FileNotFoundError:
            raise ValueError(f"Key file not found at {key_file_path}")

        self.client = Client(auth)

        self.base_dir = self._find_folder(storage_config["base_dir_id"])

        self.project_folder = self._find_subfolder_by_name(
            project_name, self.base_dir.id
        )
        if self.project_folder is None:
            self.project_folder = self.client.folder(self.base_dir.id).create_subfolder(
                project_name
            )

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

    def get_info(self) -> tuple[str, str, str]:
        return (
            self.base_dir.name,
            self.project_folder.name,
        )

    def upload_experiment(self, zip_path: str):
        self.client.folder(self.project_folder.id).upload(zip_path, basename(zip_path))

    def download_experiment(self, ex_name: str, zip_path: str):
        filename = ex_name + ".zip"
        items = self.project_folder.get_items()
        for item in items:
            if item.name != filename:
                continue
            with open(join(zip_path, filename), "wb") as f:
                f.write(item.content())

    def get_all_experiment_names(self) -> list[str]:
        items = self.client.folder(self.project_folder.id).get_items()
        folders = []
        for item in items:
            if item.type == "file" and item.name[-3:] == "zip":
                folders.append(item.name[:-4])
        return folders
