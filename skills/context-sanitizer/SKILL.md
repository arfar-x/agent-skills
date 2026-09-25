---
name: context-sanitizer
description: >-
  Sanitizes a repository's code comments and implementation
  documentation so they describe the current software, not the
  conversation, meeting, or decision process that produced it. Scans
  structure lightly, asks the user which scope to inspect, classifies
  each comment/doc item as KEEP, REWRITE, REMOVE, or REVIEW, and applies
  changes only after approval. Use when the user asks to clean up,
  sanitize, or de-contextualize comments or docs ("remove AI/chat
  context from comments", "strip decision narratives from the code",
  "clean up leftover discussion in the docs"). Not for architectural, product,
  business, roadmap, or planning documents.
version: 1.0.0
metadata:
  category: software-development
  hermes:
    tags: [documentation, comments, cleanup, code-quality]
    category: software-development
---

# Context sanitizer

The repository should answer **"What does the software currently do,
and what does the current implementation need to know?"** -- never
"What did the developer, customer, or AI discuss while creating it?"
This skill edits comments and documentation only; it never changes
code behavior.

## Scope of content

**Preserve:** current behavior and implementation; current business
and domain rules; technical constraints and invariants; APIs and
contracts; security and operational requirements; implementation
details needed to understand the code; TODOs and tasks the user
explicitly requested.

**Remove or rewrite:** AI, session, and conversation context ("we
discussed", "we decided", "as mentioned earlier"); customer or company
context that isn't part of the current software contract; personal
reasoning and meeting context; future-feature speculation and roadmap
information; temporary implementation plans; competitor or alternative
evaluations; business or architectural decision narratives.

**Out of scope:** ADRs and business, product, roadmap, and planning
documents. Never create, modify, or evaluate them, and leave them out of
the scopes offered to the user. Decision rationale belongs there, so
when an implementation comment carries a decision narrative, keep only
the technical fact the current code needs:

```text
BEFORE  // We decided to build our own engine because n8n was not a good
        // fit -- its community does not support feature X.
AFTER   // The application uses an internal workflow engine for workflow execution.
```

If the code doesn't need even that fact, remove the comment entirely.

Mentioning a company, customer, technology, or third-party service is
not by itself a reason to remove something. What matters is whether it
is part of the current software contract: "Payloads are signed as the
payment provider's webhook spec requires" stays; "The customer asked
for this on the kickoff call" goes.

## Future work and TODOs

Remove future features from implementation comments and docs
(`// Eventually we will support multi-tenancy.` → REMOVE), unless they
are maintained in planning documentation, which is out of scope anyway.

A TODO is different: never remove one merely because it describes
future work. Keep it when it represents a task the user explicitly
requested, and strip only its conversational wording:

```text
BEFORE  // TODO: As we discussed with the AI, eventually add retries.
AFTER   // TODO: Add retry handling for failed webhook deliveries.
```

If you can't tell whether a TODO was explicitly requested, classify it
REVIEW rather than removing it.

## Classification

For every comment or documentation item, ask:

1. Does it describe current behavior?
2. Is it a current technical constraint or invariant?
3. Is it a current business or domain rule?
4. Is it necessary to understand the current implementation?
5. Or does it instead describe a conversation, session, customer
   discussion, personal reasoning, decision process, roadmap, or future
   feature?

Then classify it:

- **KEEP** -- information required to understand the current software.
- **REWRITE** -- the technical information is valid but the wording
  carries contextual or conversational framing; keep the fact, drop
  the framing.
- **REMOVE** -- the item exists only because of a conversation, session,
  customer discussion, roadmap, speculation, or decision-making process.
- **REVIEW** -- it's unclear whether the item is current repository
  knowledge or context. Do not guess; surface it to the user.

## Scoping and token efficiency

Never read the entire repository by default.

1. **Discover.** Run a lightweight structural scan only -- directories,
   files, packages/modules, source areas, docs, tests, infrastructure.
   Do not read file contents deeply at this stage.
2. **Ask for scope.** Show the discovered logical scopes (e.g.
   `src/auth`, `src/billing`, `src/api`, `tests`, `docs`) and ask which
   to inspect. The user may pick directories, files, several scopes, or
   the whole repository.
3. **Stay inside the selected scope.** Never deeply inspect or modify
   anything unselected. If understanding the selected scope requires
   another one, ask before expanding.
4. **Subdivide large scopes.** If a selected scope is too large to
   process well at once, split it into smaller logical sub-scopes and
   ask which to process.
5. **Process incrementally.** Treat each scope independently, and don't
   re-analyze a processed scope unless the user asks or a later change
   directly invalidates the earlier analysis.
6. **Whole repository only on request.** Run a repository-wide pass
   only when the user explicitly selects it, and even then work through
   it scope by scope rather than loading everything into one context.

## Workflow

1. Discover the repository structure.
2. Ask the user to select a scope.
3. Analyze only the selected scope.
4. Classify each finding as KEEP / REWRITE / REMOVE / REVIEW.
5. Show the proposed changes -- for each REWRITE or REMOVE, the file and
   line, the current text, and the replacement (or "removed"); list
   REVIEW items separately with the question each one raises. KEEP
   items need no listing.
6. Apply changes only after the user approves them, unless the user
   explicitly asked for automatic application.
7. Re-scan only the modified scope to confirm the result.
8. Report what changed and every unresolved REVIEW item.

Never modify files outside the approved scope.
