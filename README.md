# hermes-skills

A personal collection of AI-agent skills -- a portable developer/work
toolset, not a single-purpose repo. It currently holds a Jira toolset;
it's meant to grow with unrelated toolsets (e.g. a company back-office
toolset) as siblings, each following the same convention. Installed via
`skills.external_dirs` in `~/.hermes/config.yaml` pointed at this repo's
`skills/` directory (Hermes), or via `.claude/skills/` (Claude Code) --
see "Using these skills" below.

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
├── jira-worklog/          # Thin skill: log time (write, confirm-gated)
└── jira-transition/       # Thin skill: move an issue's status (write, confirm-gated)
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

See `skills/jira/README.md` for that toolset's architecture,
configuration, and test suite -- future toolsets should have their own
equivalent README under `skills/<toolset>/`.

## Using these skills

Every skill here is a standard `SKILL.md`-fronted directory: YAML
frontmatter (`name`, `description`, ...) plus a markdown body of
instructions, with all actual logic living in a plain Python CLI that
gets invoked via a shell/terminal tool. That shape is not
Hermes-specific -- it's portable to any agent runtime that supports
"skills" as folders of instructions + a tool-call surface. What differs
between runtimes is (a) how the skill gets discovered/installed and (b)
how environment variables reach the process that runs `jira_tool.py`.

### Hermes Agent

- **Discovery**: point `skills.external_dirs` in `~/.hermes/config.yaml`
  at this repo's `skills/` directory, or `hermes skills install
  <owner>/<repo>/<path-to-one-skill>` to fetch a single skill by path.
  There is no bulk/sub-package install -- one `SKILL.md` per install
  call, so `external_dirs` is the practical option for a growing
  personal collection like this one.
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
  See the "Conventions" note in `AGENTS.md`.

### Claude (Code or claude.ai)

- **Discovery (Claude Code)**: copy or symlink a skill directory into
  `.claude/skills/<name>/` (project-scoped) or `~/.claude/skills/<name>/`
  (personal, available in every project). Claude Code decides when to
  invoke a skill by matching its `description` against the task at hand
  -- there's no separate per-skill slash-command registration step.
- **Discovery (claude.ai web/app)**: zip the skill directory and upload
  it under Settings -> Capabilities -> Skills. Code there runs inside
  Anthropic's own sandboxed container.
- **Env vars**: Claude Code's shell tool inherits your actual shell
  environment, so a toolset's required env vars (e.g. `JIRA_BASE_URL` /
  `JIRA_USERNAME` / `JIRA_PASSWORD`) just need to be exported normally
  (`.zshrc`, a sourced `.env`, etc.) -- there's no separate allowlist to
  satisfy. claude.ai's hosted sandbox, by contrast, has no access to your
  local shell environment *or* your internal network, so any toolset
  that calls out to an internal host (an on-prem Jira, an internal
  back-office API, ...) won't be reachable from there regardless of env
  vars -- that path only really works for services reachable from the
  public internet.
- **Frontmatter compatibility**: Hermes-only keys (`metadata.hermes.*`,
  `required_environment_variables`) are just unknown YAML to Claude and
  are ignored -- no stripping or per-platform variant is needed. The same
  `SKILL.md` file works unmodified across both runtimes.

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
   but harmless elsewhere -- see "Using these skills" above).
4. Follow the repo-wide conventions in `AGENTS.md` regardless of
   toolset -- credentials only from env vars, no hardcoded local paths,
   write/mutating actions confirmation-gated in code (not just
   prompted).

No registration step is needed beyond adding the files -- Hermes
discovers new skills the next time it scans `external_dirs`, and Claude
discovers them the next time you copy/symlink into `.claude/skills/`
(or re-zip for claude.ai).
