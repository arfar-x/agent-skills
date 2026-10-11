"""Lenient matching in the shared text patch (lib/text_patch.py -> _shared)."""

import pytest

from lib.text_patch import PatchError, replace_text

ZWNJ = "‌"


def test_exact_match_is_preferred():
    assert replace_text("cap 100", "100", "120") == ("cap 120", 1)


def test_zero_width_non_joiner_differences_still_match_and_keep_the_rest():
    text = f"به سقف ۱۰۰ فیلتر ذخیره{ZWNJ}شده رسیده"
    out, count = replace_text(text, "سقف ۱۰۰ فیلتر ذخیره شده", "سقف ۱۲۰ فیلتر ذخیره‌شده")
    assert count == 1
    assert out == "به سقف ۱۲۰ فیلتر ذخیره‌شده رسیده"


def test_missing_zwnj_in_the_page_still_matches():
    out, _ = replace_text("ذخیرهشده رسیده", f"ذخیره{ZWNJ}شده", "X")
    assert out == "X رسیده"


def test_arabic_and_persian_letter_forms_are_equivalent():
    out, _ = replace_text("کاربر یک فیلتر", "كاربر يك", "user one")
    assert out == "user one فیلتر"


def test_whitespace_runs_are_equivalent():
    out, _ = replace_text("a  b\nc", "a b c", "x")
    assert out == "x"


def test_lenient_matching_keeps_the_uniqueness_rule():
    with pytest.raises(PatchError, match="ambiguous"):
        replace_text(f"ذخیره{ZWNJ}شده و ذخیرهشده", "ذخیره شده", "x")


def test_still_not_found_when_the_text_really_differs():
    with pytest.raises(PatchError, match="not found"):
        replace_text("cap 100", "cap 200", "x")
