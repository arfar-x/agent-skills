import datetime as dt

import pytest

from lib.models import Issue, IssueLink
from lib.utils import (
    InvalidDateError,
    InvalidDurationError,
    adf_to_plain_text,
    blocking_reasons,
    format_jira_timestamp,
    is_issue_blocked,
    jql_date_literal,
    parse_duration_to_seconds,
    parse_jira_timestamp,
    parse_jql_date,
    parse_worklog_date,
    safe_get,
)


@pytest.mark.parametrize(
    "duration, expected_seconds",
    [
        ("2h", 2 * 3600),
        ("30m", 30 * 60),
        ("1d", 8 * 3600),
        ("1w", 5 * 8 * 3600),
        ("1d 4h", 8 * 3600 + 4 * 3600),
        ("1h 30m", 3600 + 30 * 60),
    ],
)
def test_parse_duration_to_seconds(duration, expected_seconds):
    assert parse_duration_to_seconds(duration) == expected_seconds


@pytest.mark.parametrize("bad_duration", ["", "   ", "abc", "2x", "0h"])
def test_parse_duration_rejects_invalid(bad_duration):
    with pytest.raises(InvalidDurationError):
        parse_duration_to_seconds(bad_duration)


def test_adf_to_plain_text_extracts_text_nodes():
    adf = {
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "Hello "}, {"type": "text", "text": "world"}]}
        ],
    }
    assert "Hello" in adf_to_plain_text(adf)
    assert "world" in adf_to_plain_text(adf)


def test_adf_to_plain_text_passthrough_for_plain_string():
    assert adf_to_plain_text("already plain") == "already plain"


def test_safe_get_walks_nested_dicts():
    data = {"a": {"b": {"c": 42}}}
    assert safe_get(data, "a", "b", "c") == 42
    assert safe_get(data, "a", "x", default="missing") == "missing"
    assert safe_get(None, "a", default="missing") == "missing"


def _issue(status="To Do", links=None):
    return Issue(
        key="PAY-1",
        summary="s",
        status=status,
        priority="High",
        issue_type="Task",
        assignee="Alice",
        reporter="Bob",
        updated=None,
        created=None,
        due_date=None,
        links=links or [],
    )


def test_blocking_reasons_status_flag():
    issue = _issue(status="Blocked")
    reasons = blocking_reasons(issue)
    assert any("Status is 'Blocked'" in r for r in reasons)
    assert is_issue_blocked(issue) is True


def test_blocking_reasons_open_blocking_link():
    link = IssueLink(
        link_type="is blocked by",
        direction="inward",
        related_key="PAY-2",
        related_summary="dependency",
        related_status="In Progress",
    )
    issue = _issue(status="To Do", links=[link])
    reasons = blocking_reasons(issue)
    assert reasons == ["Blocked by PAY-2 (status: In Progress)"]
    assert is_issue_blocked(issue) is True


def test_blocking_reasons_resolved_blocking_link_not_blocked():
    link = IssueLink(
        link_type="is blocked by",
        direction="inward",
        related_key="PAY-2",
        related_summary="dependency",
        related_status="Done",
    )
    issue = _issue(status="To Do", links=[link])
    assert blocking_reasons(issue) == []
    assert is_issue_blocked(issue) is False


def test_blocking_reasons_unrelated_link_ignored():
    link = IssueLink(
        link_type="relates to",
        direction="outward",
        related_key="PAY-3",
        related_summary="other",
        related_status="Done",
    )
    issue = _issue(status="To Do", links=[link])
    assert blocking_reasons(issue) == []


_NOW = dt.datetime(2026, 7, 22, 12, 0, tzinfo=dt.timezone.utc)


@pytest.mark.parametrize(
    "value, expected_delta_seconds",
    [
        ("-14d", 14 * 86400),
        ("-2w", 2 * 7 * 86400),
        ("-1d", 86400),
        ("-30m", 30 * 60),
        ("-6h", 6 * 3600),
    ],
)
def test_parse_jql_date_relative(value, expected_delta_seconds):
    parsed = parse_jql_date(value, now=_NOW)
    assert parsed == _NOW - dt.timedelta(seconds=expected_delta_seconds)


def test_parse_jql_date_absolute():
    assert parse_jql_date("2026-07-01") == dt.datetime(2026, 7, 1, tzinfo=dt.timezone.utc)


def test_parse_jql_date_rejects_garbage():
    with pytest.raises(InvalidDateError):
        parse_jql_date("not-a-date")


@pytest.mark.parametrize(
    "value, expected",
    [("-14d", "-14d"), ("2026-07-01", '"2026-07-01"')],
)
def test_jql_date_literal_quotes_only_absolute_dates(value, expected):
    assert jql_date_literal(value) == expected


def test_parse_jira_timestamp_with_milliseconds():
    parsed = parse_jira_timestamp("2026-07-10T09:00:00.000+0000")
    assert parsed == dt.datetime(2026, 7, 10, 9, 0, tzinfo=dt.timezone.utc)


def test_parse_jira_timestamp_rejects_empty():
    with pytest.raises(InvalidDateError):
        parse_jira_timestamp("")


def test_parse_worklog_date_bare_date_inherits_current_time_of_day():
    now = dt.datetime(2026, 7, 23, 14, 30, 5, tzinfo=dt.timezone.utc)
    parsed = parse_worklog_date("2026-07-20", now=now)
    assert parsed == dt.datetime(2026, 7, 20, 14, 30, 5, tzinfo=dt.timezone.utc)


def test_parse_worklog_date_relative_uses_full_now():
    now = dt.datetime(2026, 7, 23, 14, 30, 5, tzinfo=dt.timezone.utc)
    parsed = parse_worklog_date("-3d", now=now)
    assert parsed == now - dt.timedelta(days=3)


def test_parse_worklog_date_full_datetime_passes_through():
    parsed = parse_worklog_date("2026-07-20T09:15:00+00:00")
    assert parsed == dt.datetime(2026, 7, 20, 9, 15, tzinfo=dt.timezone.utc)


def test_format_jira_timestamp():
    value = dt.datetime(2026, 7, 20, 9, 0, tzinfo=dt.timezone.utc)
    assert format_jira_timestamp(value) == "2026-07-20T09:00:00.000+0000"


def test_format_jira_timestamp_assumes_utc_when_naive():
    value = dt.datetime(2026, 7, 20, 9, 0)
    assert format_jira_timestamp(value) == "2026-07-20T09:00:00.000+0000"
