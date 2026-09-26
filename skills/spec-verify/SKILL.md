---
name: spec-verify
description: >-
  Verifies that a project's specifications (GitHub Spec Kit layout:
  constitution, spec.md, plan.md, data-model.md, contracts/) accurately
  describe the code, without anyone reading every document. Runs checks
  in order of cost -- static checks and existing tests automatically,
  then asks before running the system, an adversarial audit, or a
  reimplementation trial -- stops early on capabilities that already
  fail, and reports per-capability verdicts plus the few decisions a
  human must make. Use when the user asks to verify, validate, or audit
  specs against the code, check spec accuracy or drift, or confirm
  generated specs before trusting them as the source of truth.
version: 1.0.0
metadata:
  category: software-development
  hermes:
    tags: [specification, spec-driven-development, spec-kit, verification, testing]
    category: software-development
---

# Spec verify

Answers one question per capability: **can these specs be trusted as
the source of truth for this code?** It does so by turning the specs'
claims into checks that run against the code, cheapest first, instead
of relying on someone reading every document.

This skill reports; it never edits code. It proposes spec corrections
and applies them only after the user approves. It never commits unless
the user asks.

## Before starting

- Locate the specs: `.specify/memory/constitution.md` and the
  numbered capability directories under `specs/`. If the project uses
  a different layout, map it onto the same artifact roles (behavior
  spec, technical plan, data model, contracts) and say so.
- Read `AGENTS.md` for how to build, run, and test the project.
- Ask which capabilities to verify if the user didn't say; default to
  all of them.

## Verification tiers

Run the tiers in order. Tiers 0 and 1 run automatically. Before each of
tiers 2-4, tell the user what it will do, what it will touch, and a
rough cost (time, and how many capabilities and workers), then wait for
approval -- the user may approve it for all capabilities, a subset, or
skip it.

**Stop early**: a capability that fails a cheaper tier badly (its
contracts or data model don't match, or most of its tests fail) is not
sent to the more expensive tiers. Report it as needing regeneration or
correction first; spending an adversarial audit on a spec already known
to be wrong wastes the budget.

### Tier 0 -- Static structure (automatic)

No code execution, no model reasoning beyond parsing:

- Spec Kit template sections present and in order in each artifact.
- IDs (`FR-###`, `SC-###`, `KD-###`, `GAP-###`) unique, well-formed,
  never reused; every cross-reference resolves.
- No implementation detail in `spec.md` (file paths, code identifiers
  that aren't contract or glossary names, code excerpts).
- Counts of `[NEEDS CLARIFICATION]` and `TODO(...)` markers per
  artifact.
- Glossary terms used consistently; listed synonyms absent.

### Tier 1 -- Static comparison and existing tests (automatic)

Compare machine-checkable artifacts with the code without running the
system, and run tests that already exist:

- `data-model.md` against the schema as the code defines it (migrations,
  ORM models, schema files): entities, fields, types, nullability,
  defaults, constraints, relationships.
- `contracts/` against the interface definitions in the code (routes,
  handlers, message schemas, CLI parsers): every operation exists on
  both sides, with the same parameters, types, and status codes.
- `plan.md` Technical Context against manifests and config: language
  and versions, dependencies, storage, test framework.
- The project's test suite, including any characterization tests that
  cite requirement IDs: a failing test that cites an `FR-###` is a
  direct spec-versus-code mismatch. List every `FR-###` no test cites.

Tier 1 runs only the test command `AGENTS.md` documents. If running it
needs external services (a database, a queue, credentials), treat it as
tier 2 and ask first.

### Tier 2 -- Runtime contract checks (ask first)

Start the system in a local or test environment and exercise its
interfaces against `contracts/` (property-based or schema-driven
contract testing where a tool for the contract format is available;
targeted requests otherwise), and compare the live schema against
`data-model.md`.

Never run against a shared, staging, or production environment. State
exactly what will be started and what may be written (test data,
fixtures) before asking.

### Tier 3 -- Adversarial audit (ask first)

One independent worker per capability -- in parallel if the environment
supports subagents or parallel tasks, sequentially otherwise -- given
the capability's artifacts and its code, with one goal: **prove the
specs wrong.** Use a worker that did not write the specs, and a
different model if the environment allows it.

- Every claimed mismatch must cite evidence (file and line, or a test);
  claims without evidence are discarded.
- Each worker checks, per requirement: does the code do exactly this,
  including limits, error cases, and ordering? And the reverse: what
  observable behavior in the code has no requirement at all?
- Workers also flag requirements that are true but imprecise -- where an
  implementer would still have to decide something.

### Tier 4 -- Reimplementation trial (ask first, sampled)

The direct test of the goal: can the specs alone reproduce the system?

- Apply it to a sample, not everything: propose one or two capabilities,
  prioritizing the riskiest (money, permissions, data deletion) and the
  ones earlier tiers flagged least.
- A fresh worker that has never seen the code receives only the
  constitution, the capability's artifacts, and what they link to, and
  implements the capability in an isolated location (a scratch
  directory or separate worktree) -- never inside the project's own
  source tree.
- Run the same tests against both implementations (the project's
  characterization tests, or scenario tests written from `spec.md`),
  or feed both the same inputs and compare outputs.
- Every behavioral difference is a spec gap: the reimplementation had to
  decide something the specs left open.
- Remove the scratch implementation afterwards unless the user wants to
  keep it.

## Findings

Each finding is classified before it is reported:

- **SPEC ERROR** -- the spec contradicts the code; propose the corrected
  text.
- **SPEC GAP** -- behavior exists in code with no requirement, or a
  requirement leaves a decision open; propose the missing requirement.
- **UNRECORDED DEFECT** -- the code does something that looks
  unintended; propose a `KD-###` entry for the user to decide.
- **DRIFT** -- spec and code once agreed and no longer do (a
  characterization test that cites the requirement now fails); report
  which side changed if history shows it.

## Report

Short, exact, and skimmable -- no narrative, no restated methodology:

```text
VERDICTS
  Capability           T0  T1  T2  T3  T4   Verdict
  001-invoice-billing  ok  ok  ok  2   --   2 issues
  004-authentication   ok  x   --  --  --   regenerate (contracts mismatch)
  ...                  (-- = not run, x = failed, n = issues found)

FINDINGS
  001 FR-012  SPEC ERROR  <what the spec says> vs <what the code does>  (<evidence>)
  ...

UNTESTED REQUIREMENTS
  <n> FRs with no test: <IDs, by capability>

NEEDS HUMAN DECISION
  <each proposed KD-###, each open NEEDS CLARIFICATION, each constitution
   principle the code violates>

NEXT
  <the next tier worth running and on which capabilities, with its cost>
```

The human-decision list is the part a person must actually read: it
contains only what the code cannot answer. Offer to apply the proposed
spec corrections; apply them only after approval, then rerun tiers 0-1
on the changed capabilities.
