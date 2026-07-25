---
name: jira-track
description: >-
  Tracks what you're working on as the day goes, then turns it into Jira
  worklogs. Use when someone narrates their work rather than naming one
  ticket -- "I'm starting on X now", "two bugs came in, took me an
  hour", "after that I spent 3h on Y", "log my day", "what have I worked
  on today". Finds the matching issues, separates interruptions from
  focused work, and writes the time to Jira one confirmation at a time.
version: 1.0.0
metadata:
  hermes:
    tags: [jira, project-management, worklog, time-tracking, write]
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
  - name: JIRA_DEFAULT_PROJECT
    prompt: "Default Jira project key (e.g. PAY), if you always work on the same project"
    required_for: optional -- scopes issue lookups to the project being worked in
  - name: JIRA_AUTO_CONFIRM_WRITES
    prompt: "Skip the confirm step before logging work / creating tickets? (true/false)"
    required_for: optional, defaults to false (asks before every write)
---

# Jira: Track

**Read + write (writes gated).** Run commands from this skill's directory:

```bash
python3 ../jira/scripts/jira_tool.py now
```

(First-time setup, once per environment: `pip install -r ../jira/requirements.txt`.)

## What this is

The user tells you about their work in pieces, across the day, in
whatever language and order it happens: what they're starting, what
interrupted them, how long something took. Your job is to accumulate an
accurate timeline from those pieces and, at the end, write it to Jira as
worklogs on the right issues.

**The timeline lives in this conversation.** There's no storage tool
holding it -- it's whatever you and the user have established so far in
this chat. That has one consequence you must design around, below.

## 1. Keep a running tally in every reply

End each reply with the day so far, compactly -- one line per stretch:
what it was, when it started, how long. Something like:

```
📋 Today so far (4h)
⏱ 09:30 · 1h · [PAY-96](url) media bugs
⏱ 10:30 · 3h · [PAY-121](url) structured logging
```

This isn't decoration. Restating it is what carries the timeline forward
if earlier turns get summarized away. Two rules follow from that:

- **Never invent or "reconstruct" a stretch you can't actually see** in
  this conversation. If the history looks incomplete (the user refers to
  work you have no record of), say so plainly and ask them to restate
  the day -- don't fill the gap with a plausible guess.
- A stretch with no issue assigned yet still belongs in the tally, shown
  with the user's own words as its label.

## 2. Starting or switching work

Run `now` **first**, before anything else -- you do not otherwise know
the current time, and every later calculation depends on this one being
real:

```bash
python3 ../jira/scripts/jira_tool.py now
```

Record that timestamp against whatever the user called the work. Don't
stall the clock while you look up the Jira issue -- capture the start
time now, resolve the issue afterwards (or at the end of the day). If
something was already in progress, this new start closes it.

## 3. Resolving what they meant to a real issue

The user says "the media thing" or "those logs", not `PAY-96` -- and may
say it in any language. To resolve it:

1. Check what you already know first -- issues already named in this
   conversation, or anything remembered about this project's issues and
   labels. Don't re-search for something you've already resolved today.
2. Then `my_work` (scoped to the current project by default), since it's
   almost always one of their own open issues.
3. Only then a fresh `search` with a JQL `summary ~ "..."` on the term
   they used, scoped to the project.

If several issues match, **ask which one** -- show key, summary and
status for each. Don't pick the first result. If the user's phrase
matches nothing, see the next section.

## 4. When no issue exists

Say plainly that nothing matched, and state what you actually searched
(the project and the term), so the user can correct a wrong term rather
than being told their work doesn't exist. Then **ask whether to create
it**. Only if they say yes:

```bash
python3 ../jira/scripts/jira_tool.py create_issue --project PAY \
  --summary "..." --issue_type Task --confirm
```

Never create an issue on your own initiative just to have somewhere to
put the time.

## 5. Interruptions and ordering -- the part that matters

Work described in the past tense with a duration ("two bugs came in,
took me an hour total") is a **finished stretch inserted into the day**,
not what they're doing now. It interrupted something.

- Place it in the day where their phrasing puts it. "After the media
  work I spent 3h on the logs" means the media hour came first and the
  3h followed it -- not that both ran at once.
- **Stretches never overlap, and the interrupted task is not credited
  the interrupting time.** If they started the logs at 09:00, were
  pulled onto media bugs for an hour, then did 3h of logs, the logs task
  gets 3h -- not 4h, and not "09:00 to now".
- A stated duration wins over one you'd infer from the clock. If they
  say an hour, log an hour, even if the wall clock between two messages
  was ninety minutes -- the gap includes things they didn't mention.
- If the ordering or a boundary is genuinely ambiguous, **ask**. One
  short question is much cheaper than a wrong worklog the user has to
  find and fix later.

## 6. Logging it at the end of the day

When the user asks to log the day (or says they're done):

1. Group the day's stretches by issue and sum each issue's time.
2. Show the whole breakdown first -- per issue: linked key, summary,
   total duration, start time, and the description you propose to log.
   Include any stretch still not tied to an issue as an explicit
   unresolved item.
3. **Resolve the unassigned ones with the user before logging anything.**
   Never log a stretch that isn't tied to a real issue key.
4. Then confirm and log **one issue at a time** -- state that issue's
   entry, wait for an explicit yes, run its command, report the result,
   then move to the next:

   ```bash
   python3 ../jira/scripts/jira_tool.py worklog --issue_key PAY-121 \
     --duration 3h --description "json log support" \
     --date 2026-07-25T10:30:00+03:30 --confirm
   ```

   `--date` takes the full ISO timestamp `now` gave you for that
   stretch's start, so the worklog lands at the real time of day rather
   than whenever you happened to submit it.

Default to **one worklog per issue per day**, summing that issue's
stretches. If the user wants each stretch logged separately (a task
picked up three times shows as three entries), offer it -- but don't
default to it.

If a `worklog` result comes back with `"requires_confirmation": true`,
that's the tool declining to act -- relay `pending_action` and ask;
don't re-run with `--confirm` on your own.

## Related

- Already know the exact issue and duration, and just want it logged?
  `jira-log` routes a single log/edit/delete request without any of this
  day-tracking.
- Correcting something already written to Jira: `jira-worklog-edit` /
  `jira-worklog-delete`.
- Checking what's already logged over a period: `jira-worklog-report`.

If any result contains `"error"`, tell the user what went wrong in plain
language instead of retrying silently or fabricating a result.

See `../jira/README.md` for architecture details and the full
environment-variable table.
