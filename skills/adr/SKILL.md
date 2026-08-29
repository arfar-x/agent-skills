---
name: adr
description: >-
  Turns a design decision (with its context, options, and consequences)
  into a complete Architecture Decision Record (ADR) and saves it under
  docs/ADRs/ -- never makes the decision itself, only records one already
  made or being made. Use when the user asks to write/draft an ADR,
  record a design/architecture decision, or document why one option was
  chosen over another for future readers.
version: 1.0.1
metadata:
  category: software-development
  doc_type: adr
  hermes:
    tags: [architecture, documentation, decision-record, adr, engineering]
    category: software-development
---

# ADR

**Instructions-only, no code.** Nothing to install, no environment
variables -- this skill turns a decision into an ADR document and saves
it to disk, nothing else.

## What this is

You are acting as a staff engineer recording a design/architecture
decision for future readers who weren't in the room -- why the system is
the way it is, what else was considered, and what it costs. An ADR
records a decision; it doesn't make one. If the user hasn't actually
decided yet, help them think it through in conversation first, then
write the ADR once there's a real decision to record.

**Never implement the decision -- only document it.** No code changes,
migrations, or config changes, even to "make the ADR concrete." The
deliverable is the ADR file.

## Input

The brief typically supplies: **Title**, **Status** (defaults to
`Proposed` if not stated), **Context** (the problem/state that motivates
this), **Decision** (what was decided, and the concrete reasons), and
**Consequences** (positive and negative). It may also supply: concurrent
systems/processes the decision must coexist with, work deliberately
descoped, real alternatives that were considered and rejected, a
ticket/epic id, and authors.

If the input is free-form, work with what you have. **`Decision` and
`Consequences` are what make an ADR meaningful -- if either is missing or
too vague to write down concretely, ask the user for it specifically
before drafting that section.** Don't fabricate a decision or invent
consequences to fill space; an ADR that guesses at its own subject is
worse than no ADR. Every other section below is fair to infer, mark
optional and omit, or draft from context.

## Where to save it

Same convention-check as [`prd`](../prd)/[`trd`](../trd), adapted for
ADRs' own numbering -- ADRs are sequential decisions, not per-day
documents, and (unlike `prd`/`trd`'s folder-per-doc) are conventionally a
single flat file:

1. An explicit user instruction wins.
2. If `docs/ADRs/` already exists, match its existing numbering/filename
   convention instead of the default below (e.g. it may already use
   3-digit numbers, a different directory name, or a folder-per-ADR
   shape -- consistency with what's on disk beats this default).
3. Otherwise:

   ```
   docs/ADRs/NNNN-short-descriptive-title.md
   ```

   `NNNN` is a 4-digit, zero-padded, strictly sequential id -- list
   existing files under `docs/ADRs/`, take the highest `NNNN`, and
   increment it (start at `0001` if none exist yet). Unlike `prd`/`trd`,
   this sequence is never reset by date. Don't renumber or rename
   existing ADRs.

## Output structure

Sections marked **(optional)** should only appear when the decision
actually needs them and the user has given (or the context supplies)
real information for them -- omit rather than pad. Everything else is
part of what makes an ADR an ADR; for `Decision` and `Consequences`
specifically, ask rather than omit or invent (see "Input" above).

### Status

One of `Proposed` / `Accepted` / `Rejected` / `Deprecated` / `Superseded
by ADR NNNN` (link the other ADR's file when superseding).

### Context

What in the system motivates this decision -- the problem, limitation,
or gap. Include any prior/adjacent work that was in scope and
deliberately withdrawn or descoped, and why, so a future reader doesn't
wonder if it was simply missed.

### Decision

One-sentence statement of the decision, then a numbered list of its
distinct decision points -- one point per genuinely separate decision,
not per implementation detail. Each point: what was decided and the
concrete reason, preferring a specific mechanism or example over a
general principle. Use nested bullets under a point for its sub-parts
(e.g. several measures that together produce one guarantee).

### Concurrency and interaction with `<adjacent system/component>` (optional)

Only when this decision runs alongside other concurrent processes
touching shared state, resources, or infrastructure. Enumerate isolation
guarantees explicitly (e.g. no shared resource, no shared mutable state,
no new startup/import-time work, which side owns which read/write path,
what specific condition triggers this path) as bullets, followed by a
"Known and accepted" list of any limitation this introduces, stated
plainly with the condition under which it manifests.

A nested **`### Required <index/migration/config/ops action>`**
subsection belongs here specifically -- any deploy-blocking or
environment-specific action needed before this is safe to run, called
out separately from Consequences so it isn't missed.

### Deferred to `<other system/future work>` (optional)

Capability deliberately **not** built here and not to be re-added to
this component -- one bullet per capability, stating exactly what's
excluded. Note the migration path when the deferred work lands, if
known (e.g. "becomes a one-function change") -- it shows the current
design already anticipated it.

### Alternatives considered (optional)

Real alternatives only -- option, why it was rejected. Skip this section
rather than padding it with options nobody seriously considered. Worth
including whenever there was a genuine fork in the road: a future reader
questioning "why not X" is exactly who this section is for.

### Consequences

**Positive** and **Negative** subsections, each a bullet list. Under
Negative, be explicit about any metric, guarantee, or safety property
that only holds approximately, and under what condition it breaks down
-- a consequence stated too optimistically is worse than one left out.

### Note (optional, but recommended when known)

- **Authors**: who wrote this ADR
- **Developers**: who implements the decision, if different
- **Date**: when this was written
- **Ticket**: ticket id (and parent/epic ticket, if any)

## Style

- State the decision and its reasons plainly -- no hedging language for
  a decision that's actually been made.
- Keep Context (the situation), Decision (the choice), and Consequences
  (the cost) in their own sections -- never blend them.
- Every claim in Consequences should be something a reader could verify
  later, not an adjective.

## Relationship with other documents

`PRD -> TRD -> RFC/ADR/ERD/API spec -> Implementation`. An ADR usually
exists because a [`trd`](../trd)'s "Risks & trade-offs" section flagged a
decision as deserving a permanent record, or because an [`rfc`](../rfc)'s
review settled a specific decision worth recording on its own -- link
back to that TRD/RFC from Context if one exists. When a later ADR
reverses an earlier one, set the earlier ADR's Status to `Superseded by
ADR NNNN` rather than deleting or rewriting it -- the record of what was
once decided, and why it changed, is the point of keeping ADRs at all.
