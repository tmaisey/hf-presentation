# Eval run protocol

How the orchestrating agent (you) runs an eval of a deck, its PPTX and its build process. The
rubric lives in the criterion library (read `evals/CRITERIA.md` first); this part says how to run
it. You orchestrate and never judge: every judgement is made by a fresh judge that sees only the
artefact, the rubric and the anchors.

Two uses: assessing any deck built with the skill, and iterating on the skill against a bundled
brief (then the deck project built from the brief is the target; results never go in the skill
folder).

## 1 · Scope prompt (MUST, before any run)

Ask the user **one question at a time**, inline, each with your recommendation; never a
multi-option picker. Ask before capturing any evidence or dispatching any judge. Record every
answer in the run's `manifest.json` (§6).

1. **Target:** a bundled brief or a deck path? Then confirm the profile (`profiles/<id>.json`)
   that fits the deck type.
2. **Output and/or process:** judge the artefacts (deck, PPTX), the build process (repo history),
   or both?
3. **Concerns:** which of content, research, voice, design-layout, design-palette, design-style,
   architecture, pptx, process? Default: every concern the answer to 2 covers; drop pptx when no
   PPTX exists. The scope narrows concerns, never the profile.
4. **Depth:** gates only (deterministic `D` criteria, cheap) or gates + judges (`S`/`T` too)?
5. **k:** independent judge repeats per criterion and unit (recommend 3; 5 for a release or a
   skill A/B). Gates run once.
6. **Transcripts** (ask only if process is in scope): may Claude Code session transcripts be read
   for this run? Default no. Approval holds for this run only; record it as `transcripts`.

For a skill-version A/B, also ask which two skill versions (A, B) and confirm the same brief for
both; that run is pairwise (§4).

Process evidence is repo artefacts only (git history, docs, SPEC states, tests, outputs incl.
screenshots), plus transcripts when approved. **NEVER** ask the builder to keep, or a judge to
trust, a self-reported process log.

## 2 · Evidence capture

Capture once per run into `evidence/`, before any judge starts; judges read only these files.

- **Screenshots:** every slide × step × review size of the assembled deck (the deck project's
  screenshot tool, or Playwright at the review sizes its `AGENTS.md` names). Name files
  `<slide>-<step>-<w>x<h>.png` so a judge can cite slide, step and size.
- **PPTX renders:** when pptx is in scope, render each PPTX slide to PNG (judges can't open
  PPTX) and keep the `.pptx` for deterministic checks.
- **Text:** per slide, its title, body copy, Insight, notes and sources as extracted text, for
  `T` judges.
- **Repo facts** (process): `git log --stat`, the SPEC file at each commit that flips a status,
  the diff and test files of each spec's red and done commits, and the docs index. Transcripts only
  when approved.

Never strip self-assessment (e.g. a note praising the deck) from the evidence: judges are told to
ignore it, so the artefact stays as shipped.

## 3 · Deterministic gates

Run the deterministic gate runner over the deck and repo for every selected `D` criterion in
scope. It emits verdicts in the judge format (§4) with `repeat` 1 into `verdicts/`. Until the
runner ships, a `D` criterion has no verdict and the report lists it as `missing`; never judge a
`D` criterion with an LLM instead. A failed gate already fails the deck, but still run the judges
the user asked for: the report is for improving the deck.

## 4 · Judge dispatch

Get the rubric: `uv run ${CLAUDE_SKILL_DIR}/evals/criteria.py resolve <profile>`. Keep the
selected `S` and `T` criteria whose concern is in scope.

For each (criterion × repeat), and per unit where the criterion's `scope` is slide, step or spec,
spawn **one generic subagent** (Claude Code: `general-purpose`). **NEVER** a fork or any agent that
inherits this conversation: the judge must not see the builder's context. One criterion per judge;
spawn repeats independently, never one judge scoring twice.

Build each prompt from a template, filling every `{{placeholder}}`:

| Template | For |
| --- | --- |
| `judges/output-judge.md` | `S`/`T` criteria with target `deck` or `pptx` |
| `judges/process-judge.md` | criteria with target `repo` |
| `judges/pairwise-judge.md` | skill-version A/B runs only |

Fill with the criterion's resolved JSON (question, form, anchors, `params`), its flaw tags with
descriptions from `flaws.json`, the unit, the repeat number, the verdict path
(`verdicts/<criterion>_<unit>_r<repeat>.json`, unit slugged) and the list of evidence file paths
for that unit only. Nothing else: no deck PRD, storyboard or chat summary unless the criterion
judges it.

**Pointwise by default.** **Pairwise only for skill-version A/B**, each repeat judged in **both
orders** (`AB`, then `BA` by a separate judge; candidates shown as *first* and *second*, never by
version name). Gates are not pairwise: gate each version pointwise.

A judge writes its verdict file and replies with only the path and result. Re-dispatch (new judge,
same repeat number) any verdict the aggregator rejects.

## 5 · Aggregation and report

`uv run ${CLAUDE_SKILL_DIR}/evals/aggregate.py <run-dir>` validates every verdict (schema, known
and selected criterion, result fits the form, in scope) and writes the report. Its docstring holds
the rules; in short: median of k (binary: majority, tie → fail), insufficient evidence is its own
outcome and never a pass, high spread is flagged, any failed gate fails the deck whatever the
weighted score, a missing gate makes it incomplete, pairwise order disagreement is a tie.

Read the markdown report to the user: outcome, gates, concern scores, then every flagged item
(high spread, ties, insufficient evidence, missing criteria) as the ones needing their eyes. Every
report states that calibration is unmeasured: agreement with the presenter is unknown until a
calibration set exists; say so, never present scores as the presenter's judgement. If a criterion's
question or levels changed since the last run, say the rubric changed.

## 6 · Where results go

In the deck project (never the skill folder), one dated folder per run:

```text
evals/runs/yymmdd-<label>/
  manifest.json              scope answers: label, date (yymmdd), target, profile, concerns,
                             depth, k, transcripts, mode (+ versions for A/B, judge model)
  evidence/                  screenshots, PPTX renders, text extracts, repo facts
  verdicts/*.json            one per gate check or judge call
  yymmdd-<label>.json        report (aggregate.py)
  yymmdd-<label>.md          report for the presenter
```

Runs are dated records: never edit a past run; re-run into a new folder. Add an `evals/` row to the
project index on the first run.
