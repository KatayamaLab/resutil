from pathlib import Path
import zipfile

import pytest
import yaml

from resutil.storage import Storage

A = "aaaaaa_20240101T000000_A"
B = "aaaaab_20240101T000001_B"
C = "aaaaac_20240101T000002_C"


class MemoryStorage(Storage):
    def __init__(self):
        self.archives = {}
        self.downloads = []
        self.fail_upload = False

    def get_info(self):
        return {"destination": "test"}

    def upload_experiment(self, zip_path):
        if self.fail_upload:
            raise OSError("network unavailable")
        self.archives[Path(zip_path).stem] = Path(zip_path).read_bytes()

    def download_experiment(self, zip_path):
        name = Path(zip_path).stem
        self.downloads.append(name)
        if name not in self.archives:
            raise FileNotFoundError(name)
        Path(zip_path).write_bytes(self.archives[name])

    def get_all_experiment_names(self):
        return list(self.archives)

    def remove_experiment(self, name):
        del self.archives[name]


@pytest.fixture
def storage():
    return MemoryStorage()


@pytest.fixture
def experiment(tmp_path):
    def make(name=A, deps=(), root=None):
        directory = (Path(root) if root else tmp_path / "results") / name
        directory.mkdir(parents=True, exist_ok=True)
        data = {"dependency": list(deps), "result_dir": str(directory)}
        (directory / "resutil-exp.yaml").write_text(
            yaml.safe_dump(data), encoding="utf-8"
        )
        (directory / "data.txt").write_text("valuable result", encoding="utf-8")
        return directory

    return make


def archive_metadata(content):
    import io

    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        return yaml.safe_load(archive.read("resutil-exp.yaml"))
