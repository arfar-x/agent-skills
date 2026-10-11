"""The attachment directory a request gets, and what it can list there."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import lib.credentials as credentials
from lib.attachment_listing import build_list_attachment_files

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = SimpleNamespace(toolset="jira", required_environment_variables=())


def setup_function():
    credentials.configure(trust_request_credentials=False)


def _headers(user=None):
    return {"x-agent-skills-user": user} if user is not None else {}


def test_without_per_user_mode_the_configured_directory_is_used(monkeypatch):
    monkeypatch.setenv("AGENT_SKILLS_ATTACHMENT_DIR", "/srv/files")
    with patch("lib.credentials._get_http_headers", return_value=_headers("alice")):
        assert credentials.resolve_env(MANIFEST, trust_request_credentials=False)["AGENT_SKILLS_ATTACHMENT_DIR"] == "/srv/files"


def test_per_user_mode_scopes_each_request_to_its_users_folder(monkeypatch):
    monkeypatch.setenv("AGENT_SKILLS_ATTACHMENT_DIR", "/srv/uploads")
    credentials.configure(trust_request_credentials=True, attachment_dir_per_user=True)
    with patch("lib.credentials._get_http_headers", return_value=_headers("6a9b3d2d6d3ebdca8e521e41")):
        env = credentials.resolve_env(MANIFEST, trust_request_credentials=True)
    assert env["AGENT_SKILLS_ATTACHMENT_DIR"] == "/srv/uploads/6a9b3d2d6d3ebdca8e521e41"


@pytest.mark.parametrize("user", [None, "", "..", ".", "../bob", "a/b", "a\\b", "/etc", " ", "x" * 200, ".hidden"])
def test_per_user_mode_without_a_plain_user_id_gets_no_directory(monkeypatch, user):
    monkeypatch.setenv("AGENT_SKILLS_ATTACHMENT_DIR", "/srv/uploads")
    credentials.configure(trust_request_credentials=True, attachment_dir_per_user=True)
    with patch("lib.credentials._get_http_headers", return_value=_headers(user)):
        assert "AGENT_SKILLS_ATTACHMENT_DIR" not in credentials.resolve_env(MANIFEST, trust_request_credentials=True)


def test_per_user_mode_ignores_the_header_when_headers_are_not_trusted(monkeypatch):
    monkeypatch.setenv("AGENT_SKILLS_ATTACHMENT_DIR", "/srv/uploads")
    credentials.configure(trust_request_credentials=False, attachment_dir_per_user=True)
    with patch("lib.credentials._get_http_headers", return_value=_headers("alice")):
        assert "AGENT_SKILLS_ATTACHMENT_DIR" not in credentials.resolve_env(MANIFEST, trust_request_credentials=False)


def test_resolve_per_user_flag_wins_then_env(monkeypatch):
    monkeypatch.delenv("MCP_ATTACHMENT_DIR_PER_USER", raising=False)
    assert credentials.resolve_attachment_dir_per_user(False) is False
    assert credentials.resolve_attachment_dir_per_user(True) is True
    monkeypatch.setenv("MCP_ATTACHMENT_DIR_PER_USER", "1")
    assert credentials.resolve_attachment_dir_per_user(False) is True


def test_listing_shows_only_the_callers_own_allowed_files(tmp_path, monkeypatch):
    alice, bob = tmp_path / "alice", tmp_path / "bob"
    (alice / "sub").mkdir(parents=True)
    bob.mkdir()
    (alice / "a1__report.pdf").write_bytes(b"pdf")
    (alice / "sub" / "notes.txt").write_text("n")
    (alice / ".env").write_text("X=1")
    (alice / "server.pem").write_text("k")
    (alice / "escape.txt").symlink_to(bob / "b.txt")
    (bob / "b.txt").write_text("bob's")
    monkeypatch.setenv("AGENT_SKILLS_ATTACHMENT_DIR", str(tmp_path))
    credentials.configure(trust_request_credentials=True, attachment_dir_per_user=True)
    list_files = build_list_attachment_files(REPO_ROOT)
    with patch("lib.credentials._get_http_headers", return_value=_headers("alice")):
        out = list_files()
    assert sorted(f["path"] for f in out["files"]) == ["a1__report.pdf", "sub/notes.txt"]
    with patch("lib.credentials._get_http_headers", return_value=_headers()):
        assert list_files()["files"] == []
