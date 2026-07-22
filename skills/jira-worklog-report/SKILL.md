---
name: jira-worklog-report
description: >-
  Aggregate the current user's logged Jira time over a date range,
  compared against each touched issue's original estimate. Use for "how
  many hours did I log this week", "how much more than estimated did I
  work", "what did I get stuck on recently".
version: 1.0.0
metadata:
  hermes:
    tags: [jira, project-management, worklogs, time-tracking]
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

# Jira: Worklog Report

Read-only. Run from this skill's directory:

```bash
python3 ../jira/scripts/jira_tool.py worklog_report [--since -14d] [--until 2026-07-20] [--max_issues 50]
```

(First-time setup, once per environment: `pip install -r ../jira/requirements.txt`.)

`--since`/`--until` accept a JQL-style relative date (`-14d`, `-2w`) or an
ISO date/datetime; `--since` defaults to 14 days ago, `--until` defaults to
now. Prints one JSON document:

```json
{"since": "-14d", "until": null, "total_logged_seconds": 0,
 "total_original_estimate_seconds": 0, "total_delta_seconds": 0,
 "issue_count": 0, "issues": [{"key": "...", "summary": "...",
 "status": "...", "original_estimate_seconds": null,
 "logged_seconds": 0, "delta_seconds": null, "worklogs": [...]}]}
```

- Only worklogs authored by the current user and started within the
  window are counted -- never sum or estimate from memory, always run
  the command fresh.
- `original_estimate_seconds` (and therefore `delta_seconds`) is `null`
  for any issue with no estimate set. Exclude those issues from an
  "over/under estimate" claim instead of treating a missing estimate as
  zero.
- For "what did I get stuck on", reason over each issue's
  `logged_seconds` vs. `original_estimate_seconds` *and* its worklogs'
  `comment` text -- don't just name the top issue by hours without
  reading what the comments actually say happened.
- Convert `*_seconds` fields to hours/minutes in your response; don't
  make the user do that arithmetic.

If the result contains `"error"`, tell the user what went wrong in
plain language instead of retrying silently or fabricating a result.

See `../jira/README.md` for architecture details and the full
environment-variable table.
