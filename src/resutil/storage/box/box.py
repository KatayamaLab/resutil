from os.path import basename, normpath
from os import makedirs
from concurrent.futures import ThreadPoolExecutor, Future

from .box_client import BoxClient


class Box:
    def __init__(self, storage_config: dict, project_name: str):
        self.client = BoxClient(storage_config["key_file_path"])

        self.base_dir = self.client.find_folder(storage_config["base_dir_id"])

        self.project_folder = self.client.find_subfolder_by_name(
            project_name, self.base_dir.id
        )
        if self.project_folder is None:
            self.project_folder = self.client.create_folder(
                project_name, self.base_dir.id
            )

    def get_info(self) -> tuple[str, str, str]:
        return (
            self.base_dir.name,
            self.project_folder.name,
        )

    def upload_experiment(
        self, local_ex_path: str, callback, executor: ThreadPoolExecutor
    ) -> None:
        """Uploads a folder and its contents to Box.

        Args:
            local_ex_path (str): path to the folder to be uploaded
        """
        ex_dir_name = basename(normpath(local_ex_path))
        callback(ex_dir_name)
        ex_dir = self.client.create_subfolder(ex_dir_name, self.project_folder.id)

        futures = []
        self.client.upload_recursively(local_ex_path, ex_dir, executor, futures)
        return futures

    def download_experiment(
        self, local_ex_path: str, callback, executor: ThreadPoolExecutor
    ) -> Future:
        """Downloads a folder and its contents to Box.

        Args:
            local_ex_path (str): path to the folder to be uploaded
        """
        ex_dir_name = basename(normpath(local_ex_path))
        callback(ex_dir_name)
        makedirs(local_ex_path, exist_ok=True)
        ex_dir = self.client.find_subfolder_by_name(ex_dir_name, self.project_folder.id)

        futures = []
        self.client.download_recursively(ex_dir, local_ex_path, executor, futures)
        return futures

    def get_all_experiment_names(self) -> list[str]:
        """Get all experiment names in the project folder.

        Returns:
            list[str]: List of experiment names
        """
        folders = self.client.get_folders_in(self.project_folder.id)
        return [folder.name for folder in folders]
