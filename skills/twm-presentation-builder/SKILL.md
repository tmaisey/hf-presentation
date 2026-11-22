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

Parts are linked below as they land; each says when to read it.
