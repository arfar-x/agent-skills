---
name: agents-md
description: >-
  Writes or updates an AGENTS.md file for a target project (or, for a
  monorepo, a root AGENTS.md plus nested per-subproject AGENTS.md files)
  -- the open, tool-agnostic convention (agents.md) that gives a coding
  agent the build/test/architecture/style context a README doesn't.
  Infers the project's real structure from workspace tooling and CI, not
  guesses. Searches the whole project tree for AGENTS.md files that
  already exist in subdirectories and inspects each for staleness or
  gaps -- without mechanically listing every one in the root's Project
  map, since agents already find the nearest one by directory proximity
  -- and asks the user before enhancing any of them or creating a new
  one. A nested AGENTS.md this skill writes stays scoped to its own
  subtree -- it never restates the root file's overview or structure.
  Never invents a command, architecture detail, or convention the
  project doesn't actually have -- asks instead. Use when the user asks
  to write/create/generate/update an AGENTS.md (or CLAUDE.md) file,
  onboard a coding agent onto a codebase, or document build/test/
  architecture/style conventions for agents working in a repo.
version: 1.2.0
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

## Inferring the project's structure

Getting the shape wrong -- treating a real monorepo as one flat project,
or fragmenting a single-language project into nested files "just in
case" -- undermines the whole graph before you've written a word. Ground
the root-only vs. root+nested call in explicit signals, not a guess from
directory names:

- **Workspace/monorepo tooling is the strongest signal.** Check for a
  `package.json` `"workspaces"` field, `pnpm-workspace.yaml`,
  `lerna.json`, `nx.json`/`turbo.json`, a Cargo workspace's `[workspace]
  members` in `Cargo.toml`, `go.work`, or multiple independent
  `pyproject.toml`/`setup.py` roots under one repo. When one of these
  exists, its declared members *are* the real subproject boundaries --
  don't independently guess boundaries from directory names when the
  repo already states them in config.
- **Directory conventions (`packages/`, `apps/`, `services/`, `libs/`,
  `cmd/`) are a hint, not proof.** Confirm each candidate actually has
  its own manifest/lockfile, its own build/test setup, or already its
  own `README.md`/`AGENTS.md` before treating it as an independent
  subproject -- a `packages/` folder whose contents all share one root
  manifest and one root test command is not a workspace.
- **Independent CI jobs** (a workflow matrix keyed by directory, or
  separate workflow files per subproject) confirm a subproject is
  actually built/tested independently, not merely organized into its
  own folder.
- **This repo is the worked example for the signal, not just the
  output.** `skills/<toolset>/` bundles are independently
  `pip install`-able and independently tested (`cd skills/<toolset> &&
  pytest`) -- that combination (own dependencies, own test command) is
  exactly what earns a subdirectory its own nested `AGENTS.md`; a
  subdirectory that only has its own *files*, not its own *build/test*,
  usually doesn't.
- **If none of the above signals are present** -- one shared manifest,
  one shared test command, no per-directory CI -- it's a single-stack
  project regardless of how many subdirectories it has. Don't fragment
  it just because it "feels" large; see "Monorepo -- surface where
  nested files would help" below for what to do when signals genuinely
  are present.

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
3. **Discover existing nested files -- inspect them, but don't
   mechanically list or rewrite them.** From the whole-tree search in
   "Input" above, you already have every `AGENTS.md` that exists
   anywhere under the target root, at any depth -- not just ones this
   skill wrote. Each one already defines a **context scope**: per
   agents.md's precedence rule ("the closest AGENTS.md file to the file
   being edited takes precedence"), a nested file's instructions govern
   every file at or below its own directory, up to the next nested file
   that's closer to the file being edited (or up to the root file, if
   nothing closer exists). Because that lookup happens automatically by
   directory proximity -- an agent working inside a subdirectory finds
   its nested file without the root file needing to point to it -- treat
   discovery as inspection, not automatic inclusion:
   - **Don't mechanically add every discovered nested file to the
     root's Project map.** List one there only when it's for a
     subproject or component substantial enough that someone *browsing
     the root file* genuinely benefits from knowing it exists up front
     -- the same bar used for proposing a brand-new nested file below --
     not as a complete index of everything the search turned up.
   - **Read each one anyway**, to understand the scope it already
     covers and to notice whether it looks like it needs enhancement --
     stale commands, sections this skill's standard structure would
     otherwise cover but that are missing, or content that no longer
     matches the directory's actual current structure.
   - **Never edit a discovered nested file as a side effect of the
     current task.** If any look like they need enhancement, tell the
     user what you found -- which files, what's stale or missing -- and
     ask whether they'd like you to update them too, as a separate,
     explicit step. Don't fold that work into the current request
     unprompted, even when the fix looks obvious.
   - **Treat its directory as an already-claimed scope** when deciding
     whether a *new* nested file is warranted elsewhere (below) --
     don't propose a new nested file for a subdirectory that a
     discovered file already covers, unless that subdirectory is itself
     an independent subproject deep enough to deserve its own, more
     specific file (closest-file-wins still applies among nested
     files, not just between root and nested).
   - If a discovered nested file's own scope is ambiguous (it's unclear
     which directories it's meant to govern, or two nested files
     appear to overlap), ask the user rather than guessing a boundary.
4. **Monorepo -- surface where nested files would help, then ask before
   writing any.** When "Inferring the project's structure" above turns
   up genuinely independent subprojects (their own build/test/deploy,
   own language or stack, or already their own `README.md`) that aren't
   already covered by a file discovered in step 3, compile the
   candidates with a one-line reason each (e.g. "own `package.json` +
   test script, no `AGENTS.md` yet") -- see "The graph, not a monolith"
   below for the shape -- and present the list to the user before
   creating any of them. Per agents.md's own stated precedence rule,
   "the closest AGENTS.md file to the file being edited takes
   precedence," so each subproject gets its own file rather than one
   giant root file trying to cover all of them. Don't fragment a
   single-stack project into nested files just to force the pattern --
   a plain single-language project gets one root `AGENTS.md`, full
   stop. The confirm-before-creating rule applies to every proposed
   nested file, not just the ambiguous ones -- an unambiguous signal is
   a reason to propose it confidently, not a reason to skip asking.

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
  save it") and account for all of them when deciding what the root
  file still needs to say and where new nested files are still needed --
  surfacing the substantial ones in the root's Project map by the same
  judgment as any other candidate, not as a mechanical index. Never
  assume the graph is empty, or that it only contains what you're about
  to write.
- **A nested file stays scoped to its own subtree -- it is not a
  shrunk copy of the root file.** When the target of this run is a
  subdirectory's own `AGENTS.md` rather than the root, assume the
  reader already has the root file's Overview, repo-wide setup, and
  overall structure loaded -- an agent reaches the nested file precisely
  because it's already working in that subtree, closest-file-wins style
  -- so don't restate any of that. Document only what's specific to, or
  different within, this directory or feature: its own build/test steps
  only if they differ from the root's, its own architecture within the
  larger system, its own conventions. If a nested file's real content
  would just repeat what the root already says, that's a sign this
  directory doesn't need its own file at all -- say so and fold whatever
  it has back into the root instead of creating a near-duplicate.
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
below apply to that one subproject only, scoped as described in "A
nested file stays scoped to its own subtree" above -- don't restate the
root file's Overview or repo-wide structure inside a nested file; the
root file itself mainly needs Project map plus whatever is genuinely
repo-wide.

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
  with docs worth pointing to) -- one line per subproject or major doc
  worth signposting from the root: what it is, and the relative path to
  its own `AGENTS.md`/`README.md`. This lists what a reader browsing the
  root benefits from knowing about up front, not an exhaustive index of
  every nested `AGENTS.md` the whole-tree search finds (see "Discover
  existing nested files" above) -- a nested file an agent is already
  working under gets found by directory proximity whether or not the
  root links to it. This section **is** the cross-referencing structure,
  not a summary of it -- keep each line to a pointer, not a paragraph.

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
