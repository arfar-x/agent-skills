"""Append-only audit log -- the detection layer for whatever prevention misses.

Every executed action (never a merely-requested one that stopped at the
confirmation gate) appends one JSON line here. The schema is fixed and
narrow on purpose: `timestamp`, `tool`, `chat_id`, `chat_title`,
`message_id`, `counts`, `outcome`. Nothing else is ever written -- in
particular, never a message body, never the session string, never a phone
number. See `skills/telegram/README.md`'s "Security model" for why the
schema is this specific and no wider.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

_ALLOWED_KEYS = {"timestamp", "tool", "chat_id", "chat_title", "message_id", "counts", "outcome"}


def append_event(
    audit_log: Path,
    *,
    tool: str,
    chat_id: Optional[int],
    chat_title: Optional[str],
    message_id: Optional[int],
    counts: Optional[Dict[str, int]],
    outcome: str,
) -> None:
    """Append one audit event. Never raises on a logging failure.

    A failure to write the audit log must never block or mask the result of
    the action it's recording -- callers call this after the action's
    outcome is already decided, so an audit-write failure surfaces as a
    logger warning, not an exception that changes what the caller reports.
    """
    event: Dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
        "tool": tool,
        "chat_id": chat_id,
        "chat_title": chat_title,
        "message_id": message_id,
        "counts": counts or {},
        "outcome": outcome,
    }
    assert set(event) <= _ALLOWED_KEYS, "audit event carries an unexpected key"

    try:
        audit_log.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(str(audit_log), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.write(fd, (json.dumps(event, sort_keys=True) + "\n").encode("utf-8"))
        finally:
            os.close(fd)
    except OSError:
        # Best-effort: never let a logging failure mask a real tool result.
        pass
