from unittest.mock import MagicMock

import pytest

import lib.jira_client as jc
from lib.jira_client import JiraApiError
from tests.conftest import make_response
from tools import delete_attachment, get_attachment, get_attachments, upload_attachment

BASE = "https://jira.example.com"
META = {
    "id": "10001",
    "filename": "../shot.png",
    "size": 4,
    "mimeType": "image/png",
    "created": "2026-07-01T10:00:00.000+0000",
    "author": {"displayName": "Alice"},
    "content": f"{BASE}/secure/attachment/10001/shot.png",
}


def stream_response(chunks, status_code=200):
    r = make_response(status_code=status_code, text="" if status_code == 200 else "boom")
    r.iter_content.return_value = chunks
    return r


@pytest.fixture(autouse=True)
def _patch_client(client, monkeypatch):
    monkeypatch.setattr(jc, "_client_singleton", client)
    return client


def test_get_attachments_lists_metadata(mock_session):
    mock_session.request.return_value = make_response(json_data={"fields": {"attachment": [META]}})
    out = get_attachments.get_attachments("PAY-1")
    assert out["count"] == 1
    assert out["attachments"][0] == {
        "id": "10001", "filename": "../shot.png", "size_bytes": 4,
        "media_type": "image/png", "created": META["created"], "author": "Alice",
    }
    assert mock_session.request.call_args.kwargs["params"] == {"fields": "attachment"}


def test_get_attachment_saves_under_a_sanitized_name(mock_session, tmp_path):
    mock_session.request.side_effect = [make_response(json_data=META), stream_response([b"ab", b"cd"])]
    out = get_attachment.get_attachment("10001", out_dir=str(tmp_path))
    assert out["saved_to"] == str(tmp_path.resolve() / "shot.png")
    assert (tmp_path / "shot.png").read_bytes() == b"abcd"
    assert out["size_bytes"] == 4
    assert mock_session.request.call_args.kwargs["stream"] is True


def test_get_attachment_refuses_to_overwrite(mock_session, tmp_path):
    (tmp_path / "shot.png").write_text("keep")
    mock_session.request.return_value = make_response(json_data=META)
    out = get_attachment.get_attachment("10001", out_dir=str(tmp_path))
    assert out["error"]["type"] == "invalid_input" and "already exists" in out["error"]["message"]
    assert (tmp_path / "shot.png").read_text() == "keep"
    assert mock_session.request.call_count == 1  # metadata only, no download started


def test_get_attachment_enforces_size_limit_up_front(mock_session, tmp_path):
    mock_session.request.return_value = make_response(json_data=META)
    out = get_attachment.get_attachment("10001", out_dir=str(tmp_path), max_bytes=3)
    assert out["error"]["type"] == "invalid_input" and "limit" in out["error"]["message"]
    assert mock_session.request.call_count == 1


def test_get_attachment_never_sends_credentials_to_another_host(mock_session, tmp_path):
    mock_session.request.return_value = make_response(json_data={**META, "content": "https://evil.example/x"})
    out = get_attachment.get_attachment("10001", out_dir=str(tmp_path))
    assert out["error"]["type"] == "JiraApiError" and "outside" in out["error"]["message"]
    assert mock_session.request.call_count == 1


def test_get_attachment_http_error_leaves_no_file(mock_session, tmp_path):
    mock_session.request.side_effect = [make_response(json_data=META), stream_response([], status_code=404)]
    out = get_attachment.get_attachment("10001", out_dir=str(tmp_path))
    assert out["error"]["type"] == "JiraNotFoundError"
    assert list(tmp_path.iterdir()) == []


def test_get_attachment_requires_numeric_id():
    assert get_attachment.get_attachment("../etc")["error"]["type"] == "invalid_input"


def test_upload_gate_shows_resolved_file_and_sends_nothing(mock_session, tmp_path):
    f = tmp_path / "log.txt"
    f.write_text("hello")
    out = upload_attachment.upload_attachment("PAY-1", str(f))
    assert out["requires_confirmation"] is True
    assert out["pending_action"] == {
        "action": "upload_attachment", "issue_key": "PAY-1", "file_path": str(f.resolve()),
        "filename": "log.txt", "size_bytes": 5, "media_type": "text/plain",
    }
    mock_session.request.assert_not_called()


def test_upload_bad_file_fails_before_the_gate(mock_session, tmp_path):
    out = upload_attachment.upload_attachment("PAY-1", str(tmp_path / "missing"))
    assert out["error"]["type"] == "invalid_input"
    mock_session.request.assert_not_called()


def test_upload_confirmed_posts_multipart_with_xsrf_header(mock_session, tmp_path):
    f = tmp_path / "log.txt"
    f.write_text("hello")
    mock_session.request.return_value = make_response(json_data=[META])
    out = upload_attachment.upload_attachment("PAY-1", str(f), filename="renamed.txt", confirm=True)
    assert out["confirmed"] is True and out["attachments"][0]["id"] == "10001"
    method, url = mock_session.request.call_args.args
    kwargs = mock_session.request.call_args.kwargs
    assert method == "POST" and url == f"{BASE}/rest/api/2/issue/PAY-1/attachments"
    assert kwargs["headers"] == {"X-Atlassian-Token": "no-check", "Content-Type": None}
    assert kwargs["files"]["file"][0] == "renamed.txt"


def test_upload_auto_confirm_skips_the_gate(client, mock_session, tmp_path):
    object.__setattr__(client.config, "auto_confirm_writes", True)
    f = tmp_path / "a.txt"
    f.write_text("x")
    mock_session.request.return_value = make_response(json_data=[META])
    assert upload_attachment.upload_attachment("PAY-1", str(f))["confirmed"] is True


def test_delete_gate_shows_the_attachment_and_deletes_nothing(mock_session):
    mock_session.request.return_value = make_response(json_data=META)
    out = delete_attachment.delete_attachment("10001")
    assert out["requires_confirmation"] is True
    assert out["pending_action"]["attachment"]["filename"] == "../shot.png"
    assert [c.args[0] for c in mock_session.request.call_args_list] == ["GET"]


def test_delete_confirmed_issues_a_delete(mock_session):
    mock_session.request.side_effect = [make_response(json_data=META), make_response(status_code=204)]
    out = delete_attachment.delete_attachment("10001", confirm=True)
    assert out["deleted"] is True and out["attachment"]["id"] == "10001"
    method, url = mock_session.request.call_args.args
    assert method == "DELETE" and url == f"{BASE}/rest/api/2/attachment/10001"


def test_delete_unknown_or_malformed_id_fails_before_the_gate(mock_session):
    mock_session.request.return_value = make_response(status_code=404, json_data={"errorMessages": ["nope"]})
    assert delete_attachment.delete_attachment("999", confirm=True)["error"]["type"] == "JiraNotFoundError"
    assert delete_attachment.delete_attachment("../x")["error"]["type"] == "invalid_input"
    assert all(c.args[0] == "GET" for c in mock_session.request.call_args_list)


def test_delete_auto_confirm_skips_the_gate(client, mock_session):
    object.__setattr__(client.config, "auto_confirm_writes", True)
    mock_session.request.side_effect = [make_response(json_data=META), make_response(status_code=204)]
    assert delete_attachment.delete_attachment("10001")["deleted"] is True


def test_single_attachment_payload_without_an_id_still_reports_the_requested_id(mock_session, tmp_path):
    # real Jira's GET /attachment/{id} omits "id" on some versions
    no_id = {k: v for k, v in META.items() if k != "id"}
    mock_session.request.return_value = make_response(json_data=no_id)
    assert delete_attachment.delete_attachment("10001")["pending_action"]["attachment"]["id"] == "10001"
    mock_session.request.side_effect = [make_response(json_data=no_id), stream_response([b"abcd"])]
    assert get_attachment.get_attachment("10001", out_dir=str(tmp_path))["id"] == "10001"


def test_upload_content_gate_then_posts_the_bytes(mock_session):
    out = upload_attachment.upload_attachment("PAY-1", content="# Notes", filename="notes.md")
    assert out["pending_action"] == {
        "action": "upload_attachment", "issue_key": "PAY-1", "source": "content",
        "filename": "notes.md", "size_bytes": 7, "media_type": "text/markdown",
    }
    mock_session.request.assert_not_called()
    mock_session.request.return_value = make_response(json_data=[META])
    out = upload_attachment.upload_attachment("PAY-1", content="# Notes", filename="notes.md", confirm=True)
    assert out["confirmed"] is True
    assert mock_session.request.call_args.kwargs["files"]["file"][:2] == ("notes.md", b"# Notes")


def test_upload_of_a_file_outside_the_directory_fails_before_the_gate(mock_session):
    out = upload_attachment.upload_attachment("PAY-1", "/proc/self/environ", confirm=True)
    assert out["error"]["type"] == "invalid_input" and "outside" in out["error"]["message"]
    mock_session.request.assert_not_called()
