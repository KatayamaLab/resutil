from datetime import datetime
import os
import pytest

from resutil.ex_dir import create_ex_dir, delete_ex_dir, change_comment


def test_create_ex_dir(mocker):
    mocker.patch("os.makedirs", return_value=None)
    path = create_ex_dir(datetime(2024, 1, 1, 0, 0, 0, 0), "test", "results")
    assert path == "aaaaaa_20240101T000000_test"


def test_delete_ex_dir(mocker):
    mocker.patch("shutil.rmtree", return_value=None)
    assert delete_ex_dir("results/aaaaaa_20240101T000000_test")

    # check if raise error
    with pytest.raises(ValueError) as exec_info:
        delete_ex_dir("aaa")
    assert str(exec_info.value) == "aaa does not exist"


def test_change_comment_():
    os.makedirs("results/aaaaaaa_20240101T000000_test")
    new_ex_name = change_comment("results", "aaaaaaa_20240101T000000_test", "new_test")
    assert new_ex_name == "aaaaaaa_20240101T000000_new_test"
    os.rmdir("results/aaaaaaa_20240101T000000_new_test")
