from concurrent.futures import ThreadPoolExecutor, as_completed
from os.path import join, exists

from rich import print

from .storage import Box
from .config_file import ConfigYaml
from .exp_file import ExpFile

config_file_name = "resutil-conf.yaml"
exp_file_name = "resutil-exp.yaml"


def initialize():
    try:
        config = ConfigYaml(config_file_name)
    except FileNotFoundError:
        print(f"⚠️ Config file {config_file_name} does not exist.")
        print("Create a config file by running [bold]resutil init[/bold] and try again")
        exit(1)

    if config.storage_type == "box":
        storage = Box(config.storage_config, config.project_name)
        print("📦 Connected to [bold]box[/bold]")
        base_dir_name, project_folder_name = storage.get_info()
        print(f"  📁 Base dir: [bold]{base_dir_name}[/bold]")
        print(f"  📁 Project dir: [bold]{project_folder_name}[/bold]")
    else:
        raise (
            ValueError(
                f"⛔️ Wronge storage type. Check your [bold]{config_file_name}[/bold] file."
            )
        )
    return config, storage


def upload(ex_name: str, results_dir: str, storage: Box, no_dependency=False):
    with ThreadPoolExecutor(max_workers=10) as executor:
        ex_dir_path = join(results_dir, ex_name)

        def callback(ex_name):
            print(f"🗂️ Uploading: [bold]{ex_name}[/bold]")

        storage.upload_experiment(ex_dir_path, callback, executor)

        if no_dependency:
            return

        ex_file_path = join(ex_dir_path, exp_file_name)
        if exists(ex_file_path):
            exp_file = ExpFile(ex_file_path)
            for d in exp_file.dependency:
                upload(d, results_dir, storage, no_dependency)


def upload_all(ex_names_to_upload: list[str], results_dir: str, storage: Box):
    with ThreadPoolExecutor(max_workers=5) as executor:
        for ex_name in ex_names_to_upload:
            ex_dir_path = join(results_dir, ex_name)

            def callback(ex_name):
                print(f"🗂️ Uploading: [bold]{ex_name}[/bold]")

            storage.upload_experiment(ex_dir_path, callback, executor)


def download(ex_name: str, results_dir: str, storage: Box, no_dependency=False):
    with ThreadPoolExecutor(max_workers=10) as executor:
        ex_dir_path = join(results_dir, ex_name)

        def callback(ex_name):
            print(f"🗂️ Downloading: [bold]{ex_name}[/bold]")

        futures = storage.download_experiment(ex_dir_path, callback, executor)

        if no_dependency:
            return

        for future in as_completed(futures):
            f = future.result()
            if f == exp_file_name:
                exp_file = ExpFile(join(ex_dir_path, f))
                for d in exp_file.dependency:
                    download(d, results_dir, storage, no_dependency)


def download_all(ex_names_to_download: list[str], results_dir: str, storage: Box):
    with ThreadPoolExecutor(max_workers=5) as executor:
        for ex_name in ex_names_to_download:
            ex_dir_path = join(results_dir, ex_name)

            def callback(ex_name):
                print(f"🗂️ Downloading: [bold]{ex_name}[/bold]")

            storage.download_experiment(ex_dir_path, callback, executor)
