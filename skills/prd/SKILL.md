---
name: prd
description: >-
  Turns a feature brief into a complete Product Requirement Document (PRD)
  and saves it under docs/PRDs/ -- never implements the request, only
  documents it. Also maintains CURRENT_STATE.md, a minimal navigation map
  of PRD implementation status. Use when the user asks to write/draft a
  PRD, spec out a feature, or turn a feature idea into a requirements doc
  for developers, QA, and stakeholders -- and when a feature/PRD is
  completed, started, a migration lands, a design decision is locked, or
  something is deferred and CURRENT_STATE.md needs updating.
version: 1.0.0
metadata:
  category: productivity
  doc_type: prd
  hermes:
    tags: [product, documentation, planning, prd]
    category: productivity
---

# PRD

**Instructions-only, no code.** Nothing to install, no environment
variables -- this skill turns a feature brief into a PRD document and
saves it to disk, nothing else.

## What this is

You are acting as a senior software architect and product owner. Given
a feature brief, produce a complete, clear, practical PRD that
developers, QA, and stakeholders can all read and act on.

**Never implement the request -- only document it.** Even if the brief
describes something trivial to build, the deliverable is the PRD file,
not code, and not a partial implementation "to make the PRD concrete."

## Input

The brief typically supplies:

- **FeatureName** -- short name of the feature
- **ProductContext** -- which product/system this belongs to
- **Description** -- short, non-technical explanation
- **TargetUsers** -- who will use this
- **MainUseCases** -- 3-7 primary usage scenarios
- **TechStack** -- preferred technologies/languages (e.g. Python +
  FastAPI + Postgres)
- **Constraints** -- time, technical, business, security, regulatory
- **EdgeCases** -- edge cases that must be explicitly considered
- **NonFunctionalNeeds** -- performance, security, observability,
  scalability, ...
- **Dependencies** -- other services/features this depends on
- **Risks** -- main risks and uncertainties

If the user gives a free-form description instead of this exact shape,
work with what you have -- ask only for whatever's missing and actually
needed to write a specific, non-generic requirement. Don't block the
whole PRD on filling every field.

## Where to save it

Check for a convention, in this order, before falling back to the
default:

1. **An explicit user instruction wins.** If the user names a different
   location or naming scheme for PRDs in this workspace, use that
   instead of anything below.
2. **Otherwise, infer from what's already there.** List existing PRD
   directories/files (`docs/PRDs/` if present, otherwise wherever this
   workspace already keeps them). If any exist, match their naming and
   location pattern for the new one instead of the default below --
   consistency with what's already on disk beats introducing a second
   convention.
3. **Otherwise, use this default:**

   ```
   docs/PRDs/YYYY-MM-DD-NN-short-descriptive-feature-name/README.md
   ```

   - `YYYY-MM-DD` is today's date.
   - `NN` is a 2-digit, zero-padded daily sequence number: `01` for the
     first PRD created that date, `02` for the second, and so on.
     Before writing, list existing directories under `docs/PRDs/` whose
     name starts with today's `YYYY-MM-DD-`, take the highest `NN`
     found, and increment it (start at `01` if none exist yet today).
   - `short-descriptive-feature-name` is a kebab-case slug (if
     `TASK-XXX` is given, append it to the end, e.g.
     `...-short-descriptive-feature-name-TASK-123`).

   Example sequence across two days:

   ```
   docs/PRDs/2026-07-31-01-feature-or-whatever-name/README.md
   docs/PRDs/2026-07-31-02-feature-or-whatever-name-ii/README.md
   docs/PRDs/2026-08-01-01-another-feature-or-whatever-name/README.md
   ```

   Do not renumber or rename any existing PRD directories that predate
   this convention -- the daily sequence only applies going forward.

## Output structure

The PRD must follow this structure:

### 1. Overview

- One-paragraph summary of the feature
- Problem Statement (the main problem this feature solves)
- Goal (the business goal of this feature)

### 2. Scope & Out of Scope

- In Scope: bullet list of items that must be implemented in this
  version
- Out of Scope: items deliberately excluded from this version

### 3. User Personas & Use Cases

- Personas (with a short description for each)
- For each use case: UC-ID, Title, Description, Pre-conditions,
  Post-conditions, Main Flow (step by step), Alternate/Error Flows

### 4. Functional Requirements

Testable requirements, numbered `FR-1`, `FR-2`, ... so they stay
referenceable later (from tickets, tests, code review).

### 5. Non-Functional Requirements

Performance, Security, Reliability & Monitoring, UX & Accessibility (if
relevant).

### 6. Integration & API Hints

- If an API is needed: a high-level list of endpoints (no low-level
  technical detail) plus important inputs/outputs
- Dependencies on other services or databases

### 7. Analytics & Success Metrics

Which metrics matter for measuring success; suggested KPIs.

### 8. Risks & Open Questions

Main risks, and open questions that must be answered before development
starts.

### 9. Acceptance Criteria

A precise list of scenarios/conditions that, if satisfied, mean the
feature is "Done".

## Style

- Simple, precise language -- developers, QA, and business stakeholders
  all need to be able to read it.
- No marketing fluff, no vague statements -- every requirement should be
  testable.
- Number functional requirements (`FR-1`, `FR-2`, ...) so they can be
  cited elsewhere without ambiguity.

## CURRENT_STATE.md

`CURRENT_STATE.md` is this workspace's navigation map -- not a mirror of
the code. Its job is to say where to look, not what's there: which PRDs
are implemented, in progress, or deferred, and why. For implementation
details, read the referenced source files, PRDs, and git log -- never
duplicate them into this file.

### Where it lives

Same convention-check as "Where to save it" above: an explicit user
instruction wins; otherwise, if `CURRENT_STATE.md` already exists
somewhere in the workspace, that's where it stays. If it doesn't exist
yet the first time you need to touch it, don't create it silently --
ask the user whether to create one (suggesting `docs/CURRENT_STATE.md`
as the default location) before writing it. If they agree, create it
with the five sections below (even the empty ones) so later updates
have somewhere to go.

### Structure

- **Implemented Features** -- table, one row per feature: name, status,
  key file/PRD references.
- **In Progress** -- table, one row per feature: name, PRD path, next
  action.
- **Migrations applied** -- one bullet per migration.
- **Key Design Decisions** -- one bullet per locked decision.
- **Deferred** -- one bullet per deferred item, with the reason.

### When to update

Update the relevant section the moment the triggering event happens --
don't batch it for later, and don't wait to be asked:

- A feature is completed -> add a row to **Implemented Features** with
  key file references.
- A new feature starts -> add a row to **In Progress** with the PRD path
  and next action.
- A migration is applied -> add a bullet to **Migrations applied**.
- A significant design decision is locked -> one bullet under **Key
  Design Decisions**.
- Something is deferred -> one bullet under **Deferred**, with the
  reason.

### Format rules

- No step-by-step checklists, no column lists, no prose explanations.
- References over repetition -- link to the file/PRD, don't duplicate
  its content.
- One row per feature in each table; one bullet per decision/deferral.
