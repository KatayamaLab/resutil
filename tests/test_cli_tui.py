from types import SimpleNamespace
from unittest.mock import MagicMock
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import HTTPError
from threading import Thread

import httpx
import pytest

from resutil.cli import cli_main as cli
from resutil.cli.interactive import ResutilApp
from resutil.config_file import Config
from conftest import A


def test_rm_cancelled_before_connection(monkeypatch):
    monkeypatch.setattr(cli, "user_confirm", lambda *args, **kw: False)
    connect = MagicMock()
    monkeypatch.setattr(cli, "initialize", connect)
    cli.command_rm(
        SimpleNamespace(EXPERIMENT=[A], local=False, remote=False, yes=False)
    )
    connect.assert_not_called()


def test_add_invalid_comment(monkeypatch):
    monkeypatch.setattr(
        cli, "initialize", lambda **kw: (SimpleNamespace(results_dir="unused"), None)
    )
    with pytest.raises(ValueError):
        cli.command_add(SimpleNamespace(comment="invalid/path", dependency=None))


def test_login_ignores_unrelated_and_invalid_callbacks(tmp_path, monkeypatch):
    import resutil.storage.server.server as server

    monkeypatch.setattr(server, "CREDENTIALS_PATH", tmp_path / "credentials.json")
    browser_threads = []
    states = {}

    def login_response(url, *, params, **kw):
        states.update(params)
        return httpx.Response(
            200,
            json={
                "login_url": "https://example.test/signin?" + urlencode(params),
                "api_key": "key",
            },
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", login_response)

    def open_browser(url):
        def callbacks():
            base = f"http://localhost:{states['port']}"
            for path in [
                "/favicon.ico",
                "/callback?id_token=attacker&state=wrong",
                "/callback?"
                + urlencode(
                    {
                        "id_token": "valid",
                        "refresh_token": "refresh",
                        "state": states["state"],
                    }
                ),
            ]:
                try:
                    with urlopen(base + path, timeout=5) as response:
                        response.read()
                except HTTPError:
                    pass

        thread = Thread(target=callbacks)
        thread.start()
        browser_threads.append(thread)

    monkeypatch.setattr(cli.webbrowser, "open", open_browser)
    cli.command_login(SimpleNamespace(server_url="https://example.test"))
    for thread in browser_threads:
        thread.join(timeout=5)
        assert not thread.is_alive()
    assert server._load_credentials()["id_token"] == "valid"


def test_login_rejects_old_server_without_state(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "get",
        lambda url, **kw: httpx.Response(
            200,
            json={"login_url": "https://example.test/signin"},
            request=httpx.Request("GET", url),
        ),
    )
    browser = MagicMock()
    monkeypatch.setattr(cli.webbrowser, "open", browser)
    with pytest.raises(RuntimeError, match="state"):
        cli.command_login(SimpleNamespace(server_url="https://example.test"))
    browser.assert_not_called()


def test_tui_network_error(tmp_path, storage, monkeypatch):
    import asyncio

    config = Config()
    config.project_name = "test"
    config.results_dir = str(tmp_path)
    monkeypatch.setattr(
        storage, "get_all_experiment_names", MagicMock(side_effect=OSError("offline"))
    )
    monkeypatch.setattr(
        ResutilApp, "_detect_theme", staticmethod(lambda: "resutil-dark")
    )
    app = ResutilApp(config, storage)

    async def exercise():
        async with app.run_test() as pilot:
            app._after_error("upload failed")
            await pilot.pause()
            assert app._remote_available is False
            assert app.is_running

    asyncio.run(exercise())
