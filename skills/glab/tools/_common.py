"""Shared plumbing for tool entry points (not itself a tool).

Centralizes error-to-JSON conversion and input validation so individual
tool modules stay thin and never duplicate this logic.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from lib.auth import ConfigurationError
from lib.diff_position import PositionError
from lib.glab_client import GitLabApiError, get_client

logger = logging.getLogger("glab_skill.tools")


class ToolInputError(ValueError):
    """Raised by tools when caller-supplied arguments are invalid."""


def run_tool(tool_name: str, fn: Callable[[], Any]) -> Any:
    """Execute a tool body, normalizing all errors into structured JSON.

    The agent must never receive a raw traceback. Errors surface as
    ``{"error": {"type": ..., "message": ...}}``.
    """
    try:
        result = fn()
        logger.info("Tool %s succeeded", tool_name)
        return result
    except (ToolInputError, PositionError) as exc:
        logger.warning("Tool %s rejected invalid input: %s", tool_name, exc)
        return {"error": {"type": "invalid_input", "message": str(exc)}}
    except ConfigurationError as exc:
        return {"error": {"type": "configuration_error", "message": str(exc)}}
    except GitLabApiError as exc:
        logger.error("Tool %s failed calling GitLab: %s", tool_name, exc)
        return {"error": {"type": type(exc).__name__, "message": str(exc), "status_code": exc.status_code}}
    except Exception as exc:  # noqa: BLE001 - last-resort safety net at the tool boundary
        logger.exception("Tool %s failed unexpectedly", tool_name)
        return {"error": {"type": "internal_error", "message": str(exc)}}


def require_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ToolInputError(f"'{field_name}' is required and must be a non-empty string.")
    return value.strip()


def require_iid(value: Any) -> int:
    try:
        iid = int(value)
    except (TypeError, ValueError):
        raise ToolInputError("'mr_iid' must be an integer (the number after '!' in the MR URL).") from None
    if iid <= 0:
        raise ToolInputError("'mr_iid' must be a positive integer.")
    return iid


def resolve_project(project: Optional[str]) -> str:
    """Return the explicit project, else ``GITLAB_DEFAULT_PROJECT``, else fail."""
    if project and project.strip():
        return project.strip()
    default = get_client().config.default_project
    if default:
        return default
    raise ToolInputError("'project' is required (numeric id or group/project path) -- or set GITLAB_DEFAULT_PROJECT.")
