from functools import wraps
from datetime import datetime
from os.path import join
import sys

from rich import print

from .utils import user_confirm, parse_result_dirs
from .config_file import create_ex_yaml
from .ex_dir import create_ex_dir, delete_ex_dir, find_unuploaded_ex_dirs
from .git import find_git_repo, get_git_info, store_uncomited

from .core import initialize, upload, upload_all


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

            print("")

            comment = input("📝 Input comment for this experiment: ")

            print("")

            ex_name = create_ex_dir(
                datetime.now(),
                comment,
                config.results_dir,
            )
            ex_dir_path = join(config.results_dir, ex_name)

            # check uncommited files
            git_repo = find_git_repo()
            if git_repo is None:
                commit_hash, unstaged_files = None, None
            else:
                commit_hash, unstaged_files = get_git_info(git_repo)
                if len(unstaged_files) > 0:
                    print("🔍 Unstaged files will be stored in the result dir:")
                    for file in unstaged_files:
                        print(f"  - {file}")
                    store_uncomited(
                        unstaged_files, join(ex_dir_path, "uncommited_files")
                    )

            dependency = parse_result_dirs(" ".join(sys.argv))

            create_ex_yaml(
                ex_dir_path,
                dependency,
                commit_hash=commit_hash,
                uncommited_files=unstaged_files,
            )

            # Run the main function
            print("🚀 Running the main function...")

            try:
                func(resutil_args(ex_dir_path), *args, **kwargs)
            except KeyboardInterrupt:
                print("")
                if user_confirm(
                    "🔔 Interrupted by user. Do you want to [bold]delete[/bold] experiment file for trial?",
                    default="n",
                ) and user_confirm(
                    "🔔 Are your sure to [bold]DELETE[/bold] it?",
                    default="n",
                ):
                    delete_ex_dir(ex_dir_path)
                    print(f"🗑️  Deleted [bold]{ex_dir_path}[/bold]")
                    print("⛔️ Aborted")

            print("")

            upload(ex_name, config.results_dir, storage)

            ex_names_to_upload = find_unuploaded_ex_dirs(config.results_dir, storage)

            n = len(ex_names_to_upload)
            if n > 0 and user_confirm(
                f"ℹ️ There are {n} other experiment directory(s) that have not been uploaded. Do you want to upload them?",
                default="y",
            ):
                upload_all(ex_names_to_upload, config.results_dir, storage)

            print("✅ Done")

        return wrapper

    return main_wrapper
