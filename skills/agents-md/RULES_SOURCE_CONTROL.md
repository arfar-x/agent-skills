# Global rule: source control

Canonical text for the source-control rule that the `agents-md` skill
inlines into a target repo's `AGENTS.md` (under its "Commit / PR
instructions" section). Global and always-on: it applies to any target
repo regardless of that repo's own conventions. This file is a source of
truth the skill reads -- it is not itself copied into the target.

## Commit atomicity and independence

- **Commit the whole change unit.** When a task creates or modifies
  several files, all related files, behaviors, and actions that jointly
  caused the change go into ONE commit. Never split a single logical
  change across commits, and never bundle unrelated changes into one.
- **Every commit must be self-contained.** The codebase must build and
  run correctly at any commit; checking out any past commit must not
  produce errors. A commit must not import, reference, or depend on code,
  config, or behavior that does not exist in that commit (e.g. no route
  importing a service that arrives in a later commit; no code reading a
  Config attribute that is added later).
- **Dependencies only flow forward.** Newer commits may build on older
  ones. An older commit must never depend on, reference, or wait for a
  change that lands later.
- **Never mention non-existent things.** Do not reference tools, topics,
  user stories, specs, or plans that are not part of the project or
  finalized in documentation -- not in commit messages, docs, code, or
  comments.
- **Exception -- deliberate forward references.** Only when (a) the user
  explicitly asks, or (b) you are intentionally preparing an
  abstraction/interface that a known future feature will fill, may a
  `TODO:` comment name a not-yet-existing capability. No other forward
  references.
