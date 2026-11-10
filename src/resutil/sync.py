"""Local receipts for the exact archive last transferred to each destination."""

import hashlib
import json
from pathlib import Path
from threading import RLock
import zipfile

from .utils import atomic_write

_LOCK = RLock()


def _digest(entries):
    result = hashlib.sha256()
    for name, digest in sorted(entries):
        result.update(name.encode("utf-8") + b"\0" + digest)
    return result.hexdigest()


def directory_digest(path):
    entries = []
    root = Path(path)
    for file in sorted(root.rglob("*")):
        if file.is_symlink():
            raise ValueError(f"Symlinks cannot be synced: {file}")
        if file.is_file():
            with file.open("rb") as stream:
                digest = hashlib.sha256()
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            entries.append((file.relative_to(root).as_posix(), digest.digest()))
    return _digest(entries)


def archive_digest(path):
    with zipfile.ZipFile(path) as archive:
        entries = []
        for info in archive.infolist():
            if not info.is_dir():
                digest = hashlib.sha256()
                with archive.open(info) as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
                entries.append((info.filename, digest.digest()))
        return _digest(entries)


def _key(name, storage):
    return json.dumps(
        [storage.__class__.__module__, storage.get_info(), name], sort_keys=True
    )


def _read(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def record_sync(results_dir, name, storage, digest):
    path = Path(results_dir) / ".resutil-sync.json"
    with _LOCK:
        receipts = _read(path)
        receipts[_key(name, storage)] = digest
        atomic_write(path, json.dumps(receipts, indent=2))


def is_synced(results_dir, name, storage):
    path = Path(results_dir) / ".resutil-sync.json"
    with _LOCK:
        digest = _read(path).get(_key(name, storage))
    return digest is not None and digest == directory_digest(Path(results_dir) / name)
