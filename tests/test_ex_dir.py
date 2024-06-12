from datetime import datetime

import pytest

from resutil.ex_dir import create_ex_dir, delete_ex_dir


def test_create_ex_dir(mocker):
    mocker.patch("os.makedirs", return_value=None)
    path = create_ex_dir(datetime(2024, 1, 1, 0, 0, 0, 0), "test", "results")
    assert path == "results/aaaaa_20240101T000000_test"


def test_delete_ex_dir(mocker):
    mocker.patch("shutil.rmtree", return_value=None)
    assert delete_ex_dir("results/aaaaa_20240101T000000_test")

    # check if raise error
    with pytest.raises(ValueError) as exec_info:
        delete_ex_dir("aaa")
    assert str(exec_info.value) == "aaa does not exist"
