from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import yaml
import pytest

from resutil.ex_dir import create_ex_dir, delete_ex_dir, change_comment
from conftest import A, B


def test_create_and_collision(tmp_path):
    now = datetime(2024, 1, 1, tzinfo=timezone.utc)
    with ThreadPoolExecutor(4) as pool:
        names = list(
            pool.map(lambda _: create_ex_dir(now, "test", str(tmp_path)), range(4))
        )
    assert len(set(names)) == 4
    assert "aaaaaa_20240101T000000_test" in names


def test_delete(tmp_path):
    path = tmp_path / A
    path.mkdir()
    assert delete_ex_dir(path)
    with pytest.raises(FileNotFoundError):
        delete_ex_dir(path)


def test_comment_updates_dependencies(experiment):
    a = experiment(A)
    b = experiment(B, [str(a)])
    new = change_comment(a.parent, A, "new_comment")
    assert new.endswith("_new_comment")
    assert not a.exists()
    metadata = yaml.safe_load((b / "resutil-exp.yaml").read_text(encoding="utf-8"))
    assert metadata["dependency"] == [new]
    own = yaml.safe_load(
        (a.parent / new / "resutil-exp.yaml").read_text(encoding="utf-8")
    )
    assert own["result_dir"] == new


def test_rename_rolls_back_on_metadata_failure(experiment, monkeypatch):
    from resutil import ex_dir

    a = experiment(A)
    b = experiment(B, [A])
    originals = {
        path: path.read_text(encoding="utf-8")
        for path in (a / "resutil-exp.yaml", b / "resutil-exp.yaml")
    }
    writer = ex_dir.write_yaml
    calls = []

    def fail_second(path, data):
        calls.append(path)
        if len(calls) == 2:
            raise OSError("disk error")
        writer(path, data)

    monkeypatch.setattr(ex_dir, "write_yaml", fail_second)
    with pytest.raises(OSError):
        change_comment(a.parent, A, "new")
    assert a.is_dir()
    assert all(
        path.read_text(encoding="utf-8") == text for path, text in originals.items()
    )
