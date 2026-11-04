"""Tools to fetch a repository snapshot and publish a change: gated, validated and idempotent."""

import base64
import json

import pytest

import lib.glab_client as gc
from tests.conftest import make_response
from tools import create_commit, ensure_mr, get_archive, reply_discussion, resolve_discussion


@pytest.fixture(autouse=True)
def _patch_client(client, monkeypatch):
    monkeypatch.setattr(gc, "_client_singleton", client)
    return client


def _streamed(data: bytes, status=200):
    response = make_response(status_code=status)
    response.iter_content.return_value = [data[i:i + 4] for i in range(0, len(data), 4)]
    return response


def test_get_archive_returns_the_snapshot_and_its_commit(mock_session):
    mock_session.request.side_effect = [make_response(json_data={"id": "abc123"}), _streamed(b"TARBALL!")]
    out = get_archive.get_archive("main", project="g/p")
    assert out["sha"] == "abc123" and out["size"] == 8 and base64.b64decode(out["content_base64"]) == b"TARBALL!"
    assert mock_session.request.call_args.kwargs["params"] == {"sha": "abc123"}


def test_get_archive_refuses_a_repository_over_the_limit_and_a_silly_limit(mock_session):
    mock_session.request.side_effect = [make_response(json_data={"id": "abc"}), _streamed(b"x" * ((1 << 20) + 8))]
    out = get_archive.get_archive("main", project="g/p", max_mb=1)
    assert out["error"]["type"] == "GitLabValidationError" and "larger than" in out["error"]["message"]
    assert get_archive.get_archive("main", project="g/p", max_mb=0)["error"]["type"] == "invalid_input"


ACTIONS = [{"action": "update", "file_path": "src/a.py", "content": "print(1)\n"},
           {"action": "create", "file_path": "b.bin", "content_base64": base64.b64encode(b"\x00\x01").decode()}]


def test_create_commit_is_gated_and_shows_what_it_would_change(mock_session):
    out = create_commit.create_commit("ai/fix/X-1", "Fix", ACTIONS, project="g/p", start_branch="main", marker="m-1")
    assert out["requires_confirmation"] and out["pending_action"]["files"] == ["src/a.py", "b.bin"]
    assert out["pending_action"]["message"].endswith("m-1")
    mock_session.request.assert_not_called()


def test_create_commit_creates_the_branch_from_start_and_sends_encoded_content(mock_session):
    mock_session.request.side_effect = [make_response(json_data=[]),                                  # no commit with the marker yet
                                        make_response(status_code=404, json_data={"message": "404 Branch Not Found"}),
                                        make_response(json_data={"id": "c1", "short_id": "c1", "title": "Fix", "web_url": "u"})]
    out = create_commit.create_commit("ai/fix/X-1", "Fix", json.dumps(ACTIONS), project="g/p", start_branch="main",
                                      marker="m-1", confirm=True)
    assert out["confirmed"] and out["commit"]["id"] == "c1"
    body = mock_session.request.call_args.kwargs["json"]
    assert body["start_branch"] == "main" and body["branch"] == "ai/fix/X-1" and body["commit_message"].endswith("m-1")
    assert body["actions"][1]["encoding"] == "base64" and "encoding" not in body["actions"][0]


def test_create_commit_with_a_marker_already_committed_commits_nothing(mock_session):
    mock_session.request.side_effect = [make_response(json_data=[{"id": "old", "short_id": "old", "title": "Fix", "message": "Fix\n\nm-1"}])]
    out = create_commit.create_commit("ai/fix/X-1", "Fix", ACTIONS, project="g/p", marker="m-1", confirm=True)
    assert out["skipped"] == "exists" and out["commit"]["id"] == "old"
    assert mock_session.request.call_count == 1


@pytest.mark.parametrize("actions", ["not json", [], [{"action": "explode", "file_path": "a"}],
                                     [{"action": "update", "file_path": "../etc/passwd", "content": "x"}],
                                     [{"action": "update", "file_path": "/abs", "content": "x"}],
                                     [{"action": "update", "file_path": "a"}],
                                     [{"action": "create", "file_path": "a", "content_base64": "!!!"}],
                                     [{"action": "move", "file_path": "a"}]])
def test_create_commit_rejects_bad_actions_before_anything_is_sent(mock_session, actions):
    out = create_commit.create_commit("b", "m", actions, project="g/p", confirm=True)
    assert out["error"]["type"] == "invalid_input"
    mock_session.request.assert_not_called()


def test_ensure_mr_returns_the_open_one_and_never_makes_a_second(mock_session):
    mock_session.request.side_effect = [make_response(json_data=[{"iid": 7, "web_url": "u", "title": "T", "state": "opened",
                                                                  "source_branch": "ai/x", "target_branch": "main"}])]
    out = ensure_mr.ensure_mr("ai/x", "main", "T", project="g/p", confirm=True)
    assert out["created"] is False and out["mr"]["iid"] == 7 and mock_session.request.call_count == 1


def test_ensure_mr_opens_one_assigned_to_the_named_user(mock_session):
    mock_session.request.side_effect = [make_response(json_data=[]), make_response(json_data=[{"id": 42}]),
                                        make_response(json_data={"iid": 9, "web_url": "u", "assignee": {"username": "ana"}})]
    out = ensure_mr.ensure_mr("ai/x", "main", "T", "Body", project="g/p", assignee_username="ana", labels=["ai"], confirm=True)
    assert out["created"] and out["mr"]["iid"] == 9 and out["mr"]["assignee"] == "ana"
    body = mock_session.request.call_args.kwargs["json"]
    assert body["assignee_id"] == 42 and body["labels"] == "ai" and body["remove_source_branch"] is True


def test_ensure_mr_with_an_unknown_assignee_opens_nothing_and_is_gated_first(mock_session):
    assert ensure_mr.ensure_mr("a", "b", "T", project="g/p")["requires_confirmation"]
    mock_session.request.assert_not_called()
    mock_session.request.side_effect = [make_response(json_data=[]), make_response(json_data=[])]
    out = ensure_mr.ensure_mr("a", "b", "T", project="g/p", assignee_username="ghost", confirm=True)
    assert out["error"]["type"] == "invalid_input" and mock_session.request.call_count == 2


def test_reply_discussion_is_gated_and_a_repeat_with_the_same_marker_is_a_no_op(mock_session):
    assert reply_discussion.reply_discussion(5, "d1", "Done", project="g/p", marker="r-1")["requires_confirmation"]
    mock_session.request.assert_not_called()
    mock_session.request.side_effect = [make_response(json_data={"id": "d1", "notes": [{"id": 1, "body": "Done\n\nr-1"}]})]
    assert reply_discussion.reply_discussion(5, "d1", "Done", project="g/p", marker="r-1", confirm=True)["skipped"] == "exists"
    mock_session.request.side_effect = [make_response(json_data={"id": "d1", "notes": []}), make_response(json_data={"id": 2, "body": "x"})]
    posted = reply_discussion.reply_discussion(5, "d1", "Done", project="g/p", marker="r-1", confirm=True)
    assert posted["note"]["id"] == 2 and mock_session.request.call_args.kwargs["json"]["body"].endswith("r-1")


def test_resolve_discussion_is_gated_and_resolves(mock_session):
    assert resolve_discussion.resolve_discussion(5, "d1", project="g/p")["requires_confirmation"]
    mock_session.request.return_value = make_response(json_data={"id": "d1", "notes": [{"id": 1, "resolved": True}]})
    out = resolve_discussion.resolve_discussion(5, "d1", project="g/p", confirm=True)
    assert out["discussion"]["notes"][0]["resolved"] is True
    assert mock_session.request.call_args.kwargs["json"] == {"resolved": True}


def test_the_merge_request_list_carries_the_head_sha_so_a_poll_can_fire_on_new_commits_only(mock_session):
    from tools import list_mrs

    mock_session.request.return_value = make_response(json_data=[{"iid": 7, "state": "opened", "web_url": "u", "sha": "abc123", "updated_at": "t"}])
    out = list_mrs.list_mrs(project="g/p")
    assert out["merge_requests"][0]["sha"] == "abc123" and out["merge_requests"][0]["web_url"] == "u"
