import importlib
from types import SimpleNamespace
import pytest

m = importlib.import_module("resutil.main")


@pytest.fixture
def runtime(tmp_path, monkeypatch, storage):
    config = SimpleNamespace(results_dir=str(tmp_path / "results"))
    monkeypatch.setattr(
        m, "initialize", lambda **kw: (config, storage if kw.get("connect") else None)
    )
    monkeypatch.setattr(
        m, "GitRepo", lambda: SimpleNamespace(get_git_info=lambda **kw: (None, []))
    )
    monkeypatch.setattr(m.sys, "argv", ["example.py"])
    monkeypatch.setenv("RESUTIL_NO_INTERACTIVE", "1")
    return config, storage


def test_return_value_and_upload(runtime):
    config, storage = runtime

    @m.main()
    def run(params):
        return 42

    assert run() == 42
    assert len(storage.archives) == 1


@pytest.mark.parametrize(
    "flag", ["RESUTIL_NO_REMOTE", "RESUTIIL_REMOTE", "RESUTIL_DEBUG"]
)
def test_offline_checkpoint(runtime, monkeypatch, flag):
    _, storage = runtime
    monkeypatch.setenv(flag, "1")

    @m.main()
    def run(params):
        assert params.save_checkpoint() is False
        return params.ex_dir

    directory = run()
    assert not storage.archives
    if flag == "RESUTIL_DEBUG":
        from pathlib import Path

        assert not Path(directory).exists()


def test_checkpoint_failure_does_not_abort(runtime):
    _, storage = runtime

    @m.main()
    def run(params):
        storage.fail_upload = True
        assert params.save_checkpoint() is False
        storage.fail_upload = False
        return "completed"

    assert run() == "completed"


@pytest.mark.parametrize("interactive", [True, False])
def test_user_error_preserved_and_results_uploaded(runtime, monkeypatch, interactive):
    if interactive:
        monkeypatch.delenv("RESUTIL_NO_INTERACTIVE")
        monkeypatch.setattr(m, "get_comment", lambda *a: "")
        monkeypatch.setattr(m, "user_confirm", lambda *a, **k: False)

    @m.main()
    def run(params):
        raise ValueError("user error")

    with pytest.raises(ValueError, match="user error"):
        run()
    assert runtime[1].archives


def test_upload_failure_is_failure(runtime):
    runtime[1].fail_upload = True

    @m.main()
    def run(params):
        return "ok"

    with pytest.raises(OSError):
        run()


def test_system_exit_uploads(runtime):
    @m.main()
    def run(params):
        raise SystemExit(3)

    with pytest.raises(SystemExit) as error:
        run()
    assert error.value.code == 3
    assert runtime[1].archives


def test_interrupt_delete(runtime, monkeypatch):
    monkeypatch.delenv("RESUTIL_NO_INTERACTIVE")
    monkeypatch.setattr(m, "get_comment", lambda *a: "")
    monkeypatch.setattr(m, "user_confirm", lambda *a, **kw: True)

    @m.main()
    def run(params):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        run()
    assert not list(__import__("pathlib").Path(runtime[0].results_dir).iterdir())
    assert not runtime[1].archives


def test_invalid_environment_comment(runtime, monkeypatch):
    monkeypatch.setenv("RESUTIL_COMMENT", "../invalid")

    @m.main()
    def run(params):
        pytest.fail("must not execute")

    with pytest.raises(ValueError, match="RESUTIL_COMMENT"):
        run()


@pytest.fixture
def offline_start(tmp_path, monkeypatch, runtime):
    config, storage = runtime

    def initialize(connect=True):
        if connect:
            raise m.StorageOfflineError("Cannot reach server storage")
        return config, None

    monkeypatch.setattr(m, "initialize", initialize)
    return config, storage


def test_offline_at_start_runs_locally(offline_start, capsys):
    config, storage = offline_start

    @m.main()
    def run(params):
        assert params.save_checkpoint() is False
        return params.ex_dir

    from pathlib import Path

    directory = run()
    assert Path(directory).is_dir()
    assert not storage.archives
    out = capsys.readouterr().out
    assert "offline mode" in out
    assert "resutil push" in out


def test_auth_error_at_start_stops(runtime, monkeypatch):
    def initialize(connect=True):
        raise PermissionError("Run 'resutil login' again.")

    monkeypatch.setattr(m, "initialize", initialize)

    @m.main()
    def run(params):
        pytest.fail("must not execute")

    with pytest.raises(PermissionError):
        run()


def test_network_failure_on_final_upload_is_not_fatal(runtime, monkeypatch, capsys):
    _, storage = runtime

    def unreachable(zip_path):
        raise ConnectionError("getaddrinfo failed")

    monkeypatch.setattr(storage, "upload_experiment", unreachable)

    @m.main()
    def run(params):
        assert params.save_checkpoint() is False
        return "ok"

    assert run() == "ok"
    assert "resutil push" in capsys.readouterr().out


def test_network_failure_after_user_error_keeps_user_error(runtime, monkeypatch):
    _, storage = runtime

    def unreachable(zip_path):
        raise ConnectionError("getaddrinfo failed")

    monkeypatch.setattr(storage, "upload_experiment", unreachable)

    @m.main()
    def run(params):
        raise ValueError("user error")

    with pytest.raises(ValueError, match="user error"):
        run()


def test_missing_dependency_offline_does_not_run(offline_start, monkeypatch):
    config, _ = offline_start
    from pathlib import Path

    from conftest import A

    monkeypatch.setattr(
        m.sys, "argv", ["example.py", str(Path(config.results_dir) / A / "x.npy")]
    )

    @m.main()
    def run(params):
        pytest.fail("must not execute")

    with pytest.raises(FileNotFoundError, match="offline") as info:
        run()
    assert A in str(info.value)
    assert not Path(config.results_dir).exists() or not any(
        Path(config.results_dir).iterdir()
    )


def test_dependency_download_network_failure_does_not_run(runtime, monkeypatch):
    config, storage = runtime
    from pathlib import Path

    from conftest import A

    monkeypatch.setattr(
        m.sys, "argv", ["example.py", str(Path(config.results_dir) / A / "x.npy")]
    )

    def unreachable(*args):
        raise ConnectionError("getaddrinfo failed")

    monkeypatch.setattr(m, "download_with_dependency", unreachable)

    @m.main()
    def run(params):
        pytest.fail("must not execute")

    with pytest.raises(m.StorageOfflineError, match=A):
        run()
