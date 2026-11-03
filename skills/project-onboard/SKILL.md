---
name: project-onboard
description: >-
  Gets a user back in control of a project they no longer fully
  understand -- typically one built mostly by AI ("vibe coded") -- with
  the least reading possible. Investigates the code itself, then
  delivers a pocket brief of about 25 lines: what it is, a map with
  traffic-light danger zones, the story of one request told as it
  travels through the code, where the project's claims and its code
  disagree, and the decisions that are the user's. Continues in short
  cards chosen by typing one digit, so the user never has to write or
  read much. Read-only by default; saves an ONBOARDING.md only when
  asked. Use when the user says they lost track of their project, asks
  "how does this project work", "onboard me", "explain this codebase",
  "give me the big picture", "what did the AI build", or needs to regain
  control of a codebase fast. Not for fixing bugs or writing features,
  and not for documenting a project for other people (use agents-md or
  spec-baseline).
version: 1.1.0
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

The user is smart, busy, and done reading. What they lost is not
information -- it is **a correct picture in their head**, so they can't
judge architecture, trace a flow, or decide what to do next. Your job
is to rebuild that picture in the fewest seconds of attention, not to
document the project.

Reply in the language the user writes in. Keep identifiers, paths, and
commands as they are.

## The design rules (these drive everything below)

1. **Answer first, evidence second.** Every card opens with its
   conclusion. The user can stop reading after the first line of any
   card and still be right.
2. **Cards, not documents.** Each reply is one card that fits one
   screen. Never send two cards unless the user typed `all`.
3. **Pictures and symbols beat paragraphs.** Boxes and arrows, traffic
   lights, one-line bullets. A sentence longer than a line is a sign to
   cut. No tables of more than three columns, no walls of bold.
4. **The user steers with one digit.** Every card ends with a numbered
   menu of at most four choices, tailored to what you just found. The
   user replies `2` -- they never have to compose a question.
5. **Teach the gap, not the topic.** The user's existing picture is
   mostly right and wrong in a few places. Spend words only where their
   picture and the code differ; skip what they obviously know.
6. **Evidence tags, always.** Every claim is `✓` (you read the code;
   cite `path:line`) or `?` (inferred from names/structure). Never show
   a `?` as a `✓`, never invent a component, and say "couldn't tell"
   when you couldn't.
7. **Read-only.** Investigate, never modify. Running the project's own
   tests or linter is fine when it's safe; starting servers, installing
   dependencies, or touching a database or network is not unless the
   user says so. The only file this skill ever writes is the optional
   save at the end, and only with approval.

## Investigate (cheap, bounded, before saying anything)

Don't read the project; **interrogate it**. A handful of fast probes:

- **Shape** -- layout, manifests, entry points, how it's run/deployed.
- **Weight** -- which files hold most of the code.
- **Heat** -- `git log`: the most-changed files are where the real
  action and the real instability are, whatever the README says. Also
  read the commit story: the project's history in three acts ("started
  as X, pivoted to Y, last month bolted on Z") explains why it looks the
  way it does, in one sentence.
- **Surfaces** -- routes, CLI commands, jobs, consumers, UI entry points:
  the table of contents of what it actually does.
- **State** -- schemas/models, files, caches, external services, env
  vars it needs.
- **Own vocabulary** -- vibe-coded projects invent names (`Hub`,
  `Orchestrator`, `Pipeline`) that mean nothing outside the project.
  Collect the 4-8 terms that appear everywhere.
- **Claims** -- what README/docs/PRD/comments say it does.

On a large repo, fan independent areas out to parallel read-only
sub-agents and take back only cited conclusions, not file dumps. Prefer
signature lists and grep over reading whole files. For a monorepo,
orient on the layout and ask which part matters before going deep.

Then pick **the golden request**: the one flow that is the project's
reason to exist. If it isn't obvious, take the most-changed surface and
say so.

## The pocket brief (the first reply)

About 25 lines, in this order. Drop any part with nothing to say.

**1. One line.** What it is, for whom, in plain words.

**2. The map.** 4-8 boxes with arrows in plain text, labelled by
*responsibility*, not folder name, each box prefixed with a light:

- 🟢 safe -- small, tested or isolated, change freely
- 🟡 careful -- central or coupled; check before changing
- 🔴 danger -- fragile, untested, or load-bearing and confusing

Add one line: the single idea that holds it together ("everything goes
through X") -- or "no organizing idea" if that's the truth, which is
itself a finding.

**3. One request, told as a journey.** The golden request narrated as
the thing travelling through the code, 4-7 short arrows, each with a
`path:line`:

```
user clicks Pay → routes/checkout.ts:41 → calls priceCart() in lib/cart.ts:88
→ writes order to db.orders → fires email job queue/mail.ts:12 → returns 200
```

A real journey through real code teaches the architecture better than
any component list, because it shows how the parts are *actually*
wired rather than how they're drawn.

**4. Says vs does.** Up to three places where the project's claims
(README, docs, comments, names) and its code disagree -- "README says
tests run in CI; no CI config exists". These are the drift vibe coding
creates, and each one is a wrong belief the user is currently acting
on. Omit if none found.

**5. Your calls.** The decisions that are the user's and that were
made silently for them (stack, data store, auth, hosting, a pattern the
whole codebase now leans on), as `chose X · alternative Y · switching
costs ~Z`. Add the forks the code is about to force. Keep these apart
from implementation detail they can safely delegate.

**6. Blind spots.** One line: what you did not look at.

**7. Menu.** Up to four numbered next steps, generated from what you
found, such as:

```
1 💥 What breaks if I change <hottest thing>?
2 🧪 Test me -- 3 questions to check I really get it
3 🧹 Fix-first list (what to clean before building more)
4 🔎 Zoom into <the 🔴 box>
```

## The cards (one per menu choice)

Each is one screen, answer-first, same symbols and evidence tags.

- **💥 Blast radius.** For a thing the user names or the hottest file:
  *if you change this, these break, in this order.* Direct dependents
  first, then the surprising indirect ones. This is the fastest way to
  learn an architecture -- by what moves when you push on it -- and it's
  what actually prevents the next bad decision.
- **🧪 Test me.** Belief-diff, not a quiz. Ask the user to answer three
  tiny multiple-choice or one-word questions about the project
  ("where does the price get computed? 1 cart.ts 2 checkout.ts 3
  both"), **then stop and wait**. Reveal answers afterwards and teach
  only the misses -- the gaps are where their picture is wrong. Asking
  and answering in the same message defeats it. Only run it when the
  user asks for it or is about to make a change.
- **🧹 Fix-first list.** At most five hazards, ranked by how much each
  would hurt, each as `what (path:line) → why it bites → ⛔ blocks you
  / ⏳ will bite later / 💤 cosmetic`. Look specifically for what AI
  sessions leave behind: duplicated logic that will drift, state or a
  rule living in two places, dead or half-finished code beside the live
  version, modules reaching into each other's internals, one huge
  most-changed file, an untested core path, three styles for one job,
  secrets in code or an unguarded endpoint or destructive operation,
  and core dependencies that are unpinned or abandoned. Silence on a
  category is information -- don't pad.
- **🔎 Zoom.** One component, in the same shape as the pocket brief
  scaled down: one line, its inputs → outputs, its own journey, its
  traps. Building on what's already shown, never restarting.
- **🧰 Cheat sheet.** The operating card: how to run it, how to test it,
  where a new feature of the common kinds goes, the three things never
  to do (each with the reason), and the words from the project's own
  vocabulary.
- **🧭 Decision.** For one of "Your calls": the options, what each
  costs, a recommendation when evidence supports one, and what to
  check before committing.
- **all.** If the user types `all`, send every card in sequence. Not
  before.

If the runtime can render a visual page, offer the map and journey as a
single clickable diagram page; otherwise the text version is the
deliverable. Never make the user wait for a visual to get the answer.

## Optional save

If the user wants to keep it, offer to write the brief and any cards
they used to `ONBOARDING.md` at the project root (or a path they
choose), **after** they approve the contents. Keep the `✓`/`?` tags, and
add the date and commit it describes so a reader knows how stale it is.
Never commit it unless asked.

## What this skill is not

- Not a bug-fixer or feature-builder: once the user asks to change
  something, onboarding is done -- continue as a normal task.
- Not documentation for a team: a brief tuned to one person's missing
  context is the wrong artifact. Point to `agents-md` for agent-facing
  docs or `spec-baseline` for a spec-grade baseline.
- Not a code review: hazards here serve *understanding and control*,
  not an exhaustive defect list. Point to `code-review` for that.
