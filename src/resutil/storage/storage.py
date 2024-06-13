class Storage:
    def __init__(self, storage_config: dict, project_name: str):
        pass

    def get_info(self) -> dict:
        return {}

    def upload_experiment(self, zip_path: str):
        pass

    def download_experiment(self, zip_path: str):
        pass

    def get_all_experiment_names(self) -> list[str]:
        pass
