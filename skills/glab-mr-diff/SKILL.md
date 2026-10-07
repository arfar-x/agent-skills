---
name: glab-mr-diff
description: >-
  Returns the per-file unified diffs of a GitLab merge request, optionally for
  one file. Use for "show me the changes in MR 42" or as the input to a code
  review of a remote MR. Read-only.
version: 1.0.0
metadata:
  category: software-development
  hermes:
    tags: [gitlab, merge-request, diff, read]
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

# GitLab: Merge Request Diff

**Read-only.** Run from this skill's directory:

```bash
python3 ../glab/scripts/glab_tool.py get_mr_diff --project group/repo --mr_iid 42 [--file_path src/app.py]
```

(First-time setup, once per environment: `pip install -r
../glab/requirements.txt`.)

Each file entry has `old_path`, `new_path`, and a unified `diff` of
hunks. GitLab may omit the diff of a very large file -- an entry with an
empty `diff` for a changed file means you must read it another way
(`get_file` at the MR's head SHA), not that it is unchanged.

If the result contains `"error"`, tell the user what went wrong in
plain language (relay the tool's message) instead of retrying silently or
fabricating a result. When you mention an MR, project, or file, link it
with the `web_url` a tool returned -- never construct a URL yourself.

See `../glab/README.md` for architecture details and the full
environment-variable table.
