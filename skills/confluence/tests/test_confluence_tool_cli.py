"""Tests for scripts/confluence_tool.py's own dispatcher logic -- the
comma-split/flag-translation glue that isn't already exercised by
tests/test_tools.py (which calls the tool functions directly)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from scripts import confluence_tool


def test_build_parser_requires_a_subcommand():
    parser = confluence_tool.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_get_page_expand_flag_is_comma_split():
    parser = confluence_tool.build_parser()
    args = parser.parse_args(["get_page", "--page_id", "1", "--expand", "body.storage,version"])
    with patch("scripts.confluence_tool.get_page.get_page") as mock_fn:
        confluence_tool.dispatch(args)
    mock_fn.assert_called_once_with("1", expand=["body.storage", "version"])


def test_get_page_expand_flag_omitted_passes_none():
    parser = confluence_tool.build_parser()
    args = parser.parse_args(["get_page", "--page_id", "1"])
    with patch("scripts.confluence_tool.get_page.get_page") as mock_fn:
        confluence_tool.dispatch(args)
    mock_fn.assert_called_once_with("1", expand=None)


def test_page_summary_sections_flag_is_comma_split():
    parser = confluence_tool.build_parser()
    args = parser.parse_args(["page_summary", "--page_id", "1", "--sections", "page,comments"])
    with patch("scripts.confluence_tool.page_summary.page_summary") as mock_fn:
        confluence_tool.dispatch(args)
    mock_fn.assert_called_once_with("1", sections=["page", "comments"])


def test_create_page_forwards_confirm_flag():
    parser = confluence_tool.build_parser()
    args = parser.parse_args(
        ["create_page", "--space_key", "ENG", "--title", "T", "--body_storage", "<p>x</p>", "--confirm"]
    )
    with patch("scripts.confluence_tool.create_page.create_page") as mock_fn:
        confluence_tool.dispatch(args)
    mock_fn.assert_called_once_with("ENG", "T", "<p>x</p>", parent_id=None, confirm=True)


def test_dispatch_unknown_tool_raises_assertion_error():
    class FakeArgs:
        tool = "not_a_real_tool"

    with pytest.raises(AssertionError):
        confluence_tool.dispatch(FakeArgs())


def test_main_prints_single_json_document_on_configuration_error(capsys):
    with patch("scripts.confluence_tool.build_parser") as mock_build_parser:
        mock_parser = MagicMock()
        mock_parser.parse_args.return_value = MagicMock(tool="list_spaces")
        mock_build_parser.return_value = mock_parser
        with patch(
            "scripts.confluence_tool.dispatch", side_effect=confluence_tool.ConfigurationError("boom")
        ):
            exit_code = confluence_tool.main()

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output == {"error": {"type": "configuration_error", "message": "boom"}}
