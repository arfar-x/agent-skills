---
name: rfc
description: >-
  Turns a proposed technical/architecture change (with its problem
  statement, goals, proposed design, alternatives, risks, and rollout
  plan) into a complete Request for Comments (RFC) and saves it under
  docs/RFCs/ -- never implements the proposal itself, only documents it
  and opens it for review. Use when the user asks to write/draft an RFC,
  propose a system or architecture change, or open a design proposal for
  team review and discussion before work starts.
version: 1.0.0
metadata:
  category: software-development
  doc_type: rfc
  hermes:
    tags: [rfc, architecture, documentation, design-proposal, engineering, review]
    category: software-development
---

# RFC

**Instructions-only, no code.** Nothing to install, no environment
variables -- this skill turns a proposed change into an RFC document and
saves it to disk, nothing else.

## What this is

You are acting as a staff/principal engineer opening a technical
proposal for team review -- what's wrong today, what you propose
instead, what it costs, and what's still undecided. An RFC proposes and
solicits feedback; it doesn't itself ratify a decision the way an
[`adr`](../adr) does. If the user hasn't actually worked out a concrete
proposal yet, help them think it through in conversation first, then
write the RFC once there's a real design to put in front of reviewers.

**Never implement the proposal -- only document it.** No code changes,
migrations, or config changes, even to "make the RFC concrete." The
deliverable is the RFC file.

## Input

The brief typically supplies: **Title**, **Author(s)**, the **current
state and its concrete pain** (Context and problem statement), the
**proposed design** (Proposed architecture), and enough sense of
**Goals** to know what success looks like. It may also supply: an
explicit list of non-goals, functional/non-functional requirements,
known open questions, alternatives already considered and rejected, a
migration/rollout plan, known risks, operational concerns, reviewers,
and related documents/tickets.

If the input is free-form, work with what you have. **The problem
statement, the proposed design, and an honest risk accounting are what
make an RFC worth reviewing -- if any of them is missing or too vague to
write down concretely, ask the user for it specifically before drafting
that section.** A vague pain point ("it's hard to maintain") is not a
problem statement; push for the concrete version ("every new X requires
changes in three places in Y"). Don't invent numbers for
performance/scale targets you weren't given -- mark them `TBD:` instead
(see "4. Requirements" below). Every other section is fair to infer,
mark optional, and omit.

## Where to save it

Same convention-check as [`adr`](../adr) -- RFCs are sequential
proposals, not per-day documents, and are conventionally a single flat
file:

1. An explicit user instruction wins.
2. If `docs/RFCs/` already exists, match its existing numbering/filename
   convention instead of the default below (e.g. it may already use
   3-digit numbers, a different directory name, or a folder-per-RFC
   shape -- consistency with what's on disk beats this default).
3. Otherwise:

   ```
   docs/RFCs/NNNN-short-descriptive-title.md
   ```

   `NNNN` is a 4-digit, zero-padded, strictly sequential id -- list
   existing files under `docs/RFCs/`, take the highest `NNNN`, and
   increment it (start at `0001` if none exist yet). This sequence is
   never reset by date. Don't renumber or rename existing RFCs.

## Output structure

Start with a header block, then the numbered sections below. Sections
marked **(optional)** should only appear when the proposal actually
needs them and the user has given (or the context supplies) real
information for them -- omit rather than pad. For "2. Context and
problem statement", "5. Proposed architecture", and "9. Risks and
mitigations" specifically, ask rather than omit or invent (see "Input"
above).

### Header

```
RFC NNNN: <Title>

Status: Draft
Author(s): ...
Created: YYYY-MM-DD
Last updated: YYYY-MM-DD
Reviewers: ... (optional, but recommended once review starts)
Related: ... (optional -- linked PRD/TRD/ADR/tickets)
```

`Status` is one of `Draft` / `In Review` / `Accepted` / `Rejected` /
`Withdrawn` / `Superseded by RFC NNNN` (link the other RFC's file when
superseding) -- defaults to `Draft` for a new RFC. `Created`/`Last
updated` default to today; update `Last updated` whenever the document
is meaningfully revised.

### 1. Summary

Two to four sentences. A reader should be able to stop here and know
what's being proposed and why. Write this last, once every other section
is settled, so it can't drift from what the rest of the doc actually
says.

### 2. Context and problem statement

What exists today, and what's concretely wrong with it. Include a
diagram of the current state whenever the system has enough moving parts
that prose alone would leave a reader guessing. Be concrete about the
pain -- "it is hard to maintain" is not a problem statement; "every new
notification channel requires changes in three places" is.

### 3. Goals and non-goals

**Goals** -- what success looks like, as a list of outcomes rather than
tasks.

**Non-goals (optional)** -- explicitly out of scope. This is what keeps
review from sprawling into adjacent problems this proposal isn't
solving, and protects the design from scope creep later.

### 4. Requirements

**Functional** -- what the system must do.

**Non-functional** -- performance, availability, and scale targets. If a
number hasn't actually been agreed, write `> **TBD:**` rather than
guessing one.

### 5. Proposed architecture

The core of the RFC. A diagram of the target state, followed by
component responsibilities, contracts, and data models. Mark anything
not yet ratified by the team as a proposal, not a settled fact.

### 6. Open questions (optional)

Numbered, so each can be discussed and closed independently. For each:
the question, the options, the trade-offs, and who needs to decide.
Resist the urge to answer them in this section -- that's what review is
for.

### 7. Alternatives considered (optional)

Each alternative with an honest account of why it wasn't chosen. "Do
nothing" is always a valid alternative and is usually worth including.
Skip this section rather than padding it with options nobody seriously
considered.

### 8. Migration plan (optional)

Only when rolling the change out actually requires phased work. Phased,
with an explicit rollback and a "done when" criterion per phase.

### 9. Risks and mitigations

A table: Risk / Impact / Likelihood / Mitigation. An RFC that skips this
is asking reviewers to sign off blind -- if the user hasn't named real
risks, ask rather than leaving this empty or inventing generic ones.

### 10. Operational concerns (optional)

Observability, alerting, scaling, on-call impact, cost -- only the ones
that actually change as a result of this proposal.

### 11. Work breakdown (optional)

Grouped by phase (matching the migration plan's phases, if there is
one). Each item independently assignable and small enough to become a
single ticket. Usually only worth filling in once the design is stable
enough that breaking it into tickets is real work, not guesswork.

### 12. Appendix (optional)

Glossary, references, prior art.

## Style

- State the problem and the proposal plainly -- vague adjectives
  ("robust", "scalable") don't survive review; a concrete mechanism or
  number does.
- Keep Context (what's wrong today), Proposed architecture (what
  changes), and Risks (what it costs) in their own sections -- never
  blend them.
- Mark anything unresolved as `TBD` or as an Open Question instead of
  quietly picking an answer on the user's behalf.

## Relationship with other documents

`PRD -> TRD -> RFC/ADR/ERD/API spec -> Implementation`. Reach for an RFC
instead of (or before) a narrower [`adr`](../adr) when the proposed
change is broad enough to need explicit reviewer sign-off and
cross-team comment before work starts -- the `Reviewers` field, "Open
questions" section, and phased "Migration plan" all exist because an RFC
is meant to be actively discussed, not just recorded. Individual
decisions that come out of an RFC's review are often worth their own ADR
once settled -- link back to this RFC from that ADR's Context. When a
later RFC reverses an earlier one, set the earlier RFC's Status to
`Superseded by RFC NNNN` rather than deleting or rewriting it.
