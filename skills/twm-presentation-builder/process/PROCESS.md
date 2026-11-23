# Process

Read at the start of any deck project, and whenever unsure what comes next.

## Phases (in order)

1. **PRD.** Write `docs/PRD.md` from the template: what, why, core message (M1, M2…), audience,
   delivery. Keep it living: intent changes land here first.
2. **Interview.** Ask the presenter **one question at a time**, inline, with a short recommendation
   and its trade-off. Never multi-option pickers. Capture each answer in the PRD as you go.
3. **Research (ask first).** Propose topics and get consent, then write sourced notes under
   `docs/research/` (method: the research part). No claim reaches a slide without a source.
4. **Storyboard.** Slide-by-slide arc in `docs/STORYBOARD.md` (method: the content part). Titles
   follow the voice profile and need presenter approval.
5. **Prototype or in-situ.** New visual language (a component, diagram style or layout not yet in
   the skill) is a throwaway prototype in `design/prototypes/`, judged by eye with the presenter,
   ideally at the delivery size and through a screen-share. Or the presenter chooses to build it
   straight into the deck behind spec + tests; record that choice in PRD *Decisions*.
6. **Spec.** One `todo` line per feature in `docs/SPEC.jsonl`, with `depends_on`.
7. **TDD: red, then green.** Tests first, run them, read the real failure, commit them (status
   `build`), then build until they pass.
8. **Screenshot look.** Run the layout guard, then shoot the **assembled** deck at every affected
   step and review size and look at every image before claiming anything is finished (*Tools*).
9. **Done.** Flip the spec only when the project `AGENTS.md` *Definition of done* holds, docs
   first.

Afterwards, optionally: PPTX hand-off, then the eval.

## Tools

Shipped in the skill's `scripts/`; run from the skill folder with `uv run`, any deck path, `--help`
for options. Both drive the system Chrome through Playwright and wait for animations to settle
before each state, never a fixed sleep.

- `uv run scripts/layout_guard.py deck.html [--sizes 1920x1080,1280x720,1288x598] [--slides s-2,s-5] [--json]`:
  every slide × step × size; exit 0 clean, 1 with one `FAIL <slide>@<step> <WxH> <kind>: …` line
  per fault (`overlap`, `overflow`, `off-canvas`, `occlusion`), 2 if the deck can't be used.
  `--json` prints a machine-readable report; the eval's gate runner (`evals/gates.py`) imports
  the guard's check directly, so a guard-clean deck starts from the same faults. Wire it into the
  deck's test suite so it runs on every visual change: the project template's
  `tests/test_layout_guard.py` does (one case per slide), calling `guard(deck)` in-process, which
  runs Chrome in a worker thread and so works beside the suite's own Playwright fixtures (or pass
  `browser=` to reuse one). Never wrap the CLI in a subprocess for this.
- `uv run scripts/shoot.py deck.html [out_dir] [--sizes …] [--slides …] [--settle ms] [--notes]`:
  writes `<slide>-<step>-<w>x<h>.png` (with `--notes`, `<slide>-n<i>-<w>x<h>.png` per reader
  note) and `shots.json`, into `shots/` beside the deck by default. `--settle` adds an extra wait
  only for timed beats that run after the page looks still. A full run replaces every earlier
  shot; a `--slides` run replaces only those slides' shots and keeps (and re-indexes) the other
  slides' shots, dropping any for slides no longer in the deck. Re-shoot everything after a change
  to anything shared (components, theme, engine, a scene). Called in-process (`shoot.shoot(deck, …)`), it too runs Chrome in a
  worker thread, beside any Playwright session the caller holds.
- Slides: the deck file's SLIDES block is the **source of truth** for the slides. Edit it in
  place, or take a working copy out and put it back with
  `uv run scripts/assemble.py slides deck.html --to slides.html` / `--from slides.html` (only
  SLIDES changes, plus the module blocks when the new slides need a different module set). Never
  keep a separate slides file as a second source; `assemble.py new --slides` is for the first build.
- Fonts: `assemble.py` embeds them on `new`; `uv run scripts/assemble.py swap deck.html` with no
  options re-embeds them (and the theme) from the names the deck records.

## Install into the deck project (first session)

Copy `assets/templates/project/` into the project root: `AGENTS.md`, `CLAUDE.md` (a bare
`@AGENTS.md`), `docs/PRD.md`, `docs/SPEC.jsonl`, `docs/ADR.md`, `tests/test_layout_guard.py` and
`tests/helper_skill_tools.py` (set its `DECK` to the deck path; the guard test runs once the deck
exists). `AGENTS.md` is what carries this process across sessions: skill text fades after context
compaction, `AGENTS.md` loads every session.

Other docs are **born on content**, each when it gets its first content, with its index row copied
from the template's *Rows born on content* table in the same commit:

- `docs/STORYBOARD.md`: at the storyboard phase, from the content part's template.
- `docs/VOICE.md`: once the presenter names a voice profile, copied from it (voice part).
- `docs/research/RESEARCH.md` + notes: from the research part's templates, when research starts
  (with consent).
- `docs/DESIGN.md`: when the first visual rule is agreed; the chosen layout, palette and style
  and this deck's own rules (layout part and tokens part; never a copy of them).
- `design/prototypes/PROTOTYPES.md`, `docs/ADR.jsonl`, `evals/runs/`: with the first prototype,
  decision record or eval run.
- The deck: `assemble.py new` at the path the project's house rules give, else
  `deck/<name>.html`.

- **If `AGENTS.md` already exists, NEVER overwrite it.** Ask the presenter, then merge: add the
  missing sections and index rows, keep their wording where it conflicts, and show the diff.
- Same for any existing `CLAUDE.md`: it must end up pointing at `AGENTS.md`, nothing more.
- An existing project's house rules (paths, rounding, naming) win over the template where they
  conflict; record each such call in PRD *Decisions*.

## Compliance is measured, not enforced

There is no automation guarding these phases. The eval's process criteria check them from the
repo: failing-test commits before build commits, docs changed with their index rows, screenshots
taken before a spec was marked finished, a PRD decision for every in-situ choice. Work as if every
commit will be read.

## Lessons from the worked example

The full case, with before/after screenshots, is `examples/hf-incident/first-draft-failure.md`.

- **A green suite is not a look.** An early draft shipped titles overlapping step lists with every
  test passing, because layout tests were off and only per-slide component shots were taken.
- **Prototype before parallel builds.** The same draft skipped prototypes for new visuals and fell
  below the earlier version's quality; briefs led with merge-safety, not design targets.
- **Fewer elements per slide.** Step lists that restate the diagram in prose crowd the slide; let
  the diagram carry the story.
- **Never cut copy to fit.** Re-check trimmed copy against the voice profile.
- **Short-wide windows matter.** Review at 1920×1080, 1280×720 and ~1288×598 (a screen-share
  viewer's window), not 16:9 only.
