import yaml
from git import Repo

from resutil.config_file import Config
from resutil.git import GitRepo


def test_config_preserves_cwd_and_resolves_paths(tmp_path, monkeypatch):
    config = {
        "project_name": "test",
        "results_dir": "results",
        "storage_type": "gcs",
        "storage_config": {"bucket_name": "test", "key_file_path": "key.json"},
    }
    (tmp_path / "resutil-conf.yaml").write_text(
        yaml.safe_dump(config), encoding="utf-8"
    )
    child = tmp_path / "child"
    child.mkdir()
    monkeypatch.chdir(child)
    loaded = Config()
    loaded.load()
    from pathlib import Path

    assert Path.cwd() == child
    assert loaded.results_dir == str(tmp_path / "results")
    assert loaded.storage_config["key_file_path"] == str(tmp_path / "key.json")


def test_git_without_repository(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert GitRepo().get_git_info() == (None, [])


def test_unborn_repository_and_untracked_files(tmp_path, monkeypatch):
    repo = Repo.init(tmp_path)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "new.py").write_text("print(1)", encoding="utf-8")
    snapshot = GitRepo()
    commit, files = snapshot.get_git_info()
    assert commit is None and files == ["new.py"]
    repo.index.add(["new.py"])
    (tmp_path / "new.py").unlink()
    assert snapshot.get_git_info() == (None, [])
    assert snapshot.deleted_files == ["new.py"]


def test_git_deleted_and_untracked_after_commit(tmp_path, monkeypatch):
    repo = Repo.init(tmp_path)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "old.py").write_text("old", encoding="utf-8")
    repo.index.add(["old.py"])
    repo.index.commit("initial")
    (tmp_path / "old.py").unlink()
    (tmp_path / "new.py").write_text("new", encoding="utf-8")
    snapshot = GitRepo()
    commit, files = snapshot.get_git_info()
    assert commit and files == ["new.py"]
    assert snapshot.deleted_files == ["old.py"]


def test_snapshot_excludes_results(tmp_path, monkeypatch):
    Repo.init(tmp_path)
    monkeypatch.chdir(tmp_path)
    results = tmp_path / "results"
    results.mkdir()
    (results / "large-result").write_text("data", encoding="utf-8")
    (tmp_path / "main.py").write_text("pass", encoding="utf-8")
    _, files = GitRepo().get_git_info(exclude_paths=[results])
    assert files == ["main.py"]
