import os
import subprocess
import sys

import pytest
import yaml


@pytest.mark.parametrize("fail", [False, True])
def test_decorated_program_from_subdirectory(tmp_path, fail):
    child = tmp_path / "child"
    child.mkdir()
    (tmp_path / "resutil-conf.yaml").write_text(
        yaml.safe_dump(
            {
                "project_name": "smoke",
                "results_dir": "results",
                "storage_type": "server",
                "storage_config": {
                    "server_url": "https://unused.invalid",
                    "bucket_name": "test",
                },
            }
        ),
        encoding="utf-8",
    )
    script = child / "program.py"
    script.write_text(
        "from pathlib import Path\n"
        "import resutil\n"
        "@resutil.main()\n"
        "def run(params):\n"
        "    assert Path.cwd().name == 'child'\n"
        "    (Path(params.ex_dir) / 'data.txt').write_text('result', encoding='utf-8')\n"
        + ("    raise ValueError('user failure')\n" if fail else "    return 42\n")
        + "run()\n",
        encoding="utf-8",
    )
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("RESUTIL_", "RESUTIIL_"))
    }
    env.update(
        RESUTIL_NO_REMOTE="1", RESUTIL_NO_INTERACTIVE="1", RESUTIL_TIMEZONE="Asia/Tokyo"
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=child,
        env=env,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == (1 if fail else 0), result.stderr
    results = list((tmp_path / "results").iterdir())
    assert len(results) == 1
    assert (results[0] / "data.txt").read_text(encoding="utf-8") == "result"
    metadata = yaml.safe_load(
        (results[0] / "resutil-exp.yaml").read_text(encoding="utf-8")
    )
    assert metadata["started_at"].endswith("+09:00")
    assert "Experiment directory" in result.stdout


def test_cli_rm_rejects_results_root(tmp_path):
    marker = tmp_path / "keep.txt"
    marker.write_text("keep", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "resutil.cli", "rm", "-l", "--yes", "."],
        cwd=tmp_path,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 1
    assert "Invalid experiment name" in result.stderr
    assert marker.exists()
