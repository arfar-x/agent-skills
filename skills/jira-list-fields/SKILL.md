---
name: jira-list-fields
description: >-
  Enumerate every field this Jira instance knows about, including custom
  fields (id, name, whether it's custom). Use to discover a custom
  field's ID by its display name -- e.g. finding "Figma Link" so it can
  be requested via jira-issues' fields option -- before answering
  questions that depend on an instance-specific field.
version: 1.0.0
metadata:
  hermes:
    tags: [jira, project-management, fields, discovery]
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

# Jira: List Fields

Read-only. Run from this skill's directory:

```bash
python3 ../jira/scripts/jira_tool.py list_fields
```

(First-time setup, once per environment: `pip install -r ../jira/requirements.txt`.)

Prints a JSON list of every field Jira knows about:
`[{"id": "customfield_10056", "name": "Figma Link", "custom": true}, ...]`.

Use this to find a custom field's `id` by matching its `name` (case-
insensitively, and try obvious synonyms -- "Figma", "Figma Link", "Design
Link" -- since the exact label varies per instance) before asking
`jira-issues`/`search` for it via `--fields customfield_10056`. Never
guess or hardcode a `customfield_NNNNN` id without confirming it here
first -- IDs are not portable across Jira instances.

If the result contains `"error"`, tell the user what went wrong in
plain language instead of retrying silently or fabricating a result.

See `../jira/README.md` for architecture details and the full
environment-variable table.
