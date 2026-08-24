#!/usr/bin/env python3
"""MCP server exposing this repo's skills/ to MCP clients that can't read
the Agent Skills (SKILL.md) format natively.

`SKILL.md` stays the single source of truth for every skill's
instructions -- this server never reimplements or hardcodes a second
copy of any skill's guidance. It only:

  - serves each skill's SKILL.md verbatim, read fresh on every call
    (`get_skill`), for a client whose own model needs to read the
    instructions to know how to use a tool;
  - exposes each toolset's CLI subcommands as typed MCP tools, generated
    at startup by introspecting that toolset's own `argparse`
    `build_parser()` -- see lib/introspect.py and lib/mcp_tools.py -- so
    the tool list stays in sync automatically as a toolset's CLI changes,
    with no server-code edits needed.

See README.md for setup, MCP client configuration, the --include-internal
flag, and (important) telegram's /dev/tty confirm-mode caveat.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.adapter_note import adapter_note  # noqa: E402
from lib.doc_gen import build_doc_gen_tool  # noqa: E402
from lib.introspect import IntrospectionError  # noqa: E402
from lib.mcp_tools import register_toolset_tools  # noqa: E402
from lib.registry import (  # noqa: E402
    discover_skills,
    load_subcommands,
    parse_skill_md,
    resolve_include_internal,
)

REPO_ROOT = Path(os.environ.get("AGENT_SKILLS_REPO_ROOT", str(Path(__file__).resolve().parent.parent)))


def build_app(*, include_internal: bool) -> FastMCP:
    manifests = discover_skills(REPO_ROOT, include_internal=include_internal)
    by_name = {m.name: m for m in manifests}

    app = FastMCP(
        name="agent-skills",
        instructions=(
            "Exposes this repo's skills/ toolsets as typed MCP tools "
            "(one tool per CLI subcommand, named <toolset>_<subcommand>) "
            "plus each skill's raw SKILL.md instructions via get_skill. "
            "Call list_skills() first, then get_skill(name) for any "
            "skill whose full instructions you need before calling its "
            "tools."
        ),
    )

    @app.tool()
    def list_skills() -> dict:
        """List every available skill (name, kind, one-line description).
        Call get_skill(name) for the full instructions body."""
        return {
            "skills": [
                {
                    "name": m.name,
                    "kind": m.kind,
                    "description": (m.frontmatter.get("description") or "").strip(),
                }
                for m in manifests
            ]
        }

    @app.tool()
    def get_skill(name: str) -> dict:
        """Return one skill's SKILL.md instructions verbatim, read fresh
        from disk on every call (never cached). For a toolset-root skill,
        prepends a short generated note (not part of the file on disk)
        explaining the <toolset>_<subcommand> tool-name mapping."""
        manifest = by_name.get(name)
        if manifest is None:
            return {"error": {"type": "not_found", "message": f"No such skill: {name!r}."}}
        frontmatter, body = parse_skill_md(manifest.skill_md_path)
        prefix = adapter_note(manifest) if manifest.kind == "toolset_root" else ""
        return {"name": name, "frontmatter": frontmatter, "instructions": prefix + body}

    doc_gen_tool = build_doc_gen_tool(manifests)
    if doc_gen_tool is not None:
        app.add_tool(doc_gen_tool)

    for manifest in manifests:
        if manifest.kind != "toolset_root":
            continue
        try:
            subcommands = load_subcommands(manifest)
        except IntrospectionError as exc:
            print(
                f"agent-skills mcp-server: skipping {manifest.name}'s execution tools "
                f"({exc}); get_skill({manifest.name!r}) still works.",
                file=sys.stderr,
            )
            continue
        register_toolset_tools(app, manifest, subcommands)

    return app


# Module-level `app`, built with the safe (no-internal-skills) default --
# exists purely so fastmcp's own CLI tooling (`fastmcp run/list/call`,
# `fastmcp dev inspector`) can find this server. Those expect a bare
# `mcp`/`server`/`app` variable, not a function to call, since they're
# meant to work against arbitrary third-party servers without knowing how
# any particular one builds itself. `python3 server.py`'s own startup
# (below) doesn't use this at all when --include-internal is passed --
# it rebuilds instead, so telegram's tools are never silently included
# just because this default object exists.
app = build_app(include_internal=resolve_include_internal(False))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-internal",
        action="store_true",
        help=(
            "Expose skills with metadata.internal: true (e.g. telegram). "
            "Falls back to INSTALL_INTERNAL_SKILLS=1 if this flag isn't passed, "
            "matching this repo's existing internal-skill convention."
        ),
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "sse", "streamable-http"],
        default="stdio",
        help=(
            "MCP transport. 'stdio' (default) is for a client that spawns this "
            "process itself (Claude Desktop, `fastmcp` CLI tools) -- no "
            "network involved, no port. Use 'http' for a client that connects "
            "to an already-running server over the network instead -- e.g. "
            "Dify's 'Add MCP Server (HTTP)', which needs a URL, not a "
            "command. 'http' and 'streamable-http' are the same modern "
            "transport; 'sse' is the older one, for a client that only "
            "supports that."
        ),
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help=(
            "Bind host for --transport http/sse (ignored for stdio). "
            "127.0.0.1 (default) only accepts connections from this machine -- "
            "use 0.0.0.0 so a container/host running Dify (or anything else "
            "not on localhost) can reach it."
        ),
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Bind port for --transport http/sse (ignored for stdio)."
    )
    parser.add_argument(
        "--path",
        default=None,
        help=(
            "Endpoint path for --transport http/sse (ignored for stdio). "
            "Defaults to /mcp for http/streamable-http, /sse for sse -- e.g. "
            "http://127.0.0.1:8000/mcp is the full URL a client connects to "
            "with the defaults above."
        ),
    )
    args = parser.parse_args()

    global app
    if args.include_internal:
        app = build_app(include_internal=True)

    if args.transport == "stdio":
        app.run()
    else:
        app.run(transport=args.transport, host=args.host, port=args.port, path=args.path)


if __name__ == "__main__":
    main()
