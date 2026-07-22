"""list_fields: enumerate every field this Jira instance knows about.

Thin tool: delegates to the shared JiraClient. Exists so a custom field
(e.g. a "Figma Link" URL field, which is typically ``customfield_XXXXX``
and varies per Jira instance) can be discovered by its display name and
then requested explicitly via ``search``'s ``fields`` option -- nothing
in this skill hardcodes instance-specific custom field IDs.
"""

from __future__ import annotations

from typing import Any, Dict, List

from lib.jira_client import get_client
from tools._common import run_tool


def list_fields() -> List[Dict[str, Any]]:
    """Return every field Jira knows about.

    Returns:
        A JSON list, e.g.::

            [{"id": "customfield_10056", "name": "Figma Link", "custom": true},
             {"id": "summary", "name": "Summary", "custom": false}]
    """

    def _run() -> List[Dict[str, Any]]:
        return get_client().list_fields()

    return run_tool("list_fields", _run)
