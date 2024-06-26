from os.path import join
import sys
from os.path import exists
from typing import Optional

import yaml

from .utils import parse_result_dirs


class ConfigYaml:
    def __init__(self, config_file_path=None):
        if config_file_path is None:
            return

        try:
            with open(config_file_path, "r") as f:
                conf = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"config file {config_file_path} does not exist.")

        self.project_name = conf["project_name"]
        self.results_dir = conf["results_dir"]
        self.storage_type = conf["storage_type"]
        self.storage_config = conf["storage_config"]

    def set_project_name(self, project_name: str):
        self.project_name = project_name

    def set_results_dir(self, results_dir: str):
        # check existence
        if not exists(results_dir):
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
        elif self.storage_type == "gs" or self.storage_type == "gs":
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

    def save(self, config_file_path):
        data = {
            "project_name": self.project_name,
            "results_dir": self.results_dir,
            "storage_type": self.storage_type,
            "storage_config": self.storage_config,
        }
        with open(config_file_path, "w") as stream:
            yaml.dump(data, stream)


def create_ex_yaml(
    dir: str,
    dependency: list[str] = [],
    commit_hash: Optional[str] = None,
    uncommited_files: list[str] = [],
):
    args = " ".join(sys.argv)
    data = {
        "args": args,
        "result_dir": dir,
        "dependency": dependency,
        "git": {
            "uncommited_files": uncommited_files,
            "commit_hash": commit_hash,
        },
    }
    with open(join(dir, "resutil-exp.yaml"), "w") as stream:
        yaml.dump(data, stream)
