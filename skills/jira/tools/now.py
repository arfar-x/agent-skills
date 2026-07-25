"""now: report the current local wall-clock time.

Thin tool, and the only one here that makes no Jira call at all. It
exists because the rest of this skill's date handling assumes the caller
knows what time it is -- ``worklog``/``worklog_edit`` require relative
phrasing ("last Tuesday", "yesterday", "now") to be resolved to an
unambiguous date *before* they're called, and an agent's own sense of
the current time is often stale or absent. Reading the clock through a
tool keeps that a checked fact rather than an assumption, and avoids
the skill having to instruct an ad-hoc shell command to get it.

``now`` is emitted in the same tz-aware ISO format ``worklog --date``
already accepts, so a start time can be passed straight through.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any, Dict

from tools._common import run_tool


def now() -> Dict[str, Any]:
    """Return the current local time, timezone-aware.

    Returns:
        ``{"now": "2026-07-25T14:32:11+03:30", "date": "2026-07-25",
        "time": "14:32", "weekday": "Saturday", "timezone": "+03:30"}``
        -- ``now`` is directly usable as ``worklog --date``.
    """

    def _run() -> Dict[str, Any]:
        current = _dt.datetime.now().astimezone().replace(microsecond=0)
        return {
            "now": current.isoformat(),
            "date": current.strftime("%Y-%m-%d"),
            "time": current.strftime("%H:%M"),
            "weekday": current.strftime("%A"),
            "timezone": current.strftime("%z"),
        }

    return run_tool("now", _run)
