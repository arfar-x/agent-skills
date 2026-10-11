"""The attachment tools of the REAL jira and confluence dispatchers are
discovered by the MCP server and registered under `<toolset>_<subcommand>`.
"""

from pathlib import Path

import pytest

from lib.introspect import introspect_subcommands, load_build_parser
from lib.mcp_tools import build_tool

SKILLS = Path(__file__).resolve().parents[2] / "skills"


def _specs(toolset):
    script = SKILLS / toolset / "scripts" / f"{toolset}_tool.py"
    return {s.name: s for s in introspect_subcommands(load_build_parser(script)())}


@pytest.mark.parametrize(
    "toolset, id_flag",
    [("jira", "issue_key"), ("confluence", "page_id")],
)
def test_attachment_tools_are_discovered_with_the_right_params(toolset, id_flag):
    specs = _specs(toolset)
    assert {"get_attachments", "get_attachment", "upload_attachment", "delete_attachment"} <= set(specs)

    get = {p.name: p for p in specs["get_attachment"].params}
    assert get["attachment_id"].required is True
    assert get["out_dir"].required is False
    assert get["overwrite"].kind == "bool"
    assert get["max_bytes"].kind == "int"

    up = {p.name: p for p in specs["upload_attachment"].params}
    assert up[id_flag].required is True
    assert up["file_path"].required is False
    assert up["content"].required is False and up["content_base64"].required is False
    assert up["confirm"].kind == "bool" and up["confirm"].default is False

    delete = {p.name: p for p in specs["delete_attachment"].params}
    assert delete["attachment_id"].required is True
    assert delete["confirm"].kind == "bool" and delete["confirm"].default is False


@pytest.mark.parametrize("toolset", ["jira", "confluence"])
def test_attachment_tools_get_the_documented_mcp_names(toolset):
    for name in ("get_attachment", "upload_attachment", "delete_attachment"):
        tool = build_tool(toolset, manifest=None, spec=_specs(toolset)[name])
        assert tool.name == f"{toolset}_{name}"
        assert tool.description
