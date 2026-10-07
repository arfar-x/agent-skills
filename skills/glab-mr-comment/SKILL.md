---
name: glab-mr-comment
description: >-
  Posts a comment on a GitLab merge request -- either a general note or an
  inline comment on a specific diff line (optionally as an unpublished draft).
  Routes to add_mr_note vs add_mr_discussion from what's being asked. Use for
  "comment on MR 42", "leave this note on line 10 of app.py". Write
  operations, gated behind explicit user confirmation.
version: 1.0.0
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
    prompt: "Skip the confirm step before posting MR comments? (true/false)"
    required_for: optional -- defaults to false (asks before every write)
---

# GitLab: Comment on a Merge Request

**Write, gated.** Run from this skill's directory:

```bash
# (append --confirm only after the user's explicit yes -- see below)
# General comment on the MR as a whole
python3 ../glab/scripts/glab_tool.py add_mr_note --project group/repo --mr_iid 42 \
  --body "Overall looks good." [--draft]

# Inline comment on a diff line (new_line: added/unchanged line; old_line: removed line)
python3 ../glab/scripts/glab_tool.py add_mr_discussion --project group/repo --mr_iid 42 \
  --file_path src/app.py --new_line 10 --body "This can be None here." [--draft]
```

(First-time setup, once per environment: `pip install -r
../glab/requirements.txt`.)

Bodies are GitLab Markdown. Choose the tool from the request: a comment
tied to a file and line is `add_mr_discussion`; anything else is
`add_mr_note`. `--draft` saves an unpublished draft note that only the
token's user sees until they submit their review in GitLab's UI -- use it
only when the user asks.

Both refuse to execute unless run with `--confirm` (enforced in code).
Unless `GITLAB_AUTO_CONFIRM_WRITES=true` is set:

1. Run the command **without** `--confirm` first. It returns
   `"requires_confirmation": true` and a `pending_action` -- for an
   inline comment its `file_path`/`new_line`/`old_line` are the line
   GitLab will actually anchor to, already validated against the MR's
   diff.
2. State exactly what will be posted (MR, location, full text, draft or
   published) and wait for the user's explicit yes.
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
