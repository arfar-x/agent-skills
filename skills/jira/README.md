# Jira Assistant

A production-ready agent skill that lets an LLM act as a high-level Jira
assistant -- answering questions like "what should I work on next?" or
"what's blocking PAY-123?" -- without ever exposing raw Jira REST APIs to
the model. Runtime-specific details (Hermes, Claude Code, claude.ai) are
confined to `SKILL.md`'s `metadata.hermes` block and the "Installing
into Hermes" section below -- the skill body and CLI itself don't
assume any particular agent runtime. See "Agent memory" below for what a
consuming agent should remember across turns and sessions.

## Design

- **Thin tools, smart model.** Every tool in `tools/` only validates
  input, calls the shared Jira client, and returns structured JSON. No
  tool summarizes, prioritizes, or explains -- that reasoning happens in
  the agent, guided by `SKILL.md`.
- **One Jira client.** `lib/jira_client.py` is the only code in this
  skill that talks HTTP to Jira. It owns authentication, retries,
  pagination, rate-limit handling, error normalization, and optional
  response caching. No tool constructs its own HTTP request.
- **Deterministic "blocked" logic shared everywhere.** `lib/utils.py`
  defines the single rule set for what counts as "blocked" (status flags,
  unresolved "blocked by" links, flagged comments). `blockers()` and
  `my_work()` both use it, so they can never disagree.
- **Write operations are gated.** `worklog()`, `worklog_edit()`,
  `worklog_delete()`, `transition()`, `create_issue()`, and `edit_issue()`
  refuse to execute unless called with `confirm=true` (CLI: `--confirm`),
  or `JIRA_AUTO_CONFIRM_WRITES=true` is set. This backs up `SKILL.md`'s
  confirmation rule with an enforced safety net in code.
- **Fields are fetched and returned on demand, not by fixed set.**
  `resolve_issue_fields()` in `lib/jira_client.py` maps every named
  `Issue` field to the raw Jira field it needs, so a tool can ask for
  (and get back) only the fields it actually uses instead of a
  one-size-fits-all field list. `search()` exposes this to the caller as
  `only=[...]` (defaulting to everything except `description` and
  time-tracking fields -- the ones least often needed to scan many issues
  at once); `my_work()` uses it internally to fetch only its fixed
  output's fields; `issue_summary()` has an analogous `sections=[...]` to
  skip fetching comments/worklogs/changelog entirely when not needed.
  Single-issue tools (`get_issue`) still return everything by default,
  since a single call's cost is fixed regardless of field verbosity.
- **Project reference data is fetched fresh, not cached in code.**
  `project_context()` returns a project's statuses/labels/users/etc. as a
  plain read, with no disk cache or TTL logic of its own -- reuse across
  turns is delegated entirely to whatever persistent-memory feature the
  calling agent runtime already has (Claude Code's memory files, Hermes'
  memory subsystem, ...), per `SKILL.md`'s rule 12, rather than this skill
  reimplementing a caching layer that would only duplicate what the
  runtime already does. Both its user list and its label scan walk
  bounded pages via `_paginate()`/`search()` rather than requesting one
  large page of everything.

## Agent memory

This section is for the **agent using these skills**, not for someone
maintaining this repo (that's the top-level `AGENTS.md`/`CLAUDE.md`). It's
the canonical catalog every `jira-*` skill's own "check memory first"
notes point back to, so the rule is written once instead of diverging
six different ways across skills.

**The rule, stated once:** save a fact to your runtime's
persistent-memory feature (if it has one) the moment you learn it -- in
the same turn, unprompted. Not as a follow-up triggered by the user
asking "will you remember that?" or "do you have this saved?". If a
runtime waits to be asked before it saves something it was always going
to need again, it pays the same lookup cost every session and adds a
round-trip the user shouldn't have to initiate themselves. Saving
belongs in the same turn as reporting the result -- it is not a
separate, optional step.

This applies with no toolset-runtime coupling: it's written into each
skill's `SKILL.md` body (see "Frontmatter compatibility" in the
top-level `README.md`), so whatever memory mechanism the current runtime
provides -- Claude Code's memory files, Hermes' memory subsystem, or
none at all -- gets used the same way. If a runtime has no persistent
memory, none of this applies past the current conversation; that's fine,
these are instructions, not a guarantee.

**What to remember, and where each fact comes from:**

| Fact | Source | Why it's safe to cache |
|---|---|---|
| Issue types, statuses, `statuses_by_issue_type`, components, priorities, a labels sample | `project_context` | A project's workflow rarely changes; this is the primary seed call -- see `jira-project-context/SKILL.md` |
| Board type (Scrum vs. Kanban) and board id | `sprint`'s `"note"`, `kanban_status`, or `jira-board` | A project doesn't switch board types turn to turn -- see `jira-board`/`jira-sprint`/`jira-kanban-status`'s `SKILL.md`s |
| Real transition/status names | A `transition` error's "Available transitions" list, or `project_context`'s `statuses` | Same status set `project_context` already covers; a failed `transition` call is a free opportunity to learn it if you haven't already -- see `jira-status/SKILL.md` |
| A person's `account_id` (scoped to a project) | `search_users`, or `project_context`'s `users` | An account_id doesn't change once resolved -- see `jira-search-users/SKILL.md` |

**What NOT to remember:** only the *shape* of a project is stable. Never
treat as memorable:

- **Issue content** -- summaries, descriptions, comments, worklogs.
  Always fetched fresh (`my_work`, `search`, `issue_summary`).
- **Anything counted or dated** -- a kanban board's
  `issue_counts_by_column`, a sprint's active dates/goal, `worklog_report`
  totals. The type of board is memorable; how many issues are in each
  column right now is not.
- **Assignments/status of a specific issue** -- `SKILL.md`'s rule 4
  already forbids trusting stale conversation history for this; it
  applies doubly to persistent memory, which outlives even more turns.

If you're ever unsure whether a fact belongs in this list, ask: "would
this still be true next week without anyone doing anything?" Statuses,
board type, and account_ids: yes. Everything above in "What NOT to
remember": no.

**Workflow conventions -- a different kind of memory.** Everything above
is a Jira-side fact this toolset *learns* from an API response. A
convention is different: it's the user's own team process (e.g. "every
task also gets a specific kind of subtask" or "issues of a certain type
always get a certain label"), and it only ever enters memory because
the user explicitly told you to remember it -- never because you
inferred a "best practice" or copied one team's habit onto another
project. This toolset stays generic on
purpose: no skill hardcodes anyone's process, so this is the one place
that process can live without polluting the tools everyone else shares.
Once remembered, treat it as standing instruction for future writes on
that project (`SKILL.md`'s rule 15) -- not a fact to relearn or
re-verify against Jira, since Jira has no API for "our team's
convention."

## Project layout

```
skills/jira/
├── SKILL.md                # Skill manifest: frontmatter + agent instructions
├── scripts/
│   └── jira_tool.py         # CLI dispatcher the agent runs via `terminal`
├── prompts/                 # Source material SKILL.md was authored from
│   ├── system.md
│   └── examples.md
├── tools/                   # Thin, agent-facing entry points (Python functions)
│   ├── my_work.py
│   ├── issue_summary.py
│   ├── blockers.py
│   ├── worklog.py
│   ├── worklog_edit.py
│   ├── worklog_delete.py
│   ├── transition.py
│   ├── search.py
│   ├── search_users.py
│   ├── sprint.py
│   ├── kanban_status.py
│   ├── worklog_report.py
│   ├── list_fields.py
│   ├── now.py
│   ├── triage.py
│   ├── create_issue.py
│   ├── edit_issue.py
│   └── project_context.py
├── lib/                     # Shared implementation, not directly agent-facing
│   ├── jira_client.py       # The single Jira REST client
│   ├── auth.py              # Env-based configuration + validation
│   ├── models.py            # Typed, JSON-serializable data models
│   └── utils.py             # Duration parsing, ADF text extraction, blocking rules
├── skill.yaml                # Generic tool-schema manifest, kept for non-Hermes
│                              # integrations that consume function-calling schemas
└── tests/                    # Unit tests for the client and every tool
```

## Configuration

All configuration comes from environment variables. **No credentials are
ever hard-coded.**

| Variable | Required | Default | Description |
|---|---|---|---|
| `JIRA_BASE_URL` | Yes | -- | Root URL of your Jira instance, e.g. `https://jira.mycompany.com` |
| `JIRA_USERNAME` | Yes | -- | Basic-auth username |
| `JIRA_PASSWORD` | Yes | -- | Basic-auth password |
| `JIRA_TIMEOUT_SECONDS` | No | `30` | Per-request timeout |
| `JIRA_MAX_RETRIES` | No | `3` | Retries for `429`/`5xx` responses |
| `JIRA_VERIFY_SSL` | No | `true` | Disable only for trusted self-signed internal instances |
| `JIRA_AUTO_CONFIRM_WRITES` | No | `false` | Skip the confirmation gate for `worklog`/`transition`/`create_issue`/`edit_issue` |
| `JIRA_CACHE_TTL_SECONDS` | No | `0` | Optional TTL cache for idempotent GET requests; `0` disables caching |
| `JIRA_DEFAULT_PROJECT` | No | -- | Project key (e.g. `PAYKAN`) used by `triage` when `--project` isn't given; if unset, the model must resolve/pass a project itself |

Configuration is validated eagerly: `lib.auth.load_config()` raises a
`ConfigurationError` with a specific, actionable message if required
variables are missing (e.g. `JIRA_PASSWORD` not set). Wire this into
your Hermes installation's startup/health check so misconfiguration
fails fast instead of at first tool call.

This skill only supports HTTP Basic auth (`JIRA_USERNAME` +
`JIRA_PASSWORD`), which works against both Jira Cloud and self-hosted
Jira Server/Data Center.

## Tools

| Tool | Read/Write | Description |
|---|---|---|
| `my_work(project, all_projects, order_by, max_results)` | Read | Unresolved issues assigned to the current user; scoped to `project`/`JIRA_DEFAULT_PROJECT` by default, `all_projects` forces instance-wide |
| `issue_summary(issue_key, sections)` | Read | Issue + comments + worklogs + changelog + links, as one document (or a subset via `sections`) |
| `blockers(issue_key)` | Read | `{"blocked": bool, "reasons": [...]}` from links/status/comments |
| `search(jql, fields, only)` | Read | Arbitrary JQL, structured issue results, projected to exactly the named fields in `only` (default: everything except `description`/time-tracking) |
| `search_users(query, project, all_projects, max_results)` | Read | Look up users by name/email fragment, to resolve an `account_id` for assignee filters/fields; `project` scopes to that project's assignable users (narrower, disambiguates common names), `all_projects` forces an unscoped search |
| `transition(issue_key, status, confirm)` | Write (gated) | Move an issue to a status; transition IDs resolved automatically |
| `worklog(issue_key, duration, description, date, confirm)` | Write (gated) | Log time against an issue, optionally backdated |
| `worklog_edit(issue_key, worklog_id, duration, description, date, confirm)` | Write (gated) | Update an existing worklog's duration/description/date |
| `worklog_delete(issue_key, worklog_id, confirm)` | Write (gated) | Permanently delete a worklog entry |
| `sprint(board_id, project)` | Read | Active sprint, board, dates, and goal; board resolved scoped to `project`/`JIRA_DEFAULT_PROJECT` by default -- reports a `note` instead of a sprint if the resolved board is kanban |
| `kanban_status(board_id, project)` | Read | A kanban board's columns and per-column issue counts, resolved the same way as `sprint` |
| `worklog_report(since, until, max_issues)` | Read | Aggregate your logged time over a date range vs. each issue's estimate |
| `list_fields()` | Read | Enumerate every field (incl. custom fields) to discover a custom field's id by name |
| `now()` | Read (local) | Current local wall-clock time, tz-aware, in the ISO format `worklog --date` accepts. The only tool that makes no Jira call -- it exists so relative dates ("now", "last Tuesday") get resolved against a checked clock instead of an assumed one |
| `triage(project, parent_issue_types, max_results)` | Read | Group unresolved parent issues (Story/Bug/Task) with their labeled subtasks, for frontend/backend/design-readiness triage |
| `create_issue(project, summary, issue_type, description, parent_key, labels, assignee_account_id, priority, components, confirm)` | Write (gated) | Create a new issue or subtask (pass `issue_type="Sub-task"` + `parent_key` for the latter) |
| `edit_issue(issue_key, summary, description, labels, assignee_account_id, priority, components, confirm)` | Write (gated) | Update one or more fields on an existing issue or subtask |
| `project_context(project)` | Read | Reference snapshot of a project: identity, `issue_types`, `statuses`/`statuses_by_issue_type`, `components`, instance `priorities`, assignable `users`, and a sample of `labels` in use -- meant to be fetched once and remembered by the caller rather than re-fetched every turn |

Each tool is reachable both as a Python function (`tools/<name>.py`) and
as a CLI subcommand (`scripts/jira_tool.py <name>`). See `skill.yaml` for
exact JSON Schemas and `SKILL.md` for the CLI invocation the agent uses.

## Running tests

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest
pytest -q
```

Tests mock the HTTP layer (`requests.Session`) so they run without a real
Jira instance, and cover: configuration validation, duration/ADF
parsing, blocking-rule logic, pagination, error-code mapping (401/403/
404/429/5xx), transition resolution, and every tool's success/validation/
confirmation-gate paths.

## Installing into Hermes

This is a manual, one-time setup step that a human operator performs in
their own local Hermes installation. Nothing in this repository -- no
script, no `SKILL.md` instruction, no tool -- edits Hermes configuration
on its own; the steps below are for you to carry out by hand.

Hermes discovers skills as `SKILL.md`-fronted directories, either under
`~/.hermes/skills/<skill-name>/` or under a directory of your own
choosing that you list in your local Hermes settings (see Hermes' own
docs for the exact setting name). Doing the latter and pointing it at
the `skills/` directory that contains `jira/` means you don't
need to copy this repo anywhere -- it's available immediately, with live
edits.

1. In your own Hermes settings file, list the absolute path to this
   repo's `skills/` directory under the setting that holds
   operator-defined skill locations, for example:

   ```yaml
   skills:
     external_dirs:
       - /path/to/your/local/checkout/of/skills/skills
   ```

2. Install dependencies (into whatever Python environment Hermes' sandbox
   uses to run `terminal`/`execute_code`):

   ```bash
   pip install -r /path/to/your/local/checkout/of/skills/skills/jira/requirements.txt
   ```

3. Set the environment variables from the table above wherever Hermes'
   sandbox inherits its environment (`SKILL.md`'s
   `required_environment_variables` will also prompt for them on first
   use if Hermes' onboarding flow supports it).

4. In a Hermes chat, run `/skills` to confirm `jira` is listed,
   or invoke it directly with `/jira`.

Alternatively, if your Hermes deployment can't use `external_dirs` (e.g.
a remote/managed instance), install by copying:
`cp -r skills/jira ~/.hermes/skills/jira`. Note this
creates a disconnected copy -- future changes to this repo won't apply
until you re-copy.

Hermes' skill mechanism (`SKILL.md` + on-demand instructions run via its
own `terminal` tool) is different from the generic function-calling
`skill.yaml` manifest also included here -- that file is kept for any
other agent runtime you might integrate with that expects structured
tool schemas instead of a markdown-instructed CLI.
