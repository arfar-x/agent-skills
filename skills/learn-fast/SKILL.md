---
name: learn-fast
description: >-
  Explains a topic as a compressed mental model rather than an
  information dump. Selects the highest-leverage concepts, makes
  mechanisms and causal structure explicit, anchors new ideas to what
  the user already knows, uses prediction and retrieval when they add
  learning value, corrects the most consequential misconception, and
  expands depth one branch at a time. Use when the user asks to
  understand, learn, or be taught something ("explain X", "how does X
  work", "why does X happen", "teach me X", "I keep mixing up X and
  Y"), not for task execution, lookups, code changes, recommendations,
  or verdicts.
version: 1.0.0
metadata:
  category: productivity
  hermes:
    tags: [learning, explanation, teaching, mental-models]
    category: productivity
---

# Learn fast

Optimize for **mental-model change per unit of attention**. The user
should read a little and come away able to **reconstruct, apply, and
extend** the idea -- not merely recognize it as familiar.

This governs how an explanation is shaped, never what is true.
Simplify aggressively, but never into something materially false:
preserve uncertainty, conditions, exceptions, and qualifications when
removing them would distort the model.

## When this applies

A request to understand something -- a mechanism, a distinction, a
concept offered as a bare topic name -- rather than a request to get
something done.

Not for task execution, factual lookup, code changes, recommendations,
or verdicts; those want a direct answer, not a lesson. When a request
mixes both ("why is this slow, and fix it"), answer directly first and
teach only if the user reaches for the why.

## 1. Select the highest-leverage knowledge

Use the **80/20 principle as a selection heuristic**. Ask: *if the user
retained only a fraction of this topic, which concepts would produce the
most understanding and unlock the most learning afterward?*

Prioritize:

* core concepts
* causal mechanisms
* structural relationships
* high-degree concepts that many others depend on
* distinctions that prevent predictable confusion
* the most consequential misconception
* examples that reveal general principles

Cut:

* trivia
* redundant restatement
* low-leverage details
* long enumerations
* unnecessary history
* edge cases unless relevant to the user's goal

Do not force every topic into an arbitrary 20% of its content. The rule
determines **what to teach first**, not a fixed word count.

## 2. Build a mental model, not a fact list

An explanation should make the user able to answer: what is it, how does
it work, what causes what, what is it *not*, and why does it matter.

Prefer relationships over isolated facts. When mechanism is central,
expose its structure -- `A → B → C`, `input → process → output`,
`X ≠ Y` -- so the user can regenerate the explanation from its
relationships rather than memorize disconnected statements.

## 3. Anchor new knowledge to existing knowledge

New structure is easier to encode when attached to an existing one:
**known → bridge → new**. Infer prior knowledge from the conversation,
the user's terminology, questions, and demonstrated competence, and
avoid explaining what they clearly already understand.

Lead with **meaning**, then introduce the technical term
(`concept → name`, not `name → definition`). Use analogies when they
provide a strong structural mapping -- but an analogy is a model, not
reality, so state where it breaks when the difference matters.

## 4. Compress meaning, not merely words

The objective is **fewer cognitive operations to reach understanding**,
not simply fewer words. A dense paragraph that naturally builds one
coherent model is better than several terse fragments the user must
mentally assemble.

Prefer **semantic density with syntactic simplicity**: rich meaning,
familiar wording, short-to-medium sentences, one conceptual move at a
time, minimal unnecessary jargon.

Every sentence should earn its attention by doing at least one of these:

* creating a representation
* connecting concepts
* explaining a mechanism
* establishing causality
* drawing a distinction
* correcting a misconception
* improving retrieval
* enabling transfer

If it does none of these, cut it.

## 5. Use prediction when it creates useful surprise

When a mechanism is counterintuitive or consequential, let the user
predict before revealing the explanation: **prediction → outcome →
explanation of the gap**. Ask something like "what would you expect to
happen if X doubled?", then reveal the result and explain **why the
intuition was or wasn't correct**. This is most valuable when it creates
a meaningful prediction error -- a mismatch between what the user
expects and what the model predicts.

This one pauses the explanation: ask, then stop and let the user answer
before revealing the outcome, because the gap between their prediction
and the result is the lesson. Asking and immediately answering yourself
defeats it, so when the user wants a single self-contained explanation,
skip prediction rather than staging it rhetorically. Do not force it
into straightforward explanations.

## 6. Use contrast to define concepts

When concepts are easily confused, establish the boundary early --
**X ≠ Y** -- then explain the smallest distinction that generates the
important differences. When the user's intuitive model is likely to
mislead, prefer **common intuition → accurate model → why the intuition
fails**. Treat misconceptions as natural approximations, not errors
deserving correction for its own sake.

## 7. Use one example that carries structure

Prefer one strong example over several weak ones, following **example →
underlying principle → transfer**. The example should reveal the
mechanism rather than merely decorate the explanation; showing where the
same pattern appears in another context converts it from an
illustration into a reusable mental structure.

## 8. Separate encoding from retrieval

Reading creates an initial representation; retrieval tests whether that
representation can be reconstructed. For high-value concepts,
occasionally activate retrieval with one short prompt:

* **Predict:** what happens if X changes?
* **Retrieve:** explain the idea in one sentence.
* **Transfer:** where else does this pattern appear?

Unlike section 5's prediction, these close an explanation rather than
pausing it -- offer one and let the user take it up or ignore it,
without waiting. Use at most one, and do not turn every explanation into
an exercise: the user should primarily feel they are **consuming
knowledge**, not completing homework.

## 9. Expand depth one branch at a time

Start with the smallest model that makes the topic useful, then expand
only the branch relevant to the user's next question: **core → structure
→ mechanism → application → nuance**. Track what has already been
established and build on it; do not restart from the beginning unless
the user's understanding requires it.

Add nuance when it prevents a meaningful misconception, changes the
conclusion, is required by the user's goal, or would otherwise let the
simple model become misleading -- not merely to demonstrate
sophistication.

## 10. Maintain accuracy under compression

Compression must preserve the causal and conceptual structure that makes
the explanation true. Never:

* turn correlation into causation
* turn a tendency into a universal rule
* remove a condition that changes the conclusion
* present an analogy as literal reality
* hide meaningful uncertainty
* simplify a technical distinction into a false equivalence

When necessary, use **simple model → one important qualification**,
without overloading the user with every qualification.

## Response shape

A default, not a template. Skip any part that does not earn its
attention cost -- a two-sentence answer that completely lands the model
is a complete answer.

1. **The model** -- 2-4 natural sentences that establish the idea
   immediately.
2. **The structure** -- the mechanism, causal chain, contrast,
   hierarchy, or relationship that makes the model work.
3. **Precision** -- a short paragraph that makes the model accurate and
   removes the most important ambiguity.
4. **Example** -- one, when it materially improves understanding.
5. **Snapshot** -- when the concept is worth carrying forward, close
   with **Core:** one sentence, **Structure:** one compact relationship.

Do not narrate the selection process. The learning architecture should
be visible in the explanation itself.
