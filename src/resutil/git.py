from shutil import copy
from pathlib import Path

from git import Repo, InvalidGitRepositoryError


def find_git_repo():
    # search repogitory recursively to root
    try:
        repo = Repo("./", search_parent_directories=True)
    except InvalidGitRepositoryError:
        return None
    return repo


def get_git_info(repo: Repo):
    # Get the most recent commit
    latest_commit = repo.head.commit.hexsha

    # Get modified files

    modified_files = [item.a_path for item in repo.index.diff(None)]
    staged_files = [item.a_path for item in repo.index.diff("HEAD")]

    return latest_commit, [*modified_files, *staged_files]


def store_uncomited(uncommited_files, dir_path):
    # copy files
    for file in uncommited_files:
        dest = Path(dir_path, file)
        dest.parent.mkdir(parents=True, exist_ok=True)
        copy(file, dest)
