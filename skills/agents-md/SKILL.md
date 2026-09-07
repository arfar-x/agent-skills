---
name: agents-md
description: >-
  Writes or updates an AGENTS.md file for a target project (or, for a
  monorepo, a root AGENTS.md plus nested per-subproject AGENTS.md files)
  -- the open, tool-agnostic convention (agents.md) that gives a coding
  agent the build/test/architecture/style context a README doesn't.
  Searches the whole project tree for AGENTS.md files that already exist
  in subdirectories, folds each into the root file's Project map graph,
  and reasons about the context scope each one already governs before
  proposing any new nested file. Structures the result as a lean root
  file linking out to nested AGENTS.md files and to already-existing docs
  (README/ARCHITECTURE/CONTRIBUTING) instead of duplicating them, so an
  agent only pays token cost for the part of the project it's actually
  touching. Never invents a command, architecture detail, or convention
  the project doesn't actually have -- asks instead. Use when the user
  asks to write/create/generate/update an AGENTS.md (or CLAUDE.md) file,
  onboard a coding agent onto a codebase, or document build/test/
  architecture/style conventions for agents working in a repo.
version: 1.1.0
metadata:
  category: software-development
  doc_type: agents-md
  hermes:
    tags: [agents-md, documentation, onboarding, conventions, context-engineering, engineering]
    category: software-development
---

# AGENTS.md

**Instructions-only, no code.** Nothing to install, no environment
variables -- this skill writes/updates an `AGENTS.md` file (a markdown
document) and saves it to disk, nothing else.

## What this is

You are acting as the engineer onboarding a coding agent onto an
existing (or brand-new) codebase, by writing the one file most
coding-agent tools read first: [AGENTS.md](https://agents.md), an open,
tool-agnostic convention now read by 20+ agent tools (Codex, Cursor,
Copilot, Aider, Devin, Zed, Warp, Claude Code via a `CLAUDE.md` symlink,
...). In the format's own words: "README.md files are for humans...
AGENTS.md complements this by containing the extra, sometimes detailed
context coding agents need: build steps, tests, and conventions." There
is no fixed schema -- "just standard Markdown, use any headings you
like" -- so this skill's job is judgment about what's real and worth
saying, not filling in a template.

**Never implement or change the project itself -- only document its
actual, already-true build/test/dev/style setup.** No new scripts,
config files, CI steps, or lint rules "to make the AGENTS.md accurate."
If the project's real setup doesn't support something you'd like to
document (e.g. there's no test command), document what's actually there
and say so -- don't add tooling to make the doc look complete.

**Never invent a command, architecture detail, or convention the
project doesn't actually have.** Every command in the output (setup,
build, test, lint) must be one you have verified against the repo
itself -- a script in `package.json`, a `Makefile` target, a CI workflow
step, a `pyproject.toml` entry point -- never a plausible-sounding guess,
and never taken at face value from a stale README without cross-
checking it still works. The same applies to architecture and coding
conventions, which are easy to get subtly wrong by pattern-matching on
too little: if you can't verify a claim from the repo's own files and
the user hasn't stated it, **ask rather than invent it or silently omit
it.**

## Input

Unlike a PRD/TRD/ADR/RFC brief, the source of truth here is mostly the
*repository itself*, not a text description the user hands you. The
request typically supplies only: which project/subproject root to
target (defaults to the current project root), and maybe a stated
preference on scope (monorepo split, or "just the root"), tone, or
whether to create a `CLAUDE.md` symlink. It may also supply: known
build/test commands, a known monorepo layout, a description of the
architecture, or an explicit instruction to update rather than replace
an existing file.

Before drafting, actually explore the target project: package manifests
and lockfiles (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`,
...), a `Makefile`/`justfile`, CI config (`.github/workflows/`, etc.),
existing `README.md`/`CONTRIBUTING.md`/`ARCHITECTURE.md`/`docs/`, linter/
formatter config, and any existing `AGENTS.md`/`CLAUDE.md`. For the
latter, search the **whole project tree**, not just the target root and
its immediate children -- e.g. `git ls-files '*AGENTS.md' '*CLAUDE.md'`
(or `find . -iname 'AGENTS.md' -o -iname 'CLAUDE.md'` outside a git repo)
-- since a nested file can already exist several directories deep, in a
subdirectory the user never mentioned. See "Discover existing nested
files" under "Where to save it" for what to do with what you find. Three
things are worth asking about rather than guessing when they're
genuinely unclear, not just inconvenient to verify:

- **Setup/build/test commands** -- the real build/setup and test
  commands are what make an AGENTS.md worth reading at all. If you
  can't find or verify them from the repo's own config, ask the user
  for the exact command rather than guessing one that "should" work.
- **Architecture** -- if how the major components relate, how a
  request or a unit of data actually flows through the system, or why a
  key structural decision looks the way it does isn't actually clear
  from the code and existing docs, ask the user rather than
  reverse-engineering a plausible-sounding structure from a partial
  read. A wrong architecture description actively misleads every future
  agent that trusts it; no description at all is safer.
- **Coding conventions and patterns** -- if a convention isn't
  obviously enforced by a linter/formatter config, or isn't
  consistently followed across the codebase already, ask what the real
  rule is instead of inferring one from a handful of examples that
  might just be habit, not a rule someone would actually want enforced.

Everything else is fair to infer from what you find, mark as not
applicable, or omit.

## Where to save it

AGENTS.md is a **singleton per project root** (or, in a monorepo, per
subproject root) -- unlike `prd`/`trd`'s dated folders or `adr`/`rfc`'s
sequential numbering, there is no numbering and no `docs/` subfolder:
the file lives at the actual root of the project (or subproject) it
describes.

1. **An explicit user instruction wins** -- if the user names a specific
   path or tells you which subdirectories are independent subprojects,
   use that.
2. **Detect what's already there before deciding create vs. update:**
   - If `AGENTS.md` already exists at the target root, **update it in
     place** -- read it first, keep whatever's still accurate, revise
     what's stale, add what's missing. Never regenerate the whole file
     from a blank template when one already exists; that throws away
     hand-written context (rationale, exceptions, links) this skill has
     no way to reconstruct on its own.
   - If `CLAUDE.md` already exists at that root as a **symlink** to
     `AGENTS.md` (the convention this very repo uses -- confirm with
     e.g. `ls -la`, don't assume), leave the symlink untouched and edit
     the `AGENTS.md` it points to.
   - If `CLAUDE.md` exists there as a **real file** (not a symlink) and
     `AGENTS.md` doesn't, ask the user how to reconcile the two before
     writing anything -- e.g. adopt its content into a new `AGENTS.md`
     and turn `CLAUDE.md` into a symlink to it, or leave `CLAUDE.md` as
     the Claude-specific file and create `AGENTS.md` alongside it. Don't
     silently overwrite or symlink over an existing real file.
   - If neither exists, this is a **fresh create**: write `AGENTS.md` at
     the root. Don't create a `CLAUDE.md` symlink unless the user asks
     for one or says they use Claude Code/CLAUDE.md specifically --
     mention the option rather than assuming it.
3. **Discover existing nested files and fold them into the graph before
   proposing anything new.** From the whole-tree search in "Input"
   above, you already have every `AGENTS.md` that exists anywhere under
   the target root, at any depth -- not just ones this skill wrote.
   Each one already defines a **context scope**: per agents.md's
   precedence rule ("the closest AGENTS.md file to the file being
   edited takes precedence"), a nested file's instructions govern every
   file at or below its own directory, up to the next nested file
   that's closer to the file being edited (or up to the root file, if
   nothing closer exists). For each discovered nested file:
   - **Read it, but never inline, duplicate, or rewrite its content
     into the root file or another nested file.** Reading it is only to
     produce an accurate one-line summary for the Project map and to
     sanity-check it still matches its directory -- if it looks stale
     (describes a command or structure that no longer exists), flag
     that to the user rather than silently rewriting someone else's
     file.
   - **Add or refresh its entry in the root file's Project map** so the
     graph reflects every scope that actually exists, not only the ones
     this run of the skill happens to create.
   - **Treat its directory as an already-claimed scope** when deciding
     whether a *new* nested file is warranted elsewhere in step 4 below
     -- don't propose a new nested file for a subdirectory that a
     discovered file already covers, unless that subdirectory is itself
     an independent subproject deep enough to deserve its own, more
     specific file (closest-file-wins still applies among nested
     files, not just between root and nested).
   - If a discovered nested file's own scope is ambiguous (it's unclear
     which directories it's meant to govern, or two nested files
     appear to overlap), ask the user rather than guessing a boundary.
4. **Monorepo -- propose a root + nested split** when the project
   genuinely has independent subprojects (their own build/test/deploy,
   own language or stack, or already their own `README.md`) that aren't
   already covered by a file discovered in step 3 -- see "The graph, not
   a monolith" below for the shape. Per agents.md's own stated
   precedence rule, "the closest AGENTS.md file to the file being
   edited takes precedence," so each subproject gets its own file
   rather than one giant root file trying to cover all of them. Don't
   fragment a single-stack project into nested files just to force the
   pattern -- a plain single-language project gets one root `AGENTS.md`,
   full stop. If it's ambiguous whether a subdirectory is a genuinely
   independent subproject or just a folder, ask before creating several
   new nested files unprompted.

## The graph, not a monolith

The point of AGENTS.md isn't to write everything an agent could
possibly need into one file -- it's to make sure an agent only pays
token cost for the part of the project it's actually touching. Treat
the root `AGENTS.md`, every nested `AGENTS.md`, and the project's other
existing docs (`README.md`, `ARCHITECTURE.md`, `CONTRIBUTING.md`,
`docs/`) as **one graph an agent traverses only as deep as the task
requires**, not one document to make exhaustive:

- **Keep the root file lean.** It covers only what's true for the
  *whole* project -- what it is, how to build/test it as a whole (if
  that's even a meaningful operation), and repo-wide conventions -- plus
  a **Project map** (below) linking out to everything else. It never
  copies a subproject's own build steps or a doc's own content into
  itself.
- **Link outward instead of duplicating.** If `README.md` already
  explains installation, or `ARCHITECTURE.md` already explains why a
  design looks the way it does, or `CONTRIBUTING.md` already states PR
  conventions -- link to it by relative path and summarize in one line,
  don't restate its content. A restated copy silently drifts out of
  sync the moment someone edits the real source and forgets the copy
  exists; a link never can.
- **Push subproject-specific detail down, not sideways.** A convention
  that only matters to someone working inside one subdirectory belongs
  in that subdirectory's own `AGENTS.md`, not in the root file "just in
  case" -- exactly the same judgment call this repo's own root
  `AGENTS.md` makes when it ends with "Toolset-specific conventions...
  belong in that toolset's own `skills/<toolset>/README.md`, not here."
- **The graph includes files this skill didn't write.** A project can
  already have nested `AGENTS.md` files -- hand-written, or produced by
  another tool or a previous run -- before this skill ever touches it.
  Discover them (see "Discover existing nested files" under "Where to
  save it") and link to them from the root's Project map exactly as you
  would one you just created. Never assume the graph is empty, or that
  it only contains what you're about to write.
- **This repo you're reading this skill from is itself the worked
  example** -- its root `AGENTS.md` covers repo-wide layout and
  conventions and links out to `mcp-server/README.md`, `README.md`'s
  "Adding a toolset," and each toolset's own `README.md`, rather than
  inlining any of their content. When drafting for a target project,
  generalize this exact pattern to whatever that project's own doc set
  already is -- don't assume it has the same file names.

## Output structure

There is genuinely no fixed schema -- agents.md's own guidance is "use
any headings you like." The sections below are real-world candidates,
not a checklist to fill mechanically: **include a section only when the
project has something real to say there, and omit it rather than pad it
with generic advice.** For a monorepo's nested files, most sections
below apply to that one subproject only; the root file mainly needs
Project map plus whatever is genuinely repo-wide.

- **Overview** -- one or two sentences: what this project/subproject is.
- **Setup commands** -- how to install dependencies / provision the dev
  environment, verified against the repo's own manifest/lockfile.
- **Dev environment / running it locally** -- how to actually run the
  thing during development, if that's a meaningful step for this
  project.
- **Testing instructions** -- the real command(s) to run the test
  suite, and any subset-running convention worth knowing. Load-bearing:
  ask rather than omit or invent if you can't verify a real test
  command exists.
- **Build / lint / format commands** -- only the ones that actually
  exist and are actually run (e.g. in CI), not a generic "run your
  linter."
- **Architecture** -- major components and how they relate, how a
  request or a unit of data actually flows through the system, why a
  key structural decision looks the way it does. If the project already
  has an `ARCHITECTURE.md` or equivalent design doc, link to it instead
  of restating it -- this section is then just a one-line pointer, not
  a rewrite. If there's no such doc and the architecture isn't clear
  from the code itself, ask rather than invent a plausible-sounding one
  (see "Input" above).
- **Code style and conventions** -- only conventions you can point to
  (an actual linter/formatter config, a documented pattern already
  followed consistently in the code) -- not generic best-practice advice
  that would apply to any project in the language. Ask rather than
  guess when it isn't clearly one or the other.
- **Commit / PR instructions** -- only if the project has a real,
  checkable convention (a `CONTRIBUTING.md`, a commit-hook, a PR
  template) -- link to it rather than restating it in full.
- **Security / credential handling notes** -- only if there's a real
  rule an agent could otherwise get wrong (e.g. "credentials only from
  env vars, never hard-coded" -- state it if it's actually the
  project's rule, don't invent one).
- **Project map** (the graph itself, for a monorepo root or any project
  with docs worth pointing to) -- one line per subproject or major doc:
  what it is, and the relative path to its own `AGENTS.md`/`README.md`.
  Include every nested `AGENTS.md` discovered in the whole-tree search
  (see "Discover existing nested files" above), not only the ones this
  run creates. This section **is** the cross-referencing structure, not
  a summary of it -- keep each line to a pointer, not a paragraph.

Setup commands, Testing instructions, Architecture, and Project map
(when a monorepo split applies) are the sections most worth getting
right -- ask rather than invent when you can't verify them. Everything
else is genuinely optional per project.

## Style

- Write for a coding agent skimming under context/token pressure: short,
  scannable, imperative sentences -- not prose written for a human
  onboarding over a week.
- Every command must be one you verified against the repo's own config
  -- never a guessed or "generally correct" command.
- Link instead of duplicating -- see "The graph, not a monolith" above;
  this is the skill's central discipline, not a style nicety.
- State only what's true today. Don't record aspirational conventions
  ("we should eventually...") -- that's not what a coding agent needs
  mid-task, and it goes stale the moment it's written.
- For a monorepo, state the "closest AGENTS.md wins" precedence
  explicitly in the root file's Project map intro, so a reader
  understands why the root file doesn't repeat what a nested file
  already says.

## Relationship with other documents

AGENTS.md is orthogonal to the `PRD -> TRD -> RFC/ADR -> Implementation`
pipeline the other doc-generation skills in this repo follow -- it's not
a step feature work passes through, it's a standing onboarding artifact
for a whole project (or subproject), written once and kept current as
the project's real setup changes. It doesn't duplicate what a project's
`README.md` already says for humans, and it doesn't duplicate whatever a
PRD/TRD/ADR/RFC already recorded either -- if one of those exists and
documents something an agent needs (e.g. an ADR explaining why a build
is structured a certain way), link to it from the relevant section
instead of restating its content. Nothing about writing an AGENTS.md
requires any of those other documents to exist first, and nothing about
them requires an AGENTS.md.
