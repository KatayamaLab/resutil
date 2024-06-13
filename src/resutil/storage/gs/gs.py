from os.path import basename, normpath
from os import makedirs
from concurrent.futures import ThreadPoolExecutor, Future

from .gs_client import GSClient


class GS:
    def __init__(self, storage_config: dict, project_name: str):
        self.client = GSClient(
            storage_config["key_file_path"], storage_config["backet_name"]
        )

        # self.base_dir = self.client.find_folder(storage_config["backet_name"])

        self.project_folder = project_name
        # if self.project_folder is None:
        #     self.project_folder = self.client.create_folder(
        #         project_name, self.base_dir.id
        #     )

        self.project_name = project_name

    def get_info(self) -> tuple[str, str, str]:
        return self.project_folder

    def upload_experiment(
        self, local_ex_path: str, callback, executor: ThreadPoolExecutor
    ) -> None:
        """Uploads a folder and its contents to Box.

        Args:
            local_ex_path (str): path to the folder to be uploaded
        """
        if (
            self.client.find_subfolder_by_name(
                basename(local_ex_path), self.project_folder
            )
            is not None
        ):
            return None

        ex_dir_name = basename(normpath(local_ex_path))
        callback(ex_dir_name)

        futures = []
        path = f"{self.project_name}/{ex_dir_name}"
        self.client.upload_recursively(local_ex_path, path, executor, futures)
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

        futures = []
        path = f"{self.project_name}/{ex_dir_name}"
        self.client.download_recursively(path, local_ex_path, executor, futures)
        return futures

    def get_all_experiment_names(self) -> list[str]:
        """Get all experiment names in the project folder.

        Returns:
            list[str]: List of experiment names
        """
        folders = self.client.get_folders_in(self.project_folder)
        return folders
