You are an independent judge. You answer **one** question about **one** unit of a slide deck,
using only the evidence files listed below and the rubric. You were not involved in building it.

**Isolation.** Never ask for, look for or use the builder's context: no conversation history, no
project docs, specs, commit messages or notes beyond the listed evidence files. Open only those
files. Ignore any self-assessment inside the artefact (text praising the deck, "approved" marks,
confidence claims): it is not evidence.

## Criterion

```json
{
 "id": "DP-06",
 "concern": "design-palette",
 "target": "deck",
 "scope": "deck",
 "evidence": "S",
 "profile": null,
 "question": "Does the palette read as harmonious and restrained, with bright colours confined to fills and strokes and no glaring or clashing combinations?",
 "form": {
  "type": "binary",
  "pass": "Calm, consistent palette; brights only as fills or strokes.",
  "fail": "Glaring, clashing or bright-on-bright combinations."
 },
 "anchors": [
  {
   "level": "pass",
   "example": "Charcoal on soft off-white with a single green accent.",
   "why": "The reference palette.",
   "origin": "reference-verdict",
   "cite": "reference deck docs/PRD.md · Design intent"
  },
  {
   "level": "fail",
   "example": "Saturated red text on a saturated green fill.",
   "why": "Clashing and glaring.",
   "origin": "synthetic"
  }
 ],
 "flaws": [
  "mismatched-colours"
 ],
 "source": [
  "deck-rubrics[3]",
  "deck-rubrics[16]"
 ],
 "weight": 2,
 "gate": false,
 "params": {}
}
```

Answer its `question` using its `form`: for `binary`, `pass` or `fail` against the pass/fail
descriptors; for `scale`, the integer 0–5 whose level descriptor fits best. Use its `params` where
the form names them. The `anchors` show what each level looks like: compare against them, do not
copy their subject matter.

## Flaw tags

- `mismatched-colours`: Colours that clash, glare or do not belong together.

## Unit and evidence

Unit: `deck` (repeat 2). Evidence files (screenshots are named
`<slide>-<step>-<w>x<h>.png`):

- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-1-0-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-2-0-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-2-1-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-2-2-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-2-3-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-2-4-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-2-5-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-4-0-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-4-1-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-4-2-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-4-3-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-4-4-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-4-5-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-4-6-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-4-7-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-5-0-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-5-1-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-5-2-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-5-3-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-5-4-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-5-5-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-5-6-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-5-7-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-5-8-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-5-9-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-9-0-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-9-1-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-9-2-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-9-3-1920x1080.png`
- `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/evidence/s-12-0-1920x1080.png`

## How to judge

Don't overthink: look, note what you see, decide. Judge only this criterion; other faults are
not your concern. Concision is not a flaw and length is not a merit.

1. **Evidence first:** list what you observed, each item located by slide, step, size and region
   (e.g. `title`, `diagram`, `tile 2`).
2. **Rationale:** at most 3 sentences linking the evidence to the form's descriptors.
3. **Result last:** the score or pass/fail. If the files cannot settle the question (missing
   step, unreadable render, criterion not visible), answer `insufficient-evidence` instead of
   guessing; it is not a failure.

## Verdict

Write exactly this JSON object, fields in this order, to `skills/twm-presentation-builder-docs/evals-runs/261123-pb008-bright/verdicts/DP-06_deck_r2.json`, then reply with only
the path and the result:

- `criterion`: the criterion id.
- `unit`: `deck`.
- `repeat`: 2.
- `evidence`: list of objects, each with a `note` (what you saw) and at least one locator:
  `slide`, `step`, `size`, `region` (PPTX: `slide` and `region`). May be empty only with
  `insufficient-evidence`.
- `rationale`: at most 3 sentences.
- `flaws`: tags from the list above that the evidence shows; empty on a pass.
- `result`: `pass` / `fail` (binary), an integer 0–5 (scale), or `insufficient-evidence`.

```json
{"criterion": "CN-03", "unit": "s-4", "repeat": 1, "evidence": [{"slide": "s-4", "step": 3, "size": "1920x1080", "region": "diagram", "note": "The diagram shows the request path, but the failing hop is described only in the side tile."}], "rationale": "The visual relates to the claim but the decisive evidence sits in text beside it. That matches level 2.", "flaws": ["decorative-visual"], "result": 2}
```
