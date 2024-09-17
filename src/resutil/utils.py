import re
from rich import print
import readline
from pathlib import Path


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
    pattern = r"[a-zA-Z]{6}_\d{8}T\d{6}_[^/\s\\]*"
    results_path = Path(results_dir).resolve()
    current_dir = Path.cwd()

    result_dirs = []
    for arg in argv:
        path = Path(arg).resolve()
        if path.is_relative_to(results_path) and re.match(pattern, str(path.name)):
            result_dirs.append(path.relative_to(current_dir))

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
