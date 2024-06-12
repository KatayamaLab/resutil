from resutil.utils import to_base26, parse_result_dirs


def test_to_base26():
    assert to_base26(0) == "aaaaa"


def test_parse_result_dirs():
    text = "aaaaa_20240101T000000_test1\naaaaa_20240101T000000_test2"
    assert parse_result_dirs(text) == [
        "aaaaa_20240101T000000_test1",
        "aaaaa_20240101T000000_test2",
    ]

    text = ""
    assert parse_result_dirs(text) == []

    text = "./aaaaa_20240101T000000_test1/test\n aaaaa_20240101T000000_test2 "
    assert parse_result_dirs(text) == [
        "aaaaa_20240101T000000_test1",
        "aaaaa_20240101T000000_test2",
    ]

    text = "./aaaaa_20240101T000000_test1/test"
    assert parse_result_dirs(text) == [
        "aaaaa_20240101T000000_test1",
    ]

    text = "./aaaaa_20240101T000000_test1\\test"
    assert parse_result_dirs(text) == [
        "aaaaa_20240101T000000_test1",
    ]

    text = "./aaaaa_20240101T000000_test1 test"
    assert parse_result_dirs(text) == [
        "aaaaa_20240101T000000_test1",
    ]

    text = "test"
    assert parse_result_dirs(text) == []
