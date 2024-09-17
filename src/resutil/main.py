from functools import wraps
from datetime import datetime
from os.path import join
import sys
import traceback
import argparse
import os
from pathlib import Path

from rich import print
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter

from .utils import user_confirm, parse_result_dirs, verify_comment
from .config_file import create_ex_yaml
from .ex_dir import create_ex_dir, delete_ex_dir, find_unuploaded_ex_dirs
from .git import GitRepo

from .core import (
    initialize,
    upload,
    upload_all,
    get_past_comments,
    download,
)


class resutil_args:
    def __init__(self, ex_dir):
        self.ex_dir = ex_dir


# Used as a decorator
def main(verbose=True):
    def main_wrapper(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            print("")
            print("✨ Runnning your code with [bold]Resutil[/bold]")
            print("")

            config, storage = initialize()

            # parse arguments
            parser = argparse.ArgumentParser("Resutil", add_help=False)
            parser.add_argument("--resutil_comment", type=str)
            parser.add_argument(
                "--resutil_no_interactive",
                action="store_true",
            )
            parser.add_argument(
                "--resutil_debug",
                action="store_true",
            )
            parser.add_argument(
                "--resutil_no_remote",
                action="store_true",
            )
            parsed_args, unknown = parser.parse_known_args(sys.argv[1:])

            # set interactive mode
            no_interactive = parsed_args.resutil_no_interactive
            debug_mode = parsed_args.resutil_debug
            no_remote = parsed_args.resutil_no_remote

            # if --resutil_comment is not specified, ask for comment
            if (no_interactive and parsed_args.resutil_comment is None) or debug_mode:
                comment = ""
            elif parsed_args.resutil_comment is not None:
                comment = parsed_args.resutil_comment
            else:
                comments = WordCompleter(get_past_comments(config.results_dir))
                print("")
                while True:
                    comment = prompt(
                        f"📝 Input comment for this experiment (press [tab] key to completion): ",
                        completer=comments,
                    )
                    if verify_comment(comment):
                        break
                    print(
                        '⛔️ Comment string is invalid. It should be less than 200 characters and not contain any of the following characters: \\ / : * ? " < > |'
                    )

            print("")

            if debug_mode:
                print("🔍 Debug mode is enabled.")
                print("")
                ex_name = "_debug"
                os.makedirs(join(config.results_dir, ex_name), exist_ok=True)
            else:
                ex_name = create_ex_dir(
                    datetime.now(),
                    comment,
                    config.results_dir,
                )
            ex_dir_path = join(config.results_dir, ex_name)

            # check uncommited files
            git_repo = GitRepo()

            if git_repo.exist():
                commit_hash, unstaged_files = git_repo.get_git_info()
                if len(unstaged_files) > 0:
                    print("🔍 Unstaged files will be stored in the result dir:")
                    for file in unstaged_files:
                        print(f"  - {file}")
                    git_repo.store_uncomited_to(join(ex_dir_path, "uncommited_files"))
            else:
                commit_hash = None
                unstaged_files = []

            dependencies = parse_result_dirs(sys.argv, config.results_dir)

            create_ex_yaml(
                ex_dir_path,
                dependencies,
                commit_hash=commit_hash,
                uncommited_files=unstaged_files,
            )

            # Check all dependencies exist
            unexisting_deps = []
            for dep in dependencies:
                print(dep)
                if not dep.exists():
                    unexisting_deps.append(dep)
            if len(unexisting_deps) > 0:
                print(
                    "🔍 The following dependencies do not exist. They will be downloaded."
                )
                for dep in unexisting_deps:
                    print(f"  📁 {dep}")
                for dep in unexisting_deps:
                    ex_name = dep.name
                    download(ex_name, config.results_dir, storage)
                print("")

            # Run the main function
            print("🚀 Running the main function...")

            # if resutil is not interactive, run the function and upload the result
            if no_interactive:
                func(resutil_args(ex_dir_path), *args, **kwargs)
                print("")
                if not (no_remote or debug_mode):
                    upload(ex_name, config.results_dir, storage)
                return

            try:
                func(resutil_args(ex_dir_path), *args, **kwargs)
                print("")
                if not (no_remote or debug_mode):
                    upload(ex_name, config.results_dir, storage)

            except KeyboardInterrupt:
                print("")
                if user_confirm(
                    "🔔 Interrupted by user. Do you want to [bold]delete[/bold] experiment file for trial?",
                    default="n",
                ) and user_confirm(
                    ".....Are your sure to [bold]DELETE[/bold] it?",
                    default="n",
                ):
                    delete_ex_dir(ex_dir_path)
                    print(f"🗑️  Deleted [bold]{ex_dir_path}[/bold]")
                else:
                    upload(ex_name, config.results_dir, storage)
            except Exception as e:
                print("")
                if user_confirm(
                    "❌ An Exception has occured. Do you want to [bold]delete[/bold] experiment file for trial?",
                    default="n",
                ) and user_confirm(
                    ".....Are your sure to [bold]DELETE[/bold] it?",
                    default="n",
                ):
                    delete_ex_dir(ex_dir_path)
                    print(f"🗑️  Deleted [bold]{ex_dir_path}[/bold]")
                else:
                    upload(ex_name, config.results_dir, storage)
                print("❌ Please check the error message below:")
                print("----------------------------------")
                traceback.print_exception(type(e), e, e.__traceback__)
                print("----------------------------------")

            ex_names_to_upload = find_unuploaded_ex_dirs(config.results_dir, storage)

            n = len(ex_names_to_upload)
            if n > 0:
                print(
                    f"ℹ️ There are {n} other experiment directory(s) that have not been uploaded."
                )

            print("✅ Done")

        return wrapper

    return main_wrapper
