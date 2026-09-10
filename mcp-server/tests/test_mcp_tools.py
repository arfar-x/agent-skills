from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from lib.introspect import ParamSpec, SubcommandSpec
from lib.mcp_tools import build_input_schema, build_tool, register_toolset_tools

SPEC = SubcommandSpec(
    name="worklog",
    help="Log time against an issue",
    params=(
        ParamSpec("issue_key", "--issue_key", "str", True, None, None, False, "Issue key"),
        ParamSpec("duration", "--duration", "str", True, None, None, False, "Duration"),
        ParamSpec("date", "--date", "str", False, None, None, False, "When it happened"),
        ParamSpec("confirm", "--confirm", "bool", False, False, None, False, "Confirm the write"),
    ),
)

APPEND_SPEC = SubcommandSpec(
    name="send_bulk",
    help="Bulk send",
    params=(ParamSpec("to", "--to", "str", True, None, None, True, "Repeat per recipient"),),
)

CHOICE_SPEC = SubcommandSpec(
    name="transition",
    help="Move status",
    params=(ParamSpec("status", "--status", "str", True, None, ("Review", "Done"), False, "Target status"),),
)


def test_build_input_schema_marks_required_and_optional():
    schema = build_input_schema(SPEC)
    assert schema["required"] == ["issue_key", "duration"]
    assert schema["properties"]["issue_key"]["type"] == "string"
    assert schema["properties"]["confirm"]["type"] == "boolean"
    assert schema["properties"]["confirm"]["default"] is False


def test_build_input_schema_repeated_becomes_array():
    schema = build_input_schema(APPEND_SPEC)
    assert schema["properties"]["to"] == {
        "type": "array",
        "items": {"type": "string"},
        "description": "Repeat per recipient",
    }


def test_build_input_schema_choices_becomes_enum():
    schema = build_input_schema(CHOICE_SPEC)
    assert schema["properties"]["status"]["enum"] == ["Review", "Done"]


@patch("lib.mcp_tools.execute_subcommand")
def test_build_tool_handler_calls_execute_subcommand(mock_execute):
    mock_execute.return_value = {"confirmed": False, "requires_confirmation": True}
    manifest = SimpleNamespace(toolset="jira")
    tool = build_tool("jira", manifest, SPEC)

    assert tool.name == "jira_worklog"
    assert tool.description == "Log time against an issue"

    result = asyncio.run(tool.run({"issue_key": "PAY-1", "duration": "2h"}))
    mock_execute.assert_called_once_with(manifest, SPEC, {"issue_key": "PAY-1", "duration": "2h"})
    assert '"requires_confirmation":true' in result.content[0].text.replace(" ", "")


def test_run_offloads_blocking_handler_so_concurrent_calls_overlap():
    """GeneratedTool.run is `async def`, but its handler ends in a real
    blocking subprocess.run() call -- being async alone doesn't stop
    that from stalling the event loop. This proves two "slow" calls
    actually run concurrently (wall time ~= one call's duration, not
    the sum of both), not just that the code doesn't crash.
    """
    import time

    manifest = SimpleNamespace(toolset="jira")
    tool = build_tool("jira", manifest, SPEC)
    tool.handler = lambda arguments: (time.sleep(0.2), {"ok": True})[1]

    async def _run_two_concurrently():
        start = time.monotonic()
        await asyncio.gather(
            tool.run({"issue_key": "PAY-1", "duration": "2h"}),
            tool.run({"issue_key": "PAY-2", "duration": "2h"}),
        )
        return time.monotonic() - start

    elapsed = asyncio.run(_run_two_concurrently())
    # Sequential (blocking) execution would take >= 0.4s; overlapped
    # execution takes ~0.2s. 0.35s leaves comfortable margin for CI
    # scheduling jitter while still failing if this regresses to blocking.
    assert elapsed < 0.35


def test_register_toolset_tools_adds_one_tool_per_subcommand():
    fastmcp = pytest.importorskip("fastmcp")
    app = fastmcp.FastMCP(name="test")
    manifest = SimpleNamespace(toolset="jira")
    register_toolset_tools(app, manifest, [SPEC, APPEND_SPEC])

    async def _get_names():
        tools = await app._local_provider.list_tools()
        return {t.name for t in tools}

    names = asyncio.run(_get_names())
    assert names == {"jira_worklog", "jira_send_bulk"}
