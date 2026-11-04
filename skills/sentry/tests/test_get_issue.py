import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.client import SentryClient  # noqa: E402
from tools import get_issue  # noqa: E402


def response(status=200, data=None):
    r = MagicMock()
    r.status_code, r.ok = status, 200 <= status < 400
    r.json.return_value = data
    return r


ISSUE = {"title": "TypeError: total is null for ana@example.org", "culprit": "OrderTotal::sum", "level": "error", "status": "unresolved",
         "firstSeen": "t1", "lastSeen": "t2", "count": "12", "userCount": 3, "permalink": "https://s/issues/1"}
EVENT = {"tags": [{"key": "env", "value": "prod"}], "dateCreated": "t3", "user": {"email": "c@example.org", "ip_address": "203.0.113.9"},
         "request": {"headers": {"Authorization": "Bearer abcdefghijklmnop1234"}, "url": "https://x/y"},
         "entries": [{"type": "breadcrumbs", "data": {"values": [{"message": "call 10.0.0.1"}]}},
                     {"type": "exception", "data": {"values": [{"stacktrace": {"frames": [{"filename": "a.php", "lineno": 3}]}}]}}]}


def client(*replies):
    session = MagicMock()
    session.get.side_effect = list(replies)
    return SentryClient(base_url="https://sentry.example.org/api/0/", token="tok", session=session), session


def test_an_issue_is_returned_with_its_stack_and_breadcrumbs_and_nothing_personal():
    c, session = client(response(data=ISSUE), response(data=EVENT))
    out = get_issue.get_issue("1234", client=c)
    assert out["title"].startswith("TypeError") and out["stacktrace"] == [{"filename": "a.php", "lineno": 3}] and out["tags"] == [{"key": "env", "value": "prod"}]
    flat = str(out)
    for secret in ("ana@example.org", "c@example.org", "203.0.113.9", "abcdefghijklmnop1234", "10.0.0.1"):
        assert secret not in flat
    assert session.get.call_args_list[0].args[0] == "https://sentry.example.org/api/0/issues/1234/"
    assert session.get.call_args.kwargs["headers"] == {"Authorization": "Bearer tok"}


def test_an_issue_without_an_event_still_answers_with_an_empty_stack():
    c, _ = client(response(data=ISSUE), response(404, {}))
    out = get_issue.get_issue("1234", client=c)
    assert out["stacktrace"] == [] and out["breadcrumbs"] == [] and out["title"]


@pytest.mark.parametrize("bad", ["", "../etc", "a b", "x" * 100, None])
def test_an_odd_issue_id_is_refused_before_any_request(bad):
    c, session = client()
    assert get_issue.get_issue(bad, client=c)["error"]["type"] == "invalid_input"
    session.get.assert_not_called()


def test_a_refused_token_and_a_missing_token_are_reported_plainly(monkeypatch):
    c, _ = client(response(401, {}))
    out = get_issue.get_issue("1", client=c)
    assert out["error"]["status_code"] == 401 and "scopes" in out["error"]["message"]
    monkeypatch.delenv("SENTRY_AUTH_TOKEN", raising=False)
    assert get_issue.get_issue("1")["error"]["type"] == "configuration_error"
