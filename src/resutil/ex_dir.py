from datetime import datetime
import os
import shutil
from glob import glob
from os.path import basename, normpath, join


from .utils import to_base26, parse_result_dirs


def create_ex_dir(now, comment, results_dir):
    base_time = datetime(2024, 1, 1, 0, 0, 0, 0)
    now_str = now.strftime("%Y%m%dT%H%M%S")

    elapsed_time = (now - base_time).total_seconds() / 60
    str26 = to_base26(int(elapsed_time))

    if comment == "":
        ex_name = f"{str26}_{now_str}"
    else:
        ex_name = f"{str26}_{now_str}_{comment}"

    ex_dir_path = os.path.join(results_dir, ex_name)

    # if exist, throw error
    if os.path.isdir(ex_dir_path):
        raise FileExistsError(f"{ex_dir_path} is already exist")

    os.makedirs(ex_dir_path)

    return ex_name


def change_comment(results_dir, ex_name, new_comment):
    ex_dir_path = os.path.join(results_dir, ex_name)
    if not os.path.isdir(ex_dir_path):
        raise FileNotFoundError(f"{ex_dir_path} does not exist")
    new_ex_name = f"{ex_name.split('_')[0]}_{ex_name.split('_')[1]}_{new_comment}"
    new_ex_dir_path = os.path.join(results_dir, new_ex_name)
    os.rename(ex_dir_path, new_ex_dir_path)
    return new_ex_name


def get_ex_dir_names(results_dir):
    ex_dir_paths = glob(join(results_dir + "/*/"))
    ex_dir_names = [
        basename(normpath(p)) for p in ex_dir_paths if basename(normpath(p)) != "_debug"
    ]
    return ex_dir_names


def find_unuploaded_ex_dirs(results_dir_path, storage):
    remote_ex_dir_names = storage.get_all_experiment_names()
    local_ex_dir_names = get_ex_dir_names(results_dir_path)
    ex_dir_names_to_upload = []
    for local_ex_dir_name in local_ex_dir_names:
        if local_ex_dir_name not in remote_ex_dir_names:
            ex_dir_names_to_upload.append(local_ex_dir_name)
    return ex_dir_names_to_upload


def find_undownloaded_ex_dirs(results_dir_path, storage):
    remote_ex_dir_names = storage.get_all_experiment_names()
    local_ex_dir_names = get_ex_dir_names(results_dir_path)
    ex_dir_names_to_download = []
    for remote_ex_dir_name in remote_ex_dir_names:
        if remote_ex_dir_name not in local_ex_dir_names:
            ex_dir_names_to_download.append(remote_ex_dir_name)
    return ex_dir_names_to_download


def delete_ex_dir(ex_dir_path):
    if os.path.exists(ex_dir_path):
        shutil.rmtree(ex_dir_path)
    return True
