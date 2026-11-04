"""get_issue: an error report's details, redacted (read)."""

from __future__ import annotations

import re
from typing import Any, Dict

from lib.client import ConfigurationError, SentryApiError, SentryClient
from lib.redact import redact


def get_issue(issue_id: str, client: SentryClient | None = None) -> Dict[str, Any]:
    """Title, culprit, level, counts, tags, breadcrumbs and the latest event's stack frames for ``issue_id`` (digits or a short id)."""
    if not isinstance(issue_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", issue_id.strip()):
        return {"error": {"type": "invalid_input", "message": "'issue_id' must be the Sentry issue id (letters, digits, - and _)."}}
    try:
        return redact((client or SentryClient()).get_issue(issue_id.strip()))
    except ConfigurationError as exc:
        return {"error": {"type": "configuration_error", "message": str(exc)}}
    except SentryApiError as exc:
        return {"error": {"type": "SentryApiError", "message": str(exc), "status_code": exc.status_code}}
