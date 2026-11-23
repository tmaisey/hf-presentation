# Bundled test briefs

Fixed inputs for iterating on **the skill itself**: build (or re-theme) a deck from a brief, then
run the eval on it (`evals/EVAL.md`, target = a bundled brief). Same brief, same research, every
time, so skill versions compare. Never use a brief for a user's own deck.

| Brief | Profile | Target | Theme | Gold reference | Tests |
| --- | --- | --- | --- | --- | --- |
| `hf-subset` | `editorial-talk` | build from brief | paper-green · editorial | `examples/hf-incident/deck.html` (+ slides, storyboard, core message) | The full method on a real case: scene, modules, PPTX, every process phase |
| `hf-subset-bright` | `editorial-talk` | re-theme `examples/hf-incident/deck.html` | bright-primaries · editorial | `examples/hf-incident/deck-bright.html` | Palette swap alone: slides byte-identical, contrast, PPTX theme, re-flow |
| `pitch-solar-coop` | `pitch` | build from brief | bright-primaries · editorial | none (synthetic) | Persuasion arc and one ask, stat, message card, key tile, a new diagram |
| `data-review-bus-reliability` | `data-review` | build from brief | paper-green · editorial | none (synthetic) | Table, terms, timeline, charts from the diagram kit, merging into an existing `AGENTS.md`, PPTX re-flow |

## Running a brief

1. Start a fresh deck project outside the skill folder. For `existing-deck`, copy the target deck
   in; for a brief with a `project/` folder, copy its files in first (they are the project's
   existing state).
2. Copy the research pack (`research`) to the project's `docs/research/`. The pack is fixed: never
   research further. Synthetic packs are invented and marked so; never present them as real.
3. Play the presenter from the brief: answer interview questions from `audience`, `length`,
   `core_message` and `constraints`, recording each call as "(agent, presenter unavailable)" in
   PRD *Decisions*. Titles stay ✎: drafting them to the brief is allowed, approving them is not
   (only a real presenter marks ✓), and a slide may still reach done with ✎ titles.
4. Build with the skill as for any deck, exercising every `features` id (`evals/features.json`).
5. Eval with the brief's `profile` and `concerns`; compare with `gold_reference` only after the
   build. Results go in the deck project, never here.

## `brief.json` schema

Fields in this order; all paths relative to the skill folder.

| Field | Meaning |
| --- | --- |
| `id` | = folder name |
| `title` | Short name |
| `synthetic` | `true` = invented topic, figures and sources (reserved `example.org` domains); `false` = real, cited |
| `profile` | Eval profile id (`evals/profiles/<id>.json`) |
| `theme` | `{palette, style}`: shipped token names |
| `target` | `{mode: "build-from-brief"}` or `{mode: "existing-deck", deck, task}` |
| `gold_reference` | Files to compare against after the build; `[]` for synthetic briefs |
| `research` | The fixed research pack folder: `RESEARCH.md` index + 3–6 notes, one disputed claim, one verbatim quote |
| `audience` · `length` · `core_message` | Who, `{minutes, slides}`, message codes `M1…` with full sentences |
| `constraints` | Binding instructions the presenter would give |
| `concerns` | Eval concerns in scope (`evals/CRITERIA.md`) |
| `features` | Feature ids (`evals/features.json`) the build must exercise |

## Feature coverage

Together the briefs **MUST** cover every skill feature. `evals/features.json` lists each observable
capability with the criteria that judge it; a brief covers a feature when it claims it and its
profile selects one of those criteria in a concern the brief scopes. Check after adding or changing
a feature, brief, criterion or profile: `uv run ${CLAUDE_SKILL_DIR}/evals/coverage.py` (`--list`
shows each feature's briefs); it exits 1 with a `FAIL` line per gap. A new capability adds its
feature, a criterion that judges it and a brief that exercises it.
