from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from resutil.utils import (
    to_base26,
    parse_result_dirs,
    verify_comment,
    validate_experiment_name,
    normalize_dependency,
    experiment_now,
    timestamp_parts,
)
from conftest import A


def test_to_base26():
    assert to_base26(0) == "aaaaaa"


def test_parse_result_dirs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "results"
    assert parse_result_dirs(
        [f"results/{A}/data.csv", f"--input=results/{A}/x"], str(root)
    ) == [root / A]
    assert parse_result_dirs([f"outside/{A}", "--flag", "results"], str(root)) == []


@pytest.mark.parametrize(
    "text", ["x/y", "x\\\\y", "x:y", "x\\n", "a" * 201, "日" * 67, "tail."]
)
def test_invalid_comments(text):
    assert not verify_comment(text)


def test_unicode_comment():
    assert verify_comment("日" * 60)
    assert verify_comment("experiment#1")


@pytest.mark.parametrize("name", [".", "..", "../x", "/tmp/x", "x/y", ""])
def test_unsafe_names(name):
    with pytest.raises(ValueError):
        validate_experiment_name(name)


def test_legacy_dependencies():
    assert normalize_dependency(f"results/{A}") == A
    assert normalize_dependency(f"C:\\\\results\\\\{A}") == A


def test_timezone(monkeypatch):
    monkeypatch.setenv("RESUTIL_TIMEZONE", "Asia/Tokyo")
    assert experiment_now().utcoffset().total_seconds() == 9 * 3600
    instant = datetime(2024, 1, 1, tzinfo=timezone.utc)
    assert (
        timestamp_parts(instant)[0]
        == timestamp_parts(instant.astimezone(ZoneInfo("Asia/Tokyo")))[0]
    )
