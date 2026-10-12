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


# --- Confinement to AGENT_SKILLS_ATTACHMENT_DIR -----------------------------
# conftest sets the directory to tmp_path; these tests move or unset it.

import base64  # noqa: E402

from lib.attachment_files import ATTACHMENT_DIR_ENV, describe_upload, describe_upload_content  # noqa: E402


@pytest.fixture
def root(tmp_path, monkeypatch):
    path = tmp_path / "root"
    path.mkdir()
    monkeypatch.setenv(ATTACHMENT_DIR_ENV, str(path))
    return path


def test_upload_from_a_path_is_disabled_without_the_directory(tmp_path, monkeypatch):
    monkeypatch.delenv(ATTACHMENT_DIR_ENV)
    f = tmp_path / "notes.txt"
    f.write_text("hello")
    with pytest.raises(AttachmentFileError, match="disabled"):
        describe_upload_file(str(f))


def test_relative_paths_are_taken_from_the_directory(root):
    (root / "sub").mkdir()
    (root / "sub" / "a.txt").write_text("x")
    assert describe_upload_file("sub/a.txt")["path"] == str((root / "sub" / "a.txt").resolve())


@pytest.mark.parametrize("path", ["/proc/self/environ", "/etc/hostname", "../outside.txt", "sub/../../outside.txt"])
def test_paths_outside_the_directory_are_refused(root, path):
    (root.parent / "outside.txt").write_text("secret")
    (root / "sub").mkdir()
    with pytest.raises(AttachmentFileError, match="outside the attachment directory"):
        describe_upload_file(path)


def test_a_symlink_out_of_the_directory_is_refused(root):
    (root.parent / "outside.txt").write_text("secret")
    (root / "link.txt").symlink_to(root.parent / "outside.txt")
    with pytest.raises(AttachmentFileError, match="outside the attachment directory"):
        describe_upload_file("link.txt")


def test_a_symlink_to_a_secret_inside_the_directory_is_refused(root):
    (root / ".env").write_text("TOKEN=x")
    (root / "notes.txt").symlink_to(root / ".env")
    with pytest.raises(AttachmentFileError, match="hidden"):
        describe_upload_file("notes.txt")


@pytest.mark.parametrize(
    "name", [".env", ".env.local", "prod.env", ".ssh/id_rsa", "keys/id_ed25519", "server.pem", "tls.key",
             "store.p12", "credentials", "secrets.json", ".git/config"],
)
def test_hidden_and_secret_looking_files_are_refused_inside_the_directory(root, name):
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("x")
    with pytest.raises(AttachmentFileError, match="hidden|secret"):
        describe_upload_file(name)


@pytest.mark.parametrize("value", ["/", "/does/not/exist"])
def test_an_unusable_directory_setting_is_an_error(tmp_path, monkeypatch, value):
    monkeypatch.setenv(ATTACHMENT_DIR_ENV, value)
    f = tmp_path / "a.txt"
    f.write_text("x")
    with pytest.raises(AttachmentFileError, match=ATTACHMENT_DIR_ENV):
        describe_upload_file(str(f))


def test_download_out_dir_must_be_inside_the_directory(root):
    assert prepare_download_target("a.txt", "saved", "jira").parent == (root / "saved").resolve()
    for out_dir in ("/tmp", "../elsewhere", ".hidden"):
        with pytest.raises(AttachmentFileError):
            prepare_download_target("a.txt", out_dir, "jira")


def test_download_out_dir_is_disabled_without_the_directory_but_scratch_works(tmp_path, monkeypatch):
    monkeypatch.delenv(ATTACHMENT_DIR_ENV)
    with pytest.raises(AttachmentFileError, match="disabled"):
        prepare_download_target("a.txt", str(tmp_path), "jira")
    assert prepare_download_target("a.txt", None, "jira", overwrite=True).name == "a.txt"


# --- Uploading content instead of a file ------------------------------------


def test_content_upload_needs_no_directory(monkeypatch):
    monkeypatch.delenv(ATTACHMENT_DIR_ENV)
    info = describe_upload_content(content="سلام", filename="note.md")
    assert info["data"] == "سلام".encode() and info["filename"] == "note.md" and info["size_bytes"] == 8
    raw = describe_upload_content(content_base64=base64.b64encode(b"\x89PNG").decode(), filename="a/../x.png")
    assert raw == {"data": b"\x89PNG", "filename": "x.png", "size_bytes": 4, "media_type": "image/png"}


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"filename": "a.txt"}, "exactly one"),
        ({"content": "x", "content_base64": "eA==", "filename": "a.txt"}, "exactly one"),
        ({"content": "x"}, "filename"),
        ({"content_base64": "not base64!", "filename": "a.bin"}, "base64"),
        ({"content": "", "filename": "a.txt"}, "empty"),
        ({"content": "12345", "filename": "a.txt", "max_bytes": 4}, "limit"),
    ],
)
def test_content_upload_rejects_bad_input(kwargs, message):
    with pytest.raises(AttachmentFileError, match=message):
        describe_upload_content(**kwargs)


def test_describe_upload_takes_exactly_one_source(root):
    (root / "a.txt").write_text("x")
    assert describe_upload("a.txt")["path"].endswith("a.txt")
    assert describe_upload(content="x", filename="b.txt")["data"] == b"x"
    with pytest.raises(AttachmentFileError, match="not both"):
        describe_upload("a.txt", content="x", filename="b.txt")
    with pytest.raises(AttachmentFileError, match="Nothing to upload"):
        describe_upload()


def test_inline_read_limit_is_clamped_to_a_hard_ceiling():
    from lib.attachment_files import DEFAULT_READ_MAX_BYTES, READ_HARD_MAX_BYTES, clamp_read_limit

    assert clamp_read_limit(10**12) == READ_HARD_MAX_BYTES
    assert clamp_read_limit(500) == 500
    for bad in (0, -5, None, "9", True, 1.5):
        assert clamp_read_limit(bad) == DEFAULT_READ_MAX_BYTES


def test_nul_in_a_path_is_a_clean_refusal(root):
    with pytest.raises(AttachmentFileError, match="NUL"):
        describe_upload_file("a\x00b")
