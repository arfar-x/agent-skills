---
name: product-spec
description: >-
  Turns a feature idea or brief into a product-level specification in
  GitHub Spec Kit's spec.md shape -- current and intended behavior,
  prioritized user stories with Given/When/Then acceptance scenarios,
  FR-/SC- requirement ids, edge cases, scope, dependencies -- written for
  non-technical readers and ready for developers to take straight into
  Spec Kit's plan step. Never implements anything and never describes
  how to build it. Use when someone asks to spec out a feature, write a
  product spec or requirements, or prepare a feature for development.
version: 1.0.0
metadata:
  category: productivity
  doc_type: product-spec
  hermes:
    tags: [product, specification, spec-driven-development, spec-kit, requirements]
    category: productivity
---

# Product spec

**Instructions-only, no code.** Nothing to install, no environment
variables. This skill produces one Markdown document: a product
specification.

## What this is

A product spec says **what** a feature must do and **why**, never how to
build it. It is written by or for product people and read by everyone:
product, design, QA and engineering.

Its shape is deliberately the same as the `spec.md` that
[GitHub Spec Kit](https://github.com/github/spec-kit) produces. The
headings, their order, the story format and the requirement ids all
match, so a developer can save an approved product spec as
`specs/NNN-<feature>/spec.md` and go straight to Spec Kit's plan step,
with nothing to translate and nothing to re-clarify. A few
product-specific sections are added (below). Spec Kit's commands read
past them without complaint.

**Never implement the request, and never design it.** No languages,
frameworks, APIs, database tables, endpoints, class names or
architecture. If the brief contains implementation ideas, keep only the
need behind them. If a constraint really is technical (for example "must
work offline"), state it as an observable behavior.

## Input

Anything from one sentence to a full brief. Work with what you have.
Before writing, find out what already exists:

- **Current behavior.** How does the product behave today in the area
  this feature touches? Use whatever documentation sources you have
  (a knowledge catalog, wiki pages, existing specs, tickets) and name
  the documents you used. Specs and docs are the source of truth for
  current behavior. If they don't cover something, say so in the spec
  instead of guessing.
- **Related work.** Existing specs or tickets this overlaps or conflicts
  with.

Don't block on gaps. Make an informed guess where a reasonable default
exists and record it under Assumptions. Where no reasonable default
exists and the answer changes scope or user experience, write a
`[NEEDS CLARIFICATION: <the specific question>]` marker in place. Use
at most **3** markers in a first draft; a clarification pass (for
example the `spec-clarify` skill) resolves them.

## Writing rules

- Plain language for a non-technical reader. Use the product's own
  terms consistently; don't switch between synonyms.
- **User stories** are prioritized journeys, `P1` first. Each one must be
  independently valuable and testable: if only that story ships, it
  still delivers something.
- **Acceptance scenarios** use the form
  `**Given** <state>, **When** <action>, **Then** <observable outcome>`.
  One behavior per scenario. Outcomes must be observable by a user or a
  tester, never internal state.
- **Functional requirements** are numbered `FR-001`, `FR-002`, ... and use
  `MUST`/`SHOULD`/`MAY`. Each must be testable and unambiguous.
- **Success criteria** are numbered `SC-001`, ... They are measurable and
  technology-agnostic, with a number, a threshold or a clear yes/no.
- Ids are stable. When revising a spec, never renumber existing ids; add
  new ones after the highest, and mark a removed one as
  `~~FR-004~~ (removed: <reason>)` instead of reusing it.
- **Questions for engineering** are questions only engineering can
  answer, such as feasibility, what the system does today when the docs
  are silent, or hard constraints. They are not design questions. Name
  who should answer each one: a person if you know them, otherwise a role
  (for example "Backend team lead").

## Template

Fill every mandatory section. Remove an optional section rather than
leaving it empty. Keep the headings exactly as written; the
`*(mandatory)*` markers are part of Spec Kit's shape.

```markdown
# Feature Specification: <Feature name>

**Feature Branch**: `[###-feature-name]`

**Created**: <YYYY-MM-DD>

**Status**: Draft

**Input**: User description: "<the original request, one or two sentences>"

## Current Behavior

<How the product behaves today in this area, in a few sentences or
bullets. Cite the documents this comes from. If there is no current
behavior (a new capability), say so.>

## Intended Behavior

<What changes, in a few sentences: the behavior after this feature, and
the user or business value. No implementation.>

## User Scenarios & Testing *(mandatory)*

### User Story 1 - <Brief title> (Priority: P1)

<The user journey in plain language.>

**Why this priority**: <The value, and why it ranks here.>

**Independent Test**: <How this story alone can be tested and what it
delivers, e.g. "Can be fully tested by ... and delivers ...">

**Acceptance Scenarios**:

1. **Given** <state>, **When** <action>, **Then** <outcome>
2. **Given** <state>, **When** <action>, **Then** <outcome>

---

### User Story 2 - <Brief title> (Priority: P2)

...

### Edge Cases

- What happens when <boundary condition>?
- How does the product handle <error scenario>?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: <Actor> MUST <capability>
- **FR-002**: ...

### Key Entities *(include if feature involves data)*

- **<Entity>**: <What it represents and its key attributes, in business terms>

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: <Measurable, technology-agnostic outcome>

## Assumptions

- <A reasonable default chosen where the request was silent>

## Out of Scope

- <What this feature deliberately does not do>

## Dependencies

- <Other teams, products, specs or decisions this needs, linked where possible>

## Questions for Engineering

- <Question> -- *for: <person or role>*
```

`## Out of Scope`, `## Dependencies` and `## Questions for Engineering`
are the product additions after Spec Kit's sections. `## Current
Behavior` and `## Intended Behavior` are the product additions before
them. If a clarification pass has run, its `## Clarifications` section
(Spec Kit's own convention) sits right after `## Intended Behavior`.

## When is it ready?

A spec is ready for development when nothing is left for a developer to
ask. In particular:

- no `[NEEDS CLARIFICATION]` markers;
- `## Questions for Engineering` is empty or removed;
- every story has acceptance scenarios.

The `spec-readiness` skill checks this formally. Set `**Status**` to
`Approved` only after a person has approved the content. Readiness alone
is not approval.

## Delivery

The output is the Markdown document itself. Where it goes is the
caller's choice:

- **In a repository using Spec Kit**: `specs/NNN-<feature-slug>/spec.md`,
  where `NNN` is the next free number. Spec Kit's commands then work on it
  directly.
- **In a chat or agent setting**: return the document. The surrounding
  agent decides whether to show it, publish it to a wiki, or turn it into
  tickets. Don't claim to have saved or published anything you didn't.

When converting the document to another markup (a wiki's own format,
for instance), keep every heading, id and scenario word for word, so it
can be converted back to this Markdown without loss.
