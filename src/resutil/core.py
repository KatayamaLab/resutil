from concurrent.futures import ThreadPoolExecutor
from os.path import join, exists
from os import makedirs
import os
import zipfile
import tempfile
import shutil


from rich import print

from .storage import Box, GCS, GDrive, Storage
from .config_file import Config
from .exp_file import ExpFile
from .ex_dir import get_ex_dir_names

exp_file_name = "resutil-exp.yaml"


def initialize():
    try:
        config = Config()
        config.load()
    except FileNotFoundError:
        print(f"⚠️ Config file does not exist.")
        print("Create a config file by running [bold]resutil init[/bold] and try again")
        exit(1)

    if config.storage_type == "box":
        storage = Box(config.storage_config, config.project_name)
        print("📦 Connected to [bold]box[/bold]")
        info = storage.get_info()
        print(f"  📁 Base folder id: [bold]{info['base_folder_id']}[/bold]")
        print(f"  📁 Project folder name: [bold]{info['project_folder_name']}[/bold]")
        print(
            f"  📁 Project folder: [bold]https://app.box.com/folder/{info['project_folder_id']}[/bold]"
        )
    elif config.storage_type == "gcs" or config.storage_type == "gs":
        storage = GCS(config.storage_config, config.project_name)
        print("📦 Connected to [bold]Google Cloud Storage[/bold]")
        info = storage.get_info()
        print(f"  📁 Bucket name: [bold]{info['bucket_name']}[/bold]")
        print(f"  📁 Project dir: [bold]{info['project_dir']}[/bold]")

    elif config.storage_type == "gdrive":
        storage = GDrive(config.storage_config, config.project_name)
        print("📦 Connected to [bold]Google Drive[/bold]")
        info = storage.get_info()
        print(f"  📁 Base folder id: [bold]{info['base_folder_id']}[/bold]")
        print(f"  📁 Project dir: [bold]{info['project_dir']}[/bold]")

    else:
        raise (
            ValueError(
                f"⛔️ Wronge storage type. Check your [bold]{config_file_name}[/bold] file."
            )
        )
    return config, storage


def zip_directory(folder_path, zip_path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=folder_path)
                zipf.write(file_path, arcname)


def upload(ex_name: str, results_dir: str, storage: Storage):
    ex_dir_path = join(results_dir, ex_name)

    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, f"{ex_name}.zip")
        zip_directory(ex_dir_path, zip_path)
        print(f"🗂️ Uploading: [bold]{ex_name}[/bold]")
        storage.upload_experiment(zip_path)


def upload_with_dependency(ex_name: str, results_dir: str, storage: Storage):
    with ThreadPoolExecutor(max_workers=10) as executor:
        recurcive_uploder(ex_name, results_dir, storage, executor)


def recurcive_uploder(ex_name: str, results_dir: str, storage, executor):
    ex_dir_path = join(results_dir, ex_name)

    executor.submit(upload, ex_name, results_dir, storage)

    ex_file_path = join(ex_dir_path, exp_file_name)

    if exists(ex_file_path):
        exp_file = ExpFile(ex_file_path)
        for dependency in exp_file.dependency:
            if not storage.exist_experiment(dependency):
                recurcive_uploder(dependency, results_dir, storage, executor)


def upload_all(ex_names_to_upload: list[str], results_dir: str, storage: Storage):
    with ThreadPoolExecutor(max_workers=1) as executor:
        for ex_name in ex_names_to_upload:
            executor.submit(upload, ex_name, results_dir, storage)


def unzip_file(zip_path, extract_to):
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)


def download(ex_name: str, results_dir: str, storage: Storage):
    print(f"🗂️ Downloading: [bold]{ex_name}[/bold]")

    with tempfile.TemporaryDirectory() as temp_dir:
        storage.download_experiment(join(temp_dir, ex_name + ".zip"))
        ex_dir = join(results_dir, ex_name)
        makedirs(ex_dir, exist_ok=True)
        unzip_file(join(temp_dir, f"{ex_name}.zip"), ex_dir)


def download_with_dependency(ex_name: str, results_dir: str, storage: Storage):
    with ThreadPoolExecutor(max_workers=10) as executor:
        recurcive_downloader(ex_name, results_dir, storage, executor)


def recurcive_downloader(ex_name: str, results_dir: str, storage: Storage, executor):
    download(ex_name, results_dir, storage)

    ex_file_path = join(results_dir, ex_name, exp_file_name)

    if exists(ex_file_path):
        exp_file = ExpFile(ex_file_path)
        for d in exp_file.dependency:
            if not exists(join(results_dir, d)):
                executor.submit(recurcive_downloader, d, results_dir, storage, executor)


def download_all(ex_names_to_download: list[str], results_dir: str, storage: Storage):
    with ThreadPoolExecutor(max_workers=10) as executor:
        for ex_name in ex_names_to_download:
            executor.submit(download, ex_name, results_dir, storage)


def remove_local(ex_names: list[str], results_dir: str):
    for ex_name in ex_names:
        path = join(results_dir, ex_name)
        if exists(path):
            print(f"🗑️ Removing (local): [bold]{ex_name}[/bold]")
            shutil.rmtree(path)
        else:
            print(f"⚠️ {ex_name} does not exist in the local directory.")


def remove_remote(ex_names: list[str], storage: Storage):
    ex_names_all = storage.get_all_experiment_names()
    for ex_name in ex_names:
        if ex_name in ex_names_all:
            print(f"🗑️ Removing (remote): [bold]{ex_name}[/bold]")
            storage.remove_experiment(ex_name)
        else:
            print(f"⚠️ {ex_name} does not exist in the remote directory.")


def get_past_comments(results_dir: str):
    ex_dir_names = get_ex_dir_names(results_dir)
    sorted_ex_dir_names = sorted(ex_dir_names, reverse=True)

    comments = []
    for ex in sorted_ex_dir_names:
        item = ex.split("_")
        if len(item) == 3:
            comments.append(item[2])

    return list(set(comments))
