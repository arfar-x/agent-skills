---
name: code-review
description: >-
  Reviews a git diff (working-tree changes, a commit range, or an
  explicitly named PR/branch/file) for correctness bugs and code-quality
  issues -- wrong conditions, removed invariants, broken call sites,
  duplicated logic, unnecessary complexity, wasted work, fixes at the
  wrong depth, and convention violations -- using eight independent
  review angles, a one-pass verification step per candidate, and a
  capped, severity-ranked report. Also reviews a remote merge request on
  a hosted platform (through that platform's own skill, e.g. `glab` for
  GitLab) and, only when asked, posts the findings back as comments. Use
  when the user asks to review code, review a PR/MR, review this diff, or
  check recent changes for bugs before merging.
version: 1.0.0
metadata:
  category: software-development
  hermes:
    tags: [code-review, quality, correctness, engineering]
    category: software-development
---

# Code Review

**Instructions-only, no code.** Nothing to install, no environment
variables of its own -- this skill runs `git` and searches the codebase
using whatever general-purpose tools you already have, and reports
findings directly in the conversation. It never edits code itself.
Reviewing a *remote* merge request additionally uses a hosting-platform
skill (e.g. [`glab`](../glab) for GitLab) for the MR's metadata, diff,
existing comments, and -- only if the user asks -- posting findings; that
skill carries the credentials, this one never touches them.

## What this is

A structured process for reviewing a diff the way a careful, skeptical
maintainer would: eight independent angles look for candidate problems,
each candidate is checked once against the actual code before being
reported, and the output is a short, ranked list of findings a
maintainer would actually act on -- not a dump of everything that
looked slightly off. Precision matters more than coverage: silence on
a marginal, unconvincing candidate is the right call more often than
including it.

This is not a linter, a test runner, or a style-guide checker. It
reasons about behavior -- what a change does under some input or state
-- and about the two forms of cost cleanup findings describe:
duplicated/wasted/harder-to-maintain code, and violations of a rule the
project has actually written down.

## Input

- **The diff to review.** If the user names a PR/MR (a number, a URL, or
  `!42`), a branch, commit range, or file path, review that. A merge
  request URL or number on a platform you have a skill for follows
  "Remote merge request" below. Otherwise, work out the diff
  yourself (see "Gathering the diff" below). Never ask the user to
  paste a diff you can retrieve yourself.
- Nothing else is required, and nothing else should be invented. If the
  intent behind a change genuinely isn't visible in the diff or the
  surrounding code, say so in the finding rather than guessing what the
  author meant.

## Gathering the diff

1. If the user gave an explicit target (a PR number, branch name,
   commit range, or file path), use that.
2. Otherwise, diff against the upstream tracking branch if the current
   branch has one; if not, diff against the repository's main/default
   branch; if neither resolves, diff against the previous commit.
3. If there are uncommitted changes, or step 1/2 produces an empty
   diff, also diff the working tree and fold those changes into scope
   -- a review commonly runs before anything is committed.

### Remote merge request

When the target is a merge request on a hosted platform and you have a
skill for it (the steps below use `glab`'s subcommands; another
platform's equivalent works the same way), review it as follows. Never
check out or modify the user's working tree to do this.

1. **Resolve the MR.** From a URL, take the project path and MR number
   (for GitLab `https://host/group/repo/-/merge_requests/42` -> project
   `group/repo`, iid `42`). Run `get_mr` for its source/target branches,
   state, and `diff_refs` (`base_sha`/`start_sha`/`head_sha`). If the MR
   is merged or closed, say so and ask whether to proceed.
2. **Get the diff.** If the current directory is a clone of that project
   (its git remote matches the project's `web_url`/path), fetch the MR's
   head ref and diff against its base -- e.g.
   `git fetch <remote> refs/merge-requests/<iid>/head` then
   `git diff <base_sha>..FETCH_HEAD` -- and read surrounding code with
   your normal file tools **at that revision** (`git show FETCH_HEAD:<path>`),
   never from the working tree, which may be on another branch. This
   gives all eight angles full repository context. Otherwise (no clone,
   or the fetch fails), use `get_mr_diff`, and read surrounding code and
   callers with `get_file --ref <head_sha>`; say in the report that
   cross-file tracing was limited to the files you fetched.
3. **Read what's already been said.** Run `get_mr_discussions` and don't
   report a point a reviewer has already raised and that is still open;
   a finding that contradicts a resolved thread needs a stronger case.
4. **Review as usual** -- the eight angles, verification, and output
   below are unchanged. The convention-files angle reads
   `AGENTS.md`/`CLAUDE.md` from the same revision (local clone, or
   `get_file` at `head_sha`).

Line numbers in findings are the **new-side** line in the head version of
the file (or the old-side line, labelled as such, for a removed line) --
the same numbering inline comments use.

Treat the result as the full scope of the review. Don't expand it to
files the diff doesn't touch, and don't narrow it because part of the
diff looks uninteresting.

## The eight review angles

Run each angle below as an independent pass over the diff -- if your
environment can run independent tasks concurrently, do these in
parallel; otherwise work through them one at a time. Each pass surfaces
**up to six candidate findings**, each with a file, a line, a one-line
summary, and a concrete failure scenario (for the three correctness
angles) or a concrete cost (for the other five). Pass every candidate
through to verification, even ones you're only half-confident about --
silently dropping a candidate here is the main way a real bug slips
through unreviewed; let the verify step make that call, not the finder.

**Correctness (three angles):**

1. **Line-by-line scan.** Read every changed hunk, then read the
   function it sits in -- a bug in an *unchanged* line of a touched
   function is in scope, since the change re-exposes it or fails to fix
   it. For every line, ask what input, state, timing, or platform makes
   it wrong: an inverted or off-by-one condition, a null/undefined
   dereference, a missing `await`, a falsy-zero check treated as
   "empty", a wrong-variable copy-paste, an error silently swallowed in
   a catch block, an unescaped regex metacharacter.
2. **Removed-behavior audit.** For every line the diff deletes or
   replaces, name the invariant or behavior it used to enforce, then
   check whether the new code re-establishes it somewhere. A removed
   guard, a dropped error path, a narrowed validation, or a deleted
   test that covered a real case are all candidates.
3. **Cross-file trace.** For each function the diff changes, find its
   callers and its callees. Does the change break a call site -- a new
   precondition, a changed return shape, a new exception type, a
   changed ordering/timing dependency? Does another change in the same
   diff make a call newly unsafe?

**Cleanup (three angles -- quality, not bugs):**

4. **Reuse.** Flag new code that re-implements something the codebase
   already has. Search adjacent and shared modules for the existing
   helper, and name it.
5. **Simplification.** Flag unnecessary complexity the diff adds:
   redundant or derivable state, copy-paste with a slight variation,
   deep nesting, dead code left behind. Name the simpler form that does
   the same job.
6. **Efficiency.** Flag wasted work: redundant computation, repeated
   I/O, independent operations run sequentially where they could run
   concurrently, blocking work added to a hot path or to startup. Also
   flag a long-lived object built from a closure or captured
   environment that holds onto more than it needs -- it keeps the
   entire enclosing scope alive for the object's lifetime, which is a
   real leak when that scope holds anything large; prefer a small
   type that copies out only the fields it actually needs. Name the
   cheaper alternative.

**Altitude (one angle):**

7. **Root-cause depth.** Check whether each change fixes the actual
   cause at the right layer, rather than patching a symptom with a
   special case bolted onto shared infrastructure. A special case
   layered on top of general infrastructure is usually a sign the fix
   isn't deep enough -- prefer, and name, the simpler and more general
   change to the underlying mechanism instead.

**Conventions (one angle):**

8. **Project conventions.** Find the convention files that actually
   govern the changed code -- a repo-root `AGENTS.md`/`CLAUDE.md`, plus
   any nested one in a directory that is an ancestor of a changed file
   (a nested file's rules take precedence over the root's for files
   under it -- this is the same monorepo convention `agents-md`
   generates for). Read whichever exist, then check the diff against
   them. **Only flag a violation you can back with an exact quote of
   the rule and the exact line that breaks it** -- no style
   preferences, no "spirit of the document" inferences. Name the file
   and quote the rule in the finding. If no convention file applies to
   any changed file, this angle produces nothing.

## Verify each candidate

First, dedup: when two or more candidates point at the same
line/mechanism, keep only the one with the most concrete failure
scenario or cost. Then, for each remaining candidate, re-examine it
independently from the angle that raised it -- re-read the diff and the
relevant file(s) with fresh eyes rather than trusting the finder's own
framing -- and settle on exactly one verdict:

- **Confirmed** -- you can name the specific input or state that
  triggers it and the resulting wrong output, crash, or cost. Quote the
  line.
- **Plausible** -- the mechanism is real, but whether it actually
  triggers depends on something you can't verify from the diff alone
  (timing, environment, configuration, a caller you can't see). State
  what would confirm it.
- **Refuted** -- the claim doesn't hold: the code doesn't do what the
  candidate says, or it's already guarded elsewhere. Quote the line
  that proves it, and drop the finding entirely.

Keep only confirmed and plausible findings.

## Output structure

Report the surviving findings as a single markdown list, most severe
first, capped at **eight** findings -- correctness findings outrank
cleanup/altitude/conventions findings when the cap forces a cut. One
entry per finding:

```
### <file>:<line> -- <one-line summary>
**Category:** correctness | reuse | simplification | efficiency | altitude | conventions
**Verdict:** confirmed | plausible

<the failure scenario for a correctness finding (concrete input/state
and the wrong outcome), or the concrete cost for a cleanup/altitude/
conventions finding (what's duplicated, wasted, harder to maintain, or
which rule -- quoted -- is broken)>
```

If nothing survives verification, say so plainly ("No findings
survived verification.") rather than listing a low-confidence candidate
just to have something to show.

## Posting findings to a merge request (optional)

Only when the user asks (e.g. "review MR 42 and post the findings" or
"comment these on the MR") -- reviewing alone never posts anything.

1. List every finding exactly as it will be posted: target
   (`file:line`, new or old side), the comment text, and whether it goes
   inline or as a general note. Write each comment as a short, standalone
   remark the MR author can act on -- the failure scenario or cost, not
   the review process. Include the verdict (confirmed/plausible) so the
   author can weigh it.
2. Post each finding with the platform skill's inline-comment action
   (`glab`: `add_mr_discussion`), and a closing summary, if wanted, with
   its general-note action (`add_mr_note`). Use drafts (`--draft`) only
   if the user asks for them. The platform skill's own confirm gate
   applies: run without `--confirm`, show the user the pending posts,
   get an explicit yes covering the listed comments, then re-run with
   `--confirm`.
3. If a line isn't commentable (not part of the diff), report that and
   ask whether to post that finding as a general note with a
   `file:line` reference instead -- never switch silently.
4. Afterwards, report which comments were posted and link the MR using
   the `web_url` the tool returned.

## Style

- Every finding should be one a maintainer would actually act on --
  when in doubt, leave it out rather than pad the list toward eight.
- Don't restate the whole diff or narrate the eight-angle process in
  the output -- that's how the findings were produced, not something to
  walk the reader through.
- Don't propose or apply a fix unless the user separately asks for
  that -- this skill reports findings, it doesn't change code.
- Never post anything to a remote platform unprompted, and never
  post more than the findings the user saw and approved.

## Relationship with other documents

Orthogonal to the `PRD -> TRD -> RFC/ADR -> Implementation` pipeline
this repo's other document-generation skills form -- this is a
point-in-time check against a diff, not a persisted artifact, and
nothing it produces gets saved to disk (posting findings to a merge
request, when asked, is the one exception, and goes through the platform
skill's own confirm gate).
