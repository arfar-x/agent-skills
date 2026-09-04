# agent-skills MCP server

An [MCP](https://modelcontextprotocol.io) server, embedded in this repo,
that exposes every skill under [`../skills/`](../skills) to MCP clients
that don't natively read the Agent Skills (`SKILL.md`) format -- Dify,
Claude Desktop, or any other MCP client.

`SKILL.md` stays the single source of truth for every skill's
instructions. This server never reimplements or hardcodes a second copy
of any skill's guidance -- it reads each file live and:

- exposes every toolset's CLI subcommands (`skills/jira/scripts/jira_tool.py`,
  ...) as typed MCP tools, named `<toolset>_<subcommand>` (e.g.
  `jira_worklog`, `jira_now`, `jira_create_issue`), generated at server
  startup by introspecting that toolset's own `argparse` `build_parser()`.
  The tool list stays in sync automatically as a toolset's CLI changes --
  no server-code edits needed when jira (or any toolset) gains a new
  action or flag.
- serves every skill's `SKILL.md` verbatim through a `get_skill(name)`
  tool, read fresh from disk on every call (never cached), for a client
  whose own model needs the real instructions to know how/when to use a
  tool.

This isn't a replacement for installing skills directly into a runtime
that already reads `SKILL.md` (Hermes, Claude Code, claude.ai) -- see the
top-level [`README.md`](../README.md#skills-directly-or-via-the-mcp-server)
for which path fits your situation.

## Setup

```bash
cd mcp-server
pip install -r requirements.txt
```

Each toolset you want tools for also needs its own dependencies
installed in the same environment -- this server literally imports a
toolset's `tools` package to read its `build_parser()`, and later
shells out to the same CLI to actually run a subcommand:

```bash
pip install -r ../skills/jira/requirements.txt
# and/or, only if you're passing --include-internal:
pip install -r ../skills/telegram/requirements.txt
```

Credentials come from environment variables only, exactly as every
`SKILL.md` documents (`JIRA_BASE_URL`/`JIRA_USERNAME`/`JIRA_PASSWORD`,
`TELEGRAM_API_ID`/..., etc.) -- set them in whatever process environment
runs this server. A tool whose toolset is missing a required variable
returns a clear `{"error": {"type": "missing_environment_variables", ...}}`
instead of a raw traceback; it's never silently skipped.

## Running it

```bash
python3 server.py
```

Runs over stdio by default -- point your MCP client's config at this
command. Example (Claude Desktop-style config; adapt to your client):

```json
{
  "mcpServers": {
    "agent-skills": {
      "command": "python3",
      "args": ["/path/to/agent-skills/mcp-server/server.py"],
      "env": {
        "JIRA_BASE_URL": "https://your-instance.atlassian.net",
        "JIRA_USERNAME": "you@example.com",
        "JIRA_PASSWORD": "..."
      }
    }
  }
}
```

If your checkout lives somewhere the server can't infer on its own, set
`AGENT_SKILLS_REPO_ROOT` to the repo's root (defaults to the parent of
this directory).

### Running over HTTP (Dify, or any client that connects to a URL)

`stdio` only works when the client spawns this process itself, on the
same machine. A client like self-hosted **Dify** connects to an
already-running server over the network instead -- in Dify, that's
**Tools -> MCP -> Add MCP Server (HTTP)**. Start the server with
`--transport http`:

```bash
python3 server.py --transport http --host 0.0.0.0 --port 8321
```

Then give Dify the URL `http://<this-machine's-address>:8321/mcp`
(`/mcp` is the default path for `http`/`streamable-http`; `--path` to
change it). `--host 0.0.0.0` is what makes it reachable from outside
this machine -- e.g. from Dify running in its own Docker container.
Leave `--host` at its default `127.0.0.1` if only local clients need
it. `--include-internal`/env vars/every other flag work the same as
under stdio.

`sse` is also available (`--transport sse`) for a client that only
supports the older SSE transport rather than `http`/`streamable-http`.

### Internal skills (e.g. `telegram`)

Skills marked `metadata.internal: true` are excluded by default. Turn
them on with either:

```bash
python3 server.py --include-internal
```

or the same `INSTALL_INTERNAL_SKILLS=1` environment-variable convention
this repo's other install paths already use (checked only if
`--include-internal` isn't passed). Both mean the same thing; use
whichever your MCP client config makes easier to set.

**Telegram's outbound actions need a second, separate opt-in.** In
`TELEGRAM_CONFIRM_MODE=tty` (the default), `telegram_send_message`,
`telegram_send_bulk`, and `telegram_forward_message` read a literal
`yes` from `/dev/tty` before doing anything -- a headless MCP server
process has no controlling terminal, so these calls will return
`{"error": {"type": "tty_unavailable", ...}}`. Reaching them requires
you to *also* set `TELEGRAM_CONFIRM_MODE=flag` in this server's own
environment, switching those actions to the same two-step
`requires_confirmation`/`pending_action` flow every other write tool
here already uses. **This server never does that switch itself** --
doing so is a deliberate choice you're making that trades away the "an
agent can never self-approve a send" guarantee `skills/telegram/`
is built around. Reads, `mark_read`, `download_media`, `whoami`,
`allowed_chats`, and `logout` work normally either way.

### Running in a container

`Dockerfile` (in this directory) builds an image that runs the server over
HTTP for a client like self-hosted Dify or LibreChat that connects to a URL
rather than spawning this process. **Build context must be the repo root**,
not `mcp-server/` -- the image needs `../skills/` as a sibling directory,
matching the `AGENT_SKILLS_REPO_ROOT` layout `server.py` expects:

```bash
docker build -f mcp-server/Dockerfile -t agent-skills-mcp .
docker run --rm -p 8321:8321 \
  -e JIRA_BASE_URL=https://your-instance.atlassian.net \
  -e JIRA_USERNAME=you@example.com \
  -e JIRA_PASSWORD=... \
  agent-skills-mcp
```

`--build-arg TOOLSETS="jira confluence"` controls which toolsets' own
`requirements.txt` get installed into the image alongside `mcp-server`'s --
default is `jira` alone. `--include-internal` is deliberately never passed in
the image's `CMD`; `skills/telegram/`'s write-gate assumes a controlling
terminal a headless container doesn't have (see the internal-skills section
above). Credentials still come from environment variables only, exactly as
running the server directly -- pass them with `-e` / `--env-file`, or via
whatever your orchestrator's secret mechanism is.

The image binds `0.0.0.0:8321` with no authentication of any kind -- the MCP
HTTP transport has none built in. Never publish this container's port to a
public network; put it on a private/internal network reachable only by the
MCP client that needs it (Dify, LibreChat, ...).

## Tool naming and shape

Every generated tool is named `<toolset>_<subcommand>` and returns
exactly one JSON document -- the same shape you'd get running
`python3 skills/<toolset>/scripts/<toolset>_tool.py <subcommand> ...`
directly. A write tool's confirm gate works the same two-step way it
already does on the CLI: call once without `confirm`, get back
`{"confirmed": false, "requires_confirmation": true, "pending_action": {...}}`,
show the user what's about to happen, then call again with `confirm: true`.

Fixed tools that exist regardless of which toolsets are installed:

- `list_skills()` -- every available skill's name, kind
  (`standalone`/`toolset_root`/`toolset_thin_wrapper`), and one-line
  description.
- `get_skill(name)` -- that skill's full `SKILL.md` instructions,
  verbatim, read live from disk. For a toolset-root skill, a short
  generated note is prepended (never written back to the file)
  explaining that its documented `python3 .../scripts/..._tool.py ...`
  commands map onto this server's `<toolset>_<subcommand>` tools.
- `doc_gen(doc_type)` -- a narrower, purpose-built alternative to
  `get_skill` for the "generate a document from a template" family of
  standalone skills (`prd`, `trd`, and whatever's added later). Its
  `doc_type` argument is a real JSON Schema `enum`, built at startup
  from whichever standalone skills declare `metadata.doc_type: <slug>`
  in their own `SKILL.md` frontmatter -- see `skills/prd/SKILL.md`,
  `skills/trd/SKILL.md`, `skills/adr/SKILL.md`, and `skills/rfc/SKILL.md`.
  Adding a new document-generation skill (e.g.
  `skills/erd/SKILL.md` with `metadata.doc_type: erd`) makes it appear
  in `doc_gen`'s enum automatically; nothing in this server needs
  editing. Like `get_skill`, it never generates anything itself -- it
  returns the live instructions, and the caller's own model does the
  writing. Only registered at all if at least one skill currently
  declares a `doc_type`. The response also includes a `current_date`
  field (UTC, `YYYY-MM-DD`, computed fresh on every call) -- every
  doc-generation skill needs today's real date for its file-naming
  convention or a Date/Last-updated field, and a model reachable only
  through this server has no shell or system clock of its own to get
  that from otherwise. Use it instead of guessing.

## Known limitations

- **`required_environment_variables`'s `required_for` field is free
  prose, not an enum.** The missing-env-var check trusts the convention
  every `SKILL.md` in this repo currently follows -- `required_for`
  starting with the literal word "optional" for a genuinely optional
  var, anything else meaning required. A future `SKILL.md` that doesn't
  follow that convention could be misclassified.
- **Tool-schema generation relies on `argparse`'s private attributes**
  (`_subparsers`, `_choices_actions`, `_StoreTrueAction`, `_AppendAction`,
  ...). Stable across Python's stdlib for well over a decade, but not a
  public API. `lib/introspect.py`'s `IntrospectionError` path exists so
  an unrecognized shape fails loudly and skips only that one toolset's
  tools (its `get_skill` still works) rather than silently producing a
  wrong tool. `tests/test_introspect_jira.py` and
  `tests/test_introspect_telegram.py` run against the real toolset
  scripts specifically so any future drift is caught by this package's
  own test suite.
- A CLI flag with a custom `type=` callable (e.g. telegram's
  `--no-seen true|false`) is exposed as a plain string parameter rather
  than a proper boolean/enum -- the underlying CLI still validates and
  converts it when it runs; only the MCP-facing schema is less specific
  for that one flag.

## Tests

```bash
cd mcp-server
pip install -r requirements.txt pytest
pip install -r ../skills/jira/requirements.txt -r ../skills/telegram/requirements.txt
pytest -q
```
