---
name: twm-presentation-builder
description: Builds presenter-driven, single-file HTML slide decks (step-built diagrams, overlays, reader notes, sourced claims, swappable design themes), converts them to editable PowerPoint, and evaluates the deck and its build process with rubric-based LLM judges. Use whenever the user asks to build, design, restyle or edit HTML slides, an HTML slide deck or an HTML presentation, to turn such a deck into PPTX, or to evaluate one.
compatibility: Needs uv, Python 3.12+ and Playwright with Chromium for screenshots, layout checks and PPTX measurement.
---

# twm-presentation-builder

Build a talk as **one self-contained HTML file** the presenter drives live and shares afterwards,
the way the HF incident deck was built. Quality comes from the process and the architecture, so
both are binding, not advice.

## Rules that hold every turn

1. **Separate concerns.** Content/storyboard, research, voice, design (layout · palette · style),
   architecture, process, PPTX and eval each have one home. Never let a change in one force an edit
   in another; never put per-slide styling or scripts in slide markup.
2. **Ask, don't assume.** Interview the presenter one question at a time; never multi-option
   pickers. Ask before researching. The presenter always has more context than you.
3. **See before you build.** New visual language is prototyped and judged by eye first, unless the
   presenter records a choice to build in situ.
4. **Tests first.** Every feature: spec → failing test (read the real failure) → build → green.
5. **Look at the assembled deck.** Visual work is never done until screenshots of the assembled deck
   at every affected step and review size have been looked at. A green suite is not a look.
6. **Every claim is sourced**; disputed or single-sourced claims are flagged; quotes are verbatim.
7. **Write in the presenter's voice**, never generic AI prose.
8. **Single file, offline, endpoint-safe:** no remote scripts, no build step to view.

## Workflow

PRD (intent) → interview → research (with consent) → storyboard → prototype or in-situ choice →
spec → TDD → assembled-screenshot look → done. Optional afterwards: PPTX hand-off, eval.

## Parts

Read a part only when its line applies. Parts never link each other; every part is linked here.

- [process/PROCESS.md](process/PROCESS.md): phases, installing the project `AGENTS.md`, lessons from
  the worked example. Read first in any deck project, and whenever unsure what comes next.
- [content/STORYBOARD.md](content/STORYBOARD.md): storyboard method (message codes, chapters,
  timings, title approval marks) and fill-in template. Read before planning, reordering or
  building any slide.
- [research/RESEARCH.md](research/RESEARCH.md): sourcing, citation, flagging and verbatim-quote
  rules, plus index and note templates. Read before researching (ask first), before writing any
  factual copy, and before putting a quote on a slide.
- [voice/VOICE.md](voice/VOICE.md): how a voice profile is picked, applied and extended with
  verdicts. Read before writing or editing any slide copy, Insight, tile or note.
- [voice/profiles/twm.md](voice/profiles/twm.md): the presenter twm's voice profile (rules +
  approved/rejected pairs). Read after `voice/VOICE.md` when twm is the presenter.
- [architecture/ARCHITECTURE.md](architecture/ARCHITECTURE.md): layer order, skeleton blocks, the
  data-attribute authoring contract, component API, shared SVG defs, engine API and module hooks.
  Read before writing slide markup, styling a design layer, writing an engine module or assembling
  a deck.
- [eval/CRITERIA.md](eval/CRITERIA.md): eval criterion library, flaw taxonomy and deck-type
  profiles. Read before judging a deck or process, or before adding or changing a criterion or
  profile; not needed to build a deck.

More parts are linked here as they land.
