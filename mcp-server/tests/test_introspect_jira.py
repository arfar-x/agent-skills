"""Runs against the REAL skills/jira/scripts/jira_tool.py, deliberately --
this is the test that catches any future argparse-shape drift in the real
toolset before it breaks the dynamic tool generator silently at runtime.
"""

from pathlib import Path

from lib.introspect import introspect_subcommands, load_build_parser

JIRA_SCRIPT = Path(__file__).resolve().parents[2] / "skills" / "jira" / "scripts" / "jira_tool.py"


def _specs():
    build_parser = load_build_parser(JIRA_SCRIPT)
    return {s.name: s for s in introspect_subcommands(build_parser())}


def test_jira_tool_known_subcommands_are_all_extracted():
    specs = _specs()
    assert set(specs) == {
        "my_work", "issue_summary", "blockers", "search", "transition", "worklog",
        "sprint", "kanban_status", "worklog_report", "list_fields", "now",
        "worklog_edit", "worklog_delete", "triage", "project_context",
        "search_users", "create_issue", "edit_issue",
    }


def test_worklog_required_and_optional_params():
    params = {p.name: p for p in _specs()["worklog"].params}
    assert params["issue_key"].required is True
    assert params["issue_key"].flag == "--issue_key"
    assert params["duration"].required is True
    assert params["description"].required is True
    assert params["date"].required is False
    assert params["date"].default is None
    assert params["confirm"].kind == "bool"
    assert params["confirm"].required is False
    assert params["confirm"].default is False


def test_my_work_typed_and_boolean_params():
    params = {p.name: p for p in _specs()["my_work"].params}
    assert params["max_results"].kind == "int"
    assert params["max_results"].default == 100
    assert params["all_projects"].kind == "bool"
    assert params["project"].kind == "str"
    assert params["project"].required is False


def test_now_has_no_params():
    assert _specs()["now"].params == ()


def test_list_fields_has_no_params():
    assert _specs()["list_fields"].params == ()


def test_subcommand_help_text_is_captured():
    specs = _specs()
    assert specs["worklog"].help == "Log time against an issue (write, gated)"
    assert specs["now"].help == (
        "Current local wall-clock time, for resolving relative dates before a write"
    )


def test_create_issue_required_vs_optional():
    params = {p.name: p for p in _specs()["create_issue"].params}
    assert params["project"].required is True
    assert params["summary"].required is True
    assert params["issue_type"].required is True
    assert params["description"].required is False
    assert params["labels"].required is False
