import argparse
import os
from os.path import join
from datetime import datetime

from rich import print


from ..ex_dir import find_undownloaded_ex_dirs, find_unuploaded_ex_dirs, create_ex_dir
from ..utils import user_confirm
from ..config_file import ConfigYaml
from ..storage import Box
from ..config_file import create_ex_yaml

from ..core import initialize, upload, upload_all, download_all, download


config_file_path = "resutil-conf.yaml"


def main():
    parser = argparse.ArgumentParser(description="")
    subparsers = parser.add_subparsers()

    # init
    parser_init = subparsers.add_parser("init", help="initialize resutil")
    parser_init.set_defaults(handler=command_init)

    # pull
    parser_pull = subparsers.add_parser("pull", help="pull experiments")
    parser_pull.add_argument(
        "--no-dependency",
        action="store_true",
        help="pull experiments without dependencies",
    )
    group_pull = parser_pull.add_mutually_exclusive_group(required=True)
    group_pull.add_argument(
        "-A", "--all", action="store_true", help="pull all experiments"
    )
    group_pull.add_argument("experiment", nargs="?", help="experiment to pull")
    parser_pull.set_defaults(handler=command_pull)

    # push
    parser_push = subparsers.add_parser("push", help="push experiments")
    parser_push.add_argument(
        "--no-dependency",
        action="store_true",
        help="push experiments without dependencies",
    )
    group_push = parser_push.add_mutually_exclusive_group(required=True)
    group_push.add_argument(
        "-A", "--all", action="store_true", help="push all experiments"
    )
    group_push.add_argument("experiment", nargs="?", help="experient to push")
    parser_push.set_defaults(handler=command_push)

    # add
    parser_add = subparsers.add_parser("add", help="add experiments")
    parser_add.add_argument("comment", nargs="?", help="experient to add")
    parser_add.add_argument(
        "-d",
        "--dependency",
        nargs="+",
        help="add depending experiments",
    )
    parser_add.set_defaults(handler=command_add)

    # args
    args = parser.parse_args()

    if hasattr(args, "handler"):
        args.handler(args)
    else:
        parser.print_help()


def get_default_project_name():
    current_dir = os.getcwd()
    parent_dir_name = os.path.basename(current_dir)

    return parent_dir_name


def search_default_result_dir():
    candidate = [
        "results",
        "result",
        "data",
        "output",
        "outputs",
        "input",
        "inputs",
    ]
    default = "results"
    # get dirs in current directory
    dirs = [d for d in os.listdir() if os.path.isdir(d)]

    for c in candidate:
        if c in dirs:
            return c

    return default


def command_init(args):
    # check if already initialized
    if os.path.exists(config_file_path):
        print("⚠️ Already initialized.")
        print("  [yellow]resutil-conf.yaml[/yellow] already exists.")
        print("  If you proceed, the existing file will be overwritten.")
        yn = user_confirm("  Do you want to proceed?", default="n")
        if not yn:
            return

    # create config
    config = ConfigYaml()

    # set project name (default is parent directory name)
    d = get_default_project_name()
    print(f"Input project name [bold]({d})[/bold]: ", end="")
    s = input()
    project_name = s if s != "" else d
    config.set_project_name(project_name)

    # set directory to store results
    d = search_default_result_dir()
    print(f"Input directory name to store results [bold]({d})[/bold]: ", end="")
    s = input()
    results_dir = s if s != "" else d

    # create results directory if not exist
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)

    config.set_results_dir(results_dir)

    # add to .gitignore
    yn = user_confirm(f"Do you want to add .gitignore to {results_dir}?", default="y")
    if yn:
        with open(os.path.join(results_dir, ".gitignore"), "a") as f:
            f.write("# Resutil result dir\n")
            f.write("# Automatically added by resutil\n")
            f.write("# Files here are not managed by git\n")
            f.write("*\n")
            f.write("!.gitignore\n")

    # set storage type
    while True:
        d = "box"
        print(f"Input storage_type [bold]({d})[/bold]: ", end="")
        s = input()
        storage_type = s if s != "" else "box"
        if storage_type in ["box"]:
            break
    config.set_storage_type(storage_type)

    # set box config
    if storage_type == "box":
        d = "key.json"
        print(f"Input key file_path [bold]({d})[/bold]: ", end="")
        s = input()
        key_file_path = s if s != "" else "key.json"

        yn = user_confirm(
            f"Do you want to add {key_file_path} to .gitignore?", default="y"
        )
        if yn:
            with open(".gitignore", "a") as f:
                f.write("\n# Resutil config file\n")
                f.write(key_file_path + "\n")

        print(f"Input folder id of base dir: ", end="")
        base_dir_id = input()

        storage_config = {"key_file_path": key_file_path, "base_dir_id": base_dir_id}

        config.set_storage_config(storage_config)

        try:
            Box(config.storage_config, config.project_name)
        except Exception as e:
            print("❌ Failed to connect to storage.")
            print(f"  [red]{e}[/red]")
            return

    # save config
    config.save(config_file_path)

    print("✅ Initialized.")


def command_pull(args):
    config, storage = initialize()

    if args.experiment:
        download(args.experiment, config.results_dir, storage, args.no_dependency)
        print(args.experiment)
        print("✅ Downloaded")

    elif args.all:
        ex_names_to_upload = find_undownloaded_ex_dirs(config.results_dir, storage)

        n = len(ex_names_to_upload)
        if n > 0 and user_confirm(
            f"ℹ️ There are {n} other experiment directory(s) that have not been downloaded. Do you want to download them?",
            default="y",
        ):
            download_all(ex_names_to_upload, config.results_dir, storage)
            print("✅ Downloaded")

        elif n == 0:
            print("✅ No experiment to download.")


def command_push(args):
    config, storage = initialize()

    if args.experiment:
        upload(args.experiment, config.results_dir, storage, args.no_dependency)
        print(args.experiment)
        print("✅ Uploaded")

    elif args.all:
        ex_names_to_upload = find_unuploaded_ex_dirs(config.results_dir, storage)

        n = len(ex_names_to_upload)
        if n > 0 and user_confirm(
            f"ℹ️ There are {n} other experiment directory(s) that have not been uploaded. Do you want to upload them?",
            default="y",
        ):
            upload_all(ex_names_to_upload, config.results_dir, storage)
            print("✅ Uploaded")

        elif n == 0:
            print("✅ No experiment to upload.")


def command_add(args):
    config, _ = initialize()

    if args.comment is None:
        comment = input("📝 Input comment for this experiment: ")
    else:
        comment = args.comment
        print(f"com: {comment}")

    dependency = args.dependency if args.dependency is not None else []

    ex_name = create_ex_dir(
        datetime.now(),
        comment,
        config.results_dir,
    )
    ex_dir_path = join(config.results_dir, ex_name)

    create_ex_yaml(ex_dir_path, dependency)
