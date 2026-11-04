"""The Sentry REST client: one place that talks to Sentry, bearer-token authenticated, read-only."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests

DEFAULT_BASE = "https://sentry.io/api/0"


class ConfigurationError(RuntimeError):
    pass


class SentryApiError(RuntimeError):
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class SentryClient:
    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None, session: Optional[requests.Session] = None,
                 timeout: float = 20.0):
        self.base_url = (base_url or os.environ.get("SENTRY_BASE_URL") or DEFAULT_BASE).rstrip("/")
        self._token = token or os.environ.get("SENTRY_AUTH_TOKEN", "")
        if not self._token:
            raise ConfigurationError("SENTRY_AUTH_TOKEN is not set.")
        self.session = session or requests.Session()
        self.timeout = timeout

    def _get(self, path: str, *, allow_missing: bool = False) -> Any:
        try:
            response = self.session.get(f"{self.base_url}{path}", headers={"Authorization": f"Bearer {self._token}"}, timeout=self.timeout)
        except requests.exceptions.RequestException as exc:
            raise SentryApiError(f"Could not reach Sentry: {type(exc).__name__}") from exc
        if allow_missing and response.status_code == 404:
            return {}
        if response.status_code in (401, 403):
            raise SentryApiError("Sentry refused the token (it needs the event:read and project:read scopes).", response.status_code)
        if not response.ok:
            raise SentryApiError(f"Sentry answered {response.status_code}.", response.status_code)
        return response.json()

    def get_issue(self, issue_id: str) -> Dict[str, Any]:
        issue = self._get(f"/issues/{issue_id}/")
        event = self._get(f"/issues/{issue_id}/events/latest/", allow_missing=True)
        return {
            "issue_id": issue_id, "title": issue.get("title"), "culprit": issue.get("culprit"), "level": issue.get("level"),
            "status": issue.get("status"), "first_seen": issue.get("firstSeen"), "last_seen": issue.get("lastSeen"),
            "event_count": issue.get("count"), "affected_users": issue.get("userCount"), "permalink": issue.get("permalink"),
            "tags": [{"key": t.get("key"), "value": t.get("value")} for t in event.get("tags", [])],
            "breadcrumbs": _entry(event, "breadcrumbs", lambda d: d.get("values", [])),
            "stacktrace": _entry(event, "exception", lambda d: (d.get("values") or [{}])[0].get("stacktrace", {}).get("frames", [])),
            "user_context": event.get("user") or {}, "request_context": event.get("request") or {}, "timestamp": event.get("dateCreated"),
        }


def _entry(event: Dict[str, Any], kind: str, pick) -> list:
    for entry in event.get("entries", []):
        if entry.get("type") == kind:
            return pick(entry.get("data") or {})
    return []
