"""Classification of storage failures caused by an unreachable network."""

import socket


class StorageOfflineError(ConnectionError):
    """Storage could not be reached because the network is unavailable."""


def _network_error_types():
    types: list[type[BaseException]] = [
        ConnectionError,
        TimeoutError,
        socket.gaierror,
        socket.herror,
    ]
    try:
        import httpx

        types.append(httpx.TransportError)
    except ImportError:  # pragma: no cover
        pass
    try:
        import requests  # type: ignore[import-untyped]

        types += [requests.exceptions.ConnectionError, requests.exceptions.Timeout]
    except ImportError:  # pragma: no cover
        pass
    try:
        from google.auth.exceptions import TransportError

        types.append(TransportError)
    except ImportError:  # pragma: no cover
        pass
    try:
        import httplib2  # type: ignore[import-untyped]

        types.append(httplib2.ServerNotFoundError)
    except ImportError:  # pragma: no cover
        pass
    return tuple(types)


def is_network_error(exc):
    """True when exc, or an exception in its cause/context chain, is a network failure.

    Authentication failures (PermissionError) and HTTP status errors are not network
    failures, so they are never treated as offline.
    """
    types = _network_error_types()
    seen = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        if isinstance(exc, PermissionError):
            return False
        if isinstance(exc, types):
            return True
        if exc.__cause__ is not None:
            exc = exc.__cause__
        else:
            exc = None if exc.__suppress_context__ else exc.__context__
    return False
