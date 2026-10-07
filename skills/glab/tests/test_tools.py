import pytest

import lib.glab_client as gc
from tests.conftest import DIFF_REFS, SAMPLE_DIFF, make_response
from tools import add_mr_discussion, add_mr_note, get_file, get_mr, get_project, list_mrs


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
