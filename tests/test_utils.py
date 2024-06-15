from resutil.utils import to_base26, parse_result_dirs
import resutil.utils as utils


def test_to_base26():
    assert to_base26(0) == "aaaaaa"


def test_parse_result_dirs():
    text = "aaaaaa_20240101T000000_test1\naaaaaa_20240101T000000_test2"
    assert parse_result_dirs(text) == [
        "aaaaaa_20240101T000000_test1",
        "aaaaaa_20240101T000000_test2",
    ]

    text = ""
    assert parse_result_dirs(text) == []

    text = "./aaaaaa_20240101T000000_test1/test\n aaaaaa_20240101T000000_test2 "
    assert parse_result_dirs(text) == [
        "aaaaaa_20240101T000000_test1",
        "aaaaaa_20240101T000000_test2",
    ]

    text = "./aaaaaa_20240101T000000_test1/test"
    assert parse_result_dirs(text) == [
        "aaaaaa_20240101T000000_test1",
    ]

    text = "./aaaaaa_20240101T000000_test1\\test"
    assert parse_result_dirs(text) == [
        "aaaaaa_20240101T000000_test1",
    ]

    text = "./aaaaaa_20240101T000000_test1 test"
    assert parse_result_dirs(text) == [
        "aaaaaa_20240101T000000_test1",
    ]

    text = "test"
    assert parse_result_dirs(text) == []


def test_verify_comment():
    assert utils.verify_comment("test")
    assert not utils.verify_comment("aaa/a/aa")
    assert not utils.verify_comment("aaa:aaa")
    assert not utils.verify_comment('aaa"aaa')
    assert not utils.verify_comment("a" * 201)
