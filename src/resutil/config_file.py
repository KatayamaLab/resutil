import os
import sys
from pathlib import Path
from typing import Optional, Iterable

from .utils import normalize_dependency, write_yaml


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
                break
        try:
            with config_file_path.open("r", encoding="utf-8") as f:
                conf = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"config file {config_file_path} does not exist.")

        self.project_name: str = conf["project_name"]
        self.results_dir: str = str(
            (self.config_file_dir / conf["results_dir"]).resolve()
        )
        self.storage_type: str = conf["storage_type"]
        self.storage_config: dict = dict(conf["storage_config"])

        self._apply_env_overrides()
        if self.storage_config.get("key_file_path"):
            self.storage_config["key_file_path"] = str(
                (self.config_file_dir / self.storage_config["key_file_path"]).resolve()
            )

    def _apply_env_overrides(self):
        storage_type = os.environ.get("RESUTIL_STORAGE_TYPE")
        if storage_type:
            self.storage_type = storage_type

        if self.storage_type in ("gs", "gcs"):
            bucket_name = os.environ.get("RESUTIL_GCS_BUCKET_NAME")
            if bucket_name:
                if "bucket_name" in self.storage_config:
                    self.storage_config["bucket_name"] = bucket_name
                if "backet_name" in self.storage_config:
                    self.storage_config["backet_name"] = bucket_name
                if (
                    "bucket_name" not in self.storage_config
                    and "backet_name" not in self.storage_config
                ):
                    self.storage_config["bucket_name"] = bucket_name

            key_file_path = os.environ.get("RESUTIL_GCS_KEY_FILE_PATH")
            if key_file_path:
                self.storage_config["key_file_path"] = key_file_path

    def set_project_name(self, project_name: str):
        self.project_name = project_name

    def set_results_dir(self, results_dir: str):
        # check existence
        if not Path(results_dir).exists():
            raise ValueError(f"results_dir {results_dir} does not exist.")
        self.results_dir = results_dir

    def set_storage_type(self, storage_type: str):
        if storage_type not in ["gs", "gcs", "gdrive", "server"]:
            raise ValueError("storage_type must be 'gcs', 'gdrive' or 'server'")
        self.storage_type = storage_type

    def set_storage_config(self, storage_config):
        # check storage_config is valid
        if self.storage_type == "gs" or self.storage_type == "gcs":
            if "key_file_path" not in storage_config:
                raise ValueError("storage_config must have 'key_file_path' key")
            if (
                "bucket_name" not in storage_config
                and "backet_name" not in storage_config
            ):
                raise ValueError("storage_config must have 'bucket_name' key")
        elif self.storage_type == "gdrive":
            if "key_file_path" not in storage_config:
                raise ValueError("storage_config must have 'key_file_path' key")
            if "base_folder_id" not in storage_config:
                raise ValueError("storage_config must have 'base_folder_id' key")
        elif self.storage_type == "server":
            if "server_url" not in storage_config:
                raise ValueError("storage_config must have 'server_url' key")
            if "bucket_name" not in storage_config:
                raise ValueError("storage_config must have 'bucket_name' key")
        else:
            raise ValueError("storage_type must be 'gcs', 'gdrive' or 'server'")
        self.storage_config = storage_config

    def save(self):
        data = {
            "project_name": self.project_name,
            "results_dir": self.results_dir,
            "storage_type": self.storage_type,
            "storage_config": self.storage_config,
        }
        with open(CONFIG_FILE_NAME, "w", encoding="utf-8") as stream:
            yaml.dump(data, stream)


def create_ex_yaml(
    dir: str,
    dependencies: Optional[Iterable] = None,
    commit_hash: Optional[str] = None,
    uncommited_files: Optional[list[str]] = None,
    *,
    deleted_files=None,
    comment=None,
    started_at=None,
):
    args = " ".join(sys.argv)
    data = {
        "args": args,
        "result_dir": Path(dir).name,
        "comment": comment,
        "started_at": started_at,
        "dependency": [
            normalize_dependency(dependency) for dependency in (dependencies or [])
        ],
        "git": {
            "uncommited_files": uncommited_files or [],
            "deleted_files": deleted_files or [],
            "commit_hash": commit_hash,
        },
    }
    write_yaml(Path(dir, "resutil-exp.yaml"), data)
