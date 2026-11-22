# PRD: twm-presentation-builder skill

## What

An Agent Skill (`skills/twm-presentation-builder/`) that guides an agent through building a
presenter-driven, single-file HTML slide deck the way the HF incident deck (`deck/deck-v2.html`)
was built, plus an **HTML → editable PPTX** part and a rigorous **LLM-as-judge eval** of both the
output and the development process. It ships instructions, reusable code (engine, tokens, tools,
converter) and worked examples from the HF deck.

## Why

The HF deck's quality came from a process and an architecture, not one-off effort: separated docs
(PRD, storyboard, research, voice, design), a define-once engine (ADR-001), prototypes judged by eye,
TDD with an always-on layout guard, and looking at the assembled deck. Packaging these makes the next
deck cheaper and keeps quality measurable. Its failures are lessons too (the rejected v2 first draft).

## Users

- **Agent** building a deck for the presenter (primary reader of `SKILL.md` and parts).
- **Presenter**: answers the interview, judges prototypes and screenshots, chooses eval scope.
- **Colleague** receiving the PPTX hand-off.

## Scope

**Target:** presenter-driven editorial talks (step builds, diagrams, Insight overlays, reader notes,
sourced claims, Teams screen-share). The eval **MUST** adapt to other deck types (pitch, data
review, internal update) through profiles, without duplicating criteria.

**Separation of concerns (interchangeable parts):** content/storyboard · research · voice · design
· architecture · process · PPTX · eval. Swapping one part **MUST NOT** require editing another.

- **Design** has three layers, each consuming only those below it:
  1. **layout/components**: header bar, nav/agenda, title/lead layouts, columns, diagram kit,
     pop-overs, Insight overlays, narration tiles, tile row, notes UI;
  2. **palette**: semantic colour roles, their application rules and contrast constraints, and
     each role's PPTX theme slot;
  3. **style/material**: fonts and type scale, depth effects (bokeh, frost, shadow), motion,
     illustration style.
- **Architecture** sits beneath design: the engine, data-attribute authoring contract, component
  API (class names, slots, states), shared SVG defs, layer order, and the single-file / offline /
  endpoint-safe guarantees. It extends ADR-001 into a documented contract.
- **Voice** ships as the presenter's personal profile (rules + approved/rejected pairs from
  `docs/VOICE.md`), behind a small contract so other profiles can be added later. Not generalised.

## Requirements

- **Self-contained (MUST):** no path out of `skills/twm-presentation-builder/` (the HF deck appears
  only as copied, cited examples), so the folder can move to its own repo.
- **Not a plugin:** a plain skill. Eval judges are **generic subagents** fed the skill's
  instructions, rubric and anchors; no agent definitions, no API runner. Formats stay
  runner-agnostic so an API runner could be added later.
- **Skill structure (research: `research/skill-structure.md`):** `SKILL.md` is a router (~≤250
  lines) with the most important rules first; every part is **one link** from `SKILL.md`; scripts
  are run, not read, via `${CLAUDE_SKILL_DIR}`.
- **Output deck:** one self-contained HTML file that opens offline from email/Teams, no build step
  to view, and trips no endpoint heuristics (as HF deck S-009).
- **Design swap:** changing palette or style is a tool run over the deck file that replaces only
  the theme blocks; slides are untouched. Tokens follow the W3C DTCG 2025.10 format with ref → sys
  → comp tiers; components read only sys/comp tokens (research: `research/design-tokens.md`).
- **Toolchain:** Python + uv only (no Node). Shipped scripts declare their dependencies inline
  (PEP 723) so `uv run` works without a project file.
- **PPTX (research: `research/html-to-pptx.md`):** an **editable hand-off**: native text,
  placeholders, layouts in a master, theme colours/fonts from the palette and style tokens, and
  diagrams as named native shapes where practical, else an SVG picture with PNG fallback. Build
  steps become **native animations wherever possible** (entrance, exit, emphasis, motion paths);
  duplicated slides + Morph only where no animation equivalent exists. Effects PowerPoint can't
  render natively (backdrop blur, drift) may be sacrificed: each style declares every effect as
  native / approximated / lost.
- **Eval (research: `research/llm-judge.md`, `research/deck-rubrics.md`):**
  - **Two uses:** iterating on the skill (bundled test briefs) and assessing any deck built with it.
  - **Scope prompt (MUST):** before a run the user chooses the target (brief or deck path),
    concerns, output and/or process, and depth (gates only or gates + judges).
  - **Criterion library, defined once:** id, concern, evidence type (deterministic / screenshot
    judge / text judge), binary checklist item or 0–5 scale with every level described, anchors,
    flaw taxonomy. **Profiles** select and weight criteria by id, plus a few profile-only ones.
  - **Deterministic gates first** (geometry, contrast, offline, titles, alt text, process facts
    from git); judges score only what code can't.
  - **Judging protocol:** each criterion judged in isolation; judges see only the artefact, rubric
    and anchors (never the builder's context); verdict = evidence → rationale → score, with
    "insufficient evidence" allowed; k independent judges, median, high spread flagged; pointwise
    by default, pairwise only for skill-version A/B in both orders. Results saved as dated JSON.
  - **Process evidence:** repo artefacts only (git history, docs, SPEC states, outputs incl.
    screenshots); Claude Code transcripts **only** with the user's approval for that run. The skill
    **NEVER** makes the agent keep a self-reported process log. Process judges verify "done"
    claims against diffs and tests.
  - **Calibration:** none initially (may come later). Anchors come from recorded presenter verdicts
    (VOICE pairs, PRD decisions, the v2 first-draft rejection) plus deliberately flawed decks.
    Reports **MUST** state that agreement with the presenter is unmeasured.
  - **Briefs:** (1) HF deck subset (gold reference), (2) the same subset in a second theme,
    (3) a synthetic pitch, (4) a synthetic data review, each with a small fixed research pack.
    Together the briefs **MUST** cover every skill feature, enforced by a coverage check.

## Decisions

- **Folder layout (presenter, 22 Nov):** the shipped skill is `skills/twm-presentation-builder/`;
  its dev docs (this PRD, `SPEC.jsonl`, research) and tests live in the sibling
  `skills/twm-presentation-builder-docs/`, indexed from root `AGENTS.md`. The deck's `docs/` and
  `tests/` **NEVER** hold skill specs. Local trial via a symlink in `.claude/skills/` (root
  `skills/` is not a discovery path).
- **Second theme is specified and blind-evaluated, not prototyped (presenter, 22 Nov):** a palette +
  style swap over the same components (no new components), judged by the eval's subagents only;
  presenter verdict deferred. This is an approved exception to root Workflow phase 4.
- **PPTX is a part, not a sibling skill (for now):** `pptx/` stays self-contained so it can be
  promoted later (Anthropic ships pptx/docx as separate skills).
- **Python token generator over Style Dictionary/Terrazzo:** keeps the skill uv-only; the
  generator writes the CSS theme blocks and the PPTX `clrScheme`/`fontScheme` from one DTCG source.
- **The HF deck is not migrated** onto the skill's engine: it stays the accepted reference.

## Exclusions

- No plugin packaging, agent definitions, hooks-as-plugin or API judge runner (for now).
- No new component designs or prototyped second visual language (for now).
- No generalised voice; no presenter-calibration set (for now).
- No speaker-timer/presenter view; no framework or build step for viewing the deck.

## Open questions

- Should the screenshot gate be enforced by a hook in `SKILL.md` frontmatter, or stay prose plus
  the process gate?
- `SKILL.md` description wording (drives triggering); settle when PB-001 is built.
- Exact second theme (e.g. dark palette + flat style without blur/bokeh): settle in PB-008's red.
- Text-wrap drift between Chrome and PowerPoint: measured in PB-024, tolerance agreed then.
