---
name: project-onboard
description: >-
  Onboards the user onto a project they no longer fully understand --
  typically one built mostly by AI ("vibe coded") -- in the least reading
  possible, so they can again make architecture, flow, and maintenance
  decisions. Investigates the code itself instead of trusting READMEs,
  then delivers a one-screen brief (what it is, how it works, the one
  flow that matters traced end to end, where the risk is, which decisions
  are theirs) and deepens one branch at a time on request. Read-only by
  default; saves an ONBOARDING.md only when asked. Use when the user says
  they lost track of their project, asks "how does this project work",
  "onboard me", "explain this codebase", "give me the big picture", or
  needs to regain control of a codebase fast. Not for fixing bugs or
  writing features, and not for documenting a project for other people
  (use agents-md or spec-baseline).
version: 1.0.0
metadata:
  category: software-development
  hermes:
    tags: [onboarding, codebase, architecture, understanding, vibe-coding, mental-models]
    category: software-development
    requires_toolsets: [terminal]
---

# Project onboard

**Instructions-only, no code.** Nothing to install, no environment
variables. The agent's own file-reading and shell tools do the
investigation.

Goal: **maximum regained control per minute of the user's attention.**
The user is busy and does not want to read. They need to end up able to
answer four things: *what does this do, how does a request flow
through it, what is fragile, and which decisions are mine.* Everything
else is optional and only on request.

Reply in the language the user writes in. Keep code identifiers, paths,
and commands as they are.

## Ground rules

- **Read-only.** Investigate, never modify. Running the project's own
  test or lint command is fine; starting servers, installing
  dependencies, or touching a database or network is not, unless the
  user says so. Writing a file is only ever the optional save in step 6.
- **Evidence over narrative.** The code is the truth; READMEs, comments,
  and prior chat claims in a vibe-coded repo are often stale or
  aspirational. Every claim in the brief is either *confirmed* (you read
  the code, cite `path:line`) or marked *inferred* (a guess from names or
  structure). Never present an inferred claim as confirmed, never invent
  a component, and say plainly when you couldn't tell.
- **Less is the product.** The brief is one screen. A long onboarding is
  a failed onboarding -- the user will not read it. Cut anything that
  doesn't change what they'd decide or do.
- **Say what you skipped.** One line naming what you did *not* look at,
  so the user knows the brief's blind spots.

## 1. Orient in minutes, not hours

Spend a bounded effort (a handful of cheap commands, not a full read):

1. **Shape** -- top-level layout, manifests (`package.json`,
   `pyproject.toml`, `go.mod`, ...), entry points, framework, how it's
   run and deployed (scripts, Dockerfile, CI config).
2. **Size and weight** -- which files and directories hold most of the
   code. Big, central files are where the logic lives.
3. **History as a map** -- `git log` shows what changed most
   (churn = where the real action and the instability are), what was
   added recently, and whether work stalled. Files changed most often
   are the project's real center, whatever the README says.
4. **Surfaces** -- where the outside touches it: routes/endpoints,
   CLI commands, scheduled jobs, message consumers, UI entry screens.
   Surfaces are the table of contents of behavior.
5. **State** -- where data lives: schema/migrations/models, files,
   caches, external services, env vars it needs.

On a large repo, fan the independent areas out to parallel read-only
sub-agents and take back only conclusions with citations, not file
dumps. Don't read whole files when a signature list or grep answers it.

If the project is a monorepo, orient on the layout, then ask which part
the user cares about before going deep.

## 2. Find the golden path

Pick **the one flow that is the project's reason to exist** (the main
user action, the main job, the main request) and trace it end to end:
surface → handler → core logic → storage / external call → response.
One real flow, followed through the real code, teaches the architecture
better than any component list, because it shows how the parts are
actually connected rather than how they're drawn.

If it isn't obvious which flow matters most, pick the most-churned
surface and say so, or ask one question.

## 3. Name the shape

Reduce the architecture to something the user can hold in their head:

- **One sentence**: what it is and who/what uses it.
- **A tiny map**: 4-8 boxes with arrows, drawn as plain text, labelled
  by *responsibility*, not by folder name. If you need more boxes, group
  them.
- **The one rule that holds it together**: the single organizing idea
  (layers, plugins, event bus, "everything goes through X") -- or, if
  there isn't one, say that. A project with no organizing idea is
  itself a finding.

## 4. Find where the bodies are buried

AI-built projects fail in recognizable ways. Check for them specifically
and report only what you actually found, ranked by how much it would
hurt:

- **Duplicated logic** -- the same rule implemented in two or three
  places that will drift apart.
- **No single source of truth** -- state, config, or a business rule
  living in several places.
- **Dead and half-finished code** -- unused modules, abandoned
  approaches left beside the one in use, stubs, `TODO`s that are
  actually load-bearing.
- **Hidden coupling** -- modules that reach into each other's
  internals; a change here that silently breaks there.
- **God files** -- one huge file doing everything, usually the most
  churned one.
- **Untested core** -- is the golden path covered at all? Do the tests
  pass? (Run the project's existing test command if there is one and it
  is safe to; otherwise say you didn't.)
- **Inconsistent patterns** -- three ways of doing the same thing
  (data access, error handling, naming) from different sessions.
- **Security and data hygiene** -- secrets in code, unvalidated input at
  a surface, missing auth on an endpoint, destructive operations with no
  guard. Flag; don't dig.
- **Unpinned or abandoned dependencies** that the core relies on.

Report **at most five**, each as: *what* (with `path:line`) → *why it
bites* → *how bad* (blocks you / will bite later / cosmetic). Silence on
a category is information: don't pad.

## 5. Surface the decisions that are the user's

The user lost control because decisions were made *for* them, silently.
Give those decisions back. List the **choices already baked in** that
they may not know they made, and the **forks coming up**:

- baked in: stack, data store, auth approach, hosting, a pattern the
  whole codebase now depends on -- stated as "this project chose X;
  alternative Y exists; changing it would cost roughly Z".
- open forks: places where the code currently takes a shortcut that
  will force a decision as the project grows.

For each, one line plus a recommendation when you have an evidence-based
one. These are the **decisions only the user can make**; keep them
separate from implementation detail they can safely delegate.

## 6. Deliver, then deepen

### The brief (default response)

One screen, in this order. Skip any part that has nothing to say.

1. **In one breath** -- what it is and does.
2. **Map** -- the tiny diagram from step 3 and its organizing rule.
3. **The main flow** -- the golden path as 4-7 arrows, each with a
   `path:line`.
4. **Watch out** -- the top risks from step 4, at most five.
5. **Your calls** -- the decisions from step 5.
6. **Not examined** -- the one line of blind spots.
7. **Next** -- offer 3 concrete branches to go deeper on (a named flow,
   a risky area, a decision), tailored to what you found, and ask which.

### Check understanding (optional, one question)

Reading is not the same as understanding. When the user will soon have
to make a change or decision, close with a single prediction question
about the code ("if you changed X, what else would break?"), and wait
for their answer before revealing yours. Skip it if they only wanted the
overview -- don't turn onboarding into homework.

### Deepen on request

Expand only the branch the user picks, to the same standard (evidence,
cited, short), building on what's already established instead of
restarting. Natural branches: one more flow, one component's internals,
a risk in detail, a decision with options and trade-offs, "what would it
take to add/change X", "what should I clean up first".

### Optional save

If the user wants to keep it, offer to write the brief to
`ONBOARDING.md` at the project root (or another path they choose),
**after** they approve its contents. Mark *inferred* claims there too, and
add the date and commit it describes so a reader knows how stale it is.
Never commit it unless asked.

## What this skill is not

- Not a bug-fixer or feature-builder: if the user then asks to change
  something, onboarding is done -- proceed as a normal task.
- Not documentation for a team: a brief tuned to one person's missing
  context is the wrong artifact. Point to `agents-md` for agent-facing
  docs or `spec-baseline` for a spec-grade baseline.
- Not a code review: hazards here are about *understanding and
  control*, not an exhaustive defect list. Point to `code-review` for
  that.
