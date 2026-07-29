# Agent skills

A personal collection of AI-agent skills -- a portable developer/work
toolset, not a single-purpose repo. It currently holds a Jira toolset
plus one standalone skill (`mood`, a tone/style switch with no toolset
behind it); it's meant to grow with unrelated toolsets (e.g. a company
back-office toolset) and further standalone skills alike, each
following its own pattern's convention (see "Layout and convention" and
"Standalone skills" below).

Every skill here is a standard `SKILL.md`-fronted directory (YAML
frontmatter + a markdown body of instructions). Most toolset skills put
their actual logic in a plain Python CLI invoked via a shell/terminal
tool; standalone skills (see "Standalone skills" below) have no CLI at
all -- the instructions are the whole skill. That shape isn't tied to
one agent runtime -- see "Installation" and "Usage" below for Hermes
Agent, Claude Code, and claude.ai specifically, and "Agent Skills
format" for the open standard this follows.

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
extra frontmatter (`version`, `metadata.hermes.*`, `required_environment_variables`)
that isn't part of the open spec -- Hermes-specific keys a spec-compliant
runtime simply doesn't recognize and ignores, per "Frontmatter
compatibility" below. Nothing about the extension changes how a strictly
spec-following runtime reads these skills; it only adds information a
runtime *can* use if it knows to.

Runtime-specific docs, for context (not the spec itself, but the primary
runtimes this repo is written to run under):

- Claude Code: <https://code.claude.com/docs/en/skills>
- claude.ai: <https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview>

## Layout and convention

Every toolset in this repo follows the same shape: one directory with
the shared implementation, plus one thin directory per tool/action that
wraps it. For the existing Jira toolset:

```
skills/
├── jira/                # The full Jira client + CLI + tests (shared code)
├── jira-my-work/         # Thin skill: unresolved issues assigned to you
├── jira-issues/           # Thin skill: arbitrary JQL search
├── jira-issue-summary/    # Thin skill: full context for one issue
├── jira-blockers/         # Thin skill: blocking status for one issue
├── jira-sprint/           # Thin skill: active sprint/board/goal
├── jira-kanban-status/    # Thin skill: kanban board columns/issue counts
├── jira-board/             # Orchestrator: sprint or kanban_status, auto-detected
├── jira-worklog/          # Thin skill: log time (write, confirm-gated)
├── jira-worklog-edit/     # Thin skill: fix a worklog's duration/description/date (write, confirm-gated)
├── jira-worklog-delete/   # Thin skill: permanently delete a worklog (write, confirm-gated)
├── jira-log/               # Orchestrator: log/edit/delete a worklog, routed by intent (write, confirm-gated)
├── jira-track/             # Track a day's work as it's narrated, then log it (write, confirm-gated)
├── jira-status/           # Thin skill: move an issue's status (write, confirm-gated)
├── jira-worklog-report/   # Thin skill: logged time vs. estimate over a date range
├── jira-triage/           # Thin skill: group stories with their labeled subtasks for FE/BE/design triage
├── jira-search-users/     # Thin skill: look up a user's account_id by name/email
├── jira-create-issue/     # Thin skill: create a new issue or subtask (write, confirm-gated)
├── jira-edit-issue/       # Thin skill: update fields on an existing issue or subtask (write, confirm-gated)
└── jira-project-context/  # Thin skill: reference snapshot of a project's statuses/labels/users
```

A future toolset (say, `backoffice`) would land the same way:
`skills/backoffice/` for the shared client + CLI + tests, and
`skills/backoffice-<action>/` for each thin per-action skill -- see
"Adding a toolset" below.

Each thin `<toolset>-<action>` skill has its own `SKILL.md` so it gets
its own slash command (`/jira-my-work`, `/jira-issues`, ...) -- Hermes
maps one `SKILL.md` to exactly one slash command, with no sub-command or
namespacing support. Every thin skill is a wrapper that calls into
`<toolset>/scripts/*.py` via a relative path; `<toolset>/` itself also
still works standalone as a single do-everything skill (e.g. `/jira`).

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

See `skills/jira/README.md` for that toolset's architecture,
configuration, test suite, and (in its "Agent memory" section) what a
consuming agent should persist to its own memory feature -- future
toolsets should have their own equivalent README under
`skills/<toolset>/`.

## Tools

One row per thin skill, across all toolsets. Keep this in sync when
adding or removing a `skills/<toolset>-<action>/` directory -- it's the
single place to see everything installable at a glance.

| Skill | Toolset | Type | Description |
|---|---|---|---|
| `jira` | [jira](skills/jira) | Read + Write | Do-everything Jira assistant (all actions below, one skill) |
| `jira-my-work` | [jira](skills/jira) | Read | Unresolved issues assigned to the current user (scoped to a project by default) |
| `jira-issues` | [jira](skills/jira) | Read | Arbitrary JQL search (incl. components/subtasks/custom fields; description on request) |
| `jira-issue-summary` | [jira](skills/jira) | Read | Full context for one issue (fields, comments, worklogs, changelog, links) |
| `jira-blockers` | [jira](skills/jira) | Read | Blocking status + reasons for one issue |
| `jira-sprint` | [jira](skills/jira) | Read | Active sprint, board, dates, goal (scoped to a project by default) |
| `jira-kanban-status` | [jira](skills/jira) | Read | Kanban board columns and per-column issue counts |
| `jira-board` | [jira](skills/jira) | Read | Orchestrator: routes to `jira-sprint` or `jira-kanban-status`, auto-detected |
| `jira-worklog` | [jira](skills/jira) | Write (gated) | Log time against an issue, optionally backdated |
| `jira-worklog-edit` | [jira](skills/jira) | Write (gated) | Update an existing worklog's duration/description/date |
| `jira-worklog-delete` | [jira](skills/jira) | Write (gated) | Permanently delete a worklog entry |
| `jira-log` | [jira](skills/jira) | Write (gated) | Orchestrator: routes to `jira-worklog`/`jira-worklog-edit`/`jira-worklog-delete` by intent |
| `jira-track` | [jira](skills/jira) | Write (gated) | Track a day's work as the user narrates it, separate interruptions from focused time, then log each issue |
| `jira-status` | [jira](skills/jira) | Write (gated) | Move an issue to a new status |
| `jira-worklog-report` | [jira](skills/jira) | Read | Logged time vs. estimate over a date range, per issue and total |
| `jira-triage` | [jira](skills/jira) | Read | Group unresolved stories/bugs/tasks with their labeled subtasks, for frontend/backend/design-readiness triage |
| `jira-search-users` | [jira](skills/jira) | Read | Look up a user's account_id by name/email fragment |
| `jira-create-issue` | [jira](skills/jira) | Write (gated) | Create a new issue or subtask |
| `jira-edit-issue` | [jira](skills/jira) | Write (gated) | Update fields on an existing issue or subtask |
| `jira-project-context` | [jira](skills/jira) | Read | Reference snapshot of a project: issue types, statuses, components, priorities, users, labels |

## Standalone skills

Not every skill in this repo backs onto a toolset. A **standalone
skill** is a single `SKILL.md` file with no sibling directory to shell
out to -- no `lib/`, `tools/`, `scripts/`, `tests/`, `requirements.txt`,
or `README.md` of its own. It's pure instructions: markdown the agent
reads and follows, with no Python, no CLI, and no external API call
behind it.

```
skills/
└── mood/    # Standalone: changes the agent's tone/style for the conversation
```

The first (and, so far, only) standalone skill is [`mood`](skills/mood)
-- switches the agent's conversational tone (`neutral`/`alpha`/`angry`/
`sarcastic`/`flatterer`/`too-kind`) for the rest of the session. See its
`SKILL.md` for the full mode reference.

| Skill | Type | Description |
|---|---|---|
| `mood` | Instructions-only | Switches the agent's tone/style (`neutral`/`alpha`/`angry`/`sarcastic`/`flatterer`/`too-kind`) for the rest of the conversation |

Standalone skills need none of "Installation"'s steps 2-3 below (no
`requirements.txt` to install, no environment variables to set) --
step 1 (clone the repo) is the only one that applies.

## Installation

1. Clone this repo somewhere permanent -- skills run straight out of the
   checkout, there's no build/publish step:

   ```bash
   git clone git@github.com:arfar-x/skills.git
   ```

2. Install each toolset's Python dependencies into whatever environment
   your agent runtime actually executes shell commands in (see the
   per-runtime notes below for what that environment is):

   ```bash
   pip install -r skills/jira/requirements.txt
   ```

3. Set the environment variables each toolset needs (see that toolset's
   own `README.md`, e.g. `skills/jira/README.md`, for its config table --
   for Jira that's `JIRA_BASE_URL` / `JIRA_USERNAME` / `JIRA_PASSWORD`).
   Where those variables need to live differs by runtime -- see below.

### Installing via `npx skills`

[`npx skills`](https://github.com/vercel-labs/skills) is a third-party
CLI (not part of the Agent Skills spec itself) that fetches `SKILL.md`
directories straight from a GitHub repo into whichever agent's config
directory it detects (Claude Code, Cursor, and others) -- no local clone
or `pip install` step needed on your end. It already recognizes this
repo's `skills/` layout as a standard skills location, so no special
path argument is required.

```bash
# See every skill this repo exposes before installing anything:
npx skills add arfar-x/agent-skills --list

# Install one or more specific skills by name:
npx skills add arfar-x/agent-skills --skill jira --skill jira-my-work

# Install every skill in the repo:
npx skills add arfar-x/agent-skills --all

# Target a specific agent explicitly (autodetected otherwise):
npx skills add arfar-x/agent-skills -a claude-code --skill jira
```

This only fetches `SKILL.md` and its bundled files -- it does **not**
install Python dependencies or set environment variables. After
installing, still run step 2 (`pip install -r skills/jira/requirements.txt`,
against whichever Python environment your agent actually executes shell
commands in) and step 3 (export the toolset's required env vars) above.

**Keeping installed skills in sync:** `npx skills` copies files at
install time; it does not auto-track upstream changes. When this repo's
skills change (a new commit adds a rule, a new tool, a renamed skill),
re-run:

```bash
# Re-pull everything you previously installed from this repo:
npx skills update

# Or re-pull specific skills by name:
npx skills update jira jira-my-work
```

If you instead cloned the repo directly (see steps 1-3 above, or the
Hermes `external_dirs` / Claude Code symlink approaches below), staying
in sync is just `git pull` -- skills run straight out of the checkout,
so there's nothing else to re-install. A symlinked or `external_dirs`-registered
skill always reflects the latest commit the moment you pull; only a
copied directory (`cp -r`, or a claude.ai zip upload) needs to be
manually redone after each pull.

### Hermes Agent

- **Discovery**: point `skills.external_dirs` in `~/.hermes/config.yaml`
  at this repo's `skills/` directory:

  ```yaml
  skills:
    external_dirs:
      - /path/to/your/local/checkout/of/skills/skills
  ```

  or `hermes skills install arfar-x/agent-skills/skills/<path-to-one-skill>` to fetch
  a single skill by path. There is no bulk/sub-package install -- one
  `SKILL.md` per install call, so `external_dirs` is the practical
  option for a growing personal collection like this one.
- **Slash commands**: Hermes maps exactly one `SKILL.md` to exactly one
  `/<name>` command, with no sub-command or colon-namespacing support.
  That's why each tool (`jira-my-work`, `jira-issues`, ...) is its own
  thin skill directory instead of one skill with sub-commands.
- **Env vars**: Hermes runs skill code in a sandboxed `terminal` tool
  that strips environment variables by default. A var only reaches the
  process if it's listed in that skill's `required_environment_variables`
  frontmatter *and* the skill has been loaded in the session (Hermes
  auto-registers the allowlist on `skill_view`). An env var actually read
  by the code but missing from that list is silently stripped, not just
  undocumented -- this applies to every toolset here, not just Jira, so
  each new toolset's skills must list every env var its code path reads.
  See the "Conventions" note in `AGENTS.md`. Set the actual values
  wherever Hermes' sandbox inherits its environment from (e.g. its own
  `.env` file).
- Alternatively, if your Hermes deployment can't use `external_dirs`
  (e.g. a remote/managed instance), copy a skill directory directly:
  `cp -r skills/jira ~/.hermes/skills/jira`. This creates a disconnected
  copy -- future changes to this repo won't apply until you re-copy.

### Claude Code

- **Discovery**: copy or symlink a skill directory into
  `.claude/skills/<name>/` (project-scoped) or `~/.claude/skills/<name>/`
  (personal, available in every project), e.g.:

  ```bash
  ln -s /path/to/your/local/checkout/of/skills/skills/jira ~/.claude/skills/jira
  ```

  Claude Code decides when to invoke a skill by matching its
  `description` against the task at hand -- there's no separate
  per-skill slash-command registration step.
- **Env vars**: Claude Code's shell tool inherits your actual shell
  environment, so a toolset's required env vars just need to be
  exported normally (`.zshrc`, a sourced `.env`, etc.) -- there's no
  separate allowlist to satisfy, unlike Hermes.

### claude.ai (web/app)

- **Discovery**: zip the skill directory (e.g. `skills/jira/`) and
  upload it under Settings -> Capabilities -> Skills.
- **Env vars / network**: code there runs inside Anthropic's own hosted
  sandbox, which has no access to your local shell environment *or*
  your internal network. A toolset that calls out to an internal host
  (an on-prem Jira, an internal back-office API, ...) won't be reachable
  from there regardless of env vars -- this path only really works for
  services reachable from the public internet, and you'll need another
  way to supply secrets (claude.ai's own per-skill configuration, if
  the toolset exposes one).

### Frontmatter compatibility

Hermes-only frontmatter keys (`metadata.hermes.*`,
`required_environment_variables`) are just unknown YAML to Claude and
are ignored -- no stripping or per-platform variant is needed. The same
`SKILL.md` file works unmodified across every runtime above.

## Usage

Once a toolset's env vars are set and its skill is discoverable (see
Installation), invoke it:

- **Hermes**: use its slash command directly, e.g. `/jira-my-work`, or
  `/jira` for the do-everything form (e.g. `/jira what's blocking
  PAY-123?`). Run `/skills` to confirm a skill is currently loaded.
- **Claude Code / claude.ai**: just ask in plain language -- e.g. "what
  should I work on next in Jira?" or "log 2h against PAY-123". Claude
  matches your request against each installed skill's `description` and
  invokes it (and its underlying CLI) automatically; there's no slash
  command to remember.

Every toolset documents its own read vs. write actions and any
confirmation gating in its own `README.md` -- e.g. `skills/jira/README.md`
lists `my_work`, `issue_summary`, `blockers`, `search`, `search_users`,
`sprint` (read), and `worklog`, `transition`, `create_issue`, `edit_issue`
(write, refuse to run without `--confirm` or
`JIRA_AUTO_CONFIRM_WRITES=true`). Check that file before relying on a
new toolset's write actions.

## Adding a toolset

To add an unrelated toolset (e.g. a company back-office skill-set),
follow the same pattern the Jira toolset already uses:

1. `skills/<toolset>/` -- the shared implementation: a `lib/` (client,
   auth/config from env vars), `tools/` (one module per action), a
   `scripts/<toolset>_tool.py` CLI dispatcher, a `tests/` suite, its own
   `requirements.txt`, and a `README.md` documenting its config and env
   vars. This directory's own `SKILL.md` can work standalone as a
   single do-everything skill.
2. `skills/<toolset>-<action>/` -- one thin `SKILL.md`-only directory
   per action/tool, each shelling out to
   `../<toolset>/scripts/<toolset>_tool.py <action> [flags]`. These
   exist purely so each action gets its own slash command in Hermes;
   they contain no Python of their own and nothing to test.
3. List every env var the toolset's code actually reads in each thin
   skill's `required_environment_variables` frontmatter (Hermes-only,
   but harmless elsewhere -- see "Frontmatter compatibility" above).
4. Follow the repo-wide conventions in `AGENTS.md` regardless of
   toolset -- credentials only from env vars, no hardcoded local paths,
   write/mutating actions confirmation-gated in code (not just
   prompted).
5. Add one row per new thin skill to the "Tools" table above.

No registration step is needed beyond adding the files -- Hermes
discovers new skills the next time it scans `external_dirs`, and Claude
discovers them the next time you copy/symlink into `.claude/skills/`
(or re-zip for claude.ai).
