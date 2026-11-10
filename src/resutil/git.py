from pathlib import Path
from typing import Optional
from shutil import copy2

from git import Repo, InvalidGitRepositoryError, NoSuchPathError


class GitRepo:
    def __init__(self):
        self.repo: Optional[Repo]
        try:
            self.repo = Repo(".", search_parent_directories=True)
            if self.repo.bare:
                self.repo = None
        except (InvalidGitRepositoryError, NoSuchPathError):
            self.repo = None

    def exist(self):
        return self.repo is not None

    def get_git_info(self, exclude_paths=()):
        repo = self.repo
        if repo is None:
            return None, []
        commit_hash = repo.head.commit.hexsha if repo.head.is_valid() else None
        paths = set(repo.untracked_files)
        for item in repo.index.diff(None):
            paths.update(p for p in (item.a_path, item.b_path) if p)
        if commit_hash:
            for item in repo.index.diff("HEAD"):
                paths.update(p for p in (item.a_path, item.b_path) if p)
        else:
            paths.update(str(path) for path, stage in repo.index.entries if stage == 0)
        assert repo.working_tree_dir is not None
        root = Path(repo.working_tree_dir)
        excluded = [Path(path).resolve() for path in exclude_paths]
        paths = {
            p
            for p in paths
            if not any((root / p).resolve().is_relative_to(path) for path in excluded)
        }
        self.uncommitd_file_path_list = sorted(
            p for p in paths if (root / p).is_file() and not (root / p).is_symlink()
        )
        # Preserve deletions too, so the working tree can be reconstructed.
        self.deleted_files = sorted(p for p in paths if not (root / p).exists())
        return commit_hash, self.uncommitd_file_path_list

    def store_uncomited_to(self, dir_path):
        if self.repo is None or self.repo.working_tree_dir is None:
            return
        root = Path(self.repo.working_tree_dir)
        for name in self.uncommitd_file_path_list:
            src = root / name
            dst = Path(dir_path) / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                copy2(src, dst)
            except FileNotFoundError:
                # A file may be deleted while the snapshot is being captured.
                self.deleted_files.append(name)
