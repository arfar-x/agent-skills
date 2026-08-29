---
name: jira-status
description: >-
  Moves a Jira issue to a new status. Use for "move PAY-123 to Review" or
  "close PAY-123". This is a write operation gated behind explicit user
  confirmation.
version: 1.0.0
metadata:
  category: software-development
  hermes:
    tags: [jira, project-management, tickets, write]
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
  - name: JIRA_AUTO_CONFIRM_WRITES
    prompt: "Skip the confirm step before transitioning tickets? (true/false)"
    required_for: optional, defaults to false (asks before every write)
---

# Jira: Status

**Write, gated.** Run from this skill's directory:

```bash
python3 ../jira/scripts/jira_tool.py transition --issue_key PAY-123 --status Review --confirm
```

(First-time setup, once per environment: `pip install -r ../jira/requirements.txt`.)

`--issue_key` and `--status` (target status or transition name) are
required. This refuses to execute unless run with `--confirm` (enforced
in code, not just prompted).

**`--status` matching is case-insensitive and tolerant of the user's own
wording** -- it resolves against Jira's real transition names and target
statuses by exact match first, then a substring fallback (e.g. `done`
matches a transition to `"Done"`, `review` matches `"In Review"`). When
the user describes the target colloquially ("mark it done", "close it")
rather than quoting Jira's exact status name, **just pass their word
through directly** -- don't ask them to state the exact internal status
name first, and don't spend a call checking `jira-board`/
`jira-kanban-status`/`jira-project-context` just to look up something
this resolution already handles for free.

If it genuinely doesn't match anything, the error message itself lists
every real transition available for that issue (e.g. `"'foo' does not
match any available transition... Available transitions: Done (->
Done), ..."`) -- read the target status straight out of that error and
retry with it, rather than making a separate lookup call or asking the
user to guess again. That list is exactly the kind of project fact
`jira-project-context` asks you to remember -- **save it to persistent
memory in this same turn**, unprompted, so the next transition on this
project doesn't have to fail once just to learn its real statuses. See
`../jira/README.md`'s "Agent memory" section for the full catalog of
what to save.

Unless `JIRA_AUTO_CONFIRM_WRITES=true` is set:

1. State exactly what you're about to do and wait for the user's
   explicit yes.
2. Only then re-run the same command with `--confirm` appended.
3. If the result has `"requires_confirmation": true`, treat that as the
   tool declining to act -- relay `pending_action` to the user and ask,
   don't retry with `--confirm` on your own.

If the result contains `"error"`, tell the user what went wrong in
plain language instead of retrying silently or fabricating a result.

See `../jira/README.md` for architecture details and the full
environment-variable table.
