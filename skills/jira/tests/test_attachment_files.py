"""Tests for the shared local-file helper (skills/_shared/attachments/files.py),
exercised through Jira's symlink to it -- Confluence links the same file."""

import os

import pytest

from lib.attachment_files import (
    AttachmentFileError,
    describe_upload_file,
    prepare_download_target,
    safe_filename,
    stream_to_file,
)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("report.pdf", "report.pdf"),
        ("../../etc/passwd", "passwd"),
        ("a\\b\\c.txt", "c.txt"),
        ("/abs/path/x.png", "x.png"),
        ("we\x00ird\nname.txt", "weirdname.txt"),
        ("  padded.txt  ", "padded.txt"),
    ],
)
def test_safe_filename_strips_directories_and_control_chars(raw, expected):
    assert safe_filename(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", ".", "..", "...", "dir/", None, 7])
def test_safe_filename_rejects_unusable_names(raw):
    with pytest.raises(AttachmentFileError):
        safe_filename(raw)


def test_safe_filename_truncates_long_names_keeping_the_extension():
    out = safe_filename("a" * 400 + ".pdf")
    assert len(out) <= 200 and out.endswith(".pdf")


def test_download_target_refuses_overwrite_unless_asked(tmp_path):
    (tmp_path / "x.txt").write_text("old")
    with pytest.raises(AttachmentFileError, match="already exists"):
        prepare_download_target("x.txt", str(tmp_path), "jira")
    assert prepare_download_target("x.txt", str(tmp_path), "jira", overwrite=True) == tmp_path.resolve() / "x.txt"


def test_download_target_cannot_escape_the_directory(tmp_path):
    assert prepare_download_target("../../evil.sh", str(tmp_path), "jira").parent == tmp_path.resolve()


def test_stream_to_file_writes_atomically(tmp_path):
    target = tmp_path / "f.bin"
    assert stream_to_file([b"ab", b"", b"cd"], target, max_bytes=10) == 4
    assert target.read_bytes() == b"abcd"
    assert os.listdir(tmp_path) == ["f.bin"]


def test_stream_to_file_over_limit_leaves_nothing_behind(tmp_path):
    target = tmp_path / "f.bin"
    with pytest.raises(AttachmentFileError, match="limit"):
        stream_to_file([b"abc", b"def"], target, max_bytes=4)
    assert os.listdir(tmp_path) == []


def test_describe_upload_file(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("hello")
    info = describe_upload_file(str(f))
    assert info == {"path": str(f.resolve()), "filename": "notes.txt", "size_bytes": 5, "media_type": "text/plain"}
    assert describe_upload_file(str(f), filename="../other.md")["filename"] == "other.md"


def test_describe_upload_file_resolves_symlinks(tmp_path):
    real = tmp_path / "real.txt"
    real.write_text("x")
    link = tmp_path / "link.txt"
    link.symlink_to(real)
    assert describe_upload_file(str(link))["path"] == str(real.resolve())


def test_describe_upload_file_rejects_bad_input(tmp_path):
    (tmp_path / "empty.txt").write_text("")
    (tmp_path / "big.txt").write_text("12345")
    with pytest.raises(AttachmentFileError, match="not found"):
        describe_upload_file(str(tmp_path / "missing"))
    with pytest.raises(AttachmentFileError, match="Not a regular file"):
        describe_upload_file(str(tmp_path))
    with pytest.raises(AttachmentFileError, match="empty"):
        describe_upload_file(str(tmp_path / "empty.txt"))
    with pytest.raises(AttachmentFileError, match="limit"):
        describe_upload_file(str(tmp_path / "big.txt"), max_bytes=4)
    with pytest.raises(AttachmentFileError):
        describe_upload_file("  ")
