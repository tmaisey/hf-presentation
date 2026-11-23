## Docs & progressive disclosure

**MUST / NEVER / ALWAYS are binding.** Deviate only with explicit presenter approval. Each rule's
*why* is there so you apply it correctly, not so you can reargue it.

Docs hold **intent and state** that code, docstrings and git can't. This file is the
**always-loaded root**; every other doc is read on demand, so this file **MUST** stay lean.

- **Chain:** `CLAUDE.md` (Claude Code only; a bare `@AGENTS.md`) → `AGENTS.md` → indexed docs → child
  indexes. **ALL** agent instructions **MUST** go in `AGENTS.md` or a doc it indexes; **NEVER** in
  `CLAUDE.md`: one root keeps every harness on the same rules.
- **Write for read & write speed:** minimise tokens and re-reads. One home per topic. Front-load
  what decides whether to read further. Read a doc **only** when its row's *when to use* applies.
- **Index row schema:** `file · description · when to use (and not) · when to update (and not)`.

### Index rules

- **ALWAYS** read a folder's child index before searching that folder.
- **Root row** ⟸ always-relevant. **Child index** (`<FOLDER>/<NAME>.md`, **NEVER**
  `CLAUDE.md`/`AGENTS.md`) ⟸ occasionally-relevant or grown folder. Two hops max, single parent,
  **NEVER** lateral cross-refs.
- **ALWAYS** give a significant directory one folder-level row; **NEVER** a row per code/test file.
- **MUST** add a doc's index row *before* writing it: an interrupted run recovers the unwritten doc.
- **MUST** update a row in the same commit as a change to what the doc holds or how it's used.

### Repo Index

| File | Description | When to use | When to update |
| --- | --- | --- | --- |
| `CLAUDE.md` | Claude Code entry point: a pure `@AGENTS.md` ref | Never read directly | Only if the doc-root chain changes |
| `AGENTS.md` | Root (always loaded): doc rules, index, workflow, spec model, test authoring | Every session | When a doc is added/changed or workflow changes |
| `docs/PRD.md` | Living requirements: what and why, core message, audience, delivery, design intent, decisions, exclusions | Before scoping or changing any slide or feature; on any intent change | First, on any intent change (before spec/code) |
| `docs/SPEC.jsonl` | Feature backlog + live state, one line per feature (*Spec model*) | Start of a build session; before writing tests | On spec add/refine and every status flip, in the same commit as the work |
| `docs/STORYBOARD.md` | Slide-by-slide arc: titles, visuals, overlays, sources, timings, core message served | Before building or reordering any slide | When a slide is added, cut, retitled or re-sourced |
| `docs/research/RESEARCH.md` | Child index of sourced research notes | Before writing any factual claim; before new research | When a research note is added/changed |
| `docs/VOICE.md` | Which voice profile applies, plus this deck's own approved/rejected copy verdicts | Before writing any slide copy or note | When the presenter approves/rejects copy |
| `docs/DESIGN.md` | Chosen layout, palette and style, and binding visual rules for this deck, linked to prototypes | Before writing slide markup, CSS, diagrams or animation | When a visual rule is agreed, changed or retired |
| `design/prototypes/PROTOTYPES.md` | Child index of throwaway prototypes: what each tests + verdict | Before making or judging a prototype | When a prototype is added or verdicted |
| `docs/ADR.md` | ADR model; records in `docs/ADR.jsonl` | Before adding or superseding a decision record | When the ADR model changes |
| `deck/<name>.html` | **The deliverable**: one self-contained HTML deck | To build/edit slides; open in a browser to present | Every slide/engine change, with its spec's tests |
| `evals/runs/` | Dated eval runs (`yymmdd-<label>/`: manifest, evidence, verdicts, report), written by the skill's eval protocol | To read past eval results or compare runs | Never edit a run; each run adds a new folder |
| `tests/` | pytest + Playwright: static checks and in-browser behaviour, incl. the always-on layout guard (every slide × step × review size; wrap the presentation-builder skill's `layout_guard.py`, and shoot with its `shoot.py`). Browser tests **MUST** wait on a condition, **NEVER** a fixed sleep | Before changing the deck; to prove red/green | When a spec's acceptance detail changes |

### Doc hygiene

- **NEVER** create empty scaffolds: docs are born on first content.
- **DRY:** one canonical home per fact; point or derive, **NEVER** duplicate.
- **Dated records** (`yymmdd-<name>.md`) only when the date is a primary attribute; never edit them
  after the day they were made.
- **Privacy:** **NEVER** record health or other sensitive personal details shared in conversation.

## Workflow

Phases 2–4 loop. Optional phases run only when justified or requested.

1 · **MUST** · `docs/PRD.md` — capture intent (what/why, core message the room should leave with).
2 · default · Interview the presenter **one question at a time**, inline; **NEVER** multi-option
pickers, so they can reason and redirect between answers.
3 · optional · `docs/research/` — research when a claim or decision needs grounding. Bias to do it;
**MUST** confirm with the presenter first.
4 · **MUST** for new visual language · `design/prototypes/` — throwaway prototypes judged by eye with
the presenter before spec, unless the presenter chooses in-situ prototyping (built into the deck
behind spec + tests, judged step by step): record that choice in `PRD.md` *Decisions*.
5 · **MUST** · `docs/SPEC.jsonl` — decompose PRD and storyboard into one `todo` spec per feature.
6 · **MUST** · tests + code — build from spec, TDD (below).
7 · **MUST** · commit — implementation, tests and status flip together; clean tree.
8–9 · with worktrees/branches · fetch, collision-check, merge and push.

**On any intent change (MUST):** PRD first → reopen the owning spec or add one → red → green.
**NEVER** edit code ahead of the spec that governs it.

**TDD.** Pick a `todo` spec; agree sub-agent parallelism with the presenter. Then:

1. `grep "Spec: S-0NN"` for existing coverage; **extend, NEVER duplicate**.
2. **Prove red:** run the tests and read the real assertion failure.
3. **Red commit:** failing tests before any build; flip `todo`→`build`.
4. **Build to green:** run **only the tests your change touches** (plus the layout guard for visual
   work). The full suite runs once on main after each merge.
5. Flip `build`→`done` **only** when the *Definition of done* holds.

**Parallel visual builds:** only once the design is prototyped and agreed and the layout guard is
on. Builders work to the prototypes and `DESIGN.md`, never inventing components per slide; after
every merge, re-run the layout guard and re-screenshot the assembled deck.

## Spec model

`docs/SPEC.jsonl`: one line per feature + live state, the **resume surface** a fresh session reads.

```json
{"id": "S-0NN", "status": "todo", "name": "~5-word label", "depends_on": [], "description": "built · why · not-built"}
```

- Fields **MUST** be in this order. `status`: `todo` / `build` / `done`.
- `description`: intent kernel, ≤ ~50 words: observable behaviour (never mechanism) · why · a real
  non-goal.
- **Refine, don't layer:** refining intent reopens the owning spec and edits its kernel in place.

**Definition of done**, all of:

1. the spec's deterministic tests are green;
2. docs are current (index rows, affected docs), **updated before the flip**;
3. state captured: status flipped, index current;
4. **visual work:** the layout guard is green and screenshots of the **assembled** deck at every
   affected step and review size were looked at, never only component screenshots. **NEVER** call
   deck work done or presentable without that look: a green suite once shipped overlapping titles
   because nobody looked.

## Test authoring — tests are the detailed spec

- **Spec marker (MUST):** each test file's header docstring carries `Spec: S-0NN`, **NEVER** in
  filenames. Helpers use a `helper_` prefix and carry **no** marker.
- **Test observable behaviour, NEVER implementation.**
- **Coverage shape:** happy path(s), each input partition's boundary, negative cases asserting the
  forbidden effect. **NEVER** write a test unless you can say what it catches that others don't.
- **Docstrings:** header = marker + intent + one-line coverage map; per-test only where the *why*
  isn't self-evident.

## Decisions (ADR)

**SPEC or ADR?** Observable feature ⇒ SPEC. Binding design constraint or tech bet ⇒ ADR.

- **MUST** read `docs/ADR.md` before adding, updating, superseding or deprecating an ADR.
- **MUST** honour the cited ADR whenever code or a doc you touch carries `ADR: ADR-0NN`.
- **NEVER** edit an accepted ADR. Supersede it.
