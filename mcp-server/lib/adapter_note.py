"""Serve-time-only preamble prepended to a toolset-root skill's SKILL.md
body when served via get_skill. Never written back to SKILL.md on disk --
that file remains the untouched source of truth.
"""

from __future__ import annotations


def adapter_note(manifest) -> str:
    toolset = manifest.toolset
    return (
        f"> **MCP adapter note (generated, not part of this file on disk):** "
        f"this MCP server exposes every `{toolset}` CLI subcommand documented "
        f"below as its own MCP tool, named `{toolset}_<subcommand>` (e.g. "
        f"`{toolset}_now`, `{toolset}_worklog`) -- call it directly with typed "
        f"arguments matching the flags described below, instead of running the "
        f"`python3 .../scripts/{toolset}_tool.py ...` shell command literally.\n"
        f"\n---\n\n"
    )
