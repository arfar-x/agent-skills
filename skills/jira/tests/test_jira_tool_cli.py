"""Tests for scripts/jira_tool.py's own CLI-level parsing helpers.

Only covers logic that lives in the dispatcher itself (not already
exercised via tools/lib tests) -- currently just --custom_fields JSON
parsing, whose whole point is to turn a malformed flag into the same
{"error": {...}} shape every tool already guarantees, never a raw
traceback (see AGENTS.md's CLI contract).
"""

from __future__ import annotations

from scripts.jira_tool import _parse_custom_fields


def test_parse_custom_fields_returns_none_when_omitted():
    parsed, err = _parse_custom_fields(None, "--custom_fields")
    assert parsed is None
    assert err is None


def test_parse_custom_fields_parses_valid_json_object():
    parsed, err = _parse_custom_fields('{"customfield_10201": "Expected"}', "--custom_fields")
    assert parsed == {"customfield_10201": "Expected"}
    assert err is None


def test_parse_custom_fields_rejects_malformed_json_without_raising():
    parsed, err = _parse_custom_fields("{not json", "--custom_fields")
    assert parsed is None
    assert err["error"]["type"] == "invalid_input"


def test_parse_custom_fields_rejects_non_object_json():
    parsed, err = _parse_custom_fields("[1, 2, 3]", "--custom_fields")
    assert parsed is None
    assert err["error"]["type"] == "invalid_input"
