from pathlib import Path

import yaml

from .utils import normalize_dependency


class ExpFile:
    def __init__(self, exp_file_path=None):
        self.dependency: list[str] = []
        if exp_file_path is None:
            return
        with Path(exp_file_path).open(encoding="utf-8") as stream:
            conf = yaml.safe_load(stream) or {}
        self.dependency = list(
            dict.fromkeys(normalize_dependency(d) for d in conf.get("dependency", []))
        )
