---
name: glab-mr-comment
description: >-
  Posts, edits, or deletes a comment on a GitLab merge request -- a general
  note or an inline comment on a specific diff line (new comments optionally
  as an unpublished draft). Routes to add_mr_note, add_mr_discussion,
  edit_mr_note, or delete_mr_note from what's being asked. Use for "comment
  on MR 42", "leave this note on line 10 of app.py", "fix the typo in my
  comment", "delete that comment". Write operations, gated behind explicit
  user confirmation.
version: 1.1.0
metadata:
  category: software-development
  hermes:
    tags: [gitlab, merge-request, comment, write]
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
    prompt: "Skip the confirm step before posting, editing, or deleting MR comments? (true/false)"
    required_for: optional -- defaults to false (asks before every write)
---

# GitLab: Comment on a Merge Request

**Write, gated.** Run from this skill's directory:

```bash
# (append --confirm only after the user's explicit yes -- see below)
# General comment on the MR as a whole
uv run ../glab/scripts/glab_tool.py add_mr_note --project group/repo --mr_iid 42 \
  --body "Overall looks good." [--draft]

# Inline comment on a diff line (new_line: added/unchanged line; old_line: removed line)
uv run ../glab/scripts/glab_tool.py add_mr_discussion --project group/repo --mr_iid 42 \
  --file_path src/app.py --new_line 10 --body "This can be None here." [--draft]

# Replace an existing comment's text, or delete it (ids from get_mr_discussions)
uv run ../glab/scripts/glab_tool.py edit_mr_note --project group/repo --mr_iid 42 \
  --discussion_id <discussion id> --note_id <note id> --body "Corrected text."
uv run ../glab/scripts/glab_tool.py delete_mr_note --project group/repo --mr_iid 42 \
  --discussion_id <discussion id> --note_id <note id>
```

(`uv run` installs the dependencies on first use. Without `uv`, use
`python3` in place of `uv run`, after a one-time `pip install -r ../glab/requirements.txt`.)

Bodies are GitLab Markdown. Choose the tool from the request: changing
an existing comment's text is `edit_mr_note`, removing one is
`delete_mr_note`; a new comment tied to a file and line is
`add_mr_discussion`; any other new comment is `add_mr_note`.

To edit or delete, first find the comment with `get_mr_discussions` (see
`../glab-mr/SKILL.md`): `--discussion_id` is its discussion's `id`,
`--note_id` the note's own `id`. Never guess either id; if several notes
could match what the user described, list them and ask which one.
Unpublished `--draft` notes can't be edited or deleted here. `--draft` saves an unpublished draft note that only the
token's user sees until they submit their review in GitLab's UI -- use it
only when the user asks.

All four refuse to execute unless run with `--confirm` (enforced in code).
Unless `GITLAB_AUTO_CONFIRM_WRITES=true` is set:

1. Run the command **without** `--confirm` first. It returns
   `"requires_confirmation": true` and a `pending_action` -- for an
   inline comment its `file_path`/`new_line`/`old_line` are the line
   GitLab will actually anchor to, already validated against the MR's
   diff.
2. State exactly what will change and wait for the user's explicit yes:
   for a new comment, the MR, location, full text, and draft or
   published; for an edit, `pending_action`'s `current_body` and
   `new_body`; for a delete, the `body` and `author` being deleted (it
   can't be restored).
3. Only then re-run the same command with `--confirm` appended.

If an inline comment fails because the line is not part of the diff, say
so and ask whether to post a general note referencing `file:line`
instead -- never make that substitution silently. Posting needs a token
with the `api` scope; a 403 usually means it has only `read_api`.

If the result contains `"error"`, tell the user what went wrong in
plain language (relay the tool's message) instead of retrying silently or
fabricating a result. When you mention an MR, project, or file, link it
with the `web_url` a tool returned -- never construct a URL yourself.

See `../glab/README.md` for architecture details and the full
environment-variable table.
