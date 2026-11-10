import argparse
import os
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from os.path import join
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from rich import print

from ..ex_dir import (
    find_undownloaded_ex_dirs,
    find_unuploaded_ex_dirs,
    create_ex_dir,
)
from ..utils import (
    user_confirm,
    verify_comment,
    validate_experiment_name,
    experiment_now,
)
from ..config_file import Config, create_ex_yaml

from ..core import (
    initialize,
    upload,
    upload_with_dependency,
    upload_all,
    download_all,
    download_with_dependency,
    download,
    remove_local,
    remove_remote,
    get_ex_dir_names,
    change_experiment_comment,
)

config_file_path = "resutil-conf.yaml"


def get_version():
    from importlib.metadata import version

    return version("resutil")


def main():
    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "--version", action="version", version=f"resutil {get_version()}"
    )
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
    parser_pull.add_argument(
        "-A", "--all", action="store_true", help="pull all experiments"
    )
    parser_pull.add_argument("experiments", nargs="*", help="experiment(s) to pull")
    parser_pull.set_defaults(handler=command_pull)

    # push
    parser_push = subparsers.add_parser("push", help="push experiments")
    parser_push.add_argument(
        "--no-dependency",
        action="store_true",
        help="push experiments without dependencies",
    )
    parser_push.add_argument(
        "-A", "--all", action="store_true", help="push all experiments"
    )
    parser_push.add_argument("experiments", nargs="*", help="experient(s) to push")
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

    # list
    parser_list = subparsers.add_parser("list", help="list remote experiments")
    parser_list.set_defaults(handler=command_list)

    # rm
    parser_rm = subparsers.add_parser("rm", help="remove experiments")
    parser_rm.add_argument(
        "-l",
        "--local",
        action="store_true",
        help="remove local experiment",
    )
    parser_rm.add_argument(
        "-r",
        "--remote",
        action="store_true",
        help="remove remote experiment",
    )
    parser_rm.add_argument(
        "EXPERIMENT",
        nargs="+",
    )
    parser_rm.add_argument(
        "-y", "--yes", action="store_true", help="confirm deletion without prompting"
    )
    parser_rm.set_defaults(handler=command_rm)

    # login
    parser_login = subparsers.add_parser(
        "login", help="Login to resutil server via SSO"
    )
    parser_login.add_argument(
        "--server-url",
        help="resutil server URL (uses resutil-conf.yaml if not specified)",
    )
    parser_login.set_defaults(handler=command_login)

    # logout
    parser_logout = subparsers.add_parser("logout", help="Remove saved credentials")
    parser_logout.set_defaults(handler=command_logout)

    # comment
    parser_comment = subparsers.add_parser(
        "comment", help="Change comment of experiment"
    )
    parser_comment.add_argument(
        "EXPERIMENT",
    )
    parser_comment.add_argument(
        "NEWCOMMENT",
    )
    parser_comment.set_defaults(handler=command_comment)

    # args
    args = parser.parse_args()

    if hasattr(args, "handler"):
        try:
            args.handler(args)
        except (OSError, ValueError, RuntimeError) as exc:
            parser.exit(1, f"resutil: {exc}\n")
        except Exception as exc:
            parser.exit(1, f"resutil: {exc}\n")
    else:
        # No subcommand → launch interactive TUI
        from .interactive import run_interactive

        if not run_interactive():
            # Not initialized → run init wizard, then launch TUI
            command_init(args)
            run_interactive()


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
    config = Config()

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
        with open(os.path.join(results_dir, ".gitignore"), "a", encoding="utf-8") as f:
            f.write("# Resutil result dir\n")
            f.write("# Automatically added by resutil\n")
            f.write("# Files here are not managed by git\n")
            f.write("*\n")
            f.write("!.gitignore\n")

    # set storage type
    while True:
        d = "gcs"
        print("Input storage_type ([bold]gcs[/bold]/gdrive/server): ", end="")
        s = input()
        storage_type = s if s != "" else "gcs"
        if storage_type in ["gcs", "gdrive", "server"]:
            break
    config.set_storage_type(storage_type)

    # set gcs config
    if storage_type == "gcs":
        d = "key.json"
        print(f"Input key file_path [bold]({d})[/bold]: ", end="")
        s = input()
        key_file_path = s if s != "" else "key.json"

        yn = user_confirm(
            f"Do you want to add {key_file_path} to .gitignore?", default="y"
        )
        if yn:
            with open(".gitignore", "a", encoding="utf-8") as f:
                f.write("\n# Resutil config file\n")
                f.write(key_file_path + "\n")

        print("Input bucket name: ", end="")
        bucket_name = input()

        storage_config = {"key_file_path": key_file_path, "bucket_name": bucket_name}

        config.set_storage_config(storage_config)

        try:
            from ..storage import GCS

            GCS(config.storage_config, config.project_name)
        except Exception as e:
            print("❌ Failed to connect to storage.")
            print(f"  [red]{e}[/red]")
            return

    # set gdrive config
    elif storage_type == "gdrive":
        d = "key.json"
        print(f"Input key file_path [bold]({d})[/bold]: ", end="")
        s = input()
        key_file_path = s if s != "" else "key.json"

        yn = user_confirm(
            f"Do you want to add {key_file_path} to .gitignore?", default="y"
        )
        if yn:
            with open(".gitignore", "a", encoding="utf-8") as f:
                f.write("\n# Resutil config file\n")
                f.write(key_file_path + "\n")

        print("Input folder id of base dir: ", end="")
        base_dir_id = input()

        storage_config = {"key_file_path": key_file_path, "base_folder_id": base_dir_id}

        config.set_storage_config(storage_config)

        try:
            from ..storage import GDrive

            GDrive(config.storage_config, config.project_name)
        except Exception as e:
            print("❌ Failed to connect to storage.")
            print(f"  [red]{e}[/red]")
            return

    # set server config
    elif storage_type == "server":
        d = "http://localhost:8080"
        print(f"Input server URL [bold]({d})[/bold]: ", end="")
        s = input()
        server_url = s if s != "" else d

        print("Input bucket name: ", end="")
        bucket_name = input()

        storage_config = {"server_url": server_url, "bucket_name": bucket_name}

        config.set_storage_config(storage_config)

        try:
            from ..storage import ResutilServerStorage

            ResutilServerStorage(config.storage_config, config.project_name)
        except FileNotFoundError:
            print("⚠️ Not logged in yet. Run [bold]resutil login[/bold] after init.")
        except Exception as e:
            print("❌ Failed to connect to server.")
            print(f"  [red]{e}[/red]")
            return

    # save config
    config.save()

    print("✅ Initialized.")


def command_push(args):
    config, storage = initialize()

    if args.experiments:
        for ex_name in args.experiments:
            if args.no_dependency:
                upload(ex_name, config.results_dir, storage)
            else:
                upload_with_dependency(ex_name, config.results_dir, storage)
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
    else:
        print("⚠️ Specify experiment name(s) or use -A option.")


def command_pull(args):
    config, storage = initialize()

    if args.experiments:
        for ex_name in args.experiments:
            if args.no_dependency:
                download(ex_name, config.results_dir, storage)
            else:
                download_with_dependency(ex_name, config.results_dir, storage)
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
    else:
        print("⚠️ Specify experiment name(s) or use -A option.")


def command_add(args):
    config, _ = initialize(connect=False)

    if args.comment is None:
        while True:
            comment = input("📝 Input comment for this experiment: ")
            if verify_comment(comment):
                break
            print(
                '⛔️ Comment string is invalid. It should be at most 200 UTF-8 bytes and not contain any of the following characters: \\ / : * ? " < > |'
            )

    else:
        comment = args.comment

    if not verify_comment(comment):
        raise ValueError("Invalid comment (maximum 200 UTF-8 bytes).")
    dependency = args.dependency if args.dependency is not None else []
    for name in dependency:
        validate_experiment_name(name)

    ex_name = create_ex_dir(
        experiment_now(),
        comment,
        config.results_dir,
    )
    ex_dir_path = join(config.results_dir, ex_name)

    create_ex_yaml(ex_dir_path, dependency)


def command_list(args):
    config, storage = initialize()

    print("📦 Remote experiment list")

    local_ex_names = get_ex_dir_names(config.results_dir)
    remote_ex_names = storage.get_all_experiment_names()
    all_ex_names = sorted(list(set(local_ex_names) | set(remote_ex_names)))

    print("")
    print(" Local |Remote | Experiment name")
    print("-------|-------|------------------------------")
    for ex_name in all_ex_names:
        remote = "✅" if ex_name in remote_ex_names else "  "
        local = "✅" if ex_name in local_ex_names else "  "
        print(f"   {local}  |  {remote}   | {ex_name}")


def command_rm(args):
    for name in args.EXPERIMENT:
        validate_experiment_name(name)
    local = not args.remote or args.local
    remote = not args.local or args.remote
    scope = "local and remote" if local and remote else "local" if local else "remote"
    if not getattr(args, "yes", False) and not user_confirm(
        f"Delete {', '.join(args.EXPERIMENT)} ({scope})?", default="n"
    ):
        return
    config, storage = initialize(connect=remote)
    if remote:
        remove_remote(args.EXPERIMENT, storage)
    if local:
        remove_local(args.EXPERIMENT, config.results_dir)


def command_login(args):
    import secrets
    import time
    import httpx
    from ..storage.server.server import _save_credentials, normalize_server_url

    server_url = args.server_url
    if server_url is None:
        config = Config()
        config.load()
        if config.storage_type != "server":
            raise ValueError("Use --server-url for server login.")
        server_url = config.storage_config["server_url"]
    server_url = normalize_server_url(server_url)
    state = secrets.token_urlsafe(32)
    received_tokens = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def do_GET(self):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            valid = (
                parsed.path == "/callback"
                and secrets.compare_digest(params.get("state", [""])[0], state)
                and bool(params.get("id_token", [""])[0])
            )
            if not valid:
                self.send_response(400)
                self.end_headers()
                return
            received_tokens["id_token"] = params["id_token"][0]
            received_tokens["refresh_token"] = params.get("refresh_token", [""])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(
                "<!doctype html><meta charset='utf-8'><p>Login successful. You may close this window.</p>".encode(
                    "utf-8"
                )
            )

        def log_message(self, format, *args):
            pass

    # Bind and listen before opening the browser; let the OS choose the port.
    with HTTPServer(("localhost", 0), CallbackHandler) as server:
        server.timeout = 1
        resp = httpx.get(
            f"{server_url}/auth/login",
            params={"port": server.server_port, "state": state},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        login_url = data["login_url"]
        # Explicitly require state round-tripping; never fall back to accepting unbound tokens.
        if parse_qs(urlparse(login_url).query).get("state") != [state]:
            raise RuntimeError(
                "Server does not support login state. Apply docs/server-login-state.patch to resutil-server and deploy it first."
            )
        print(f"🔐 Opening browser for login: {login_url}")
        webbrowser.open(login_url)
        deadline = time.monotonic() + 120
        while not received_tokens and time.monotonic() < deadline:
            server.handle_request()
    if not received_tokens:
        raise TimeoutError("Login failed: no valid callback within 120 seconds.")
    _save_credentials(
        {
            "server_url": server_url,
            "id_token": received_tokens["id_token"],
            "refresh_token": received_tokens["refresh_token"],
            "api_key": data.get("api_key"),
        }
    )
    print("✅ Login successful!")


def command_logout(args):
    credentials_path = Path.home() / ".resutil" / "credentials.json"
    if credentials_path.exists():
        credentials_path.unlink()
        print("✅ Logged out. Credentials removed.")
    else:
        print("ℹ️ No credentials found.")


def command_comment(args):
    config, storage = initialize()
    new_name = change_experiment_comment(
        config.results_dir, args.EXPERIMENT, args.NEWCOMMENT, storage
    )
    print(f"✅ Renamed {args.EXPERIMENT} to {new_name}")
