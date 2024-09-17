from shutil import copy
from pathlib import Path

from git import Repo, InvalidGitRepositoryError


class GitRepo:
    def __init__(self):
        # search repogitory recursively to root
        try:
            self.repo = Repo("./", search_parent_directories=True)
        except InvalidGitRepositoryError:
            self.repo = None

    def exist(self):
        return self.repo is not None

    def get_git_info(self):
        # Get the most recent commit
        latest_commit = self.repo.head.commit.hexsha

        # Get modified files

        modified_files = [
            item.a_path
            for item in self.repo.index.diff(None)
            if not item.change_type == "D"
        ]
        staged_files = [
            item.a_path
            for item in self.repo.index.diff("HEAD")
            if not item.change_type == "A"
        ]

        self.uncommitd_file_path_list = [*modified_files, *staged_files]

        return latest_commit, self.uncommitd_file_path_list

    def store_uncomited_to(self, dir_path):
        # copy files
        # cd to the root of the repository
        # get the root of the repository
        working_tree_dir = self.repo.working_tree_dir
        for uncommitd_file_path in self.uncommitd_file_path_list:
            src = Path(working_tree_dir, uncommitd_file_path)
            dst = Path(dir_path, uncommitd_file_path)
            dst.parent.mkdir(parents=True, exist_ok=True)
            copy(src, dst)
