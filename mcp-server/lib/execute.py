"""Build argv for one CLI subcommand and run it as a subprocess.

Every toolset's dispatcher already prints exactly one JSON document to
stdout, success or failure (see e.g. skills/jira/scripts/jira_tool.py's
own docstring) -- this module's job is just building the right argv and
turning subprocess-level failures (nonzero exit, non-JSON stdout,
timeout, missing env vars) into the same `{"error": {...}}` shape those
scripts already use for a handled failure, so a caller never has to
special-case "the wrapper failed" vs. "the tool itself reported an
error".
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import TYPE_CHECKING, Any

from .introspect import SubcommandSpec

if TYPE_CHECKING:
    from .registry import SkillManifest

DEFAULT_TIMEOUT_SECONDS = 60


def _missing_required_env_vars(manifest: "SkillManifest") -> list[str]:
    """`required_for` is free prose, not an enum -- every SKILL.md in this
    repo currently writes it starting with the literal word "optional"
    for a genuinely optional var, and something else otherwise. This
    trusts that convention; it's a heuristic over prose, not a real
    schema, and could misclassify a future SKILL.md that doesn't follow
    it.
    """
    missing = []
    for var in manifest.required_environment_variables:
        required_for = str(var.get("required_for", "")).strip().lower()
        is_optional = required_for.startswith("optional")
        if not is_optional and not os.environ.get(var["name"]):
            missing.append(var["name"])
    return missing


def _build_argv(python: str, script: str, subcommand: str, spec: SubcommandSpec, kwargs: dict[str, Any]) -> list[str]:
    argv = [python, script, subcommand]
    by_name = {p.name: p for p in spec.params}
    for name, value in kwargs.items():
        if value is None:
            continue  # omitted optional arg -- flag not passed at all
        param = by_name[name]  # KeyError here is a genuine bug: our own schema disagreeing with itself
        if param.kind == "bool":
            if value is True:
                argv.append(param.flag)
            # False -> flag omitted entirely (argparse store_true's own default is False)
        elif param.repeated:
            for item in value:  # argparse action="append": repeat the flag once per element
                argv.extend([param.flag, str(item)])
        else:
            argv.extend([param.flag, str(value)])
    return argv


def execute_subcommand(
    manifest: "SkillManifest",
    spec: SubcommandSpec,
    kwargs: dict[str, Any],
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    missing = _missing_required_env_vars(manifest)
    if missing:
        return {"error": {"type": "missing_environment_variables", "missing": missing}}

    argv = _build_argv("python3", str(manifest.script_path), spec.name, spec, kwargs)

    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            shell=False,
            cwd=str(manifest.script_path.parent.parent),
            env=os.environ.copy(),
        )
    except subprocess.TimeoutExpired:
        return {
            "error": {
                "type": "timeout",
                "message": f"{manifest.toolset} {spec.name} exceeded {timeout_seconds}s.",
                "argv": argv,
            }
        }
    except OSError as exc:
        return {"error": {"type": "spawn_failed", "message": str(exc), "argv": argv}}

    if proc.returncode != 0:
        return {
            "error": {
                "type": "nonzero_exit",
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "argv": argv,
            }
        }

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {
            "error": {
                "type": "invalid_json_output",
                "message": "Subcommand exited 0 but stdout was not a single JSON document.",
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "argv": argv,
            }
        }
