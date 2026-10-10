---
name: glab-file
description: >-
  Reads a file, or lists a directory, from a GitLab project's repository at a
  branch/tag/commit. Use for "show me src/app.py on main", "what's in the
  docs folder of group/repo". Read-only.
version: 1.0.1
metadata:
  category: software-development
  hermes:
    tags: [gitlab, git, repository, read]
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

# GitLab: Read Files

**Read-only.** Run from this skill's directory:

```bash
uv run ../glab/scripts/glab_tool.py get_file --project group/repo --file_path src/app.py --ref main
uv run ../glab/scripts/glab_tool.py get_tree --project group/repo [--path docs] [--ref main] [--recursive]
```

(`uv run` installs the dependencies on first use. Without `uv`, use
`python3` in place of `uv run`, after a one-time `pip install -r ../glab/requirements.txt`.)

`--ref` is required for `get_file` (branch, tag, or commit SHA); for an
MR's version of a file, use the MR's `diff_refs.head_sha` from
`get_mr`. Content is truncated at `--max_bytes` (default 200000) --
check `truncated` in the result before assuming you saw the whole file;
binary files come back with `binary: true` and no content.

If the result contains `"error"`, tell the user what went wrong in
plain language (relay the tool's message) instead of retrying silently or
fabricating a result. When you mention an MR, project, or file, link it
with the `web_url` a tool returned -- never construct a URL yourself.

See `../glab/README.md` for architecture details and the full
environment-variable table.
