---
name: spec-readiness
description: >-
  Checks whether a product specification (Spec Kit spec.md shape, e.g.
  from the product-spec skill) is ready for development, using Spec
  Kit's own requirements-quality checklist plus product checks, and
  returns a Ready / Not ready verdict with every failing item and the
  fix for it. Changes nothing itself. Use before approving a spec,
  before turning it into tickets, or when someone asks whether a spec is
  ready, complete, or good enough for developers.
version: 1.0.0
metadata:
  category: productivity
  doc_type: spec-readiness
  hermes:
    tags: [product, specification, spec-driven-development, spec-kit, quality]
    category: productivity
---

# Spec readiness

**Instructions-only, no code.** Nothing to install, no environment
variables.

These are unit tests for requirements. They test whether the **spec**
is complete, clear and testable, not whether a product works. A Ready
verdict means a developer can take this spec into planning without
asking anyone anything.

This skill **only reports**. It never edits the spec, approves it,
publishes it or creates tickets. Fixes go back through whoever owns the
spec (the `spec-clarify` skill for open questions).

## Input

A specification in Spec Kit `spec.md` shape, read in full. If you have
only a link or title, fetch the current text first.

## The checklist

Check every item. Each one is **Pass** or **Fail**. For a Fail, quote or
point to the exact place in the spec, and state the smallest change
that would make it pass.

The first three groups are Spec Kit's own requirements checklist, word
for word, so the result can also be saved as Spec Kit's
`checklists/requirements.md`.

### Content Quality

- [ ] No implementation details (languages, frameworks, APIs)
- [ ] Focused on user value and business needs
- [ ] Written for non-technical stakeholders
- [ ] All mandatory sections completed

### Requirement Completeness

- [ ] No [NEEDS CLARIFICATION] markers remain
- [ ] Requirements are testable and unambiguous
- [ ] Success criteria are measurable
- [ ] Success criteria are technology-agnostic (no implementation details)
- [ ] All acceptance scenarios are defined
- [ ] Edge cases are identified
- [ ] Scope is clearly bounded
- [ ] Dependencies and assumptions identified

### Feature Readiness

- [ ] All functional requirements have clear acceptance criteria
- [ ] User scenarios cover primary flows
- [ ] Feature meets measurable outcomes defined in Success Criteria
- [ ] No implementation details leak into specification

### Product Readiness

- [ ] Current behavior is described and its sources are named, or the
      spec says plainly that this is a new capability
- [ ] Intended behavior is stated, and it matches the user stories
- [ ] Every user story has a priority, a "Why this priority", an
      Independent Test, and at least one Given/When/Then scenario
- [ ] Every scenario's Then is observable by a user or tester
- [ ] Ids are unique and sequential (`FR-###`, `SC-###`), with no reused ids
- [ ] Out of Scope is stated
- [ ] `## Questions for Engineering` is empty or absent
- [ ] One term per concept throughout (no drifting synonyms)

## How to judge

- **Testable** means two people would agree whether it passed. "Fast",
  "intuitive", "robust" and "user-friendly" fail unless a number or an
  observable condition follows.
- **Implementation detail** means naming a technology, an API, a data
  store, a screen component library or a code structure. Naming another
  product or team the feature depends on is a dependency, and that is
  fine.
- **Mandatory sections**: User Scenarios & Testing, Requirements and
  Success Criteria, each with real content rather than template
  placeholders.
- Be strict. A borderline item is a Fail with a suggested fix, not a
  Pass with a note.

## Verdict

Report in this order:

1. **Verdict**: **Ready** if every item passes, otherwise **Not ready**.
2. **Failing items**: each with its location in the spec and the fix.
   Group them by who can fix them: the requester (product decisions),
   engineering (open questions) or the writer (wording and structure).
3. **The checklist**: all four groups with `[x]` / `[ ]`, ready to keep
   next to the spec.

Never report Ready while a `[NEEDS CLARIFICATION]` marker or an
engineering question remains, however minor it seems.
