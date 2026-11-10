import io
import zipfile
import pytest

from resutil import core
from resutil.ex_dir import find_unuploaded_ex_dirs, find_undownloaded_ex_dirs
from resutil.sync import is_synced
from conftest import A, B, C, archive_metadata


def test_missing_upload_does_not_overwrite(tmp_path, storage):
    storage.archives[A] = b"valuable data"
    with pytest.raises(FileNotFoundError):
        core.upload(A, tmp_path, storage)
    assert storage.archives[A] == b"valuable data"


def test_upload_errors_propagate(experiment, storage):
    a = experiment()
    storage.fail_upload = True
    with pytest.raises(OSError, match="network"):
        core.upload_with_dependency(A, a.parent, storage)
    with pytest.raises(OSError):
        core.upload_all([A], a.parent, storage)


def test_legacy_dependency_graph(experiment, storage, tmp_path):
    a = experiment(A)
    experiment(B, [str(a)])
    experiment(C, [f"results/{B}"])
    core.upload_with_dependency(C, a.parent, storage)
    assert set(storage.archives) == {A, B, C}
    root = tmp_path / "download"
    core.download_with_dependency(C, root, storage)
    assert all((root / name / "data.txt").exists() for name in (A, B, C))
    assert set(storage.downloads) == {A, B, C}


def test_cycle(experiment, storage, tmp_path):
    a = experiment(A, [B])
    experiment(B, [A])
    core.upload_with_dependency(A, a.parent, storage)
    core.download_with_dependency(A, tmp_path / "download", storage)
    assert storage.downloads.count(A) == storage.downloads.count(B) == 1


def test_checkpoint_changes_are_dirty(experiment, storage):
    a = experiment()
    core.upload(A, a.parent, storage)
    assert is_synced(a.parent, A, storage)
    assert find_unuploaded_ex_dirs(a.parent, storage) == []
    (a / "data.txt").write_text("final result", encoding="utf-8")
    assert find_unuploaded_ex_dirs(a.parent, storage) == [A]
    storage.fail_upload = True
    with pytest.raises(OSError):
        core.upload(A, a.parent, storage)
    assert not is_synced(a.parent, A, storage)
    storage.fail_upload = False
    core.upload(A, a.parent, storage)
    assert find_unuploaded_ex_dirs(a.parent, storage) == []


@pytest.mark.parametrize("name", [".", "..", "../outside", "/tmp/outside"])
def test_remove_rejects_unsafe_names(tmp_path, name):
    with pytest.raises(ValueError):
        core.remove_local([name], tmp_path)


def test_remove_rejects_symlink(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    results = tmp_path / "results"
    results.mkdir()
    try:
        (results / A).symlink_to(outside, target_is_directory=True)
    except OSError:
        import os

        if os.name == "nt":
            pytest.skip("Windows runner does not allow creating symlinks.")
        raise
    with pytest.raises(ValueError):
        core.remove_local([A], results)
    assert outside.exists()


def test_failed_download_leaves_no_partial_directory(tmp_path, storage):
    storage.archives[A] = b"corrupt"
    with pytest.raises(zipfile.BadZipFile):
        core.download(A, tmp_path, storage)
    assert not (tmp_path / A).exists()
    assert find_undownloaded_ex_dirs(tmp_path, storage) == [A]


def test_zip_traversal(tmp_path):
    content = io.BytesIO()
    with zipfile.ZipFile(content, "w") as archive:
        archive.writestr("../outside", "bad")
    content.seek(0)
    with pytest.raises(ValueError):
        core.unzip_file(content, tmp_path / "extract")
    assert not (tmp_path / "outside").exists()


def test_missing_pull_is_clear(tmp_path, storage):
    with pytest.raises(FileNotFoundError, match="Remote experiment"):
        core.download_with_dependency(A, tmp_path, storage)


def test_rename_updates_remote_and_local_dependencies(experiment, storage):
    a = experiment(A)
    b = experiment(B, [f"results/{A}"])
    core.upload_with_dependency(B, a.parent, storage)
    new = core.change_experiment_comment(a.parent, A, "new", storage)
    assert A not in storage.archives and new in storage.archives
    assert archive_metadata(storage.archives[B])["dependency"] == [new]
    assert archive_metadata(storage.archives[new])["result_dir"] == new
    assert (a.parent / new).is_dir()
    assert b.exists()


def test_failed_rename_preserves_original(experiment, storage):
    a = experiment(A)
    core.upload(A, a.parent, storage)
    original = storage.archives[A]
    storage.fail_upload = True
    with pytest.raises(OSError):
        core.change_experiment_comment(a.parent, A, "new", storage)
    assert storage.archives[A] == original and a.is_dir()


def test_rename_remote_only_target_updates_local_references(experiment, storage):
    import shutil
    import yaml

    a = experiment(A)
    core.upload(A, a.parent, storage)
    shutil.rmtree(a)
    b = experiment(B, [f"results/{A}"])
    new_name = core.change_experiment_comment(a.parent, A, "new", storage)
    data = yaml.safe_load((b / "resutil-exp.yaml").read_text(encoding="utf-8"))
    assert data["dependency"] == [new_name]
    assert data["result_dir"] == str(b)
    assert new_name in storage.archives
