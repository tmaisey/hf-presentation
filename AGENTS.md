## Docs & progressive disclosure

**MUST / NEVER / ALWAYS are binding.** Deviate only with explicit user approval. Each rule's *why*
is there so you apply it correctly, not so you can reargue it.

Docs hold **intent and state** that code, docstrings and git can't. This file is the
**always-loaded root**; every other doc is read on demand, so this file **MUST** stay lean.

- **Chain:** `CLAUDE.md` (Claude Code only; a bare `@AGENTS.md`) → `AGENTS.md` → indexed docs → child indexes.
  **ALL** agent instructions, incl. harness-specific ones, **MUST** go in `AGENTS.md` or a doc it
  indexes; **NEVER** in `CLAUDE.md`: one root keeps every harness on the same rules.
- **Write for read & write speed:** minimise tokens and re-reads. One home per topic, never spread
  across reads. Front-load what decides whether to read further. Cut low-signal tokens. Read a doc
  **only** when its row's *when to use* applies.
- **Index row schema:** `file · description · when to use (and not) · when to update (and not)`.

### Index rules

- **ALWAYS** read a folder's child index before searching that folder: it holds intent search can't show.
- **Root row** ⟸ always-relevant (PRD, SPEC.jsonl, README, GLOSSARY…). **Child index**
  (`<FOLDER>/<NAME>.md`, e.g. `RESEARCH.md`; **NEVER** `CLAUDE.md`/`AGENTS.md`) ⟸ occasionally-relevant
  or grown folder. Two hops max, single parent, **NEVER** lateral cross-refs: they break silently.
- **ALWAYS** give a significant directory one folder-level row (`tests/`, `src/api/`) so agents don't
  re-explore or duplicate. **NEVER** add a row per code/test file: code is ground truth. Promote a
  folder to a child index when it gains folder-specific intent.
- **MUST** add a doc's index row *before* writing it: an interrupted run recovers the unwritten doc.
- **MUST** update a row in the same commit as a change to what the doc holds or how it's used.

### Repo Index

| File | Description | When to use | When to update |
| --- | --- | --- | --- |
| `CLAUDE.md` | Claude Code entry point: a pure `@AGENTS.md` ref, nothing else | Never read directly; auto-loaded. Not for content | Only if the doc-root chain changes. **NEVER** add content, even Claude Code-specific: put it in `AGENTS.md` |
| `AGENTS.md` | Root (always loaded): doc rules + index, workflow, spec model, test authoring, ADR trigger | Every session | When a doc is added/changed (row in same commit) or workflow/models change. Not for project content |
| `docs/PRD.md` | Living requirements: what and why, scope, exclusions | Before scoping, prioritising or changing any feature; on any intent change | First, on any intent change (before spec/code). Not for feature state: that's `SPEC.jsonl` |
| `docs/SPEC.jsonl` | Feature backlog + live state, one line per feature (*Spec model* below) | Start of a build session to find done/next; before writing tests | On spec add/refine and every status flip, in the same commit as the work |
| `docs/research/RESEARCH.md` | Child index of incident research: sourced facts, timeline, forensics, commentary | Before writing any factual slide or storyboard claim; before new research (avoid repeat searches) | When a research doc is added/changed (row in same commit) |
| `design/prototypes/PROTOTYPES.md` | Child index of frozen reference prototypes (single HTML files): what each tests + verdict | Before making or judging a prototype; when a DESIGN.md link needs checking | When a prototype is added, verdicted or retired (row in same commit) |
| `deck/deck-v2.html` | **The deliverable (v2)**: ~10-slide diagram-led single-file deck (ADR-001 layers: tokens, components, shared SVG defs, engine, then the shared incident world and slide sections) | To build/edit v2 slides (S-017+); open in a browser to present | Every v2 slide/engine change, with its spec's tests |
| `deck/deck.html` | v1 deck (18 slides, S-001–S-016): reference and source of engine, components and copy for v2 | To copy/consult v1 engine, components or approved copy. Not for new work | Only if a v1 spec reopens; otherwise frozen |
| `tests/` | pytest + Playwright suite: static DRY/voice/safety checks and in-browser behaviour checks. `uv run pytest -n auto --deck v2` (default deck v2); `@pytest.mark.deck("v1")` marks v1-only tests; v1 is guarded by a byte-hash test, so **NEVER** run `--deck v1` browser tests unless shared test code changes. Two timing-sensitive tests (notes pins, compact title bar) can fail under `-n auto` load: rerun them serially before treating it as a regression. **NEVER** mark layout/visual tests v1-only for the deck being built | Before changing the deck; to prove red/green | When a spec's acceptance detail changes or the deck-selection contract changes |
| `tools/embed_fonts.py` | Fetches the deck's woff2 fonts (`fetch`) and inlines them as base64 between `FONTS:BEGIN/END` in the deck (`embed`) | After changing fonts or if the font block is lost; `uv run python tools/embed_fonts.py embed` | When the font set or embed format changes |
| `tools/shoot.py` | Screenshots one v2 slide at every step at 1920×1080, 1280×720, 1288×598 (`uv run python tools/shoot.py s-4 [out] [--settle ms]`; raise `--settle` for timed beats, e.g. s-4's crash at ~4 s) | Every visual change, to look at the assembled deck step by step before calling it done (Definition of done 4) | When review sizes or the engine API change |
| `assets/fonts/` | Raw latin woff2 files (Newsreader roman/italic, Inter) the deck embeds | Only via `tools/embed_fonts.py` | Only by re-running `fetch` |
| `pyproject.toml` | uv project: test dependencies only | When adding a test dependency | On dependency change |
| `docs/STORYBOARD.md` | Slide-by-slide arc: chapters, timings, titles, visuals, overlays, sources, core message served | Before building or reordering any slide; when checking timing or coverage of the core message | When a slide is added, cut, retitled or re-sourced; when timings change |
| `docs/DESIGN.md` | Binding visual design rules (tokens, type, components, motion, diagrams), each linked to the prototype code that demonstrates it | Before writing or reviewing any slide markup, CSS, diagram or animation | When a visual rule is agreed, changed or retired; when a linked prototype line moves |
| `docs/VOICE.md` | Presenter's writing voice: rules + approved/rejected examples for titles, bullets, overlays, notes | Before writing or editing any slide copy, Insight, note or speaker text | When the presenter approves/rejects copy or states a style preference |
| `docs/ADR.md` | ADR model: schema, lifecycle, `ADR:` marker. Records live in `docs/ADR.jsonl` | Before adding, updating, superseding or deprecating an ADR. Not for reading live constraints: filter `ADR.jsonl` for `accepted` | When the ADR model changes. Not for individual decisions: those are `ADR.jsonl` lines |

### Doc hygiene

- **NEVER** create empty scaffolds: docs are born on first content.
- **DRY:** one canonical home per fact; point or derive, **NEVER** duplicate. Git holds history.
  Exceptions: `README.md` (human shopfront; redundancy and persuasion allowed) and `PRD.md`
  (requirements, decomposed into specs, tests, code, docs).
- **Dated records:** name `yymmdd-<name>.md` **only** when date-performed is a primary attribute
  (point-in-time, not feature-aligned) so they sort chronologically. Everything else stays undated.
  A dated record **may** be corrected in place on the day it was made; after that **NEVER** edit it:
  add a new dated file.
- **Privacy:** **NEVER** record health or other sensitive personal details shared in conversation
  unless the user asks: the repo outlives the conversation.

## Workflow

Phases 2–4 loop; the lifecycle is incremental. 1–5 capture intent; 6–9 build and integrate.
Optional phases run only when justified or requested.

1 · **MUST** · `docs/PRD.md` — PRD: capture intent (what/why); keep it living, updated to match code/docs.
2 · default · PRD/docs — Grill-me: one question at a time, inline; **NEVER** multi-option pickers, so the user can reason and redirect between answers.
3 · optional · `docs/research/` + `RESEARCH.md` — Research prior art (web + codebase) when a decision needs grounding; captured so searches aren't repeated. Bias to do it; **MUST** confirm with the user first.
4 · **MUST** for new visual language, else optional · `design/prototypes/` + child index — Throwaway, spec-free prototypes when options must be *seen* before spec. **MUST** precede spec/build of any new component, diagram style or layout, judged by eye with the presenter: v2's first draft skipped this and fell below v1's quality (Nov 2026). The presenter may instead choose **in-situ prototyping** (built straight into the deck behind spec + tests, judged by eye step by step): record that choice in `PRD.md` *Decisions*.
5 · **MUST** · `docs/SPEC.jsonl` — Decompose PRD → one `todo` spec per feature with `depends_on`; add specs as intent emerges.
6 · **MUST** · tests + code — Build from spec, TDD (below).
7 · **MUST** · commit — Done commit: implementation, tests and status flip together; clean tree.
8 · with worktrees/remote · clean tree — Fetch, collision-check, resolve until clean; may need human clarification.
9 · with branch/remote · merged/pushed — Merge and push.

**On any intent change (MUST):** PRD first → reopen the owning spec (*Refine, don't layer*) or add a
new one → red → green. **NEVER** edit code ahead of the spec that governs it: the loop holds on every
change, not just at the outset.

**Phase 6 — TDD.** Pick a `todo` spec. **MUST** agree sub-agent parallelism with the user. Then:

1. `grep "Spec: S-0NN"` for existing coverage; **extend, NEVER duplicate**. Write tests per *Test authoring*.
2. **Prove red:** run the tests and read the real assertion failure: not self-report, not boilerplate
   that always fails.
3. **Red commit:** commit failing tests before any build; flip `todo`→`build`. Locks the spec pre-build.
4. **Build to green:** implement, run the full suite, repeat until green.
5. Flip `build`→`done` **only** when the *Definition of done* holds.

**Worktree or direct (MUST choose):** a worktree per feature when work runs alongside other work
(isolation); direct on branch when it's small and serial. Phases 8–9 apply either way.

**Parallel visual builds:** parallelism is fine once the design is prototyped and agreed and the
layout guard is on: every builder works to those prototypes and `DESIGN.md` rules, never inventing
components per slide (propose them instead), and briefs lead with the design and quality targets,
not just file-slot rules; after every merge, re-run the layout guard and re-screenshot the assembled
deck: a shared component (e.g. a layout column) changes every slide that uses it.

## Spec model

`docs/SPEC.jsonl`: one line per feature + live state, the **resume surface** a fresh session reads
for done/next. Core intent only: **tests are detailed spec**, code/docstrings are ground truth, git
holds history.

Fields **MUST** be in this order (description last: verbose, read on demand):

```json
{"id": "S-001", "status": "done", "name": "Repo scaffold", "depends_on": [], "description": "built · why · not-built"}
```

- `id`: `S-0NN`, unique; tests reference it.
- `status`: `todo` / `build` / `done`.
- `name`: ~5-word label.
- `depends_on`: spec ids that must land first; drives ordering and resume. `[]` allowed.
- `description`: intent kernel, ≤ ~50 words: **built · why · not-built**.

**Kernel (declarative):** "built" = observable behaviour/contract (trigger→response, guarantees),
**NEVER** mechanism; concrete examples live in tests. "not-built" = a real non-goal (plausible scope
deliberately excluded), not a trivial negation ("shouldn't crash" is noise).

**Refine, don't layer:** refining intent **MUST** reopen the owning spec (`done`→`todo`) and edit its
kernel in place. New line ⇔ new capability; a near-duplicate line is noise: git carries history.

**Lifecycle:** `todo`→`build` at the red commit. `build`→`done` **only** when the **Definition of done**
holds, all of:

1. the spec's deterministic tests are green;
2. docs are current (index rows, affected docs, born-on-content), **updated before the flip**.
   Enforced by mandate, never keyword check: token passes over semantic edits give false confidence;
3. state captured: status flipped, index current;
4. **visual work:** the deck's layout guard (S-030) is active and green, and screenshots of the
   **assembled** deck at every affected step were looked at, never only component screenshots.
   **NEVER** call deck work done or presentable without that look: v2's first draft shipped title
   overlaps with a green suite because the layout tests were off and nobody looked (Nov 2026).

## Test authoring — tests are the detailed spec

Tests carry the acceptance detail the spec omits. If `docs/TESTS.md` exists, **MUST** read it before
writing tests.

- **Spec marker (MUST):** each test file's header docstring carries `Spec: S-0NN` (one or more),
  **NEVER** in filenames: names stay stable and one test may cover several specs. Helpers use a
  `helper_` prefix and carry **no** marker, so grep/glob cleanly separates tests from helpers.
- **Test observable behaviour, NEVER implementation:** assert the promise to the caller (return value,
  resulting state, genuine external effect) unless an ADR mandates the mechanism. Robustness to
  legitimate refactor is non-negotiable.
- **Coverage shape:** happy path(s), each input partition's boundary, negative cases asserting the
  forbidden effect. Silence is not coverage. **NEVER** write a test unless you can say what it
  catches that existing ones don't.
- **Docstrings:** header = marker + collection intent + one-line coverage map (happy/edge/negative).
  Per-test docstring **only** where the *why* isn't self-evident from name + assert (usually
  edge/negative). Name tests as behaviour statements.

## Decisions (ADR)

**SPEC or ADR?** Observable feature ⇒ SPEC (declarative). Binding design constraint or tech bet ⇒ ADR (imperative).

- **MUST** read `docs/ADR.md` before adding, updating, superseding or deprecating an ADR.
- **MUST** read and honour the cited ADR whenever code or a doc you touch carries `ADR: ADR-0NN` in
  its docstring (code) or prose (docs).
- **NEVER** edit an accepted ADR. Supersede it, because an editable decision can't be trusted.
