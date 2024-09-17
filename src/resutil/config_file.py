import os
import sys
from pathlib import Path
from typing import Optional


import yaml

CONFIG_FILE_NAME = "resutil-conf.yaml"


class Config:
    def __init__(self):
        self.current_dir = Path.cwd()

    def load(self):
        # serch config file from current dir to root dir
        for parent in [self.current_dir, *self.current_dir.parents]:
            config_file_path = Path(parent, CONFIG_FILE_NAME)
            if config_file_path.exists():
                self.config_file_dir = parent
                os.chdir(parent)
                break
        try:
            with config_file_path.open("r") as f:
                conf = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"config file {config_file_path} does not exist.")

        self.project_name: str = conf["project_name"]
        self.results_dir: str = conf["results_dir"]
        self.storage_type: str = conf["storage_type"]
        self.storage_config: str = conf["storage_config"]

    def set_project_name(self, project_name: str):
        self.project_name = project_name

    def set_results_dir(self, results_dir: str):
        # check existence
        if not Path(results_dir).exists():
            raise ValueError(f"results_dir {results_dir} does not exist.")
        self.results_dir = results_dir

    def set_storage_type(self, storage_type: str):
        if storage_type not in ["box", "gs", "gcs", "gdrive"]:
            raise ValueError("storage_type must be 'local', 'box', 'gcs' or 'gdrive'")
        self.storage_type = storage_type

    def set_storage_config(self, storage_config):
        # check storage_config is valid
        if self.storage_type == "box":
            if "key_file_path" not in storage_config:
                raise ValueError("storage_config must have 'key_file_path' key")
            if "base_folder_id" not in storage_config:
                raise ValueError("storage_config must have 'base_folder_id' key")
        elif self.storage_type == "gs" or self.storage_type == "gcs":
            if "key_file_path" not in storage_config:
                raise ValueError("storage_config must have 'key_file_path' key")
            if "backet_name" not in storage_config:
                raise ValueError("storage_config must have 'base_folder_id' key")
        elif self.storage_type == "gdrive":
            if "key_file_path" not in storage_config:
                raise ValueError("storage_config must have 'key_file_path' key")
            if "base_folder_id" not in storage_config:
                raise ValueError("storage_config must have 'base_folder_id' key")
        else:
            raise ValueError("storage_type must be 'box'")
        self.storage_config = storage_config

    def save(self):
        data = {
            "project_name": self.project_name,
            "results_dir": self.results_dir,
            "storage_type": self.storage_type,
            "storage_config": self.storage_config,
        }
        with open(CONFIG_FILE_NAME, "w") as stream:
            yaml.dump(data, stream)


def create_ex_yaml(
    dir: str,
    dependencies: list[Path] = [],
    commit_hash: Optional[str] = None,
    uncommited_files: list[str] = [],
):
    args = " ".join(sys.argv)
    data = {
        "args": args,
        "result_dir": dir,
        "dependency": [str(dependency) for dependency in dependencies],
        "git": {
            "uncommited_files": uncommited_files,
            "commit_hash": commit_hash,
        },
    }
    with Path(dir, "resutil-exp.yaml").open("w") as stream:
        yaml.dump(data, stream, width=10000, allow_unicode=True)
