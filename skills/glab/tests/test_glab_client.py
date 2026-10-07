import pytest

from tests.conftest import DIFF_REFS, SAMPLE_DIFF, make_response
from lib.glab_client import (
    GitLabApiError, GitLabAuthError, GitLabClient, GitLabNotFoundError, GitLabRateLimitError,
    GitLabValidationError, encode_project,
)


def test_encode_project_path_and_id():
    assert encode_project("group/sub/proj") == "group%2Fsub%2Fproj"
    assert encode_project(42) == "42"


def test_get_project_url_and_normalization(client, mock_session):
    mock_session.request.return_value = make_response(
        json_data={"id": 1, "path_with_namespace": "g/p", "default_branch": "main", "web_url": "u", "secret": "x"})
    out = client.get_project("g/p")
    assert mock_session.request.call_args.args[:2] == ("GET", "https://gitlab.example.com/api/v4/projects/g%2Fp")
    assert out["default_branch"] == "main" and "secret" not in out


@pytest.mark.parametrize("status,exc", [(401, GitLabAuthError), (403, GitLabAuthError), (404, GitLabNotFoundError),
                                         (422, GitLabValidationError), (429, GitLabRateLimitError), (503, GitLabApiError)])
def test_error_mapping(client, mock_session, status, exc):
    mock_session.request.return_value = make_response(status, json_data={"message": "boom"})
    with pytest.raises(exc) as ei:
        client.current_user()
    assert ei.value.status_code == status


def test_pagination_follows_next_page_and_caps(client, mock_session):
    mock_session.request.side_effect = [
        make_response(json_data=[{"name": "a"}, {"name": "b"}], headers={"X-Next-Page": "2"}),
        make_response(json_data=[{"name": "c"}], headers={"X-Next-Page": ""}),
    ]
    assert [b["name"] for b in client.list_branches("1")] == ["a", "b", "c"]
    assert mock_session.request.call_args_list[1].kwargs["params"]["page"] == 2

    mock_session.request.side_effect = [make_response(json_data=[{"name": "a"}, {"name": "b"}], headers={"X-Next-Page": "2"})]
    assert len(client.list_branches("1", max_results=1)) == 1


def test_get_file_truncates_and_flags_binary(client, mock_session):
    mock_session.request.return_value = make_response(content=b"hello world")
    out = client.get_file("g/p", "src/a b.py", "main", max_bytes=5)
    assert out["content"] == "hello" and out["truncated"] is True
    assert "src%2Fa%20b.py/raw" in mock_session.request.call_args.args[1]

    mock_session.request.return_value = make_response(content=b"\x00\x01")
    assert client.get_file("g/p", "x.bin", "main")["binary"] is True


def test_get_mr_diff_falls_back_to_changes(client, mock_session):
    mock_session.request.side_effect = [
        make_response(404, json_data={"message": "nf"}),
        make_response(json_data={"changes": [{"old_path": "a", "new_path": "a", "diff": "d"}]}),
    ]
    files = client.get_mr_diff("1", 5)
    assert files[0]["new_path"] == "a"
    assert mock_session.request.call_args.args[1].endswith("/merge_requests/5/changes")


def test_list_mrs_instance_wide_and_reviewer(client, mock_session):
    mock_session.request.side_effect = [make_response(json_data={"username": "me"}), make_response(json_data=[])]
    client.list_mrs(reviewer_me=True)
    last = mock_session.request.call_args
    assert last.args[1].endswith("/api/v4/merge_requests")
    assert last.kwargs["params"]["reviewer_username"] == "me"


def _mr_calls(mock_session):
    mock_session.request.side_effect = [
        make_response(json_data={"diff_refs": DIFF_REFS}),
        make_response(json_data=[{"old_path": "a.py", "new_path": "a.py", "diff": SAMPLE_DIFF}], headers={}),
    ]


def test_resolve_inline_position(client, mock_session):
    _mr_calls(mock_session)
    pos = client.resolve_inline_position("1", 5, "a.py", new_line=3)
    assert pos["new_line"] == 3 and pos["base_sha"] == "b"


def test_resolve_inline_position_file_not_in_mr(client, mock_session):
    _mr_calls(mock_session)
    with pytest.raises(GitLabValidationError, match="not changed"):
        client.resolve_inline_position("1", 5, "other.py", new_line=3)


def test_discussion_vs_draft_endpoints(client, mock_session):
    mock_session.request.return_value = make_response(json_data={"id": "d", "notes": []})
    client.add_mr_discussion("1", 5, "hi", {"new_line": 1}, draft=False)
    assert mock_session.request.call_args.args[1].endswith("/merge_requests/5/discussions")
    client.add_mr_discussion("1", 5, "hi", {"new_line": 1}, draft=True)
    assert mock_session.request.call_args.args[1].endswith("/merge_requests/5/draft_notes")
    assert mock_session.request.call_args.kwargs["json"] == {"note": "hi", "position": {"new_line": 1}}


def test_note_vs_draft_endpoints(client, mock_session):
    mock_session.request.return_value = make_response(json_data={"id": 1, "body": "hi"})
    client.add_mr_note("1", 5, "hi")
    assert mock_session.request.call_args.args[1].endswith("/merge_requests/5/notes")
    client.add_mr_note("1", 5, "hi", draft=True)
    assert mock_session.request.call_args.args[1].endswith("/merge_requests/5/draft_notes")
