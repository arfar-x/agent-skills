---
name: glab
description: >-
  GitLab (self-hosted or gitlab.com) assistant. Answers questions like "what's
  in MR 42", "show me src/app.py on main", "what MRs are waiting on my
  review", and posts, edits, or deletes general or inline comments on merge
  requests -- by calling
  structured GitLab tools and reasoning over their JSON output, never by
  guessing or inventing repository, file, or MR content. Use whenever the
  user asks about a GitLab project, file, or merge request.
version: 1.2.0
metadata:
  category: software-development
  hermes:
    tags: [gitlab, git, merge-request, code-review, tools]
    category: software-development
    requires_toolsets: [terminal]
required_environment_variables:
  - name: GITLAB_BASE_URL
    prompt: "GitLab base URL (e.g. https://gitlab.mycompany.com)"
    required_for: all functionality
  - name: GITLAB_TOKEN
    prompt: "GitLab personal access token (scope read_api for read-only use, api to post MR comments)"
    required_for: all functionality
    sensitive: true
  - name: GITLAB_DEFAULT_PROJECT
    prompt: "Default project (numeric id or group/project path), if you mostly work in one"
    required_for: optional -- used when --project is omitted; if unset, pass --project yourself
  - name: GITLAB_AUTO_CONFIRM_WRITES
    prompt: "Skip the confirm step before posting MR comments? (true/false)"
    required_for: optional -- defaults to false (asks before every write)
  - name: GITLAB_VERIFY_SSL
    prompt: "Verify TLS certificates? (true/false)"
    required_for: optional -- defaults to true; disable only for trusted internal instances
  - name: GITLAB_TIMEOUT_SECONDS
    prompt: "Per-request timeout in seconds"
    required_for: optional -- defaults to 30
  - name: GITLAB_MAX_RETRIES
    prompt: "Max retries for rate-limited/5xx GET requests"
    required_for: optional -- defaults to 3
---

# GitLab Assistant

## When to use

Any time the user asks about GitLab content: a project's info or
branches, a file or directory in a repository, merge requests and their
diffs and discussions -- or wants a comment posted on a merge request
(including the findings of a code review).

## How it works

A thin CLI wrapper (`scripts/glab_tool.py`) around a typed GitLab REST
client (`lib/glab_client.py`), the same shape
`confluence/scripts/confluence_tool.py` uses. The CLI **only** validates
input, calls GitLab, and prints one JSON document to stdout -- it never
summarizes, explains, or reasons. **All reasoning is your job.**

Run it from this skill's directory:

```
uv run scripts/glab_tool.py <tool> [--flags...]
```

(`uv run` installs the dependencies on first use. Without `uv`, use
`python3` in place of `uv run`, after a one-time `pip install -r requirements.txt`.)

Authentication is a single `GITLAB_TOKEN` (a personal access token --
scope `read_api` to read, `api` to post comments) acting on the user's
behalf; there is no username/password mode.

## Core rules

1. **Always call a tool before answering a GitLab question.** Never
   answer from memory or assumption.
2. **Never invent content.** Every title, diff line, file excerpt, or
   comment you state must come from JSON a tool returned.
3. **Write operations require confirmation.** `add_mr_note`,
   `add_mr_discussion`, `edit_mr_note`, and `delete_mr_note` refuse to
   execute unless run with `--confirm` (enforced in code). Unless
   `GITLAB_AUTO_CONFIRM_WRITES=true`:
   - Run without `--confirm` first, show the user exactly what will be
     posted (MR, file/line for an inline comment, full text, draft or
     published), and wait for an explicit yes. For an edit, show the
     note's current body and the new one (`pending_action`'s
     `current_body`/`new_body`); for a delete, the body that will be
     deleted and its author.
   - Only then re-run the same command with `--confirm`.
   - If a result has `"requires_confirmation": true`, treat it as the
     tool declining to act -- relay `pending_action` and ask.
   - A batch (e.g. several review findings) may be approved in one yes
     only if you listed every comment's full text and location first.
   - Don't post twice to "retry" -- check `get_mr_discussions` first if
     unsure whether a post landed. To fix a posted comment, edit it
     (`edit_mr_note`) rather than posting a correction; a deleted note
     cannot be restored.
   - Take `--discussion_id` and `--note_id` from `get_mr_discussions`
     (a discussion's `id` and one of its `notes[].id`) -- never guess
     them. Both edit and delete fetch the note first, so a wrong pair
     fails before anything changes.
   - **If the write the user asked for fails, never silently
     substitute another write.** E.g. if an inline comment fails because
     the line isn't in the diff, report it and ask before falling back
     to a general note.
4. **Comment bodies are GitLab Markdown**, not HTML or plain text.
5. **If a result contains `"error"`,** relay the real error text so the
   user knows what GitLab rejected -- don't retry silently or invent a
   cause. A 403 on a write usually means the token has only `read_api`.
6. **Link, don't just name.** Results include `web_url`; render MRs,
   projects, and branches as markdown links with it. Never build a URL
   yourself.
7. **Never write ad-hoc code** against the GitLab API or to post-process
   tool output -- use the tools above and reason over the JSON.
8. **Resolve a pasted MR URL, don't ask for its parts.** For
   `https://host/group/sub/repo/-/merge_requests/42`: `--project` is
   `group/sub/repo` (between the host and `/-/`), `--mr_iid` is `42`.
9. **Ask for only what you need.** `get_mr_diff --file_path` narrows to
   one file; `get_file` truncates at `--max_bytes` -- check `truncated`
   before reasoning about a "whole" file.
10. **Remember stable facts, the moment you learn them, in the same
    turn** -- see `README.md`'s "Agent memory" section for what is safe
    to save (a project path's numeric id and default branch, the token's
    username) and what is not (MR state, diffs, discussions, file
    contents).

## Commands

```bash
# Who the token acts as
uv run scripts/glab_tool.py whoami

# Project identity, default branch, URL
uv run scripts/glab_tool.py get_project --project group/repo
uv run scripts/glab_tool.py search_projects --search repo [--membership] [--max_results 20]
uv run scripts/glab_tool.py list_branches --project group/repo [--search feat]

# Repository content at a ref
uv run scripts/glab_tool.py get_tree --project group/repo [--path src] [--ref main] [--recursive]
uv run scripts/glab_tool.py get_file --project group/repo --file_path src/app.py --ref main [--max_bytes 200000]

# Merge requests (read)
uv run scripts/glab_tool.py list_mrs [--project group/repo] [--state opened|closed|merged|locked|all] \
  [--scope created_by_me|assigned_to_me|all] [--reviewer_me] [--search "text"]
uv run scripts/glab_tool.py get_mr --project group/repo --mr_iid 42
uv run scripts/glab_tool.py get_mr_diff --project group/repo --mr_iid 42 [--file_path src/app.py]
uv run scripts/glab_tool.py get_mr_discussions --project group/repo --mr_iid 42

# Comment on a merge request (write, gated -- see rule 3; append --confirm only after the user's yes)
uv run scripts/glab_tool.py add_mr_note --project group/repo --mr_iid 42 --body "..." [--draft]
uv run scripts/glab_tool.py add_mr_discussion --project group/repo --mr_iid 42 \
  --file_path src/app.py --new_line 10 --body "..." [--draft]

# Edit or delete an existing comment (write, gated; ids from get_mr_discussions)
uv run scripts/glab_tool.py edit_mr_note --project group/repo --mr_iid 42 \
  --discussion_id <discussion id> --note_id <note id> --body "..."
uv run scripts/glab_tool.py delete_mr_note --project group/repo --mr_iid 42 \
  --discussion_id <discussion id> --note_id <note id>
```

Edit and delete work on published notes only -- general and inline
alike, since a general note is a single-note discussion. Unpublished
`--draft` notes don't appear in `get_mr_discussions` and aren't covered.

`--project` may be omitted when `GITLAB_DEFAULT_PROJECT` is set.

## Inline comments: which line number?

`add_mr_discussion` takes the line as it appears in the MR's diff:
`--new_line` for an added or unchanged line (the line number in the
head version of the file), `--old_line` for a removed line. The tool
resolves the exact GitLab position (SHAs, old/new line pair) itself and
rejects a line that isn't part of the diff -- only changed lines and
their surrounding context can take an inline comment.

## Reviewing an MR

For "review MR 42", use the `code-review` skill: it fetches the MR
through this toolset (`get_mr`, `get_mr_diff`, `get_file`,
`get_mr_discussions`) and, only if the user asks, posts its findings
back with `add_mr_discussion`/`add_mr_note` under the confirm rule above.
