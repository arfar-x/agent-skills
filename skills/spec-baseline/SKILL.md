---
name: spec-baseline
description: >-
  Reverse-engineers an existing, under-documented codebase into a GitHub
  Spec Kit baseline -- constitution, per-capability specs, plans, data
  models, and contracts, with known defects and gaps beside each spec --
  precise enough to reimplement it with identical behavior, so the specs
  become the source of truth. Analyzes scopes in parallel, reports what
  to write and gets approval, then installs a spec-driven workflow for
  future changes, referenced from AGENTS.md. Use when the user asks to
  document an existing project from its code, lock current behavior into
  specs, or adopt spec-driven development or Spec Kit on a legacy
  codebase. Not for specifying a new feature.
version: 1.0.0
metadata:
  category: software-development
  hermes:
    tags: [documentation, specification, spec-driven-development, spec-kit, reverse-engineering]
    category: software-development
---

# Spec baseline

Turns code into a specification baseline in the format of
[GitHub Spec Kit](https://github.com/github/spec-kit). Before this
skill runs, the code is the source of truth. After it, the specs are:
any competent implementer given only these artifacts must be able to
rebuild the project with the same business logic and the same
observable behavior, down to the details. From then on, every change is
made to the specs first and implemented second.

This skill writes specification artifacts, plus characterization tests
when the user approves them. It never changes application code,
never "fixes" behavior while describing it, never installs tooling, and
never commits unless the user asks.

## Non-negotiable principles

1. **Describe current behavior exactly, including its flaws.** The
   baseline locks what the code does today, not what it should do.
   Behavior that looks like a bug is recorded as a known defect beside
   the spec it belongs to (see "Known defects and gaps"), and the user
   decides whether the requirement states the current behavior or the
   corrected one.
2. **Never invent.** Every statement must be backed by code, config,
   schema, tests, or an explicit user answer. What can't be determined
   is marked `[NEEDS CLARIFICATION: <question>]` in the artifact and
   raised with the user, never filled with a plausible guess. Rationale
   in particular is usually absent from code: a decision's *why* comes
   from the user, or the decision record isn't written.
3. **Precision over prose.** An artifact is done when an implementer has
   nothing left to decide. Vague phrasing ("validates the input",
   "handles errors appropriately") fails that bar; the exact rule,
   limit, message, code, and order of operations passes it.
4. **Behavior, not code.** `spec.md` is technology-agnostic: it states
   what the system does, never how the code does it. Technical detail
   lives in `plan.md`, `data-model.md`, and `contracts/` -- and even
   there, only at the level of components, technologies, and contract
   names, never file-and-line references, function bodies, or code
   excerpts. Code may be refactored freely without a spec change.
5. **Artifacts are self-contained and neutral.** They are written in the
   project's documentation language (the language of existing docs;
   English if none) in a standard technical register. They never
   mention this skill, the agent, the user, the conversation, or how the
   information was obtained. The report to the user follows the user's
   language and tone; the artifacts don't.

## Output layout

Follow Spec Kit's layout and templates, using the **living spec**
persistence model -- `spec.md` is the maintained contract, and the other
artifacts are kept in line with it. If the project already has Spec Kit
installed (a `.specify/` directory), use its templates from
`.specify/templates/` verbatim and extend its existing `specs/` tree.
Otherwise produce the same structure by hand; installing Spec Kit's
tooling is the user's decision, never this skill's.

```text
.specify/memory/constitution.md    project constitution
specs/
  glossary.md                      optional, project-wide (see Glossary)
  001-<capability>/
    spec.md                        behavior: stories, scenarios, FR-###, entities, SC-###
    plan.md                        technical design of the capability as built
    data-model.md                  entities, fields, validation, relationships, state transitions
    contracts/                     OpenAPI / AsyncAPI / GraphQL SDL / protobuf / CLI schema
    research.md                    decisions: Decision / Rationale / Alternatives considered
    quickstart.md                  end-to-end scenarios that validate the capability
  002-<capability>/
  ...
```

One numbered directory per **capability** (a coherent area of behavior,
e.g. `003-invoice-billing`, `007-authentication`), numbered in the
order the user approves. `tasks.md` is not produced -- it tracks
implementation work, and a baseline has none; it appears with the
first change made through the workflow.

How the traditional document types map onto these artifacts:

| Traditional type | Spec Kit artifact |
|---|---|
| PRD (product behavior, business rules, acceptance criteria) | `spec.md` |
| TRD (technical design, components, NFRs, configuration) | `plan.md` |
| ERD / data model spec | `data-model.md` (with a Mermaid `erDiagram` where relationships matter) |
| API / integration spec | `contracts/` |
| ADR (decision, context, alternatives) | `research.md` entries |
| State machine spec | state transitions in `data-model.md`, behavior in `spec.md` scenarios |
| Engineering principles, standards, workflow | `constitution.md` |

Produce only the artifacts a capability needs: `spec.md` and `plan.md`
always; the rest only when some finding has no other home.

## Phase 1 -- Discover

Build a map of the project without reading it all.

- Structural scan: directory tree, manifests and lockfiles, entry points
  (servers, CLIs, workers, schedulers), routing/API definitions, schema
  and migration files, config and env-var definitions, infrastructure
  and CI files, test layout.
- Read `AGENTS.md` (and anything it references) and the repo's
  contribution/git conventions; they override this skill's defaults
  wherever they cover the same ground.
- Inventory every existing document (README, `docs/`, wiki exports,
  API specs, diagrams). Do not trust them yet.
- Note convention sources for the constitution: linter, formatter, and
  type-checker configs, CI quality gates, test setup, dependency and
  layering rules, commit history conventions.
- Check for an existing `.specify/` directory or `specs/` tree.

## Phase 2 -- Split into scopes

Split along capability boundaries, not just folders:

- **Domain capabilities** -- one per bounded context or feature area,
  including every layer that serves it (API, service, data access,
  jobs).
- **Cross-cutting capabilities** -- authentication and authorization,
  external integrations, configuration, background processing and
  scheduling, infrastructure and deployment, observability. Each is a
  capability of its own when it carries behavior; shared entities are
  owned by one capability's `data-model.md` and referenced by others.

Size each scope so one worker can analyze it thoroughly within its own
context; subdivide anything larger. Record for each scope its paths, its
entry points, and which other scopes it depends on.

## Phase 3 -- Analyze scopes in parallel

If the environment can run subagents or parallel tasks, dispatch one
read-only worker per scope and run them concurrently; otherwise process
scopes sequentially with the same contract. Give each worker its scope's
paths, the dependency list, the coverage checklist below, and the
output format below -- nothing more. Workers analyze; they do not write
artifacts.

**Coverage checklist** -- a worker extracts every item that applies:

- User-facing flows: who does what, in what order, with what outcome
- Business rules and invariants, each stated as a single testable rule
- Inputs and validation: fields, types, required/optional, formats,
  ranges, defaults, normalization, exact error codes and messages
- Outputs and contracts: request/response schemas, status codes,
  events/messages published and consumed, file formats
- State and lifecycle: states, allowed transitions, triggers, guards,
  side effects of each transition
- Calculations: formulas, rounding, precision, currency and unit
  handling, time zones and date boundaries
- Ordering, concurrency, idempotency, transactions, retries, timeouts
- Permissions: who can do what, and what an unauthorized caller sees
- Side effects: writes, notifications, external calls, cache
  invalidation, audit logs
- Scheduled and background work: schedule, input, effect, failure
  handling
- Configuration: every setting and env var that changes behavior, with
  default and effect
- Data model: entities, fields, types, constraints, defaults, indexes,
  relationships, cardinality, deletion behavior
- Measurable limits: timeouts, rate limits, size caps, pagination
  bounds, retention periods
- Edge cases the code explicitly handles, and behavior on empty,
  missing, duplicate, and boundary input
- Behavior encoded only in tests (a test asserting behavior counts as
  evidence)
- Gaps: flows that are started but not finished, inputs with no
  handling, states with no exit, contracts the code doesn't honor

**Worker output** -- structured findings, not prose:

```text
SCOPE: <name> (<paths>)
FINDINGS:
  - id: <scope>-<n>
    kind: flow | rule | contract | state | data | config | job | integration | limit
    statement: <exact behavior, one fact per finding>
    evidence: <file:line or test name>
DEFECTS: <behavior that looks unintended, with evidence>
GAPS: <missing or incomplete behavior, with evidence>
TERMS: <domain term> -- <code names> -- <synonyms/ambiguities seen>
CONVENTIONS: <pattern> -- followed in <n>/<m> places -- <evidence, deviations>
DECISIONS: <design choice visible in code whose rationale is unknown>
OPEN QUESTIONS: <what code cannot answer>
EXISTING DOCS: <doc> -- accurate | stale | wrong | partial, with the contradicting evidence
```

Evidence stays in these findings and the verification pass; it never
goes into the artifacts (principle 4).

## Writing each artifact

### `spec.md`

Follow Spec Kit's spec template, filled with current behavior:

- **Header** -- `# Feature Specification: <Capability>`, then
  `**Created**`, `**Status**` (`Accepted` for baseline specs), and
  `**Input**: Existing system behavior`. No feature branch field for a
  baseline spec.
- **User Scenarios & Testing** -- one user story per user-facing flow,
  each with a priority (`P1`, `P2`, ...; proposed in the report and
  confirmed by the user, since criticality isn't in the code), an
  independent test, and acceptance scenarios in
  `**Given** ... **When** ... **Then** ...` form covering every rule
  and error path. Then **Edge Cases**, answered with the actual
  behavior rather than left as questions.
- **Requirements** -- `**FR-###**: System MUST ...` statements, one
  testable rule each, and **Key Entities** described without
  implementation detail.
- **Success Criteria** -- `**SC-###**` measurable outcomes the current
  system actually guarantees (limits, timeouts, bounds from the
  checklist); `[NEEDS CLARIFICATION]` where none is verifiable.
- **Assumptions** -- only dependencies on the environment or other
  capabilities that are verified, never guesses.
- **Known Defects and Gaps** -- see below.

Requirement IDs (`FR-###`, `SC-###`) are permanent: never reused or
renumbered, so future changes, tests, and commits can cite exactly what
they implement.

### Known defects and gaps

Every `spec.md` ends with a `## Known Defects and Gaps` section, kept
separate from the requirements so the requirements stay a clean
contract:

```markdown
## Known Defects and Gaps

### Defects
- **KD-001** (FR-007): <observed behavior> -- expected: <correct behavior,
  if known>. Status: <Accepted as current behavior | Scheduled for correction>

### Gaps
- **GAP-001** (User Story 2): <behavior that is missing, undefined, or
  incomplete>. Status: <Accepted | Scheduled>
```

If the user decides a defect should be corrected, the requirement
states the corrected behavior and the entry records that the current
implementation diverges from it. Either way, nothing about a defect is
silently resolved in the requirements or in code.

### `plan.md`

Spec Kit's plan template, describing the capability as built:
**Summary**, **Technical Context** (language/version, primary
dependencies, storage, testing, target platform, project type,
performance goals, constraints, scale -- each from evidence or
`NEEDS CLARIFICATION`), **Constitution Check** (how the capability
satisfies each relevant principle), **Project Structure** (directory
layout only), and **Complexity Tracking** listing each approved
divergence from the constitution. Configuration settings, their
defaults, and their effects belong here.

### `data-model.md`, `contracts/`, `research.md`, `quickstart.md`

- `data-model.md` -- entities, fields, types, constraints, defaults,
  validation rules, relationships, and state transitions.
- `contracts/` -- machine-readable interface definitions in the
  project's contract language, matching the implementation exactly.
- `research.md` -- one entry per design decision whose rationale the
  user supplied, in Spec Kit's `Decision` / `Rationale` /
  `Alternatives considered` form. Decisions without a known rationale
  are not recorded (principle 2).
- `quickstart.md` -- end-to-end scenarios an implementer runs to
  confirm the capability behaves as specified.

### Glossary

Spec Kit has no glossary artifact; when the user opts in, it lives at
`specs/glossary.md` and every artifact uses its terms verbatim. Each
entry holds:

- **Term** -- the canonical domain name.
- **Definition** -- one or two sentences, in domain terms.
- **Code names** -- identifiers the concept has in code, schema, and
  APIs when they differ from the term (e.g. term *Subscriber*, class
  `Member`, table `users`, API field `member_id`). These are contract
  names, so they don't breach principle 4.
- **Avoid** -- synonyms found in code, docs, or UI that must not be used
  for this concept, and terms easily confused with it.

### Constitution

Follow Spec Kit's constitution template at
`.specify/memory/constitution.md`: `# <Project> Constitution`,
**Core Principles** (each a named, numbered principle stated with
`MUST` / `MUST NOT` / `SHOULD`, marked `(NON-NEGOTIABLE)` where it is),
additional sections for constraints and standards, the **Development
Workflow** section (Phase 7), and **Governance**, ending with
`**Version**: 1.0.0 | **Ratified**: <date> | **Last Amended**: <date>`
and a Sync Impact Report as an HTML comment at the top. A value that
is genuinely unknown is written `TODO(<FIELD>): <explanation>`.

Derive principles only from evidence -- `AGENTS.md`, consistent
patterns in code structure, rules enforced by tooling (linters, type
checkers, CI gates), and existing docs the code confirms -- or from
what the user explicitly agrees to adopt. Never add aspirational
principles to fill the template.

- **Content**: architecture and layering rules, module boundaries and
  dependency direction, technology and platform constraints, coding
  and naming conventions, error-handling and logging conventions,
  testing standards, security and data-handling rules, API and
  data-model design conventions, quality gates a change must pass.
- **Consistency threshold**: a pattern followed everywhere becomes a
  principle. A pattern with deviations is proposed with its deviations;
  the user decides whether it becomes a principle (the deviations then
  go into the affected `plan.md` Complexity Tracking) or is dropped.
- **Governance**: SemVer for the constitution itself (MAJOR for a
  removed or redefined principle, MINOR for a new principle or section,
  PATCH for wording), amendment procedure, and precedence: the
  constitution governs specs and code, and it is amended first rather
  than violated.
- **`AGENTS.md`** stays the runtime development guide and links to the
  constitution instead of restating principles. Where `AGENTS.md`
  contradicts the code, report it; don't silently pick one.

## Phase 4 -- Report and get approval

The report is short, exact, and skimmable -- no narrative, no restated
methodology:

```text
PROJECT MAP
  <scope>  <paths>  <one-line purpose>

PROPOSED SPECS
  #    Capability            Artifacts                      Covers
  001  invoice-billing (P?)  spec, plan, data-model, contracts  23 FR, 4 stories
  ...

CONSTITUTION (approve, edit, or drop each)
  I    <MUST ...>                 consistent
  II   <SHOULD ...>               3 deviations: <where>
  --   Development Workflow (spec-driven, see below)

DEFECTS (recorded as current behavior unless told otherwise)
  <scope>-<n>  <behavior>  (<evidence>)  -> <spec>

GAPS
  <scope>-<n>  <missing behavior>  -> <spec>

DECISIONS (rationale needed for research.md, or skip)
  D1  <choice visible in code>

EXISTING DOCS
  <doc>  replace | merge into <spec> | keep | archive  -- <one-line reason>

OPEN QUESTIONS
  Q1  <question>  -> <spec>

GLOSSARY  <n> terms, <m> with naming conflicts -- produce it? (yes/no)

TESTS     <n> acceptance scenarios -> <test location per project convention>
          -- write characterization tests? (yes/no)
```

Ask the user to approve specs by number and confirm story priorities,
decide each constitution principle and each defect, supply rationale for
any decision worth recording, answer the open questions, and say
whether to produce the glossary and the characterization tests. Nothing is written before approval.
Existing documents are never deleted or overwritten without an explicit
decision per document.

## Phase 5 -- Write the approved artifacts

- **Order**: constitution and glossary first, then each capability's
  `data-model.md` and `contracts/` (other artifacts reference them),
  then `spec.md`, `plan.md`, and the rest.
- **Parallel writing**: capabilities can be written by parallel workers,
  each receiving its findings plus the constitution and the glossary, if
  produced. A shared entity or contract has a single owning capability;
  others link to it instead of restating it.
- **Single source per fact**: each fact lives in exactly one artifact.
  Duplication is how specs drift apart.
- **Unresolved items** stay visible as `[NEEDS CLARIFICATION: ...]`,
  never as a guessed statement.

## Phase 6 -- Install the spec-driven workflow

Record the workflow in the constitution's **Development Workflow**
section, so it is governed and versioned with the rest of the project's
rules:

- **Source of truth**: `Accepted` specs define intended behavior; code
  that disagrees with one is a defect in one of the two, resolved
  explicitly -- never by silently editing either.
- **Persistence model**: living spec -- `spec.md` is revised first when
  intended behavior changes, and downstream artifacts are brought back
  in line with it.
- **Change flow**, in this order and in the same change or pull request
  (Spec Kit's commands where installed, the equivalent manual steps
  otherwise):
  1. *Specify* -- revise the capability's `spec.md`, or create a new
     numbered capability directory; new requirements get new IDs.
  2. *Clarify* -- resolve every `[NEEDS CLARIFICATION]` in the affected
     artifacts; nothing with an open marker is implemented.
  3. *Plan* -- revise `plan.md`, `data-model.md`, and `contracts/`, and
     pass the Constitution Check; a violation needs a constitution
     amendment or a justified Complexity Tracking entry.
  4. *Tasks* -- derive `tasks.md`, each task citing the requirement IDs
     it implements.
  5. *Analyze* -- check spec, plan, and tasks for consistency before
     implementing.
  6. *Implement* -- code and tests, with tests citing requirement IDs.
  7. *Converge* -- confirm the code satisfies the spec, resolve or record
     remaining gaps, and update the Known Defects and Gaps section.
- **Change classes**: a new capability or behavior change follows the
  full flow; a defect where the code diverges from an `Accepted` spec
  changes code only and closes its `KD-###` entry; an error in the spec
  itself is corrected in the spec first; a refactor with no observable
  behavior change needs no spec change but must pass the Constitution
  Check.
- **Specification standards**: the layout above, the ID scheme, the
  status lifecycle (`Draft` -> `Accepted` -> `Superseded`), neutral
  technical register, and no code in `spec.md`.

Then add a short section to `AGENTS.md` that links to the constitution
and `specs/`, and states in a few lines that the specs are the source of
truth, that every behavior change follows the constitution's
Development Workflow, and that plans must pass the Constitution Check --
a reference, not a copy. Follow `AGENTS.md`'s existing structure and
style; if the project has no `AGENTS.md`, ask the user before creating
one.

## Phase 7 -- Verify

### Characterization tests

If the user approved them, turn every acceptance scenario and edge case
into an executable test, then run the tests against the current code.
This is the check that proves the specs describe the code, not just
that they read well.

- **Spec-blind authoring**: one worker per capability writes the tests
  from that capability's `spec.md` and `contracts/` only. It may read
  the project's test setup (framework, fixtures, factories, how the
  system is started or called) but never the implementation it is
  testing -- a test written from the code confirms the code, not the
  spec.
- **Conventions**: follow the project's test layout, naming, and
  runner, as documented in `AGENTS.md` or evident in existing tests.
  Tests exercise observable behavior through public interfaces only.
- **Traceability**: each test names the requirement and scenario it
  covers (e.g. `FR-012`, User Story 2 scenario 3), so the test suite
  maps back to the specs.
- **Triage every failure** against the code, and fix the right side:
  - the spec is wrong or imprecise -> correct the spec from the code,
    regenerate the affected tests, rerun;
  - the code does something unintended the spec didn't capture -> a new
    `KD-###` entry, decided by the user like any other defect;
  - a requirement the user chose to state as corrected behavior (an
    existing `KD-###`) -> the test stays, marked as an expected failure
    that cites the `KD-###` entry, so fixing the defect later flips it
    to passing.
- **Coverage**: list every `FR-###` with no test. Each one is either
  untestable through public interfaces (say why) or a sign the spec's
  scenarios are incomplete.

These tests stay in the project as its characterization suite: once
the specs are the source of truth, a failing test means the code and
the specs have drifted apart.

### Artifact checks

1. **Reimplementation gaps** -- reading only a capability's artifacts
   (and what they link to), list every decision an implementer would
   still have to make. Each one is a gap: fill it from the code or mark
   it `[NEEDS CLARIFICATION]`.
2. **Spec Kit conformance** -- template sections present and in order,
   IDs unique and well-formed, no implementation detail in `spec.md`.
3. **Consistency** -- each concept has one name across all artifacts
   (the glossary's term and none of its listed synonyms, when a glossary
   exists), no fact stated twice, cross-links resolve.
4. **Constitution** -- every principle holds in the code or its
   divergence is in Complexity Tracking; nothing in `AGENTS.md`
   contradicts it.
5. **Neutrality** -- no mention of the session, agent, user, or
   evidence trail; no unsupported rationale.

Deeper independent verification -- contracts and data models against
the running system, an adversarial audit, a reimplementation trial --
is a separate step with its own costs; if a spec-verification skill is
available, recommend running it next rather than doing it here.

Fix what verification finds, then send the final report:

```text
WRITTEN       <n> capabilities, <m> artifacts  (<paths>)
CONSTITUTION  .specify/memory/constitution.md  v1.0.0, <n> principles, workflow installed
AGENTS.md     section added, links constitution and specs/
COVERAGE      <scopes covered> / <total>; not covered: <scopes, why>
TESTS         <n> written, <p> passing, <x> expected failures (KD-###), <u> FRs untested
DEFECTS/GAPS  <n> KD, <m> GAP entries across <k> specs
OPEN          <remaining NEEDS CLARIFICATION markers, by spec>
```
