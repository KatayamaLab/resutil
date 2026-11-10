from functools import wraps
from os.path import join
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import nullcontext
import os
import sys

from rich import print
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter

from .utils import (
    user_confirm,
    parse_result_dirs,
    verify_comment,
    EnvArgs,
    experiment_now,
)
from .config_file import create_ex_yaml
from .ex_dir import create_ex_dir, delete_ex_dir
from .git import GitRepo
from .core import initialize, upload, get_past_comments, download_with_dependency


class resutil_args:
    def __init__(self, ex_dir, checkpoint_callback):
        self.ex_dir = ex_dir
        self.checkpoint_callback = checkpoint_callback

    def save_checkpoint(self):
        """Return False on disabled/failed upload; never interrupt user computation."""
        return self.checkpoint_callback()


def get_comment(env_args, config):
    if env_args.debug_mode:
        return ""
    if env_args.comment_env is not None:
        comment = env_args.comment_env
        if not verify_comment(comment):
            raise ValueError("RESUTIL_COMMENT is invalid (maximum 200 UTF-8 bytes).")
        return comment
    if env_args.no_interactive:
        return ""
    comments = WordCompleter(get_past_comments(config.results_dir))
    while True:
        comment = prompt("📝 Input comment for this experiment: ", completer=comments)
        if verify_comment(comment):
            return comment
        print(
            "⛔️ Invalid comment (maximum 200 UTF-8 bytes; no path separators or control characters)."
        )


def get_env_args():
    return EnvArgs(
        comment_env=os.environ.get("RESUTIL_COMMENT"),
        no_interactive="RESUTIL_NO_INTERACTIVE" in os.environ,
        no_remote="RESUTIL_NO_REMOTE" in os.environ or "RESUTIIL_REMOTE" in os.environ,
        debug_mode="RESUTIL_DEBUG" in os.environ,
    )


def main(verbose=True):
    def main_wrapper(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            env = get_env_args()
            remote_enabled = not (env.no_remote or env.debug_mode)
            config, storage = initialize(connect=remote_enabled)
            comment = get_comment(env, config)
            now = experiment_now()
            context = (
                TemporaryDirectory(prefix="resutil-debug-")
                if env.debug_mode
                else nullcontext(None)
            )
            with context as temp:
                if temp is not None:
                    ex_dir_path = temp
                    ex_name = Path(temp).name
                else:
                    ex_name = create_ex_dir(now, comment, config.results_dir)
                    ex_dir_path = str(Path(config.results_dir) / ex_name)
                print(f"📁 Experiment directory: {ex_dir_path}")
                git_repo = GitRepo()
                commit_hash, files = git_repo.get_git_info(
                    exclude_paths=[config.results_dir, ex_dir_path]
                )
                if files:
                    git_repo.store_uncomited_to(join(ex_dir_path, "uncommited_files"))
                dependencies = parse_result_dirs(sys.argv, config.results_dir)
                create_ex_yaml(
                    ex_dir_path,
                    dependencies,
                    commit_hash,
                    files,
                    deleted_files=getattr(git_repo, "deleted_files", []),
                    comment=comment,
                    started_at=now.isoformat(),
                )
                for dependency in dependencies:
                    if not dependency.is_dir():
                        if storage is None:
                            raise FileNotFoundError(
                                f"Dependency unavailable in offline mode: {dependency}"
                            )
                        download_with_dependency(
                            dependency.name, config.results_dir, storage
                        )

                def checkpoint_callback():
                    if not remote_enabled:
                        return False
                    try:
                        upload(ex_name, config.results_dir, storage)
                        return True
                    except Exception as exc:
                        print(
                            f"⚠️ Checkpoint upload failed: {exc}. Results remain at {ex_dir_path}."
                        )
                        return False

                def final_upload():
                    if remote_enabled and Path(ex_dir_path).exists():
                        try:
                            upload(ex_name, config.results_dir, storage)
                        except Exception:
                            print(
                                f"❌ Upload failed. Results remain at {ex_dir_path}. Retry with 'resutil push {ex_name}'."
                            )
                            raise

                print("🚀 Running the main function...")
                try:
                    result = func(
                        resutil_args(ex_dir_path, checkpoint_callback), *args, **kwargs
                    )
                except BaseException as exc:
                    delete = False
                    if (
                        not env.no_interactive
                        and not env.debug_mode
                        and isinstance(exc, (Exception, KeyboardInterrupt))
                    ):
                        try:
                            delete = user_confirm(
                                "Execution failed. Delete local experiment?",
                                default="n",
                            )
                        except (EOFError, KeyboardInterrupt):
                            pass
                    if delete:
                        delete_ex_dir(ex_dir_path)
                    else:
                        try:
                            final_upload()
                        except Exception:
                            if isinstance(exc, SystemExit) and exc.code in (None, 0):
                                raise
                    # Preserve the original exception and nonzero exit status.
                    raise
                final_upload()
                if verbose:
                    print("✅ Done")
                return result

        return wrapper

    return main_wrapper
