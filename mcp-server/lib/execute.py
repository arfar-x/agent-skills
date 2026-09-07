"""Build argv for one CLI subcommand and run it as a subprocess.

Every toolset's dispatcher already prints exactly one JSON document to
stdout, success or failure (see e.g. skills/jira/scripts/jira_tool.py's
own docstring) -- this module's job is just building the right argv and
turning subprocess-level failures (nonzero exit, non-JSON stdout,
timeout, missing env vars) into the same `{"error": {...}}` shape those
scripts already use for a handled failure, so a caller never has to
special-case "the wrapper failed" vs. "the tool itself reported an
error".

The subprocess's environment is resolved per call, not just inherited
wholesale from this server's own process -- see `credentials.py`. That
resolution is scoped to exactly the toolset's own declared
`required_environment_variables`, so credentials are never accidentally
handed to a subprocess for a *different* toolset; and any secret value
that resolution injected is redacted from every error payload below,
since everything this function returns goes straight into an LLM's
context via the calling tool's `ToolResult`.
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import TYPE_CHECKING, Any

from . import credentials
from .introspect import SubcommandSpec

if TYPE_CHECKING:
    from .registry import SkillManifest

DEFAULT_TIMEOUT_SECONDS = 60


def _missing_required_env_vars(manifest: "SkillManifest", env: dict[str, str]) -> list[str]:
    """`required_for` is free prose, not an enum -- every SKILL.md in this
    repo currently writes it starting with the literal word "optional"
    for a genuinely optional var, and something else otherwise. This
    trusts that convention; it's a heuristic over prose, not a real
    schema, and could misclassify a future SKILL.md that doesn't follow
    it.

    Checks `env` (the already-resolved per-call environment -- see
    `credentials.resolve_env`), not the server process's own
    `os.environ` directly, so a per-request credential header that
    supplies a var this server's own environment doesn't have is
    correctly recognized as present.
    """
    missing = []
    for var in manifest.required_environment_variables:
        required_for = str(var.get("required_for", "")).strip().lower()
        is_optional = required_for.startswith("optional")
        if not is_optional and not env.get(var["name"]):
            missing.append(var["name"])
    return missing


def _sensitive_values(manifest: "SkillManifest", env: dict[str, str]) -> list[str]:
    """Every resolved value for a var this toolset's own SKILL.md marks
    `sensitive: true` -- these are what `_redact` strips from anything
    returned to the caller. Deliberately opt-in per var (not "redact
    every declared var's value") so a non-secret value like
    JIRA_BASE_URL isn't stripped out of error messages for no reason.
    """
    return [
        env[var["name"]]
        for var in manifest.required_environment_variables
        if var.get("sensitive") and env.get(var["name"])
    ]


def _redact(value: str, secrets: list[str]) -> str:
    for secret in secrets:
        value = value.replace(secret, "***REDACTED***")
    return value


def _redact_error(payload: dict[str, Any], secrets: list[str]) -> dict[str, Any]:
    """`payload` is always the `{"error": {...}}` shape every error branch
    below returns -- the fields worth redacting (argv/stdout/stderr/
    message) live inside that nested "error" dict, not at the top level.
    """
    if not secrets:
        return payload
    error = dict(payload["error"])
    if "argv" in error:
        error["argv"] = [_redact(a, secrets) for a in error["argv"]]
    for key in ("stdout", "stderr", "message"):
        if key in error and isinstance(error[key], str):
            error[key] = _redact(error[key], secrets)
    return {"error": error}


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
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """`env`, when omitted (the normal case -- every real caller leaves
    this as None), is resolved fresh per call via `credentials.resolve_env`,
    honoring a per-request credential header only if this server was
    started with trust in that established (see `credentials.configure`).
    The explicit parameter exists mainly so tests can inject a specific
    environment without needing to mock the resolution machinery itself.
    """
    if env is None:
        env = credentials.resolve_env(manifest, trust_request_credentials=credentials.is_trusted())

    secrets = _sensitive_values(manifest, env)

    missing = _missing_required_env_vars(manifest, env)
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
            env=env,
        )
    except subprocess.TimeoutExpired:
        return _redact_error(
            {
                "error": {
                    "type": "timeout",
                    "message": f"{manifest.toolset} {spec.name} exceeded {timeout_seconds}s.",
                    "argv": argv,
                }
            },
            secrets,
        )
    except OSError as exc:
        return _redact_error({"error": {"type": "spawn_failed", "message": str(exc), "argv": argv}}, secrets)

    if proc.returncode != 0:
        return _redact_error(
            {
                "error": {
                    "type": "nonzero_exit",
                    "exit_code": proc.returncode,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                    "argv": argv,
                }
            },
            secrets,
        )

    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return _redact_error(
            {
                "error": {
                    "type": "invalid_json_output",
                    "message": "Subcommand exited 0 but stdout was not a single JSON document.",
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                    "argv": argv,
                }
            },
            secrets,
        )
