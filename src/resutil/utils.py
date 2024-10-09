import re
from rich import print
import readline
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


def to_base26(n):
    code = "abcdefghijklmnopqrstuvwxyz"
    converted = []

    for i in range(6):
        converted.append(code[n % 26])
        n -= n % 26
        n //= 26

    converted = "".join(converted[::-1])
    converted = "a" * (5 - len(converted)) + converted

    return converted


def parse_result_dirs(argv: list[str], results_dir: str) -> list[Path]:
    pattern = r"[a-zA-Z]{6}_\d{8}T\d{6}[^/]*"
    results_path = Path(results_dir).resolve()

    result_dirs = []
    for arg in argv:
        path = Path(arg).resolve()
        ex_names = re.findall(pattern, path.as_posix())
        if len(ex_names) == 0:
            continue
        if not path.is_relative_to(results_path):
            continue
        result_dirs.append(Path(results_dir, ex_names[0]))

    return result_dirs


def user_confirm(question: str, default="") -> bool:
    yn = "(Y/n)" if default == "y" else "(y/N)" if default == "n" else "(y/n)"

    print(f"{question} [bold]{yn}[/bold]: ", end="")
    reply = str(input()).lower().strip()

    if reply[:1] == "y":
        return True
    elif reply[:1] == "n":
        return False
    elif default == "y" and len(reply) == 0:
        return True
    elif default == "n" and len(reply) == 0:
        return False
    else:
        new_question = question
        if "Please try again - " not in question:
            new_question = f"Please try again - {question}"
        return user_confirm(new_question, default)


def verify_comment(comment: str) -> bool:
    invalid_chars_pattern = r'[\\/:*?"<>|]'
    return not re.search(invalid_chars_pattern, comment) and len(comment) <= 200


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
