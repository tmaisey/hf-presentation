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
   that fits the deck type. A bundled brief (index: `evals/briefs/BRIEFS.md`) fixes its profile
   and concerns; build its deck first as that index says.
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

Run the tools from the skill folder (`${CLAUDE_SKILL_DIR}`); paths below are the run folder's.

- **Screenshots:** every slide × step × review size of the assembled deck, at the review sizes
  the deck's `AGENTS.md` names, plus contact sheets of one size for deck-scope judges (a judge
  given 30 separate screenshots opens only some of them):
  `uv run scripts/shoot.py deck.html <run>/evidence --sizes … --contact 1920x1080`. Files are
  `<slide>-<step>-<w>x<h>.png`, so a judge can cite slide, step and size, and
  `contact-<w>x<h>-<n>.png` (12 labelled states per sheet; `--contact-grid` to change).
- **PPTX renders:** when pptx is in scope, keep the `.pptx` (with its `.scene.json` and
  `.pptx-report.json`) for the gates, and render each slide for PX-06 (judges can't open PPTX):
  `soffice --headless --convert-to pdf`, then one PNG per page. PX-06 is reported missing, with
  the reason, when no renderer (LibreOffice `soffice`) is installed: the gate runner logs it
  (§3) and the report shows it; never judge PX-06 from the HTML instead.
- **Text:** per slide, its kicker, title, what each step shows, notes and sources, for `T` judges:
  `uv run evals/extract.py deck.html <run>/evidence/text` writes `<slide>.txt` (and
  `text.json`), read from the rendered deck so scene text and build steps appear as presented.
- **Repo facts** (process): `git log --stat`, the SPEC file at each commit that flips a status,
  the diff and test files of each spec's red and done commits, and the docs index. Transcripts only
  when approved.

Never strip self-assessment (e.g. a note praising the deck) from the evidence: judges are told to
ignore it, so the artefact stays as shipped.

## 3 · Deterministic gates

Write `manifest.json` first, then run the gate runner once over the deck, its PPTX and/or repo:

```bash
uv run ${CLAUDE_SKILL_DIR}/evals/gates.py <run-dir> [--deck deck/<name>.html] [--pptx <name>.pptx] [--repo .] [--no-rerun]
```

It reads profile and concerns from the manifest (or `--profile`, `--concerns`), checks every
selected `D` criterion in scope and writes one verdict per unit in the judge format (§4,
`repeat` 1) into `verdicts/`, plus `evidence/gates.json`: each criterion's rule, or why it is
`missing`. Deck checks render every slide × step × review size in Chrome with the network blocked
(deliberate stacks, such as a focus card over softened body content, are not collisions; softened
text is not contrast-checked). PPTX checks are `pptx/scripts/check.py`'s, run on the `.pptx` with
its scene and emitter report (sidecars beside it by default, or `--scene`, `--report`; without
them some come back `insufficient-evidence`). Repo checks read git history only (never a process
log) and re-run each spec's tests at its red and done commits in throwaway worktrees under the run
folder (`--no-rerun` skips that, leaving `PR-02` missing). With `--pptx` it also records under
`judge_inputs` whether the judged PPTX criteria have what they need (PX-06: a renderer on PATH, or
the reason it is missing). Exit 0 all pass, 1 any fail, 2 unusable input. A `D` criterion it lists
as missing (e.g. PX ones without `--pptx`) stays missing in the report, with that reason; never
judge a `D` criterion with an LLM instead. A failed gate already fails the deck, but still run the
judges the user asked for: the report is for improving the deck.

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
judges it. For output and process judges, write the plan (which criterion on which unit, with
which evidence files) as a JSON list and let `uv run evals/prompts.py <run> plan.json` fill every
repeat into `<run>/prompts/`; it prints one `prompt<TAB>verdict` line per judge to dispatch.
Give each unit only its own files: its step shots and its `text/<slide>.txt` for a slide or step;
the contact sheets (plus all `text/*.txt` for text criteria) for a deck-scope criterion.

**Dispatch in rolling batches.** Claude Code runs at most 20 subagents at once, so keep up to 20
judges in flight as a rolling queue: start the next judge as each one finishes, and track the
`prompt<TAB>verdict` list until every verdict file exists. A judge that ends without writing its
verdict is re-dispatched with the same prompt.

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

An outcome is `incomplete` when no gate failed but some gate is missing or undecided, and that
includes gated `S`/`T` criteria the run did not judge (e.g. RS-02 on a run that judged only a few
criteria). Read it as "not yet decided", never as a pass or a fail: the report lists each
undecided gate with its reason under the outcome, so either judge it or say why it was left out.
Record criteria left unjudged on purpose in the manifest's `not_judged` (`{criterion: reason}`):
the report shows that reason for each missing criterion, next to the gate runner's own reasons.

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
  evidence/                  screenshots, PPTX renders, text extracts, repo facts, gates.json
  verdicts/*.json            one per gate check or judge call
  prompts/*.md               filled judge prompts (prompts.py)
  yymmdd-<label>.json        report (aggregate.py)
  yymmdd-<label>.md          report for the presenter
```

**Several targets in one run** (e.g. a deck and its re-theme, or every anchor): give each target
its own sub-run folder with the layout above (its own manifest, evidence and verdicts, so verdict
names never collide), and make the dated folder a suite whose `manifest.json` holds only `label`,
`date` and `"runs"` (the sub-folder names; a sub-run may itself be a suite).
`aggregate.py <suite>` aggregates every sub-run and writes the roll-up `yymmdd-<label>.json`/`.md`
beside them: each target's outcome, failed and undecided gates and score.

**Anchor accuracy** (the lenient-judge check, whenever anchors are in a run): run each anchor as a
sub-run of an anchors suite, then `uv run evals/accuracy.py <anchors-suite>` writes
`accuracy.json` and `accuracy.md`: every labelled criterion, matched or not, judges and gates
tallied apart (verdict rule in `anchors/anchors.json`). Report judge mismatches as lenient
(must_fail passed) or over-strict (must_pass failed).

Runs are dated records: never edit a past run; re-run into a new folder. Add an `evals/` row to the
project index on the first run.
