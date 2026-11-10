class Storage:
    max_workers = 10

    def __init__(self, storage_config: dict, project_name: str):
        pass

    def get_info(self) -> dict:
        raise NotImplementedError

    def upload_experiment(self, zip_path: str):
        raise NotImplementedError

    def download_experiment(self, zip_path: str):
        raise NotImplementedError

    def get_all_experiment_names(self) -> list[str]:
        raise NotImplementedError

    def exist_experiment(self, ex_name: str) -> bool:
        return ex_name in self.get_all_experiment_names()

    def remove_experiment(self, ex_name: str):
        raise NotImplementedError

    def change_comment(self, ex_name: str, new_comment: str):
        raise NotImplementedError
