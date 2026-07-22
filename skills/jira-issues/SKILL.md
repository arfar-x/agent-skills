---
name: jira-issues
description: >-
  Runs an arbitrary JQL search against Jira and returns structured issue
  results. Use for "find issues where...", "which of my tickets haven't
  been updated recently", or any query not covered by a more specific
  Jira skill.
version: 1.0.0
metadata:
  hermes:
    tags: [jira, project-management, tickets, search]
    category: software-development
    requires_toolsets: [terminal]
required_environment_variables:
  - name: JIRA_BASE_URL
    prompt: "Jira base URL (e.g. https://jira.mycompany.com)"
    required_for: all functionality
  - name: JIRA_USERNAME
    prompt: "Jira username"
    required_for: basic auth mode (the default)
  - name: JIRA_PASSWORD
    prompt: "Jira password"
    required_for: basic auth mode (the default)
---

# Jira: Issue Search

Read-only. Run from this skill's directory:

```bash
python3 ../jira/scripts/jira_tool.py search --jql "assignee = currentUser() AND updated <= -14d" [--max_results 100] [--fields customfield_10056]
```

(First-time setup, once per environment: `pip install -r ../jira/requirements.txt`.)

`--jql` is required. Prints one JSON document: structured issue results
matching the query, each including `description`, `components`,
`subtasks` (key/summary/status/issue_type), and `custom_fields` (any
requested field not already broken out by name) by default. Never
invent or fabricate issue data -- everything you state must come from
this JSON.

- `--fields` (optional, comma-separated) requests extra fields *in
  addition to* the always-included defaults -- use it for
  instance-specific custom fields, e.g. a "Figma Link" field. Discover
  its ID first via the `jira-list-fields` skill; never guess a
  `customfield_NNNNN` id.
- For subtask/description/component questions ("which tasks have no
  subtasks", "does this need frontend or backend work"), reason over
  the returned `subtasks`/`description`/`components` yourself -- there
  is no separate classification tool, because "frontend" vs. "backend"
  isn't a fixed Jira field; it's inferred from this data.

If the result contains `"error"`, tell the user what went wrong in
plain language (invalid JQL, permission denied, etc.) instead of
retrying silently or fabricating a result.

See `../jira/README.md` for architecture details and the full
environment-variable table.
