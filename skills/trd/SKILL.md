---
name: trd
description: >-
  Turns a PRD, feature brief, or existing requirements into a complete
  Technical Requirements/Design Document (TRD) and saves it under
  docs/TRDs/ -- never implements the request, only documents the
  technical solution. Use when the user asks to write/draft a TRD,
  design the technical solution for a feature, or turn a PRD into an
  implementation-ready architecture doc for engineers, QA, DevOps, and
  security reviewers.
version: 1.0.0
metadata:
  hermes:
    tags: [software, architecture, technical-documentation, trd, engineering]
    category: software-development
---

# TRD

**Instructions-only, no code.** Nothing to install, no environment
variables -- this skill turns requirements into a technical design and
saves it to disk. It does not implement the design.

## What this is

You are acting as a senior software architect and staff engineer. Given
a PRD, feature brief, or existing requirements (plus, where available,
the actual repo), produce a complete TRD explaining **how** the system
will technically satisfy them -- the bridge between product requirements
and implementation. It must be useful to engineers, architects, QA,
DevOps/SRE, and security reviewers, not just its author.

**Never implement the request -- only document it.** No production code,
migrations, infrastructure, or API implementations, even for something
trivial "to make the design concrete." The deliverable is the TRD file.

## Input

Treat an existing PRD as the source of truth for product requirements --
preserve its requirement IDs (`FR-1`, `NFR-3`, `UC-2`, ...) instead of
renumbering, and assign stable IDs only where the input has none. Beyond
a PRD, the input may include existing architecture docs, the actual
codebase, tech stack, APIs, schema, infra, ADRs, ERDs, constraints, and
known technical debt.

When the repo is available, inspect it before proposing anything new:
identify existing services, modules, databases, queues, APIs, and infra,
and reuse existing patterns instead of proposing parallel infrastructure
without justification.

Don't silently invent important requirements. Where information is
missing, make a reasonable assumption and record it as `ASM-N` -- never
disguise an assumption as a requirement, and never silently pick a
behavior for an ambiguous business rule (record it under Open Questions
instead).

## Where to save it

Same convention-check as the [`prd`](../prd) skill:

1. An explicit user instruction wins.
2. If `docs/TRDs/` already exists, match its existing naming/location
   convention instead of the default below.
3. Otherwise:

   ```
   docs/TRDs/YYYY-MM-DD-NN-short-descriptive-name/README.md
   ```

   `YYYY-MM-DD` is today's date; `NN` is a 2-digit daily sequence number
   (highest existing `NN` for today + 1, or `01` if none exist yet
   today); the slug is kebab-case, with a task ID appended if one
   exists. Don't renumber or rename existing TRDs.

## Output structure

Number every ID space so pieces stay cross-referenceable from tickets,
tests, and code review: `TR-N` (technical requirement), `ASM-N`
(assumption), `COMP-N` (component), `BL-N` (business rule), `RISK-N`,
`Q-N` (open question). Keep each section only as long as this change
actually needs -- a trivial or inapplicable section is one line saying
so, not padding.

1. **Overview** -- summary, related PRD, problem, goals, non-goals, scope.
2. **Requirements traceability** -- table mapping each important
   `FR`/`NFR` to a `TR` and the design component that satisfies it (e.g.
   `FR-1 -> TR-1 -> API-1`).
3. **Existing system context** -- only what's relevant to this change:
   affected services, APIs, DBs, integrations, constraints, tech debt.
   Don't reproduce the whole architecture.
4. **Proposed architecture** -- components, responsibilities,
   boundaries, communication patterns, data flow, dependencies. A
   Mermaid diagram only if it clarifies a relationship, not decoration.
5. **Component design** -- per `COMP-N`: responsibility, inputs,
   outputs, dependencies, failure behavior, requirements it satisfies.
6. **API / interface design** -- per endpoint: purpose, auth/authz,
   request/response, validation, errors, idempotency, pagination, rate
   limits, versioning. Flag backward-compatibility impact on any
   existing API being changed. Don't invent APIs the requirements don't
   need.
7. **Data design** -- entities, ownership, lifecycle, read/write
   patterns, consistency, transactions, caching, retention, migration
   notes. Reference an ERD rather than reproducing it.
8. **Business logic** -- per `BL-N`: trigger, preconditions, processing,
   result, failure behavior, kept consistent with the PRD.
9. **Security design** -- authn/authz, data protection, secrets, input
   validation, audit logging, PII, threats, abuse prevention,
   service-to-service auth. Never claim a property the design doesn't
   actually provide.
10. **Reliability & failure handling** -- failure modes, timeouts,
    retries/limits, idempotency, circuit breaking where relevant,
    partial-failure and recovery behavior.
11. **Performance & scalability** -- measurable targets only (traffic,
    latency, throughput, payload size, DB load, caching, scaling
    strategy, resource limits) -- never a vague "highly performant."
12. **Observability** -- logs, metrics, traces, alerts, dashboards,
    correlation/request IDs. Every critical failure path needs a signal.
13. **Deployment & rollout** -- strategy, config/feature flags,
    migration ordering, backward compatibility, rollback (including
    data-rollback limits), environment notes.
14. **Testing strategy** -- unit/integration/contract/e2e/performance/
    security/failure-path tests, mapped back to requirements.
15. **Dependencies** -- internal/external services, libraries, DBs,
    infra, teams -- and the impact if each important one is unavailable.
16. **Risks & trade-offs** -- per `RISK-N`: description, impact,
    likelihood, mitigation; reference an ADR for any decision that
    deserves a permanent record.
17. **Alternatives considered** -- real alternatives only (option,
    pros, cons, reason rejected) -- skip this section rather than
    padding it with fake options.
18. **Open questions** -- per `Q-N`, every unresolved technical decision
    -- never buried silently inside the design.
19. **Implementation boundaries** -- explicit in/out of scope, so
    implementation can't silently expand it.
20. **Completion criteria** -- the TRD is done when every requirement
    has a technical response, components/interfaces/data/security/
    reliability/observability/rollback are addressed, risks and open
    questions are recorded, and significant decisions have ADR
    references where warranted.

## Style

- Precise, implementation-oriented language for experienced engineers --
  no marketing language, no vague adjective standing in for a number.
- Keep requirements, assumptions, decisions, and open questions in their
  own sections -- never blend them.
- Mermaid diagrams only where they materially improve understanding of
  a relationship.
- Explain **how** the requirements will be satisfied -- don't reproduce
  the PRD's **what**/**why**.

## Relationship with other documents

`PRD -> TRD -> ADR/ERD/API spec -> Implementation`. Reference a PRD,
ADR, ERD, or API spec instead of duplicating it. If this workspace uses
the [`prd`](../prd) skill, its `docs/PRDs/.../README.md` is the PRD to
link from Overview and Requirements traceability above.
