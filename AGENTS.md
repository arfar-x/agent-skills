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
  stripped at runtime, not just undocumented.
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

Toolset-specific conventions (e.g. "Jira auth is Basic-only, don't
reintroduce PAT without being asked") belong in that toolset's own
`skills/<toolset>/README.md`, not here.
