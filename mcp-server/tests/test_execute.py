from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from lib.execute import _build_argv, execute_subcommand
from lib.introspect import ParamSpec, SubcommandSpec

SPEC = SubcommandSpec(
    name="worklog",
    help="Log time",
    params=(
        ParamSpec("issue_key", "--issue_key", "str", True, None, None, False, "..."),
        ParamSpec("duration", "--duration", "str", True, None, None, False, "..."),
        ParamSpec("date", "--date", "str", False, None, None, False, "..."),
        ParamSpec("confirm", "--confirm", "bool", False, False, None, False, "..."),
    ),
)

SEND_BULK_SPEC = SubcommandSpec(
    name="send_bulk",
    help="Bulk send",
    params=(ParamSpec("to", "--to", "str", True, None, None, True, "..."),),
)


def _manifest(script_path: Path, required_env=()):
    return SimpleNamespace(
        toolset="jira",
        script_path=script_path,
        required_environment_variables=required_env,
    )


def test_build_argv_boolean_true_is_flag_only():
    argv = _build_argv("python3", "script.py", "worklog", SPEC, {"confirm": True})
    assert argv == ["python3", "script.py", "worklog", "--confirm"]


def test_build_argv_boolean_false_is_omitted():
    argv = _build_argv("python3", "script.py", "worklog", SPEC, {"confirm": False})
    assert argv == ["python3", "script.py", "worklog"]


def test_build_argv_none_optional_omits_flag_entirely():
    argv = _build_argv("python3", "script.py", "worklog", SPEC, {"date": None})
    assert argv == ["python3", "script.py", "worklog"]


def test_build_argv_string_values_pass_through():
    argv = _build_argv("python3", "script.py", "worklog", SPEC, {"issue_key": "PAY-1", "duration": "2h"})
    assert argv == ["python3", "script.py", "worklog", "--issue_key", "PAY-1", "--duration", "2h"]


def test_build_argv_repeated_action_append_repeats_flag():
    argv = _build_argv("python3", "script.py", "send_bulk", SEND_BULK_SPEC, {"to": ["111", "222"]})
    assert argv == ["python3", "script.py", "send_bulk", "--to", "111", "--to", "222"]


@patch("lib.execute.subprocess.run")
def test_execute_subcommand_parses_json_stdout(mock_run, tmp_path):
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout='{"confirmed": true}', stderr=""
    )
    manifest = _manifest(tmp_path / "skills" / "jira" / "scripts" / "jira_tool.py")
    result = execute_subcommand(manifest, SPEC, {"issue_key": "PAY-1", "duration": "2h", "confirm": True})
    assert result == {"confirmed": True}


@patch("lib.execute.subprocess.run")
def test_execute_subcommand_nonzero_exit_is_structured_error(mock_run, tmp_path):
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=2, stdout="", stderr="boom"
    )
    manifest = _manifest(tmp_path / "skills" / "jira" / "scripts" / "jira_tool.py")
    result = execute_subcommand(manifest, SPEC, {"issue_key": "PAY-1", "duration": "2h"})
    assert result["error"]["type"] == "nonzero_exit"
    assert result["error"]["exit_code"] == 2
    assert result["error"]["stderr"] == "boom"


@patch("lib.execute.subprocess.run")
def test_execute_subcommand_non_json_stdout_is_structured_error(mock_run, tmp_path):
    mock_run.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="not json", stderr=""
    )
    manifest = _manifest(tmp_path / "skills" / "jira" / "scripts" / "jira_tool.py")
    result = execute_subcommand(manifest, SPEC, {"issue_key": "PAY-1", "duration": "2h"})
    assert result["error"]["type"] == "invalid_json_output"


@patch("lib.execute.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["x"], timeout=60))
def test_execute_subcommand_timeout_is_structured_error(mock_run, tmp_path):
    manifest = _manifest(tmp_path / "skills" / "jira" / "scripts" / "jira_tool.py")
    result = execute_subcommand(manifest, SPEC, {"issue_key": "PAY-1", "duration": "2h"})
    assert result["error"]["type"] == "timeout"


@patch("lib.execute.subprocess.run", side_effect=OSError("no such file"))
def test_execute_subcommand_spawn_failure_is_structured_error(mock_run, tmp_path):
    manifest = _manifest(tmp_path / "skills" / "jira" / "scripts" / "jira_tool.py")
    result = execute_subcommand(manifest, SPEC, {"issue_key": "PAY-1", "duration": "2h"})
    assert result["error"]["type"] == "spawn_failed"


@patch("lib.execute.subprocess.run")
def test_missing_required_env_var_short_circuits_before_subprocess(mock_run, tmp_path, monkeypatch):
    monkeypatch.delenv("JIRA_BASE_URL", raising=False)
    manifest = _manifest(
        tmp_path / "skills" / "jira" / "scripts" / "jira_tool.py",
        required_env=({"name": "JIRA_BASE_URL", "required_for": "all functionality"},),
    )
    result = execute_subcommand(manifest, SPEC, {"issue_key": "PAY-1", "duration": "2h"})
    assert result == {"error": {"type": "missing_environment_variables", "missing": ["JIRA_BASE_URL"]}}
    mock_run.assert_not_called()


@patch("lib.execute.subprocess.run")
def test_optional_env_var_never_blocks_execution(mock_run, tmp_path, monkeypatch):
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="{}", stderr="")
    monkeypatch.delenv("JIRA_DEFAULT_PROJECT", raising=False)
    manifest = _manifest(
        tmp_path / "skills" / "jira" / "scripts" / "jira_tool.py",
        required_env=({"name": "JIRA_DEFAULT_PROJECT", "required_for": "optional -- scopes lookups"},),
    )
    result = execute_subcommand(manifest, SPEC, {"issue_key": "PAY-1", "duration": "2h"})
    assert result == {}
    mock_run.assert_called_once()
