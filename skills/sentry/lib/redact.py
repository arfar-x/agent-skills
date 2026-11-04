"""Personal data and secrets are removed at the tool boundary, before anything reaches a model or a log."""

from __future__ import annotations

import re
from typing import Any

_EMAIL = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE = re.compile(r"\b(?:\+?\d{1,3}[\s-]?)?\d{10,11}\b")
_TOKEN = re.compile(r"(?i)(bearer\s+|authorization[\"']?\s*[:=]\s*[\"']?|api[_-]?key[\"']?\s*[:=]\s*[\"']?|"
                    r"(?:token|secret|password)[\"']?\s*[:=]\s*[\"']?)[a-zA-Z0-9._~+/=-]{12,}")
_IP = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_SENSITIVE_KEYS = re.compile(r"(?i)(password|passwd|secret|token|authorization|cookie|api[_-]?key|session)")


def redact_text(text: str) -> str:
    if not text:
        return text
    text = _TOKEN.sub(lambda m: f"{m.group(1)}[REDACTED]", text)
    text = _EMAIL.sub("[REDACTED_EMAIL]", text)
    text = _PHONE.sub("[REDACTED_PHONE]", text)
    return _IP.sub("[REDACTED_IP]", text)


def redact(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {k: "[REDACTED]" if _SENSITIVE_KEYS.search(str(k)) and isinstance(v, (str, int)) else redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value
