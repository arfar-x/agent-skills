"""whoami: identify the account the configured token acts as."""

from __future__ import annotations

from typing import Any, Dict

from lib.glab_client import get_client
from tools._common import run_tool


def whoami() -> Dict[str, Any]:
    return run_tool("whoami", lambda: {"user": get_client().current_user()})
