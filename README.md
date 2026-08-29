# Agent skills

A personal collection of AI-agent skills -- a portable developer/work
toolset, not a single-purpose repo. It currently holds one toolset
(`jira`, plus its many thin per-action wrapper skills), four standalone
skills (`mood`, `prd`, `trd`, `adr`), and one internal toolset (`telegram`,
excluded from default installs); it's meant to grow with unrelated
toolsets (e.g. a company back-office toolset) and further standalone
skills alike, each following its own pattern's convention -- see "Layout
and convention", "Standalone skills", and "Internal skills" below for
what those patterns are, and "Skills in this repo" at the end for the
full list.

Every skill here is a standard `SKILL.md`-fronted directory (YAML
frontmatter + a markdown body of instructions), following the open
**Agent Skills** format (see below) -- the same shape works across Claude
Code, claude.ai, Hermes, and any other runtime that reads `SKILL.md`
files.

New here, or building on top of this repo (e.g. wiring it into a
workflow tool)? See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the
purpose, the request-to-response flow (both the native `SKILL.md` path
and the [MCP server](mcp-server) path), the core entities, and a worked
example of automating a doc-generation-to-Jira pipeline on top of this
repo.

## Installation

**Primary method: [`npx skills`](https://github.com/vercel-labs/skills)**,
a third-party CLI that fetches `SKILL.md` directories straight from this
repo into whichever agent's config directory it detects (Claude Code,
Cursor, and others) -- no local clone or manual `pip install` step. It
already recognizes this repo's `skills/` layout, so no special path
argument is needed, and it's what already handles the Claude
Code/Hermes-specific placement described in "Frontmatter compatibility"
below -- you don't need to configure either by hand to use it.

```bash
# See every (non-internal) skill this repo exposes before installing anything:
npx skills add arfar-x/agent-skills --list

# Install one or more specific skills by name:
npx skills add arfar-x/agent-skills --skill jira --skill jira-my-work

# Install every non-internal skill in the repo:
npx skills add arfar-x/agent-skills --all

# Target a specific agent explicitly (autodetected otherwise):
npx skills add arfar-x/agent-skills -a claude-code --skill jira
```

This only fetches `SKILL.md` and its bundled files -- it does **not**
install Python dependencies or set environment variables. After
installing a toolset, still `pip install -r skills/<toolset>/requirements.txt`
(into whatever environment your agent runtime executes shell commands
in) and export that toolset's required env vars -- see its own
`README.md` (e.g. `skills/jira/README.md`) for the exact config table.

**Installing an internal skill** (see "Internal skills" below --
`telegram` is the current example): these are excluded from `--list` and
`--all` by this repo's convention, but a named `--skill` target still
installs it regardless of that filtering, so name it explicitly and set
`INSTALL_INTERNAL_SKILLS=1` for the install:

```bash
INSTALL_INTERNAL_SKILLS=1 npx skills add arfar-x/agent-skills --skill telegram
```

Read `skills/telegram/README.md`'s disclaimer before doing this -- an
internal skill is internal because of what it grants, not because it's
unfinished.

**Keeping installed skills in sync:** `npx skills` copies files at
install time; it does not auto-track upstream changes. Re-run
`npx skills update` (or `npx skills update jira jira-my-work` for
specific skills) after this repo changes.

### Alternative: clone directly

Skills run straight out of the checkout, no build/publish step:

```bash
git clone git@github.com:arfar-x/agent-skills.git
```

Then either symlink/copy the skill directories your runtime expects
(`.claude/skills/<name>/` for Claude Code, `skills.external_dirs` in
Hermes' config, a zip upload for claude.ai), or use `jira`/`mood`/`prd`/
`trd`/`adr` straight from the checkout. A symlinked or `external_dirs`-registered
skill reflects the latest commit the moment you `git pull`; a copied
directory (`cp -r`, a claude.ai zip) needs to be manually redone after
each pull. See "Frontmatter compatibility" below for why the exact same
`SKILL.md` works across every runtime without a per-platform variant --
per-skill `README.md`s stay runtime-agnostic on purpose, so this is the
one place runtime setup specifics live.

## Skills directly, or via the MCP server?

Two ways to consume what's in this repo -- pick based on what your
runtime/client actually speaks:

- **Your runtime already reads `SKILL.md` natively** (Hermes, Claude
  Code, claude.ai) -> install the skill directly, per "Installation"
  above. Nothing below is relevant to you.
- **Your client speaks MCP but can't read `SKILL.md`/Agent Skills
  format** (Dify, Claude Desktop, or any other MCP client) -> point it
  at [`mcp-server/`](mcp-server) instead. It's a small server, embedded
  in this repo, that serves the exact same skills over MCP: every
  skill's instructions are still read live from its `SKILL.md` (via a
  `get_skill` tool -- nothing about the instructions is duplicated or
  reauthored), and each toolset's actions are exposed as typed tools
  (`jira_worklog`, `jira_now`, ...) generated from the same CLI every
  other runtime already shells out to. One source of instructions,
  fanned out to whichever format the client needs.

Internal skills (e.g. `telegram`) stay opt-in either way -- direct
install still needs `INSTALL_INTERNAL_SKILLS=1`; the MCP server needs
`--include-internal` (or the same env var) on top of that, plus
telegram's own `/dev/tty`-confirm caveat for outbound sends. See
[`mcp-server/README.md`](mcp-server/README.md) for setup and that
caveat in full.

## Usage

Once a skill is installed and its env vars (if any) are set, just ask in
plain language -- e.g. "what should I work on next in Jira?" or "log 2h
against PAY-123." Claude Code and claude.ai match your request against
each installed skill's `description` and invoke it automatically; Hermes
instead maps each skill to its own `/<name>` slash command (`/jira`,
`/jira-my-work`, ...) since it has no natural-language skill matching --
run `/skills` there to confirm what's currently loaded.

Every toolset documents its own read vs. write actions and any
confirmation gating in its own `README.md` -- check that file before
relying on a new toolset's write actions.

## Agent Skills format

Every skill in this repo follows the **Agent Skills** open format:

- Overview: <https://agentskills.io/home>
- Full specification: <https://agentskills.io/specification>

In its own words, the format defines a skill as "a folder containing a
`SKILL.md` file. This file includes metadata (`name` and `description`,
at minimum) and instructions that tell an agent how to perform a
specific task." Agents load skills through **progressive disclosure**:
only `name`/`description` at startup (cheap, so many skills can sit
available at once), the full body only once a task actually matches one,
and bundled files only as the instructions reference them. That's why
every `SKILL.md` here front-loads a specific, matchable `description` in
its frontmatter, and why per-action detail lives in the skill's body
rather than the frontmatter.

The format was originally developed and published by Anthropic as an
open standard; it's since been adopted across a large number of agent
runtimes beyond Claude (see agentskills.io's client showcase), which is
the whole point of writing skills this way instead of tying them to one
runtime's proprietary plugin format.

The spec requires only `name`/`description`. This repo's `SKILL.md`s add
extra frontmatter (`version`, `metadata.category`, `metadata.hermes.*`,
`metadata.internal`, `required_environment_variables`) that isn't part
of the open spec -- keys a spec-compliant runtime simply doesn't
recognize and ignores, per "Frontmatter compatibility" below.

Runtime-specific docs, for context (not the spec itself, but the primary
runtimes this repo is written to run under):

- Claude Code: <https://code.claude.com/docs/en/skills>
- claude.ai: <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview>

### Frontmatter compatibility

`metadata.category` is a plain string under the spec's own `metadata`
map (`author`/`version` in the spec's example are the same shape) --
every skill in this repo sets it to one of a small fixed set of values
(`software-development`, `productivity`, ...) so that any spec-compliant
client, not just Hermes, can group skills by category without knowing
about a runtime-specific namespace.

Hermes-only frontmatter keys (`metadata.hermes.*`,
`required_environment_variables`) are just unknown YAML to Claude and are
ignored -- no stripping or per-platform variant is needed.
`metadata.hermes.category` duplicates the top-level `metadata.category`
above rather than replacing it -- Hermes' own installer specifically
reads that nested path to sort an installed skill into its category
folder, so it stays even though the top-level key already covers every
other client. `metadata.internal` is a convention this repo's own
frontmatter follows (see "Internal skills" below), not part of the spec
either. The same `SKILL.md` file works unmodified across every runtime
above; Hermes specifically runs skill code in a sandboxed `terminal`
tool that strips any env var not listed in that skill's
`required_environment_variables` (see `AGENTS.md`'s "Conventions" for
the exact mechanism), which is the one place a toolset's frontmatter
does real work beyond documentation.

## Layout and convention

Every toolset in this repo follows the same shape: one directory with the
shared implementation (`lib/`, `tools/`, `scripts/<toolset>_tool.py`,
`tests/`, its own `README.md`), plus one thin `SKILL.md`-only directory
per tool/action that wraps it and exists purely so the action gets its
own Hermes slash command:

```
skills/
├── <toolset>/            # Shared implementation -- also works standalone, e.g. /jira
└── <toolset>-<action>/   # Thin wrapper, one per action -- e.g. jira-my-work, jira-worklog
```

`jira` is the only toolset in the repo today; see its own
[`README.md`](skills/jira/README.md) for its full thin-skill catalog and
the parent skill each one wraps. A future toolset (say, `backoffice`)
lands the same way -- see "Adding a toolset" below.

Thin per-action wrapper skills are the norm for a toolset meant to be
installed piecemeal, not a requirement every toolset must satisfy --
`skills/telegram/` (see "Internal skills" below) is a toolset with none,
deliberately: it's `metadata.internal: true`, so it isn't being exposed
as a discoverable per-action command catalog in the first place, and
multiplying a high-risk skill's installable surface across ten separate
entry points would be its own risk to avoid.

A thin skill normally maps 1:1 to a single CLI subcommand. The one
documented exception is an **orchestrator skill** (e.g. `jira-board`,
`jira-log`): it doesn't add a new action of its own, it routes between
two or more *existing* thin skills' subcommands based on a condition --
either a signal returned by one of them (`jira-board` checks whether
`sprint` reports a kanban board before deciding to call `kanban_status`
instead) or the caller's own phrasing (`jira-log` picks `worklog` vs.
`worklog_edit` vs. `worklog_delete` from what's being asked). This keeps
the underlying sub-skills fully usable standalone for a caller who
already knows which one they want, while giving one skill/slash command
to reach for when they don't. Skills still cannot call each other
programmatically -- an orchestrator's `SKILL.md` body just tells the
agent which subcommand to run next, the same as any other instruction in
this repo.

## Standalone skills

Not every skill in this repo backs onto a toolset. A **standalone
skill** is a single `SKILL.md` file with no sibling directory to shell
out to -- no `lib/`, `tools/`, `scripts/`, `tests/`, `requirements.txt`,
or `README.md` of its own. It's pure instructions: markdown the agent
reads and follows, with no Python, no CLI, and no external API call
behind it. `mood` (tone/style switch), `prd` (PRD drafting), `trd` (TRD
drafting), and `adr` (ADR drafting) are the four so far -- see their own
`SKILL.md`s for the full reference, or "Skills in this repo" below for a
one-line description of each.

Standalone skills need none of "Installation"'s Python/env-var steps --
installing the skill is the whole setup.

## Internal skills

A skill (standalone or toolset) can be marked **internal** --
`metadata.internal: true` in its `SKILL.md` frontmatter -- to keep it out
of normal installs and listings. The convention this repo's frontmatter
follows is that an internal skill is only visible and installable when
the installer is explicitly run with `INSTALL_INTERNAL_SKILLS=1`; without
it, the skill is skipped as if it didn't exist. This repo doesn't ship an
installer of its own -- the guarantee is only as real as whatever tool a
given user installs skills with actually honoring it; a manual copy of
the skill directory bypasses this entirely, the same way it bypasses
`required_environment_variables`. This repo's file tree is public either
way -- "internal" changes what installs by default, not what's visible
on GitHub.

This exists for a skill whose risk profile shouldn't be part of a
default install: [`skills/telegram`](skills/telegram) is the first
example -- a Telethon-based skill granting an agent access to a personal
Telegram account. It isn't a general-purpose way to de-list a skill
that just isn't ready yet -- it's specifically for "this needs the
installing human to have actively opted in, having read what it grants."
See `skills/telegram/README.md` for its disclaimer and security model
before installing it.

## Adding a toolset

To add an unrelated toolset (e.g. a company back-office skill-set),
follow the same pattern the Jira toolset already uses:

1. `skills/<toolset>/` -- the shared implementation: a `lib/` (client,
   auth/config from env vars), `tools/` (one module per action), a
   `scripts/<toolset>_tool.py` CLI dispatcher, a `tests/` suite, its own
   `requirements.txt`, and a `README.md` documenting its config, env
   vars, and (per "Layout and convention" above) its own thin-skill
   catalog. This directory's own `SKILL.md` can work standalone as a
   single do-everything skill.
2. `skills/<toolset>-<action>/` -- one thin `SKILL.md`-only directory
   per action/tool (optional -- see "Layout and convention" above for
   when a toolset should skip this), each shelling out to
   `../<toolset>/scripts/<toolset>_tool.py <action> [flags]`.
3. List every env var the toolset's code actually reads in each skill's
   `required_environment_variables` frontmatter (Hermes-only, but
   harmless elsewhere -- see "Frontmatter compatibility" above).
4. Follow the repo-wide conventions in `AGENTS.md` regardless of
   toolset -- credentials only from env vars, no hardcoded local paths,
   write/mutating actions confirmation-gated in code (not just
   prompted).
5. Add one row to "Skills in this repo" below for the toolset itself
   (not each thin skill -- those belong in the toolset's own `README.md`,
   per "Layout and convention" above).

No registration step is needed beyond adding the files -- Hermes
discovers new skills the next time it scans `external_dirs`, and Claude
discovers them the next time you copy/symlink into `.claude/skills/`
(or re-zip for claude.ai).

## Skills in this repo

Primary, installable-by-name skills only -- each toolset's own thin
per-action wrappers are cataloged in that toolset's own `README.md`
instead (linked below), not repeated here.

| Skill | Type | Description |
|---|---|---|
| [`jira`](skills/jira) | Toolset (Read + Write) | Do-everything Jira assistant -- see [`skills/jira/README.md`](skills/jira/README.md) for its full thin-skill catalog |
| [`mood`](skills/mood) | Standalone | Switches the agent's tone/style (`neutral`/`alpha`/`angry`/`sarcastic`/`flatterer`/`too-kind`) for the rest of the conversation |
| [`prd`](skills/prd) | Standalone | Drafts a PRD from a feature brief and maintains `CURRENT_STATE.md`, a PRD-implementation-status navigation map |
| [`trd`](skills/trd) | Standalone | Turns a PRD or feature brief into a Technical Requirements/Design Document under `docs/TRDs/` |
| [`adr`](skills/adr) | Standalone | Records a design/architecture decision, its context, alternatives, and consequences under `docs/ADRs/` |
| [`telegram`](skills/telegram) | Toolset, **internal** | Reads/sends personal Telegram messages via Telethon -- see [`skills/telegram/README.md`](skills/telegram/README.md) for its disclaimer and security model before installing |
