import pytest

import lib.confluence_client as cc
from tests.conftest import make_response
from tools import delete_attachment, get_attachment, upload_attachment

BASE = "https://confluence.example.com"
RAW = {
    "id": "555",
    "type": "attachment",
    "title": "diagram.png",
    "metadata": {"mediaType": "image/png"},
    "extensions": {"fileSize": 4},
    "_links": {"download": "/download/attachments/1/diagram.png?version=1"},
}


def stream_response(chunks, status_code=200):
    r = make_response(status_code=status_code, text="" if status_code == 200 else "boom")
    r.iter_content.return_value = chunks
    return r


@pytest.fixture(autouse=True)
def _patch_client(client, monkeypatch):
    monkeypatch.setattr(cc, "_client_singleton", client)
    return client


def test_get_attachment_saves_file(mock_session, tmp_path):
    mock_session.request.side_effect = [make_response(json_data=RAW), stream_response([b"ab", b"cd"])]
    out = get_attachment.get_attachment("555", out_dir=str(tmp_path))
    assert out["saved_to"] == str(tmp_path.resolve() / "diagram.png")
    assert (tmp_path / "diagram.png").read_bytes() == b"abcd"
    url = mock_session.request.call_args.args[1]
    assert url == f"{BASE}/download/attachments/1/diagram.png?version=1"


def test_get_attachment_rejects_non_attachment_content(mock_session, tmp_path):
    mock_session.request.return_value = make_response(json_data={**RAW, "type": "page"})
    out = get_attachment.get_attachment("555", out_dir=str(tmp_path))
    assert out["error"]["type"] == "ConfluenceValidationError" and "not an attachment" in out["error"]["message"]


def test_get_attachment_never_sends_credentials_to_another_host(mock_session, tmp_path):
    # base_url + "@evil.example/x" parses as userinfo@host, i.e. a different host.
    raw = {**RAW, "_links": {"download": "@evil.example/x"}}
    mock_session.request.return_value = make_response(json_data=raw)
    out = get_attachment.get_attachment("555", out_dir=str(tmp_path))
    assert out["error"]["type"] == "ConfluenceApiError" and "outside" in out["error"]["message"]
    assert mock_session.request.call_count == 1  # metadata only; no request to the other host


def test_get_attachment_refuses_overwrite_and_oversize(mock_session, tmp_path):
    (tmp_path / "diagram.png").write_text("keep")
    mock_session.request.return_value = make_response(json_data=RAW)
    assert "already exists" in get_attachment.get_attachment("555", out_dir=str(tmp_path))["error"]["message"]
    assert "limit" in get_attachment.get_attachment("555", out_dir=str(tmp_path), max_bytes=3, overwrite=True)["error"]["message"]
    assert (tmp_path / "diagram.png").read_text() == "keep"


def test_upload_gate_flags_replacement_and_sends_nothing_but_the_lookup(mock_session, tmp_path):
    f = tmp_path / "diagram.png"
    f.write_bytes(b"png!")
    mock_session.request.return_value = make_response(json_data={"results": [RAW]})
    out = upload_attachment.upload_attachment("1", str(f), comment="v2")
    pending = out["pending_action"]
    assert out["requires_confirmation"] is True
    assert pending["replaces_existing_attachment"] is True and pending["comment"] == "v2"
    assert pending["file_path"] == str(f.resolve()) and pending["size_bytes"] == 4
    assert mock_session.request.call_count == 1 and mock_session.request.call_args.args[0] == "GET"


def test_upload_new_name_posts_to_child_attachment(mock_session, tmp_path):
    f = tmp_path / "new.txt"
    f.write_text("hi")
    mock_session.request.side_effect = [
        make_response(json_data={"results": []}),
        make_response(json_data={"results": [{**RAW, "id": "777", "title": "new.txt"}]}),
    ]
    out = upload_attachment.upload_attachment("1", str(f), confirm=True)
    assert out["confirmed"] is True and out["replaced_existing"] is False
    assert out["attachment"]["id"] == "777"
    method, url = mock_session.request.call_args.args
    kwargs = mock_session.request.call_args.kwargs
    assert method == "POST" and url.endswith("/content/1/child/attachment")
    assert kwargs["headers"] == {"X-Atlassian-Token": "no-check", "Content-Type": None}
    assert kwargs["files"]["minorEdit"] == (None, "true")


def test_upload_existing_name_posts_a_new_version(mock_session, tmp_path):
    f = tmp_path / "diagram.png"
    f.write_bytes(b"png!")
    mock_session.request.side_effect = [make_response(json_data={"results": [RAW]}), make_response(json_data=RAW)]
    out = upload_attachment.upload_attachment("1", str(f), comment="v2", confirm=True)
    assert out["replaced_existing"] is True
    assert mock_session.request.call_args.args[1].endswith("/content/1/child/attachment/555/data")
    assert mock_session.request.call_args.kwargs["files"]["comment"] == (None, "v2")


def test_upload_bad_file_fails_before_any_request(mock_session, tmp_path):
    out = upload_attachment.upload_attachment("1", str(tmp_path / "missing"))
    assert out["error"]["type"] == "invalid_input"
    mock_session.request.assert_not_called()


WITH_PAGE = {**RAW, "container": {"id": "1", "title": "My page"}}


def test_delete_gate_shows_attachment_and_page_and_deletes_nothing(mock_session):
    mock_session.request.return_value = make_response(json_data=WITH_PAGE)
    out = delete_attachment.delete_attachment("555")
    info = out["pending_action"]["attachment"]
    assert out["requires_confirmation"] is True
    assert (info["title"], info["page_id"], info["page_title"]) == ("diagram.png", "1", "My page")
    assert [c.args[0] for c in mock_session.request.call_args_list] == ["GET"]


def test_delete_confirmed_issues_a_delete(mock_session):
    mock_session.request.side_effect = [
        make_response(json_data=WITH_PAGE), make_response(json_data=WITH_PAGE), make_response(status_code=204),
    ]
    out = delete_attachment.delete_attachment("555", confirm=True)
    assert out["deleted"] is True and out["attachment"]["page_id"] == "1"
    method, url = mock_session.request.call_args.args
    assert method == "DELETE" and url == f"{BASE}/rest/api/content/555"


def test_delete_refuses_a_page_id_even_when_confirmed(mock_session):
    # content ids are shared between pages and attachments: deleting by id must never hit a page
    mock_session.request.return_value = make_response(json_data={"id": "1", "type": "page", "title": "My page"})
    out = delete_attachment.delete_attachment("1", confirm=True)
    assert out["error"]["type"] == "ConfluenceValidationError" and "not an attachment" in out["error"]["message"]
    assert all(c.args[0] == "GET" for c in mock_session.request.call_args_list)


def test_client_delete_rechecks_the_type_itself(client, mock_session):
    mock_session.request.return_value = make_response(json_data={"id": "1", "type": "page"})
    with pytest.raises(Exception, match="not an attachment"):
        client.delete_attachment("1")
    assert all(c.args[0] == "GET" for c in mock_session.request.call_args_list)
