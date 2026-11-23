# PB-025 baseline eval (261123)

**Part 1: the HF example, its bright re-theme and the anchors. Part 2: the two cold builds
(`pitch-solar-coop`, `data-review-bus-reliability`), built from their briefs by fresh agents using
only the skill. Suite roll-up: `261123-baseline.md` (outcome **fail**: every target fails or is
incomplete on at least one gate).** Part 2 is partial: the account's spend limit was reached
mid-run, so the 36 process judges and 7 output judges did not run (see *Part 2* below).

**Calibration: agreement with the presenter is unmeasured until a calibration set exists.** Every score below is a judge's reading of the rubric, never the presenter's judgement. The anchors are the only check on the judges, and they measure leniency, not agreement with you.

## Headline

| Target | Outcome | Gates failed | Overall (coverage) |
| --- | --- | --- | --- |
| `hf-subset` (accepted example, paper-green) | **fail** | DL-02, DP-02 | 0.76 (0.64) |
| `hf-subset-bright` (bright-primaries + PPTX) | **fail** | DL-02 | 0.76 (0.71) |
| anchors (10 decks) | 59/59 gate labels and **19/21 judge labels** matched | as labelled | – |

Both HF decks fail on gates the PRD already lists as *Known findings on the accepted example*: pop-over illustration words below the type floor, and the decorative green on `ok` edges. The bright palette clears DP-02, so that failure belongs to the paper-green palette, not the layout. Apart from the PPTX (below), no gate failed beyond the known findings.

## Flagged items first

1. **Lenient judge, AN-09 · RS-01 (must_fail, judged pass 3/3).** The note names its survey in plain text ("regional commuter survey, 2025") with no link, and all three judges read a named, dated source as "cited". The RS-05 gate does catch the missing link, so the deck still fails. But RS-01's pass descriptor and the AN-09 label disagree on whether an unlinked source counts. **Decide:** tighten RS-01 ("cited" = linked or otherwise locatable), or move AN-09's RS-01 label to must_pass and leave links to RS-05.
2. **Lenient judge, AN-05 · DS-06 (must_fail ≤ 2, judged 3/3/3).** Judges call the crammed reproduction of the rejected draft "consistent and clean, but generic" (level 3). CN-01, CN-03, CN-05, DL-05 and DL-06 already catch the clutter on the same slide. **Decide:** sharpen DS-06 levels 2 and 3 (e.g. "any slide crammed or restating its diagram caps the deck at 2"), or relabel.
3. **RS-02 @ hf s-4: high spread (pass 2, fail 1).** One judge reads the fact tile "no agent messages survive" as overclaiming METR's hedged "likely" and widening "board activity" to all messages. Worth your eye: a one-word hedge on the tile would settle it.
4. **CN-06 @ hf deck: insufficient evidence (2 of 3).** The six-slide subset keeps the parent deck's kicker numbers (01, 02, 04, 05, 09, 12), so judges see "missing" slides and decline to judge the title arc. The third judge passed it. **Decide:** renumber the example's kickers, or accept this as an artefact of a subset.

## hf-subset (`examples/hf-incident/deck.html`, output only)

| Concern | Score | Coverage | Notes |
| --- | --- | --- | --- |
| content | 0.47 | 0.67 | CN-01 and CN-05 fail on s-4; CN-04 over 40 words on s-2/s-4/s-5/s-9 (97 at s-4 step 7); CN-03 s-2 = 3; CN-10 pass |
| research | 1.00 | 0.71 | RS-01, RS-02 (split, above), RS-04, RS-05 pass |
| voice | 1.00 | 0.41 | VC-08 median 5 (5, 4, 5); VC-03, VC-05 pass |
| design-layout | 0.93 | 0.62 | DL-02 gate fails (s-4 steps 1–2, s-5 steps 2–4: illustration words at 15 px @1920); DL-05 s-4 = 4; DL-07 pass |
| design-palette | 0.96 | 0.43 | DP-02 gate fails: s-2 `ok` edges at 2.05:1 |
| design-style | 0.28 | 0.86 | DS-01, DS-03 gates fail (known); DS-02 s-5 fails (orphan last words); DS-04 s-4 fails (1 px hairlines, faint "PUBLIC INTERNET" label); DS-06 = 4 |
| architecture | 1.00 | 0.86 | all deck gates pass; AR-07 missing (no repo) |

The judges' strongest signal on the accepted deck is that **s-4 is too much to take in at a glance** (CN-01 fails 3/3, CN-05 fails 3/3). They see the persistent dated step list beside the scene as restating what the diagram and narration tiles show, and step 3 as adding two ideas at once. This is the presenter's approved design (timeline + scene). So either the criterion misfits the editorial-talk timeline layout, or this is a real finding. **Decide.**

## hf-subset-bright (`deck-bright.html` + PPTX)

| Concern | Score | Coverage | Notes |
| --- | --- | --- | --- |
| design-layout | 0.96 | 0.38 | same DL-02 failure as the paper-green deck (style, not palette) |
| design-palette | 1.00 | 0.71 | DP-01/02/03 gates pass; DP-04 s-4 pass 3/3; DP-06 pass 3/3 |
| design-style | 0.28 | 0.86 | DS-05 s-9 **fails 3/3**: the insights backdrop blur makes the scene unrecognisable even at step 0; DS-04 s-4 fails (hairlines); DS-06 = 4 |
| architecture | 1.00 | 0.86 | pass |
| pptx | 0.69 | 0.88 | PX-01 s-5 fails (17 illustration words not native text, no picture fallback); PX-03 fails (8 literal colours equal to theme colours, e.g. `#F1F3F4`, `#FFFFFF`); PX-05 fails (356 shape opacities not declared in the emitter report); PX-02/04/07/08/09 pass; PX-06 missing (no renderer) |

The PPTX was emitted, validated and re-flowed into python-pptx's default template without error (`evidence/deck-bright-reflowed.pptx`). The DS-05 result differs from the earlier `261123-pb008-bright` run, where s-9 passed with high spread. This run gave judges every step at both sizes.

## Anchor judge accuracy (the lenient-judge check)

Judges ran only on each anchor's labelled `S`/`T` criteria, one unit each (the slide its label names), k = 3. Full table: `anchors/accuracy.md`.

| Anchor | Criterion | Label | Median | Match |
| --- | --- | --- | --- | --- |
| AN-00 | DP-04, DL-07, CN-05, VC-01, RS-01, RS-03 | must_pass | pass ×6 (all 3/3) | 6/6 |
| AN-02 | DS-04 | must_fail | fail (pass, fail, fail) | yes |
| AN-03 | VC-01 | must_fail | fail 3/3 | yes |
| AN-04 | RS-01, RS-03 | must_fail | fail 3/3 each | 2/2 |
| AN-05 | CN-05, CN-01, DL-06 | must_fail | fail 3/3 each | 3/3 |
| AN-05 | CN-03, DL-05 | must_fail | 1, 2 | 2/2 |
| AN-05 | DS-06 | must_fail | **3** | **no** |
| AN-05 | RS-03 | must_pass | pass 3/3 | yes |
| AN-06 | DL-07 | must_fail | fail 3/3 | yes |
| AN-06 | RS-03 | must_pass | pass 3/3 | yes |
| AN-07 | DP-04 | must_fail | fail 3/3 | yes |
| AN-09 | RS-01 | must_fail | **pass 3/3** | **no** |

**19/21 judge labels matched; 59/59 gate labels matched.** Judges were unanimous on 20 of 21 units, and the one split (AN-02 DS-04) still landed right. Both misses are lenient (a must_fail passed), not over-strict: no clean-control label failed.

## What the calibration line means here

Agreement with you is unmeasured. The anchors show the judges are mostly not lenient on planted flaws, but two criteria (RS-01, DS-06) pass flaws their labels say must fail. The anchors also say nothing about whether the judges' reading of the accepted deck (e.g. s-4 failing CN-01/CN-05) matches yours. That is what a calibration set would measure.

## What ran

- **Judges: 121 generic subagents** (120 planned + 1 re-dispatch of a judge that wrote no verdict): anchors 63, hf-subset 42, hf-subset-bright 15. Each got one filled `judges/output-judge.md` prompt, kept in each run's `prompts/`. The budget allowed one sampled unit per criterion; units and unjudged criteria are listed in each `manifest.json`.
- **Gates:** `gates.py` on every deck at 1920×1080, 1280×720 and 1288×598; on the bright PPTX via `--pptx`.
- **Evidence:** screenshots at 1920×1080 and 1288×598. 1280×720 was skipped for judges to keep the evidence small; the gates still checked it. Screenshots are git-ignored and regenerable (see each `.gitignore`).

## Protocol and tooling defects found

1. **No text extractor.** EVAL.md §2 asks for per-slide text (title, body, notes, sources) for `T` judges, but the skill ships no tool. This run carries its own (`extract_text.py`).
2. **No anchor-accuracy tool.** The anchors exist to produce a match table, but nothing computes it. This run carries `accuracy.py`.
3. **One deck per run folder.** Deck-scoped verdicts are named `<crit>_deck_r1.json`, so several anchors cannot share a run folder; each anchor got its own sub-run.
4. **PX-06 can't run without LibreOffice.** PPTX.md names `soffice`, and EVAL.md has no fallback and no "missing" note for it. It is reported missing.
5. **Large deck-scope evidence lists get sampled.** Two judges said they opened only 10–14 of 30 screenshots (CN-10, DS-06). A contact sheet or a cap per deck-scope criterion would fix this.
6. **Gated `S`/`T` criteria left unjudged make a run "incomplete".** Judging only labelled criteria on anchors leaves the RS-01/RS-02 gates missing on most anchors, so their outcome reads `incomplete`. Harmless here, but the wording invites misreading.
7. **PPTX emitter gaps** (from the gates): illustration text on s-5 is neither native text nor a picture (PX-01); some fills are written as literal hex equal to theme colours (PX-03); the emitter report does not declare shape opacity, so PX-05 counts 356 effects as undeclared.

## Part 2 · cold builds

Both builders finished on their own: every spec red → green → done, layout guard clean at all three
sizes, screenshots looked at, docs and decisions recorded for the absent presenter
(`*.bundle` = each build's full git history; `COLD-BUILD-FEEDBACK.md` = the 17 skill defects they
reported, since fixed under PB-027). 71 output judges ran (k = 3); gates ran on deck, repo and (data
review) PPTX.

| Build | Outcome | Gates failed | Overall (coverage) | Process (D) |
| --- | --- | --- | --- | --- |
| `pitch-solar-coop` (7 slides) | **fail** | RS-02 (judged) | 0.85 (0.62) | PR-01, 03, 09 pass · PR-02 fail · PR-04 8/9 |
| `data-review-bus-reliability` (8 slides, bar chart, merged `AGENTS.md`) | **fail** | RS-02 (judged), DP-02 | 0.85 (0.63) | PR-01, 03, 04, 09 pass · PR-02 fail |

**What the judges and gates found**

- **Unsupported claims (RS-02, a gate) on both builds.** Pitch s-2: the title states the 40% daylight
  share while the slide shows £612 (CN-03 = 1, 3/3). Data review s-4: the Insight says routes 12 and
  14 "account for almost all of the network's fall", which the pack doesn't support; s-7 fails too.
  This is the builders over-reaching their sources, the failure the skill most needs to prevent.
- **PR-02 fails on every spec in both builds.** The gate re-runs each red commit and requires every
  new test to fail *on an assertion*. The builders' red tests mostly fail on errors and timeouts
  (elements not yet in the deck), and a few already pass at red. Either the process part should
  teach "red = assertion failure" more firmly (e.g. assert presence before waiting), or the gate is
  stricter than the presenter wants. **Decide.**
- **Word caps (CN-04)** exceeded on 3 of 7 pitch and 5 of 8 data-review slides: both were built
  before PB-027 defined "visible words".
- **Data review only:** DP-02 (a chart stroke below 3:1), DS-01 (chart text off the type scale) and
  RS-05 (an unlinked source): all built before PB-027 added chart parts and the unlinked-source
  form. CN-06 fails 3/3: the extracted title order doesn't read as an argument.
- **Strong points:** palette and architecture ~1.0 on both; voice 0.92–0.93; layout 0.94–0.96; the
  data-review PPTX passes every PX gate; the data-review builder merged an existing `AGENTS.md`
  without overwriting it and followed its house rules.

**Not run (spend limit):** process judges PR-05, PR-06, PR-07, PR-08, PR-10 and DP-07 (×3, both builds)
and 7 output judges. Each has a filled prompt in `<build>/prompts/`, listed in `dispatch.tsv`;
reasons are recorded in each manifest's `not_judged`. Re-dispatch them, then re-run
`aggregate.py` on the build runs and the suite.

**How the cold builds compare with the gold deck:** they score higher overall (0.85 vs 0.76) because
they are simpler and avoid the HF deck's known findings, but both fail the sourcing gate the HF deck
passes: the skill transfers its look and process well; its sourcing discipline less so.

## Open questions for the presenter

1. Known findings (PRD): fix, accept as exceptions, or change the criterion for DL-02 pop-over words, DP-02 green `ok` edges, the CN-04 word budget on build-up slides, and DS-03 looping "tries"?
2. s-4 fails CN-01 and CN-05 with every judge: is the dated step list beside the scene a design you want the rubric to accept (change the CN-05/CN-01 anchors), or a finding to act on?
3. RS-01 and AN-09: does an unlinked but named source count as cited?
4. DS-06 levels: should a crammed slide cap the deck's craft score at 2?
5. The bright palette's s-9 backdrop blur: too heavy (3/3 judges), or intended?
6. Renumber the HF subset's kickers so its title arc reads as complete?
7. PR-02: tighten the process part (red tests must fail on an assertion) or relax the gate?
8. RS-02 failed on both cold builds: should the process add a claim-to-source check before a done
   flip (e.g. a T judge on RS-02 as part of the definition of done)?
9. Approve re-dispatching the 43 unrun judges (cost: ~43 subagent calls)?

