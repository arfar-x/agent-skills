---
name: glab-mr
description: >-
  Fetches one GitLab merge request's details (branches, state, reviewers,
  diff_refs) and every discussion thread on it. Use for "what's MR 42 about",
  "what has been said on this MR", or before reviewing/commenting on one.
  Read-only.
version: 1.0.0
metadata:
  category: software-development
  hermes:
    tags: [gitlab, merge-request, read]
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
---

# GitLab: Merge Request Details

**Read-only.** Run from this skill's directory:

```bash
python3 ../glab/scripts/glab_tool.py get_mr --project group/repo --mr_iid 42
python3 ../glab/scripts/glab_tool.py get_mr_discussions --project group/repo --mr_iid 42
```

(First-time setup, once per environment: `pip install -r
../glab/requirements.txt`.)

Given an MR URL like `https://host/group/sub/repo/-/merge_requests/42`,
`--project` is `group/sub/repo` (everything between the host and `/-/`)
and `--mr_iid` is `42`. Discussions include system notes
(`system: true`) -- ignore those when summarizing what people said.

If the result contains `"error"`, tell the user what went wrong in
plain language (relay the tool's message) instead of retrying silently or
fabricating a result. When you mention an MR, project, or file, link it
with the `web_url` a tool returned -- never construct a URL yourself.

See `../glab/README.md` for architecture details and the full
environment-variable table.
