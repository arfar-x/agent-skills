import pytest

import lib.glab_client as gc
from tests.conftest import DIFF_REFS, SAMPLE_DIFF, make_response
from tools import add_mr_discussion, add_mr_note, delete_mr_note, edit_mr_note, get_file, get_mr, get_project, list_mrs


@pytest.fixture(autouse=True)
def _patch_client(client, monkeypatch):
    monkeypatch.setattr(gc, "_client_singleton", client)
    return client


def test_add_mr_note_gate_blocks_without_confirm(mock_session):
    out = add_mr_note.add_mr_note(5, "hello", project="g/p")
    assert out["requires_confirmation"] is True and out["pending_action"]["body"] == "hello"
    mock_session.request.assert_not_called()


def test_add_mr_note_confirm_posts(mock_session):
    mock_session.request.return_value = make_response(json_data={"id": 1, "body": "hello"})
    out = add_mr_note.add_mr_note(5, "hello", project="g/p", confirm=True)
    assert out["confirmed"] is True and out["note"]["id"] == 1


def test_auto_confirm_escape_hatch(client, mock_session):
    object.__setattr__(client.config, "auto_confirm_writes", True)
    mock_session.request.return_value = make_response(json_data={"id": 1})
    assert add_mr_note.add_mr_note(5, "x", project="g/p")["confirmed"] is True


def _inline_mocks(mock_session, post=None):
    seq = [make_response(json_data={"diff_refs": DIFF_REFS}),
           make_response(json_data=[{"old_path": "a.py", "new_path": "a.py", "diff": SAMPLE_DIFF}])]
    if post:
        seq.append(post)
    mock_session.request.side_effect = seq


def test_add_mr_discussion_gate_returns_resolved_position(mock_session):
    _inline_mocks(mock_session)
    out = add_mr_discussion.add_mr_discussion(5, "a.py", "bug", project="g/p", new_line=3)
    assert out["requires_confirmation"] is True
    assert out["pending_action"]["new_line"] == 3 and out["pending_action"]["file_path"] == "a.py"


def test_add_mr_discussion_bad_line_fails_before_gate(mock_session):
    _inline_mocks(mock_session)
    out = add_mr_discussion.add_mr_discussion(5, "a.py", "bug", project="g/p", new_line=99, confirm=True)
    assert out["error"]["type"] == "invalid_input"


def test_add_mr_discussion_requires_a_line():
    out = add_mr_discussion.add_mr_discussion(5, "a.py", "bug", project="g/p")
    assert out["error"]["type"] == "invalid_input"


def test_add_mr_discussion_posts_with_confirm(mock_session):
    _inline_mocks(mock_session, post=make_response(json_data={"id": "d1", "notes": []}))
    out = add_mr_discussion.add_mr_discussion(5, "a.py", "bug", project="g/p", new_line=3, confirm=True)
    assert out["confirmed"] is True and out["discussion"]["id"] == "d1"


def test_project_required_without_default():
    assert get_project.get_project()["error"]["type"] == "invalid_input"


def test_default_project_used(client, mock_session):
    object.__setattr__(client.config, "default_project", "g/p")
    mock_session.request.return_value = make_response(json_data={"id": 1})
    get_project.get_project()
    assert mock_session.request.call_args.args[1].endswith("/projects/g%2Fp")


def test_bad_mr_iid():
    assert get_mr.get_mr("abc", project="g/p")["error"]["type"] == "invalid_input"


def test_api_error_becomes_json(mock_session):
    mock_session.request.return_value = make_response(404, json_data={"message": "nope"})
    out = get_file.get_file("a", "main", project="g/p")
    assert out["error"]["type"] == "GitLabNotFoundError" and out["error"]["status_code"] == 404


def test_list_mrs_count(mock_session):
    mock_session.request.return_value = make_response(json_data=[{"iid": 1, "title": "t"}])
    assert list_mrs.list_mrs(project="g/p")["count"] == 1


_DISCUSSION = {"id": "abc", "notes": [{"id": 7, "body": "old", "author": {"username": "alice"}}]}


def test_edit_mr_note_gate_shows_current_and_new_body(mock_session):
    mock_session.request.return_value = make_response(json_data=_DISCUSSION)
    out = edit_mr_note.edit_mr_note(5, "abc", 7, "new", project="g/p")
    assert out["requires_confirmation"] is True
    pending = out["pending_action"]
    assert (pending["current_body"], pending["new_body"], pending["author"]) == ("old", "new", "alice")
    assert mock_session.request.call_count == 1  # only the read, nothing written


def test_edit_mr_note_confirm_puts(mock_session):
    mock_session.request.side_effect = [
        make_response(json_data=_DISCUSSION),
        make_response(json_data={"id": 7, "body": "new"}),
    ]
    out = edit_mr_note.edit_mr_note(5, "abc", 7, "new", project="g/p", confirm=True)
    assert out["confirmed"] is True and out["note"]["body"] == "new"
    assert mock_session.request.call_args.args[0] == "PUT"


def test_edit_mr_note_unknown_note_fails_before_gate(mock_session):
    mock_session.request.return_value = make_response(json_data=_DISCUSSION)
    out = edit_mr_note.edit_mr_note(5, "abc", 8, "new", project="g/p", confirm=True)
    assert out["error"]["type"] == "GitLabNotFoundError"
    assert mock_session.request.call_count == 1


def test_delete_mr_note_gate_shows_what_will_be_deleted(mock_session):
    mock_session.request.return_value = make_response(json_data=_DISCUSSION)
    out = delete_mr_note.delete_mr_note(5, "abc", 7, project="g/p")
    assert out["requires_confirmation"] is True and out["pending_action"]["body"] == "old"
    assert mock_session.request.call_count == 1


def test_delete_mr_note_confirm_deletes(mock_session):
    mock_session.request.side_effect = [make_response(json_data=_DISCUSSION), make_response(status_code=204)]
    out = delete_mr_note.delete_mr_note(5, "abc", 7, project="g/p", confirm=True)
    assert out == {"confirmed": True, "deleted": True, "discussion_id": "abc", "note_id": 7, "deleted_body": "old"}
    assert mock_session.request.call_args.args[0] == "DELETE"


def test_note_tools_validate_ids():
    assert edit_mr_note.edit_mr_note(5, " ", 7, "x", project="g/p")["error"]["type"] == "invalid_input"
    assert delete_mr_note.delete_mr_note(5, "abc", 0, project="g/p")["error"]["type"] == "invalid_input"
