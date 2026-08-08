import pytest

from lib.utils import (
    InvalidChatIdError,
    UnsafeFilenameError,
    is_inside_git_worktree,
    is_service_notifications_peer,
    normalize_chat_id,
    redact,
    resolve_peer_kind,
    sanitize_download_filename,
)


# --------------------------------------------------------------------------
# normalize_chat_id
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("777000", 777000),
        (" 777000 ", 777000),
        ("+777000", 777000),
        ("0777000", 777000),
        ("-777000", -777000),
        (777000, 777000),
        (-42, -42),
    ],
)
def test_normalize_chat_id_accepts_numeric_spellings(raw, expected):
    assert normalize_chat_id(raw) == expected


@pytest.mark.parametrize("bad", ["@john", "t.me/joinchat/abc", "+1 555 123 4567", "abc123", "", "  ", None, 1.5, [1]])
def test_normalize_chat_id_rejects_non_numeric_targets(bad):
    with pytest.raises(InvalidChatIdError):
        normalize_chat_id(bad)


def test_normalize_chat_id_rejects_peer_shaped_garbage():
    with pytest.raises(InvalidChatIdError):
        normalize_chat_id("PeerUser(user_id=777000)")


# --------------------------------------------------------------------------
# resolve_peer_kind / marking scheme round-trips
# --------------------------------------------------------------------------


def test_resolve_peer_kind_user():
    assert resolve_peer_kind(777000) == ("user", 777000)


def test_resolve_peer_kind_chat():
    assert resolve_peer_kind(-42) == ("chat", 42)


def test_resolve_peer_kind_channel_round_trips_through_mark_offset():
    marked = -1_000_000_000_000 - 555
    assert resolve_peer_kind(marked) == ("channel", 555)


# --------------------------------------------------------------------------
# OTP-account denylist matching
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "marked_id",
    [
        777000,
        -777000,  # sign-spoofed
        -1_000_000_000_000 - 777000,  # channel-marked spoof of the same magnitude
    ],
)
def test_is_service_notifications_peer_catches_every_spelling(marked_id):
    assert is_service_notifications_peer(marked_id) is True


@pytest.mark.parametrize("marked_id", [777001, -777001, 123456, -1_000_000_000_000 - 123])
def test_is_service_notifications_peer_leaves_other_ids_alone(marked_id):
    assert is_service_notifications_peer(marked_id) is False


# --------------------------------------------------------------------------
# git worktree detection
# --------------------------------------------------------------------------


def test_is_inside_git_worktree_true_for_this_repo():
    # tests/ itself lives inside this repo's checkout.
    assert is_inside_git_worktree(__file__) is True


def test_is_inside_git_worktree_false_for_tmp(tmp_path):
    assert is_inside_git_worktree(tmp_path / "session.json") is False


def test_is_inside_git_worktree_detects_worktree_file_form(tmp_path):
    # A git worktree's .git is a *file*, not a directory -- .exists() must
    # still catch it.
    (tmp_path / ".git").write_text("gitdir: /somewhere/else\n")
    assert is_inside_git_worktree(tmp_path / "nested" / "session.json") is True


# --------------------------------------------------------------------------
# filename sanitizing
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        ".bashrc",
        ".hidden",
        "payload.sh",
        "payload.py",
        "x.desktop",
        "malware.exe",
        "script.ps1",
        "",
        ".",
        "..",
    ],
)
def test_sanitize_download_filename_refuses_unsafe_names(raw):
    with pytest.raises(UnsafeFilenameError):
        sanitize_download_filename(raw)


@pytest.mark.parametrize(
    "raw,expected_basename",
    [
        ("../../.ssh/authorized_keys", "authorized_keys"),
        ("../../../etc/passwd", "passwd"),
        ("../../photo.jpg", "photo.jpg"),
    ],
)
def test_sanitize_download_filename_defeats_traversal_via_basename(raw, expected_basename):
    # Traversal is neutralized by taking only the basename, not by
    # refusing the input outright -- the directory components never reach
    # the filesystem, so the result is a plain, harmless name written
    # inside the caller's out_dir, never at the traversed-to location.
    assert sanitize_download_filename(raw) == expected_basename


def test_sanitize_download_filename_allows_ordinary_names():
    assert sanitize_download_filename("vacation_photo.jpg") == "vacation_photo.jpg"


# --------------------------------------------------------------------------
# redaction
# --------------------------------------------------------------------------


def test_redact_masks_otp_code_near_keyword():
    masked, count = redact("your login code is 483920, do not share it")
    assert "483920" not in masked
    assert count == 1
    assert "[REDACTED:otp]" in masked


def test_redact_masks_code_before_keyword_too():
    masked, count = redact("948213 is your verification code")
    assert "948213" not in masked
    assert count == 1


def test_redact_masks_token_shapes():
    masked, count = redact("key: sk-abcdefghij1234567890 and Bearer xyzxyzxyzxyz1234567890")
    assert count == 2
    assert "sk-abcdefghij1234567890" not in masked


def test_redact_masks_login_link():
    # No trailing digits right after "login/" here -- deliberately, since
    # "login" is itself one of the OTP code-words and a digit run shortly
    # after it would additionally trip the OTP-near-keyword pattern too
    # (both are real, independently-triggered matches; kept separate here
    # so this test isolates the login-link pattern specifically).
    masked, count = redact("click t.me/login/AbCdEfGh to sign in")
    assert count == 1
    assert "t.me/login" not in masked


def test_redact_masks_login_link_and_a_trailing_code_as_two_matches():
    masked, count = redact("click t.me/login/482910 to sign in")
    assert count == 2  # the link pattern, and "login" + nearby digits both fire
    assert "t.me/login" not in masked
    assert "482910" not in masked


def test_redact_leaves_clean_text_untouched():
    text = "let's meet at noon tomorrow, sound good?"
    masked, count = redact(text)
    assert masked == text
    assert count == 0


def test_redact_handles_empty_and_none():
    assert redact("") == ("", 0)
    assert redact(None) == ("", 0)


# --------------------------------------------------------------------------
# Cases that turned out to be caught (better than assumed) vs. the one
# genuine known limit. All three were originally written as "known limits"
# on the assumption a plain regex couldn't handle them; running the suite
# against the real implementation showed two of the three assumptions were
# wrong, so they're corrected here rather than left asserting a false limit.
# --------------------------------------------------------------------------


def test_redact_catches_a_code_split_across_lines():
    # \D (non-digit) matches a newline too, so the keyword-to-digits
    # "window" is not actually confined to one line -- this is caught.
    text = "your code is\n483920\nplease enter it"
    masked, count = redact(text)
    assert count == 1
    assert "483920" not in masked


def test_redact_catches_non_ascii_decimal_digits():
    # Python's \d is Unicode-aware by default (no re.ASCII flag is set),
    # so Extended Arabic-Indic digits match \d{4,8} just like ASCII ones.
    text = "your code is ۴۸۳۹۲۰, do not share it"
    masked, count = redact(text)
    assert count == 1
    assert "۴۸۳۹۲۰" not in masked


def test_redact_known_limit_zero_width_characters():
    # The one genuine known limitation pinned here: a zero-width character
    # embedded inside the digit run breaks \d{4,8}'s contiguous match, and
    # nothing in this regex-based approach un-splits it.
    text = "your code is 48​3920, do not share it"
    masked, count = redact(text)
    assert count == 0
