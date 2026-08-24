# Agent instructions

This repo holds AI-agent skills (Hermes, Claude Code, claude.ai), not an
application. There is no build step and no server to run -- "testing a
change" means running the relevant toolset's pytest suite. The repo is
meant to hold multiple unrelated toolsets over time (Jira today, e.g. a
company back-office toolset later), each following the same layout.

## Repo layout

Not every skill belongs to a toolset. A **standalone skill** (e.g.
`skills/mood/`) is a single `SKILL.md` file with no sibling toolset
directory, no `lib/`/`tools/`/`scripts/`/`tests/`, and nothing to
`pip install` -- pure instructions the agent follows directly. The
toolset shape below is the common case in this repo, not a requirement
every skill must satisfy. `skills/mood/` in particular defaults to
`neutral` -- the agent's normal tone -- unless the user has explicitly
switched to another mode in the current conversation.

A toolset (or standalone skill) can also be marked **internal** --
`metadata.internal: true` in its `SKILL.md` frontmatter -- to keep it out
of normal installs and listings; it only appears when the installer is
run with `INSTALL_INTERNAL_SKILLS=1`. This is for a skill whose risk
profile doesn't belong in a default install (e.g. `skills/telegram/`,
which grants standing access to a personal account) -- it is not a
general-purpose "hide this skill" switch, and it doesn't relax any of the
conventions below.

A standalone skill that produces a document from a template (`prd`,
`trd`, and any future `erd`/`adr`/`rfc`/...) should additionally set
`metadata.doc_type: <slug>` in its `SKILL.md` frontmatter -- see
`skills/prd/SKILL.md` and `skills/trd/SKILL.md`. This is what
[`mcp-server/`](mcp-server)'s `doc_gen` tool discovers at startup to
build its `doc_type` enum; a new document-generation skill only needs
this one frontmatter line to appear there automatically, with no
`mcp-server` code changes. Don't set it on a standalone skill that isn't
a document template (`mood` doesn't set it).

A toolset also isn't required to ship thin per-action `skills/<toolset>-*/`
wrapper skills (below) -- `skills/telegram/` is the first example of a
toolset with none, deliberately, since multiplying a high-risk skill's
installable surface across ten separate entry points is itself a risk to
avoid, and an internal skill isn't being exposed as a discoverable command
catalog anyway. The wrapper pattern is the norm for a toolset meant to be
installed piecemeal, not a requirement every toolset must satisfy.

Per toolset `<toolset>` (e.g. `jira`):

- `skills/<toolset>/` -- the actual implementation: `lib/` (REST client,
  env-based config), `tools/` (thin per-action entry points),
  `scripts/<toolset>_tool.py` (CLI dispatcher), `tests/`.
- `skills/<toolset>-*/` -- thin `SKILL.md`-only skills, one per action,
  that shell out to `../<toolset>/scripts/<toolset>_tool.py`. They exist
  purely so each action gets its own Hermes slash command; they contain
  no Python of their own and nothing to test.

When changing behavior (auth, request handling, tool output shape) for
a toolset, edit its `skills/<toolset>/lib/` or `skills/<toolset>/tools/`,
then update `skills/<toolset>/tests/` and run:

```bash
cd skills/<toolset>
pip install -r requirements.txt pytest
pytest -q
```

When changing an action's CLI flags or output, update every
`<toolset>-*/SKILL.md` that documents that action's invocation -- they
hardcode example commands and are not generated from the CLI
dispatcher's argparse definitions.

`mcp-server/` is a different kind of thing and doesn't follow the shape
above -- it's not itself a toolset or a skill, it's a small MCP server
that serves every skill above (still reading each `SKILL.md` live, never
duplicating its instructions) to MCP clients that can't read the Agent
Skills format natively. Its tools are generated at startup by
introspecting each toolset's own `build_parser()`, so -- unlike the
`<toolset>-*/SKILL.md` rule just above -- **it needs no manual update
when a toolset's CLI flags change.** Its own `mcp-server/README.md` and
`mcp-server/tests/` cover its change/test workflow.

**A new toolset gets MCP support automatically, for free, if -- and
only if -- its CLI dispatcher follows the same shape
`skills/jira/scripts/jira_tool.py` and
`skills/telegram/scripts/telegram_tool.py` already use.** This isn't a
separate thing to build for MCP -- it's the same toolset layout this
file already asks for, made into a hard contract because
`mcp-server/lib/introspect.py` now reads it directly instead of a human
reading it. Concretely, for every new/changed toolset:

- `build_parser()` returns one top-level `ArgumentParser` with
  `add_subparsers(dest="tool", required=True)`; each action is
  `subparsers.add_parser("name", help="...")` with a real, one-line
  `help=` string -- that string becomes the generated MCP tool's
  description, so don't omit it or leave it generic.
- Every argument is a `--flag` (`add_argument("--name", ...)`), never
  positional. A positional argument can't be mapped to a named MCP tool
  parameter -- the introspector refuses to register *any* of that
  toolset's tools rather than guess, so one positional argument on one
  subcommand breaks MCP access to the entire toolset until it's fixed.
- Prefer plain `str` (the default, no `type=`), `int`, `float`,
  `action="store_true"` for a boolean, or `action="append"` for a
  repeatable flag (becomes a JSON array) -- these get an exact JSON
  Schema type in the generated tool. A custom `type=` callable (e.g. a
  hand-rolled true/false string parser) still works and is still
  validated by the CLI itself when it runs, but shows up as a plain
  string in the generated tool's schema since the introspector can't
  infer an arbitrary function's semantics -- use the built-in forms
  above instead whenever the flag's validation logic allows it.
- `choices=[...]` on an argument becomes a JSON Schema `enum` -- use it
  for any flag that only accepts a known, fixed set of values.
- `main()` must keep printing exactly one `json.dumps(result,
  default=str)` document to stdout, success or failure alike, and exit
  `0` for any handled outcome (`{"error": {...}}` included) -- this was
  already the rule for every human/agent reading the CLI directly, and
  it's now also what `mcp-server` itself parses, treating non-JSON
  stdout or a nonzero exit as its own structured error.
- A write action's confirm gate (see the confirm-gating rule below)
  needs no MCP-specific handling as long as `--confirm` stays a plain
  `action="store_true"` flag -- `mcp-server` only forwards whatever the
  caller passes, so the same two-step `requires_confirmation`/
  `pending_action` flow already works unchanged over MCP.

When adding a brand-new toolset, follow the "Adding a toolset" section
in the top-level `README.md`. See that file's "Agent Skills format"
section for the open format this repo's `SKILL.md`s follow, and where
this repo's frontmatter extends it.

## Conventions

These apply repo-wide, to every toolset, not just Jira:

- **Credentials only ever come from environment variables**, never
  hard-coded, never logged in plaintext.
- **No hardcoded local filesystem paths** in any `SKILL.md`, `README.md`,
  or Python source -- this repo is public. Use `../<toolset>/...`-relative
  paths or a generic `/path/to/...` placeholder in docs.
- **Write/mutating operations are confirmation-gated in code**, not just
  prompted -- e.g. the Jira toolset's `worklog`/`transition` refuse to
  execute without `--confirm` unless `JIRA_AUTO_CONFIRM_WRITES=true`.
  Any new toolset with side-effecting actions must gate them the same
  way, with an equivalent explicit `--confirm`/`*_AUTO_CONFIRM_WRITES`
  escape hatch, not just instructions in the skill's markdown body. A
  toolset may go *stricter* than this baseline when an action's
  consequence is high enough that an agent-satisfiable flag isn't a real
  guarantee -- `skills/telegram/`'s `send_message`/`send_bulk`/
  `forward_message` have no auto-confirm escape hatch at all, and in
  their default confirm mode require a `yes` typed at a real terminal
  the calling agent cannot supply. Going stricter than the baseline is
  fine; going looser (a write with no code-level gate at all) is not.
- **A `--confirm`-style flag is not, by itself, a guarantee against an
  agent that ignores its own instructions** -- the flag is something the
  calling agent passes, so it can satisfy it on the very first call.
  Where that distinction matters (an action whose consequence a human
  should verify, not just an agent), gate it behind something the agent
  genuinely cannot supply on its own -- e.g. reading a confirmation from
  a real controlling terminal rather than accepting it as a function
  argument. See `skills/telegram/lib/guard.py`'s `gate()` for the
  pattern.
- Each skill's `required_environment_variables` frontmatter must list
  every env var that its code path actually reads -- Hermes uses that
  list to decide which vars are allowed to pass through to the sandboxed
  `terminal` tool that runs the CLI. An unlisted var will be silently
  stripped at runtime, not just undocumented. `mcp-server` reads the
  same list too, for a matching but separate reason: it runs a
  pre-flight check before spawning any subcommand and returns a clear
  `missing_environment_variables` error instead of a raw traceback when
  one's unset. That check trusts one convention about each entry's
  `required_for` prose: write it starting with the literal word
  "optional" for a var that's genuinely optional (as every current
  `SKILL.md` already does, e.g. `JIRA_DEFAULT_PROJECT`'s "optional --
  scopes issue lookups"), and anything else for one that's required.
  Don't phrase a required var's `required_for` in a way that happens to
  start with "optional" -- it will be silently treated as unset-and-fine.
- **Agent/runtime-specific details belong in `SKILL.md`'s frontmatter
  (`metadata.hermes.*`, `required_environment_variables`), never in the
  skill's body prose, `prompts/`, or the tool-invocation instructions
  themselves.** E.g. don't write "run this via `terminal`" in a
  `SKILL.md` body -- that's Hermes' tool name, and the same instruction
  text is read by Claude Code and claude.ai too. Say "run this from the
  skill's directory" instead, and declare `requires_toolsets: [terminal]`
  in frontmatter for Hermes to key off of. This keeps one `SKILL.md` per
  action usable, unmodified, across every runtime -- only the manifest
  varies by consumer, not the instructions.

- **If a toolset has facts that are stable but not known in advance**
  (a project's real status names, a board's type, a resolved id for a
  person/record) **document them in that toolset's `README.md`**, in a
  section covering what a consuming agent should persist to its own
  runtime's memory feature and why each fact is safe to cache (see
  `skills/jira/README.md`'s "Agent memory" section for the pattern).
  Every skill that touches one of those facts must save it **the moment
  it's learned, in the same turn** -- not as a follow-up triggered by the
  user asking "will you remember that?". Waiting to be asked defeats the
  point: the fact still gets re-fetched (or re-asked) every session until
  someone happens to check.

  This convention has a deliberate opt-out: a toolset that handles
  private third-party data -- someone else's messages, not just the
  user's own project state -- may forbid persistence entirely instead of
  cataloging what's safe to remember. `skills/telegram/README.md`'s "No
  agent memory" section is the example; its `SKILL.md` states the
  inverse rule (persist nothing this skill returns, ever) and explains
  why saving *less* is the right default when what's being fetched is
  someone else's private content, not the user's own stable project
  facts. Note this is a case where the guarantee can't be enforced in
  code the way the rest of this document asks for -- a runtime's memory
  feature lives outside the skill's own CLI, so this specific rule rests
  on the consuming agent actually following the instruction, which
  `skills/telegram/README.md` says explicitly rather than overstating
  the guarantee.

- **A skill never hardcodes one user's or team's workflow.** Skills are
  generic tools; process ("every task also gets a specific kind of
  subtask", "issues of a certain type always get a certain label") is
  only ever the consuming agent's job to apply -- and only because a
  user told that agent, in its own memory, to remember it. A `SKILL.md`
  may instruct the agent to *check* for such a remembered convention
  before treating a write as complete (see the Jira toolset's rule 15),
  but must never state what any real convention actually is. This repo
  is public: don't write a real person's name, a real project's key or
  label, or a real team's specific process into any `SKILL.md`,
  `README.md`, test, or example -- when illustrating the pattern, use an
  obviously generic placeholder instead.

- **Releases and skill versions follow [SemVer](https://semver.org)**
  (`MAJOR.MINOR.PATCH`). Two separate surfaces carry a version, both
  governed by the same rules:
  - **Repo-level git tags** (`vX.Y.Z`, e.g. `v0.1.0`, `v0.2.0`) mark a
    release snapshot of the whole repo, as annotated tags
    (`git tag -a vX.Y.Z -m "..."`). Bump `MAJOR` for a breaking change
    (a removed/renamed tool, subcommand, CLI flag, or MCP tool; a
    changed JSON response shape an existing consumer would already be
    parsing); `MINOR` for a backward-compatible addition (a new
    toolset, a new skill, a new subcommand/flag, a new MCP tool);
    `PATCH` for a backward-compatible fix (bug fix, doc correction,
    test-only change) that doesn't add or remove anything callable.
    While the repo is still `0.x`, SemVer itself allows anything to
    change without a major bump -- keep using `MINOR`/`PATCH` by the
    same rules anyway, so the tag history stays meaningful once the
    repo reaches `1.0.0`.
  - **Each skill's own `version:` frontmatter field** in its `SKILL.md`
    tracks that one skill's changes independently, by the same
    `MAJOR`/`MINOR`/`PATCH` rules, scoped to that skill alone -- a
    breaking change to `jira`'s CLI bumps `jira`'s `version`, not every
    other skill's. Bump it in the same change that alters the skill's
    behavior, not as a separate followup -- same discipline as "When
    changing an action's CLI flags or output, update every
    `<toolset>-*/SKILL.md`" above: the version bump is part of that
    same update, not a thing to remember later.

Toolset-specific conventions (e.g. "Jira auth is Basic-only, don't
reintroduce PAT without being asked") belong in that toolset's own
`skills/<toolset>/README.md`, not here.
