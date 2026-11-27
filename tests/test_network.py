import socket

import httpx
import pytest

from resutil import core
from resutil.network import StorageOfflineError, is_network_error


def chained(outer, inner):
    try:
        try:
            raise inner
        except Exception as exc:
            raise outer from exc
    except Exception as exc:
        return exc


@pytest.mark.parametrize(
    "exc",
    [
        httpx.ConnectError("getaddrinfo failed"),
        httpx.ReadTimeout("timeout"),
        socket.gaierror(11001, "getaddrinfo failed"),
        ConnectionRefusedError(),
        TimeoutError(),
        chained(RuntimeError("wrapped"), httpx.ConnectError("down")),
    ],
)
def test_network_errors(exc):
    assert is_network_error(exc)


@pytest.mark.parametrize(
    "exc",
    [
        PermissionError("Run 'resutil login'"),
        chained(PermissionError("auth"), httpx.ConnectError("down")),
        httpx.HTTPStatusError(
            "500",
            request=httpx.Request("GET", "https://x.test"),
            response=httpx.Response(500),
        ),
        OSError("disk full"),
        FileNotFoundError("key.json"),
        ValueError("config"),
    ],
)
def test_non_network_errors(exc):
    assert not is_network_error(exc)


class FakeConfig:
    storage_type = "server"

    def load(self):
        pass


@pytest.mark.parametrize(
    "error, expected",
    [
        (httpx.ConnectError("getaddrinfo failed"), StorageOfflineError),
        (PermissionError("Run 'resutil login'"), PermissionError),
    ],
)
def test_initialize_classifies_failures(monkeypatch, error, expected):
    monkeypatch.setattr(core, "Config", FakeConfig)

    def fail(config):
        raise error

    monkeypatch.setattr(core, "create_storage", fail)
    with pytest.raises(expected) as info:
        core.initialize()
    if expected is PermissionError:
        assert not isinstance(info.value, StorageOfflineError)
