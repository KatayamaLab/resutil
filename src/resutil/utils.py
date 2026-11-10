import os
import re
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from rich import print
import readline
import yaml

_NAME = re.compile(r"[a-zA-Z]{6}_\d{8}T\d{6}(?:_[^/\\]*)?\Z")


def to_base26(n):
    code = "abcdefghijklmnopqrstuvwxyz"
    converted = []
    for _ in range(6):
        converted.append(code[n % 26])
        n //= 26
    return "".join(reversed(converted))


def verify_comment(comment: str) -> bool:
    return (
        isinstance(comment, str)
        and not re.search(r'[\\/:*?"<>|\x00-\x1f\x7f]', comment)
        and len(comment.encode("utf-8")) <= 200
        and not comment.endswith((" ", "."))
    )


def validate_experiment_name(name: str) -> str:
    if (
        not isinstance(name, str)
        or not _NAME.fullmatch(name)
        or len(name.encode("utf-8")) > 251
    ):
        raise ValueError(f"Invalid experiment name: {name!r}")
    if not verify_comment(
        name.split("_", 2)[2] if len(name.split("_", 2)) == 3 else ""
    ):
        # Generated collision suffixes may add nine bytes to the comment.
        suffix = name.split("_", 2)[2]
        if not (re.match(r"^[0-9a-f]{8}_", suffix) and verify_comment(suffix[9:])):
            raise ValueError(f"Invalid experiment name: {name!r}")
    return name


def normalize_dependency(value) -> str:
    # Older metadata stores a path, including absolute and Windows paths.
    text = str(value).replace("\\", "/").rstrip("/")
    return validate_experiment_name(text.rsplit("/", 1)[-1])


def experiment_path(results_dir, name):
    validate_experiment_name(name)
    root = Path(results_dir).resolve()
    path = root / name
    if path.is_symlink() or path.resolve().parent != root:
        raise ValueError(f"Experiment must be a direct directory under {root}: {name}")
    return path


def parse_result_dirs(argv: list[str], results_dir: str) -> list[Path]:
    root = Path(results_dir).resolve()
    found = []
    for arg in argv:
        # Also support --input=results/experiment/file.
        value = arg.split("=", 1)[1] if arg.startswith("-") and "=" in arg else arg
        try:
            relative = Path(value).resolve().relative_to(root)
            if not relative.parts:
                continue
            name = validate_experiment_name(relative.parts[0])
        except (ValueError, OSError):
            continue
        path = root / name
        if path not in found:
            found.append(path)
    return found


def experiment_now():
    name = os.environ.get("RESUTIL_TIMEZONE")
    return datetime.now(ZoneInfo(name)) if name else datetime.now().astimezone()


def timestamp_parts(now):
    # The identifier sorts by UTC; the displayed timestamp follows the selected zone.
    aware = now if now.tzinfo else now.astimezone()
    elapsed = (
        aware.astimezone(timezone.utc) - datetime(2024, 1, 1, tzinfo=timezone.utc)
    ).total_seconds()
    return to_base26(int(elapsed / 60)), aware.strftime("%Y%m%dT%H%M%S")


def user_confirm(question: str, default="") -> bool:
    yn = "(Y/n)" if default == "y" else "(y/N)" if default == "n" else "(y/n)"
    while True:
        print(f"{question} [bold]{yn}[/bold]: ", end="")
        reply = input().lower().strip()
        if reply.startswith("y"):
            return True
        if reply.startswith("n"):
            return False
        if not reply and default in ("y", "n"):
            return default == "y"
        question = question.removeprefix("Please try again - ")
        question = f"Please try again - {question}"


def atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def write_yaml(path, data):
    atomic_write(
        path, yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=10000)
    )


def input_with_default(prompt, default=""):
    def hook():
        readline.insert_text(default)
        readline.redisplay()

    print(prompt, end="")
    readline.set_pre_input_hook(hook)
    try:
        return input("")
    finally:
        readline.set_pre_input_hook()


@dataclass
class EnvArgs:
    comment_env: Optional[str]
    no_interactive: bool
    no_remote: bool
    debug_mode: bool
