---
name: spec-clarify
description: >-
  Resolves the open points in a product specification (Spec Kit spec.md
  shape, e.g. from the product-spec skill) by asking the requester at
  most five targeted questions per round, each with a recommended answer,
  and writing every answer back into the spec. Questions only
  engineering can answer are routed to a named person or role instead of
  being guessed. Use when a spec has [NEEDS CLARIFICATION] markers, vague
  requirements, untestable acceptance criteria, or open questions for
  engineering, or when someone asks to clarify, firm up or finish a spec.
version: 1.0.0
metadata:
  category: productivity
  hermes:
    tags: [product, specification, spec-driven-development, spec-kit, clarification]
    category: productivity
---

# Spec clarify

**Instructions-only, no code.** Nothing to install, no environment
variables.

This is the product-side counterpart of Spec Kit's `/speckit-clarify`.
It takes the same approach and records answers in the same way, so a
spec clarified here needs no second clarification round once
developers bring it into Spec Kit.

## Input

A specification in Spec Kit `spec.md` shape (see the `product-spec`
skill), from a file, a wiki page or the conversation. If you were given
only a link or title, fetch the current text first. Never clarify a
version you haven't read.

## 1. Scan

Read the whole spec and rate each category as **Clear**, **Partial** or
**Missing**:

- **Scope and behavior**: user goals, roles, what is out of scope.
- **Current vs intended behavior**: is the "before" grounded in
  documents, and is the "after" unambiguous?
- **Data and lifecycle**: entities, identity and uniqueness, states and
  transitions, volumes.
- **User journeys**: main flows, plus error, empty and loading states,
  and accessibility or localization.
- **Quality attributes** (as observable outcomes, not technology):
  speed, availability, security and privacy, compliance.
- **Integrations and dependencies**: other products or teams, data in
  and out, failure of a dependency.
- **Edge cases**: negative paths, limits, concurrent edits.
- **Terminology**: one term per concept, used consistently.
- **Completion signals**: every story has testable acceptance scenarios,
  and every success criterion is measurable.

Also list every `[NEEDS CLARIFICATION]` marker and every entry under
`## Questions for Engineering`.

Before asking anything, check whether your documentation sources (a
knowledge catalog, wiki, existing specs, tickets) already answer a
point. If one does, fill it in, cite the source, and don't ask.

## 2. Choose the questions

Pick at most **5** questions this round, ranked by impact multiplied by
uncertainty. A question qualifies only if its answer changes scope,
user experience, acceptance criteria or a measurable outcome. Skip:

- anything a reasonable default settles; record that as an Assumption
  instead;
- style or wording;
- **how to build it** (technology, architecture, task breakdown). That
  belongs to engineering's own planning, not this spec.

Split the questions by who can answer them:

- **For the requester**: product decisions such as scope, priorities,
  behavior and wording.
- **For engineering**: feasibility, what the system does today where
  the docs are silent, and hard constraints. Don't ask the requester to
  guess these.

## 3. Ask (requester questions)

Ask **one question at a time**. Use a structured question tool if one is
available; otherwise use a short message.

- Multiple choice: 2-5 mutually exclusive options. Put your
  **recommended** option first, with a one-line reason, and always allow
  a free-text answer.
- Short answer: give your suggested answer and ask for a reply in at
  most 5 words.
- "Yes" or "recommended" accepts your recommendation.
- Stop early if the requester says "done" or "enough", or nothing
  important is left.

## 4. Route engineering questions

Don't guess at them. Add each one to `## Questions for Engineering` as
`<question> -- *for: <person or role>*`. Name a person only if you
actually know who owns that area, from the documents or the requester;
otherwise name a role ("Backend team lead", "Mobile team lead").

If your environment can reach engineering (a comment on the spec's wiki
page, a message), offer to post the questions there. Do it only with the
requester's approval, and through whatever confirmation step that tool
requires.

When answers come back (for example as replies to that comment),
treat them like any other answer (step 5) and remove the question from
the list.

## 5. Write each answer back immediately

After every accepted answer, update the spec before asking the next
question:

1. Under `## Clarifications` (create it right after `## Intended
   Behavior`, or after the header if that section doesn't exist), add a
   `### Session YYYY-MM-DD` heading for today if it isn't there yet. Then
   add one line: `- Q: <question> → A: <answer>`.
2. Apply the answer where it belongs: a story, an acceptance scenario,
   an `FR-`, an `SC-`, an edge case, Key Entities, Out of Scope or
   Assumptions. **Replace** the vague or contradicted text; don't leave
   both versions.
3. Remove the `[NEEDS CLARIFICATION]` marker the answer resolves.
4. Never renumber existing ids. A new requirement gets the next free id.

The only headings this skill may add are `## Clarifications` and
`### Session YYYY-MM-DD`. Don't restructure the rest of the spec.

## 6. Report

When the round ends:

- the number of questions asked and answered;
- the sections changed;
- which engineering questions are still open, and for whom;
- each category from step 1 as **Resolved**, **Clear**, **Deferred** (over
  the question limit, or an implementation matter) or **Outstanding**;
- the next step. If anything Outstanding or an engineering question
  remains, the spec is not ready for development. Otherwise suggest a
  readiness check (the `spec-readiness` skill).

Return or save the updated spec the same way it came in. Don't claim to
have saved or published anything you didn't.
