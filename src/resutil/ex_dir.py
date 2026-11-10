from pathlib import Path
import shutil
from uuid import uuid4


from .utils import (
    timestamp_parts,
    validate_experiment_name,
    verify_comment,
    experiment_path,
    write_yaml,
    atomic_write,
    normalize_dependency,
)


def create_ex_dir(now, comment, results_dir):
    if not verify_comment(comment):
        raise ValueError("Invalid comment (maximum 200 UTF-8 bytes).")
    prefix, stamp = timestamp_parts(now)
    stem = f"{prefix}_{stamp}"
    name = f"{stem}_{comment}" if comment else stem
    Path(results_dir).mkdir(parents=True, exist_ok=True)
    while True:
        try:
            experiment_path(results_dir, name).mkdir()
            return name
        except FileExistsError:
            # Atomic mkdir resolves collisions between concurrent processes.
            name = f"{stem}_{uuid4().hex[:8]}" + (f"_{comment}" if comment else "")


def commented_name(ex_name, comment):
    validate_experiment_name(ex_name)
    if not verify_comment(comment):
        raise ValueError("Invalid comment (maximum 200 UTF-8 bytes).")
    return validate_experiment_name(
        "_".join(ex_name.split("_")[:2]) + ("_" + comment if comment else "")
    )


def rewrite_metadata(data, old_name, new_name):
    from .utils import normalize_dependency

    deps = [normalize_dependency(d) for d in data.get("dependency", [])]
    data["dependency"] = [new_name if d == old_name else d for d in deps]
    if data.get("result_dir") and normalize_dependency(data["result_dir"]) == old_name:
        data["result_dir"] = new_name
    return data


def _metadata_updates(results_dir, old_name, new_name, comment):
    import yaml

    updates = []
    for name in get_ex_dir_names(results_dir):
        metadata = experiment_path(results_dir, name) / "resutil-exp.yaml"
        if not metadata.exists():
            continue
        original = metadata.read_text(encoding="utf-8")
        data = yaml.safe_load(original) or {}
        deps = [normalize_dependency(d) for d in data.get("dependency", [])]
        if name == old_name or old_name in deps:
            data = rewrite_metadata(data, old_name, new_name)
            if name == old_name:
                data["comment"] = comment
                data["result_dir"] = new_name
            updates.append((metadata, data, original))
    return updates


def _apply_metadata_updates(updates):
    written = []
    try:
        for metadata, data, original in updates:
            write_yaml(metadata, data)
            written.append((metadata, original))
    except BaseException:
        for metadata, original in reversed(written):
            atomic_write(metadata, original)
        raise


def update_local_references(results_dir, old_name, new_name, comment):
    # Also used when the renamed target exists only remotely.
    _apply_metadata_updates(_metadata_updates(results_dir, old_name, new_name, comment))


def change_comment(results_dir, ex_name, new_comment):
    path = experiment_path(results_dir, ex_name)
    if not path.is_dir():
        raise FileNotFoundError(path)
    new_name = commented_name(ex_name, new_comment)
    if new_name == ex_name:
        return ex_name
    target = experiment_path(results_dir, new_name)
    if target.exists():
        raise FileExistsError(target)
    updates = _metadata_updates(results_dir, ex_name, new_name, new_comment)
    path.rename(target)
    updates = [
        (
            target / metadata.name if metadata.parent == path else metadata,
            data,
            original,
        )
        for metadata, data, original in updates
    ]
    try:
        _apply_metadata_updates(updates)
    except BaseException:
        target.rename(path)
        raise
    return new_name


def get_ex_dir_names(results_dir):
    root = Path(results_dir)
    if not root.is_dir():
        return []
    names = []
    for path in root.iterdir():
        if (
            path.is_dir()
            and not path.is_symlink()
            and not path.name.startswith(".")
            and path.name != "_debug"
        ):
            try:
                validate_experiment_name(path.name)
            except ValueError:
                continue
            names.append(path.name)
    return names


def find_unuploaded_ex_dirs(results_dir_path, storage):
    from .sync import is_synced

    remote = set(storage.get_all_experiment_names())
    return [
        name
        for name in get_ex_dir_names(results_dir_path)
        if name not in remote or not is_synced(results_dir_path, name, storage)
    ]


def find_undownloaded_ex_dirs(results_dir_path, storage):
    local = set(get_ex_dir_names(results_dir_path))
    names = storage.get_all_experiment_names()
    for name in names:
        validate_experiment_name(name)
    return [name for name in names if name not in local]


def delete_ex_dir(ex_dir_path):
    path = Path(ex_dir_path)
    if not path.exists():
        raise FileNotFoundError(path)
    if path.is_symlink():
        raise ValueError("Refusing to delete a symlink.")
    validate_experiment_name(path.name)
    shutil.rmtree(path)
    return True
