"""Runs against the REAL skills/glab/scripts/glab_tool.py: every subcommand
must introspect cleanly (no positionals), and the write tools keep a plain
boolean --confirm so the two-step confirm flow works unchanged over MCP.
"""

from pathlib import Path

from lib.introspect import introspect_subcommands, load_build_parser

GLAB_SCRIPT = Path(__file__).resolve().parents[2] / "skills" / "glab" / "scripts" / "glab_tool.py"


def _specs():
    return {s.name: s for s in introspect_subcommands(load_build_parser(GLAB_SCRIPT)())}


def test_every_subcommand_introspects():
    assert {"whoami", "get_file", "list_mrs", "get_mr_diff", "add_mr_note", "add_mr_discussion"} <= set(_specs())


def test_write_tools_have_boolean_confirm_and_draft():
    specs = _specs()
    for name in ("add_mr_note", "add_mr_discussion"):
        params = {p.name: p for p in specs[name].params}
        assert params["confirm"].kind == "bool" and params["confirm"].default is False
        assert params["draft"].kind == "bool"


def test_choices_become_enums_and_mr_iid_is_int():
    params = {p.name: p for p in _specs()["list_mrs"].params}
    assert "opened" in params["state"].choices
    assert {p.name: p for p in _specs()["get_mr"].params}["mr_iid"].kind == "int"
