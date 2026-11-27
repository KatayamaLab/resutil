from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
import shutil
import stat
import tempfile
import zipfile

import yaml
from .console import print
from .i18n import t

from .config_file import CONFIG_FILE_NAME, Config
from .exp_file import ExpFile
from .ex_dir import (
    update_local_references,
    get_ex_dir_names,
    change_comment,
    commented_name,
    rewrite_metadata,
)
from .network import StorageOfflineError, is_network_error
from .sync import archive_digest, record_sync, is_synced
from .utils import experiment_path, validate_experiment_name, write_yaml

exp_file_name = "resutil-exp.yaml"


def initialize(connect=True):
    config = Config()
    config.load()
    if not connect:
        return config, None
    try:
        storage = create_storage(config)
    except Exception as exc:
        if is_network_error(exc):
            raise StorageOfflineError(
                t(
                    "Cannot reach {storage} storage (network unavailable): {error}",
                    storage=config.storage_type,
                    error=exc,
                )
            ) from exc
        raise
    print(t("📦 Connected to {storage}", storage=config.storage_type))
    for key, value in storage.get_info().items():
        print(f"  {key}: {value}")
    return config, storage


def create_storage(config):
    if config.storage_type in ("gcs", "gs"):
        from .storage import GCS

        return GCS(config.storage_config, config.project_name)
    if config.storage_type == "gdrive":
        from .storage import GDrive

        return GDrive(config.storage_config, config.project_name)
    if config.storage_type == "server":
        from .storage import ResutilServerStorage

        return ResutilServerStorage(config.storage_config, config.project_name)
    raise ValueError(
        t("Wrong storage type. Check your {file} file.", file=CONFIG_FILE_NAME)
    )


def zip_directory(folder_path, zip_path):
    root = Path(folder_path)
    if not root.is_dir() or root.is_symlink():
        raise FileNotFoundError(
            t("Experiment directory does not exist: {path}", path=root)
        )

    def onerror(error):
        raise error

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for parent, dirs, files in os.walk(root, onerror=onerror):
            for name in dirs + files:
                if (Path(parent) / name).is_symlink():
                    raise ValueError("Symlinks cannot be archived.")
            for name in sorted(files):
                path = Path(parent) / name
                archive.write(path, path.relative_to(root).as_posix())


def upload(ex_name, results_dir, storage):
    path = experiment_path(results_dir, ex_name)
    if not path.is_dir():
        raise FileNotFoundError(
            t("Local experiment does not exist: {name}", name=ex_name)
        )
    with tempfile.TemporaryDirectory() as temp:
        archive = Path(temp) / f"{ex_name}.zip"
        zip_directory(path, archive)
        digest = archive_digest(archive)
        print(t("🗂️ Uploading: {name}", name=ex_name))
        storage.upload_experiment(str(archive))
        record_sync(results_dir, ex_name, storage, digest)


def _parallel(function, names, results_dir, storage):
    # The caller owns scheduling and observes every failure. Workers never submit.
    with ThreadPoolExecutor(max_workers=storage.max_workers) as executor:
        futures = [
            executor.submit(function, name, results_dir, storage) for name in names
        ]
        for future in futures:
            future.result()


def upload_with_dependency(ex_name, results_dir, storage):
    validate_experiment_name(ex_name)
    remote = set(storage.get_all_experiment_names())
    pending, seen, names = [ex_name], set(), []
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        path = experiment_path(results_dir, name)
        if not path.is_dir():
            if name != ex_name and name in remote:
                continue
            raise FileNotFoundError(
                t("Local experiment does not exist: {name}", name=name)
            )
        if (
            name == ex_name
            or name not in remote
            or not is_synced(results_dir, name, storage)
        ):
            names.append(name)
        metadata = path / exp_file_name
        if metadata.exists():
            pending.extend(ExpFile(metadata).dependency)
    _parallel(upload, names, results_dir, storage)


def upload_all(ex_names_to_upload, results_dir, storage):
    # Reuse graph validation and dependency handling; transfer errors propagate.
    for name in ex_names_to_upload:
        upload_with_dependency(name, results_dir, storage)


def unzip_file(zip_path, extract_to):
    root = Path(extract_to).resolve()
    with zipfile.ZipFile(zip_path) as archive:
        for entry in archive.infolist():
            path = Path(entry.filename.replace("\\", "/"))
            if (
                path.is_absolute()
                or ".." in path.parts
                or ":" in entry.filename
                or stat.S_ISLNK(entry.external_attr >> 16)
            ):
                raise ValueError(f"Unsafe archive member: {entry.filename}")
            if not (root / path).resolve().is_relative_to(root):
                raise ValueError(f"Unsafe archive member: {entry.filename}")
        archive.extractall(root)


def download(ex_name, results_dir, storage):
    target = experiment_path(results_dir, ex_name)
    if target.exists():
        raise FileExistsError(
            t("Local experiment already exists: {name}", name=ex_name)
        )
    if not storage.exist_experiment(ex_name):
        raise FileNotFoundError(
            t("Remote experiment does not exist: {name}", name=ex_name)
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    print(t("🗂️ Downloading: {name}", name=ex_name))
    with tempfile.TemporaryDirectory(
        prefix=".resutil-download-", dir=target.parent
    ) as temp:
        archive = Path(temp) / f"{ex_name}.zip"
        storage.download_experiment(str(archive))
        content = Path(temp) / "content"
        content.mkdir()
        unzip_file(archive, content)
        digest = archive_digest(archive)
        if target.exists():
            raise FileExistsError(target)
        content.rename(target)
        record_sync(results_dir, ex_name, storage, digest)


def download_with_dependency(ex_name, results_dir, storage):
    pending, seen = [validate_experiment_name(ex_name)], set()
    while pending:
        batch = list(dict.fromkeys(name for name in pending if name not in seen))
        pending = []
        if not batch:
            break
        seen.update(batch)
        missing = [
            name for name in batch if not experiment_path(results_dir, name).is_dir()
        ]
        _parallel(download, missing, results_dir, storage)
        for name in batch:
            metadata = experiment_path(results_dir, name) / exp_file_name
            if metadata.exists():
                pending.extend(ExpFile(metadata).dependency)


def download_all(ex_names_to_download, results_dir, storage):
    for name in ex_names_to_download:
        download_with_dependency(name, results_dir, storage)


def remove_local(ex_names, results_dir):
    paths = [(name, experiment_path(results_dir, name)) for name in ex_names]
    for name, path in paths:
        if path.is_dir():
            print(t("🗑️ Removing (local): {name}", name=name))
            shutil.rmtree(path)
        else:
            print(t("⚠️ {name} does not exist in the local directory.", name=name))


def remove_remote(ex_names, storage):
    for name in ex_names:
        validate_experiment_name(name)
    remote = set(storage.get_all_experiment_names())
    for name in ex_names:
        if name in remote:
            storage.remove_experiment(name)
        else:
            print(t("⚠️ {name} does not exist in the remote directory.", name=name))


def change_experiment_comment(results_dir, name, comment, storage):
    """Rename while preserving local and remote dependency references.

    Keep the old remote archive until every updated remote reference is saved.
    On failure both identifiers remain available, so existing references still work.
    """
    new_name = commented_name(name, comment)
    if new_name == name:
        return name
    local = set(get_ex_dir_names(results_dir))
    remote = set(storage.get_all_experiment_names())
    if name not in local | remote:
        raise FileNotFoundError(name)
    if new_name in local | remote:
        raise FileExistsError(new_name)
    with tempfile.TemporaryDirectory() as temp:
        updates = []
        # Remote metadata has no index, so inspect archives before mutating anything.
        for remote_name in sorted(remote):
            validate_experiment_name(remote_name)
            archive = Path(temp) / f"{remote_name}.zip"
            storage.download_experiment(str(archive))
            with zipfile.ZipFile(archive) as source:
                if exp_file_name not in source.namelist():
                    data: dict = {}
                else:
                    data = (
                        yaml.safe_load(source.read(exp_file_name).decode("utf-8")) or {}
                    )
            deps = ExpFile()
            from .utils import normalize_dependency

            deps.dependency = [
                normalize_dependency(d) for d in data.get("dependency", [])
            ]
            if remote_name != name and name not in deps.dependency:
                continue
            data = rewrite_metadata(data, name, new_name)
            if remote_name == name:
                data["comment"] = comment
                data["result_dir"] = new_name
            output_name = new_name if remote_name == name else remote_name
            directory = Path(temp) / output_name
            directory.mkdir()
            unzip_file(archive, directory)
            write_yaml(directory / exp_file_name, data)
            output = Path(temp) / f"updated-{output_name}.zip"
            zip_directory(directory, output)
            updates.append((remote_name == name, output_name, output))
        # Make the new target available before writing dependent archives.
        for _, output_name, output in sorted(updates, key=lambda item: not item[0]):
            send_dir = Path(temp) / "send"
            send_dir.mkdir(exist_ok=True)
            send = send_dir / f"{output_name}.zip"
            shutil.copyfile(output, send)
            storage.upload_experiment(str(send))
        if name in local:
            change_comment(results_dir, name, comment)
        else:
            update_local_references(results_dir, name, new_name, comment)
        if name in remote:
            storage.remove_experiment(name)
    return new_name


def get_past_comments(results_dir):
    comments = []
    for name in sorted(get_ex_dir_names(results_dir), reverse=True):
        parts = name.split("_", 2)
        if len(parts) == 3 and parts[2] not in comments:
            comments.append(parts[2])
    return comments
