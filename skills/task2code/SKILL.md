---
name: task2code
description: >-
  Turns a Jira ticket into a reviewed pull request: reads the project's
  own AGENTS.md and existing git history for its conventions, fetches
  the ticket, plans the change, scaffolds and implements it, writes
  tests, runs the project's local quality gate, then commits and opens
  a PR -- pausing for explicit user confirmation at every irreversible
  step (branch creation, plan approval, commit, PR). Use when the user
  asks to implement a ticket, start work on a Jira issue, or turn a
  ticket into code.
version: 1.0.0
metadata:
  category: software-development
  hermes:
    tags: [workflow, jira, git, code-generation, review]
    category: software-development
---

# task2code

All project-specific conventions, patterns, and code templates live in
the project's own `AGENTS.md` -- this workflow only owns the
**process**, never the implementation details, and never the
conventions either: where a step below states a default, treat it as a
fallback used only when the project hasn't already documented its own.

---

## Step 1 — Read project context

Before touching anything else:

1. Read `AGENTS.md` at the repo root. This is the source of truth for:
   - Project structure and module conventions
   - Layer responsibilities (what goes where)
   - Code patterns and templates
   - Naming conventions
   - Testing approach
   - Available scripts and generators
   - What agents must never do
2. Read `.agents/rules/` if present -- these are session-level rule
   overrides.
3. Look for a documented commit-message convention -- in `AGENTS.md`,
   `CONTRIBUTING.md`, a commit template, or similar. If none is
   documented, run `git log --oneline -20` and match whatever style the
   project already uses (Conventional Commits, a ticket-prefixed
   subject, free text) rather than assuming this skill's own default
   (Step 9) applies unchanged.
4. If a git convention (commit style, branch naming, base branch) isn't
   resolved by the above, ask the user explicitly rather than guessing.

If `AGENTS.md` is missing or incomplete, stop and tell the user before
proceeding.

---

## Step 2 — Fetch the Jira ticket

Ask the user: "What is the Jira ticket ID or URL?"

Fetch the ticket using this repo's own `jira` toolset (see
`../jira/SKILL.md`/`../jira/README.md` for setup and full details):

```bash
python3 ../jira/scripts/jira_tool.py issue_summary --issue_key TASK-XXX
```

(First-time setup, once per environment: `pip install -r
../jira/requirements.txt`.) This returns the issue plus comments,
worklogs, changelog, and linked-issue references in one document --
extract Summary/Module/Type/ACs from it. If a project instead documents
its own extractor under `AGENTS.md` → **Available tools**, use that
invocation instead.

Present the result as:

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ticket:   TASK-XXX
Summary:  <summary>
Module:   <inferred, or UNKNOWN>
Type:     feat | fix | refactor | chore | test
ACs:
  - [ ] <AC 1>
  - [ ] <AC 2>
Linked:   <list, or none>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If ACs could not be extracted automatically, infer them from the raw
description and print them for confirmation -- never proceed with
assumed ACs silently.

Recursively load any linked tickets, follow any URLs the ticket
contains, and read anything else documented to hold complete
information about it (a linked spec, design doc, or wiki page) --
not just the first level of links.

**STOP — ask the user:**

1. "Is the scope/module/component/section assignment correct? If
   UNKNOWN, which module does this belong to?"
2. "Are the inferred ACs complete, or should any be added/changed?"

Do not proceed until both are confirmed.

---

## Step 3 — Create a feature branch

Use the base branch documented in `AGENTS.md`. If not documented, ask
the user.

```bash
git checkout <base-branch> && git pull
git checkout -b <type>/TASK-XXX-<kebab-slug-from-summary>
```

Git branch names must respect the project's own convention. Look for a
documented branch-naming convention (in `AGENTS.md` or elsewhere); if
none is documented, check `git branch -a` / recent merged branches
before inventing one. Fall back to
`<type>/<ticket-id>-<kebab-summary-slug>` (`type` one of
`feat` | `fix` | `refactor` | `chore` | `test`) only if the project
shows no existing pattern either.

Print the branch name and ask the user to confirm before continuing.

---

## Step 4 — Plan

If the scope/module/component/section is still UNKNOWN, ask the user to
specify it before continuing. If the task requires a new module, ask
the user to confirm before creating anything. If the task scope is
unclear after reading the ticket and `AGENTS.md`, ask -- do not guess.

Study the relevant part of the codebase before writing the plan:

1. Re-read the relevant section of `AGENTS.md` for the identified
   module/layer.
2. List and read the existing files in the affected module or layer.
3. Read existing service/handler/controller files to understand current
   method signatures and patterns.
4. Read existing repository/data-access files to understand what
   queries already exist.
5. Check existing route/router files for prefix, middleware, and
   versioning conventions.
6. Identify which files need to be **created** vs **modified**.
7. Identify which generators or scaffold commands are available (per
   `AGENTS.md` → Commands section).

Then produce a numbered implementation plan. Be specific -- name every
file and every method:

```text
Implementation plan for TASK-XXX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Scaffold commands (if applicable):
  1. [ ] <generator command for file A>
  2. [ ] <generator command for file B>

Files to create:
  3. [ ] <path/to/file.ext>
         <ClassName or functions: list each public method/handler with its signature>
  4. [ ] <path/to/file.ext>
         ...

Files to modify:
  5. [ ] <path/to/file.ext> — <what changes: add route / add method / update field list>
  6. [ ] <path/to/file.ext> — ...

Tests to write:
  7. [ ] <path/to/test_file.ext>
         <test_method_name>() — covers AC 1
         <test_method_name>() — covers AC 2
         <test_method_name>() — covers validation/error path

Additional impact:
  8. [ ] <any config, migration, env var, queue registration, schema change — or "none">
```

**STOP — ask the user to approve the plan.**
Do not generate any files until the plan is approved. If changes are
requested, update the plan and re-print it before proceeding.

---

## Step 5 — Scaffold

Run any scaffold or generator commands from the approved plan. Follow
the exact commands documented in `AGENTS.md` → Commands section.

After each command: print the path of the created file. Do not edit
generated files yet -- run all generators first, then implement.

---

## Step 6 — Implement

Work through the approved plan checklist item by item.

For each file, refer to `AGENTS.md` for:

- The correct base class or interface to extend/implement
- The layer's responsibilities and what it must not do
- The required code patterns and templates
- The response/return type conventions
- Error and exception handling conventions

Implement in dependency order -- lower layers before higher layers:
**data model → repository/data-access → service/business logic →
handler/controller → route**

After completing each file, check it against the relevant rules in
`AGENTS.md` before moving on.

---

## Step 7 — Tests

Write tests as specified in the approved plan.

For each test file, refer to `AGENTS.md` for:

- The testing framework and runner
- Available fixtures, factories, and mocks
- The required assertions (HTTP status, response shape, DB/data state)
- Whether to use real or mocked dependencies
- Test naming conventions

Cover at minimum:

- One test per AC (happy path)
- One test per meaningful error/exception path
- One test per non-obvious validation rule
- One test per business-logic scenario or error case

Run the tests locally and confirm they pass before proceeding to
Step 8. If tests fail, fix the implementation -- do not skip or comment
out failing tests, unless the user explicitly requests it.

---

## Step 8 — Local quality gate

Run the quality checks documented in `AGENTS.md` → Testing / Environment
setup sections. The exact commands differ per project -- use what is
documented there.

Typical sequence (adapt per project):

1. Run the test suite (scoped to the affected module if possible)
2. Run the linter / code style fixer
3. Re-run tests to confirm linting did not break anything
4. Run the type checker if the project uses one

All checks must pass. Do not suppress warnings without a comment
explaining why.

---

## Step 9 — Commit

Stage only the files from the approved plan. Verify with a status check
before committing.

Use whatever commit-message convention Step 1 found already in use
(Conventional Commits, a project template, etc.). Only if the project
has none, default to (using the type from Step 3):

```text
<type>(<module-or-scope>): <short description from ticket summary>

Implements TASK-XXX
ACs covered:
- <AC 1>
- <AC 2>
```

---

## Step 10 — Open PR and update the ticket (if you have the means to)

If you have a way to interact with the remote git host (a GitHub/GitLab
CLI, an installed integration, or an equivalent tool available to you),
open a Pull/Merge Request:

- **Title**: `<type>(<module>): <ticket summary> [TASK-XXX]`
- **Base branch**: the base branch from Step 3
- **Body**: follow the project's own PR description template if one
  exists (e.g. a `PULL_REQUEST_TEMPLATE` file, or a dedicated
  PR-description skill/workflow the project documents); otherwise use
  this structure: summary → ticket link → ACs covered → how to test
  locally → checklist.

If you also have a way to interact with Jira:

- Transition the ticket to **"In Review"**
- Post a comment with the PR URL

Print both the PR URL and the Jira ticket URL. If you have no way to do
either of these, say so and tell the user what to do manually instead
of skipping the step silently.

---

## Done

```text
Branch:  <branch>
PR:      <PR URL or "opened manually">
Jira:    <moved to "In Review" or "update manually">
```

Remind the user:

- Review the diff before merging -- the service/business logic layer
  deserves the most attention.
- If a schema migration, index creation, or environment variable was
  added, confirm deployment steps.
