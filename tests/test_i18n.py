import re
import string

import pytest

from resutil import i18n
from resutil.i18n import JA, get_language, t


@pytest.fixture(autouse=True)
def clean_locale(monkeypatch):
    for name in ("RESUTIL_LANG", "LC_ALL", "LC_MESSAGES", "LANG"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(i18n.sys, "platform", "linux")
    i18n._os_language.cache_clear()
    yield
    i18n._os_language.cache_clear()


def test_resutil_lang_overrides_locale(monkeypatch):
    monkeypatch.setenv("LANG", "ja_JP.UTF-8")
    monkeypatch.setenv("RESUTIL_LANG", "en")
    assert get_language() == "en"
    monkeypatch.setenv("RESUTIL_LANG", "ja")
    assert get_language() == "ja"


@pytest.mark.parametrize(
    "env, expected",
    [
        ({"LANG": "ja_JP.UTF-8"}, "ja"),
        ({"LANG": "en_US.UTF-8"}, "en"),
        ({"LC_ALL": "ja_JP.eucJP", "LANG": "en_US.UTF-8"}, "ja"),
        ({"LANG": "fr_FR.UTF-8"}, "en"),
        ({}, "en"),
    ],
)
def test_locale_environment(monkeypatch, env, expected):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    assert get_language() == expected


def test_c_locale_falls_back_to_macos_setting(monkeypatch):
    monkeypatch.setenv("LANG", "C.UTF-8")
    monkeypatch.setattr(i18n.sys, "platform", "darwin")
    monkeypatch.setattr(i18n, "_macos_language", lambda: "ja")
    assert get_language() == "ja"


def test_translation_and_placeholders(monkeypatch):
    monkeypatch.setenv("RESUTIL_LANG", "ja")
    assert t("✅ Done") == "✅ 完了"
    assert t("🗂️ Uploading: {name}", name="x") == "🗂️ アップロード中: x"
    assert t("untranslated {x}", x=1) == "untranslated 1"
    monkeypatch.setenv("RESUTIL_LANG", "en")
    assert t("🗂️ Uploading: {name}", name="x") == "🗂️ Uploading: x"


def test_catalog_placeholders_match():
    def fields(text):
        return sorted(name for _, name, _, _ in string.Formatter().parse(text) if name)

    for english, japanese in JA.items():
        assert fields(english) == fields(japanese), english


def test_every_translated_call_site_has_an_entry():
    from pathlib import Path

    root = Path(i18n.__file__).parent
    pattern = re.compile(r'\bt\(\s*((?:"[^"\n]*"\s*)+|\'[^\'\n]*\')')
    missing = []
    for path in root.rglob("*.py"):
        for match in pattern.finditer(path.read_text(encoding="utf-8")):
            parts = re.findall(r'"([^"\n]*)"|\'([^\'\n]*)\'', match.group(1))
            key = "".join(a or b for a, b in parts).encode().decode("unicode_escape")
            key = key.encode("latin-1").decode("utf-8")
            if key not in JA:
                missing.append(f"{path.name}: {key}")
    assert not missing
