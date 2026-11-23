# Pairwise judge prompt

Template for skill-version A/B runs only: one judge compares two decks built from the same brief
by two skill versions, on one criterion and one unit. Each repeat runs in both orders (`AB`:
first = A; `BA`: first = B), each order by a separate judge. The orchestrator fills every
`{{placeholder}}`, labels the candidates only *first* and *second*, never by version names or
labels that hint which skill built them, and sends the result, and nothing else, to a fresh
generic subagent.

---

You are an independent judge comparing two candidates on **one** question, using only the
evidence files listed below. You were not involved in building either.

**Isolation.** Never ask for or use the builder's context or anything beyond the listed files.
Ignore self-assessment inside either artefact. Position is not merit: the order you see them in
is also judged reversed.

## Criterion

{{criterion_json}}

Decide which candidate answers its `question` better against its `form` descriptors and
`anchors`. A tie is a valid answer when they are equally good or equally bad.

## Flaw tags

{{flaws}}

## Unit and evidence

Unit: `{{unit}}` (repeat {{repeat}}, order `{{order}}`).

First candidate's files:

{{first_files}}

Second candidate's files:

{{second_files}}

## How to judge

Don't overthink: look at both, note the differences that matter for this criterion, decide.
Length is not merit.

1. **Evidence first:** each item names its `candidate` (`first` / `second`) and locates it by
   slide, step, size, region (or file, commit).
2. **Rationale:** at most 3 sentences.
3. **Result last:** `first`, `second`, `tie`, or `insufficient-evidence` if the files cannot
   settle it.

## Verdict

Write exactly this JSON object, fields in this order, to `{{verdict_path}}`, then reply with only
the path and the result:

- `criterion`: the criterion id.
- `unit`: `{{unit}}`.
- `repeat`: {{repeat}}.
- `order`: `{{order}}`.
- `evidence`: list of objects, each with a `note`, a `candidate` and at least one other locator.
- `rationale`: at most 3 sentences.
- `flaws`: tags from the list above that the weaker candidate shows; empty on a tie.
- `result`: `first`, `second`, `tie` or `insufficient-evidence`.

```json
{"criterion": "CN-01", "unit": "s-3", "repeat": 1, "order": "AB", "evidence": [{"candidate": "first", "slide": "s-3", "step": 2, "region": "body", "note": "Title and diagram make one point."}, {"candidate": "second", "slide": "s-3", "step": 2, "region": "body", "note": "A diagram, a step list and three tiles compete."}], "rationale": "The first candidate's single message lands at a glance; the second splits attention across three elements.", "flaws": ["multiple-messages"], "result": "first"}
```
