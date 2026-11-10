"""Rich output that also works with legacy redirected text streams."""

import sys

from rich import print as rich_print


def print(*objects, **kwargs):
    stream = kwargs.get("file") or sys.stdout
    encoding = getattr(stream, "encoding", None) or "utf-8"
    # Avoid changing the host program's stdout or its encoding policy.
    rendered = [
        (
            obj.encode(encoding, errors="backslashreplace").decode(encoding)
            if isinstance(obj, str)
            else obj
        )
        for obj in objects
    ]
    return rich_print(*rendered, **kwargs)
