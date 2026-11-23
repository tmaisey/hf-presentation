# Eval criteria and profiles

The eval's rubric, defined once and read by any runner (generic judge subagents now, an API
later). Gates and judge prompts consume it; they never restate a criterion.

| File | Holds |
| --- | --- |
| `criteria.jsonl` | Every criterion, one JSON object per line |
| `flaws.json` | Flaw taxonomy: tag → `{group, description}`; judges get it in the prompt |
| `profiles/<id>.json` | One deck-type profile each: which criteria, how much they weigh, which gate |
| `criteria.py` | Loader and validator (`check`, `resolve <profile>`); run it, don't read it |
| `anchors/anchors.json`, `anchors/an-NN.html` | Deliberately flawed decks + a clean control, each labelled `must_fail`/`must_pass`; judge them like any deck, a judge or gate that passes a `must_fail` is wrong |
| `EVAL.md`, `judges/`, `aggregate.py` | Run protocol, judge prompt templates, verdict validation and aggregation |

Validate after any edit: `uv run ${CLAUDE_SKILL_DIR}/evals/criteria.py check`. A runner gets a
profile's rubric with `uv run ${CLAUDE_SKILL_DIR}/evals/criteria.py resolve <profile>` (JSON list:
each full criterion plus `weight`, `gate`, `params`).

## Criterion schema

Fields **MUST** appear in this order (short, filterable fields first; verbose ones last):

| Field | Values | Meaning |
| --- | --- | --- |
| `id` | `CN-NN` · `RS` · `VC` · `DL` · `DP` · `DS` · `AR` · `PX` · `PR` | Stable; prefix = concern. **NEVER** renumber or reuse an id |
| `concern` | `content` `research` `voice` `design-layout` `design-palette` `design-style` `architecture` `pptx` `process` | The part of the skill it judges |
| `target` | `deck` · `pptx` · `repo` | The artefact the evidence comes from (repo = git history, docs, specs, outputs) |
| `scope` | `step` · `slide` · `deck` · `spec` | One verdict per build step, per slide, per whole artefact, or per spec in the repo history (`spec` only with `repo`) |
| `evidence` | `D` · `S` · `T` | Deterministic code check · screenshot judge · text judge (a text judge may read repo files) |
| `profile` | `null` or a profile id | `null` = generic. Otherwise profile-only: selectable by that profile alone |
| `question` | ends in `?` | What one isolated judge (or check) answers |
| `form` | `{"type":"binary","pass","fail"}` or `{"type":"scale","levels":{"0".."5"}}` | Binary checklist item by default; a 0–5 scale only where the judgement won't decompose, with a distinct descriptor for **every** level. `D` criteria are always binary |
| `anchors` | list of `{level, example, why, origin, cite?}` | Exemplars. Every `S`/`T` criterion needs a pass and a fail (binary) or a ≥ 4 and a ≤ 1 (scale) anchor |
| `flaws` | tags from `flaws.json` | What a failure looks like, in taxonomy terms |
| `source` | `llm-judge[n]`, `deck-rubrics[n]`, `PRD: …`, `reference: …` | Evidence base: numbered sources in the skill's dev research notes, or the requirement it serves |

**Anchor `origin`:** `reference-verdict` (a recorded presenter verdict on the reference deck,
`cite` required: where it is recorded), `reference-deck` (taken from the accepted reference deck,
`cite` its rule) or `synthetic` (invented, generic). Reference anchors are the **only** place the
reference deck's subject matter may appear; every other field stays generic so the library fits
any deck. Anchors calibrate the judge's scale; they are not the presenter's scores.

**Parameters:** a criterion that needs a number reads it from `params.<name>` with a default in
its `form` text (e.g. `CN-04` `max_words`); profiles set the value.

## Adding or changing a criterion

1. Prefer extending an existing criterion; add one only for a judgement no criterion covers.
2. Choose evidence by what can decide it: code if geometry, counts or file facts can; a screenshot
   judge for appearance; a text judge for copy, sources and repo history. Process criteria judge
   repo artefacts only, transcripts only when the user approves them for that run; **NEVER** a
   self-reported log.
3. Write the question for one isolated judge; prefer binary; if graded, describe all six levels.
4. Add anchors (presenter verdicts first, then synthetic), flaw tags (add a tag to `flaws.json`
   only if none fits; every tag must stay in use) and a source.
5. Append with the next free id for its concern, select it in at least one profile, run `check`.
   Changing a question or levels changes the rubric: say so in the next eval report.

## Profiles

A profile adapts the one library to a deck type. It **NEVER** redefines a criterion.

```json
{"id": "pitch", "description": "…", "weights": {"CN-01": 3, "…": 2},
 "gates": ["RS-02", "DL-01"], "params": {"CN-04": {"max_words": 30}}}
```

- `id` = file name. `weights`: the selection; each selected id → integer **1–3** (1 minor,
  2 normal, 3 central to this deck type). Unlisted criteria are not judged.
- `gates`: selected **binary** criteria that must pass; a failed gate fails the deck whatever the
  weighted score (aggregation itself belongs to the eval protocol).
- `params` (optional): values for selected criteria's `params.*`.
- Every profile covers every concern; the run's scope prompt narrows concerns, not the profile.
- The loader rejects an unknown id, a weight outside 1–3, an unselected or graded gate, another
  profile's profile-only criterion, and params for an unselected id.

| Profile | For | Profile-only criteria | Gates beyond the shared core* |
| --- | --- | --- | --- |
| `editorial-talk` | Presenter-driven projected talk, step builds, notes, sourced claims | `CN-10` diagram-led | `RS-01` `DL-02` `DP-02` `AR-02` `AR-03` `AR-05` `PR-01` `PR-04` |
| `pitch` | Persuading a decision-maker towards one ask | `CN-11` arc, `CN-12` ask | `AR-02` `CN-12` |
| `data-review` | Quantitative evidence review; denser slides | `CN-13` charts, `RS-07` context, `DP-08` colour + values | `RS-01` `DP-02` `CN-13` |
| `internal-update` | Routine team status | `CN-14` status first, `CN-15` decisions/owners | `CN-15` |

\* Every profile gates `RS-02` (faithful to source), `DL-01` (no collisions), `DP-01` (text
contrast) and `AR-01` (offline). The profile files are the source of truth; this table is a map.

**Adding a profile:** copy the closest profile file, set `id` = file name, reweight, set gates and
params, add profile-only criteria to the library with `profile` set, run `check`, and add a row
above.
