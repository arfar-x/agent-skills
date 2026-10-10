---
name: glab-mrs
description: >-
  Lists GitLab merge requests -- in one project or instance-wide -- by state,
  scope, reviewer, or search text. Use for "my open MRs", "MRs waiting on my
  review", "find the MR about X". Read-only.
version: 1.0.1
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

# GitLab: List Merge Requests

**Read-only.** Run from this skill's directory:

```bash
uv run ../glab/scripts/glab_tool.py list_mrs [--project group/repo] [--state opened] \
  [--scope assigned_to_me] [--reviewer_me] [--search "text"] [--max_results 20]
```

(`uv run` installs the dependencies on first use. Without `uv`, use
`python3` in place of `uv run`, after a one-time `pip install -r ../glab/requirements.txt`.)

`--state` is one of `opened|closed|merged|locked|all`; `--scope` is one of
`created_by_me|assigned_to_me|all`. With no `--project` (and no
`GITLAB_DEFAULT_PROJECT`) the search is instance-wide.

If the result contains `"error"`, tell the user what went wrong in
plain language (relay the tool's message) instead of retrying silently or
fabricating a result. When you mention an MR, project, or file, link it
with the `web_url` a tool returned -- never construct a URL yourself.

See `../glab/README.md` for architecture details and the full
environment-variable table.
