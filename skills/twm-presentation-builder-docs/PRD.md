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
  - **Briefs:** (1) HF deck subset (gold reference), (2) the same subset in a second palette,
    (3) a synthetic pitch, (4) a synthetic data review, each with a small fixed research pack.
    Together the briefs **MUST** cover every skill feature, enforced by a coverage check.

## Decisions

- **Folder layout (presenter, 22 Nov):** the shipped skill is `skills/twm-presentation-builder/`;
  its dev docs (this PRD, `SPEC.jsonl`, research) and tests live in the sibling
  `skills/twm-presentation-builder-docs/`, indexed from root `AGENTS.md`. The deck's `docs/` and
  `tests/` **NEVER** hold skill specs. Local trial via a symlink in `.claude/skills/` (root
  `skills/` is not a discovery path).
- **Second theme is specified and blind-evaluated, not prototyped (presenter, 22 Nov):** a palette
  swap over the same components and style (no new components). Scheme: four bright primaries on
  white (blue `#4285F4`, red `#EA4335`, yellow `#FBBC05`, green `#34A853`), near-black ink
  `#202124`, grey secondary `#5F6368`, light-grey surfaces; the brights are fills/strokes only
  where they miss text contrast, with darker shades for accent text. Its files and docs **NEVER**
  name or reference any organisation, judged by the eval's subagents only;
  presenter verdict deferred. This is an approved exception to root Workflow phase 4.
- **PPTX is a part, not a sibling skill (for now):** `pptx/` stays self-contained so it can be
  promoted later (Anthropic ships pptx/docx as separate skills).
- **Python token generator over Style Dictionary/Terrazzo:** keeps the skill uv-only; the
  generator writes the CSS theme blocks and the PPTX `clrScheme`/`fontScheme` from one DTCG source.
- **The HF deck is not migrated** onto the skill's engine: it stays the accepted reference.
- **Process carried by an injected `AGENTS.md`, no hooks (presenter, 22 Nov):** the skill installs
  its `AGENTS.md` template (workflow, spec model, test authoring, definition of done incl. looking
  at assembled screenshots) into the deck project (`CLAUDE.md` = `@AGENTS.md`), so the dev approach
  persists across sessions; compliance is measured by the process eval, never enforced by hooks.
- **Voice profile is seeded into the deck project** as its `docs/VOICE.md` and grows there with each
  verdict (PB-013). How new verdicts flow back into the skill's profile is open (below).
- **Token tiers (PB-005):** comp tokens are owned by the components layer (palettes and styles ship
  ref + sys only); style may alias palette roles, never the reverse, so a palette swap retints
  frost, shadows and bokeh. The paper-green accent is *decorative* (2.05:1 on paper): never text
  and never the only carrier of meaning. The contrast gate uses WCAG 2 ratios.
- **Pop-over tile is opaque (presenter, 23 Nov):** a shadowed opaque tile as in the reference deck,
  not frosted; fixed in PB-007.
- **Fonts ship in the skill (PB-006):** woff2 files under `assets/fonts/` with their SIL OFL 1.1
  licences; `fonts.json` maps family → files, and the assembler embeds every family a style names.
- **PPTX step-delta policy (agent, 23 Nov, presenter asleep; review):** scene camera moves use
  duplicated slides + Morph; text/line colour changes (e.g. step-list current/done) are dropped and
  each element keeps its entry look, unless an emphasis effect can express them; blur softening is
  lost. The scene is measured at its final visible step with reduced motion (`pptx/scene.schema.json`).
- **Reference visuals ported under PB-007 (agent, 23 Nov):** the reference deck's diagram and
  illustration kit (domains, dots/links, badges, glyphs, timeline body, scene key and dim/muted
  states) moved into the components layer as gap fixes, not new visual language. Anchor decks now
  embed fonts so judges see the real look (~5 MB across 10 anchors).
- **PPTX emitter calls (agent, 23 Nov; review):** 16:9 slides scaled 2/3 from the 1920 px stage; six
  layouts in one generated master (lead, standard, split, three-column scene, tile row, end); points
  build by paragraph in one placeholder; tables whose rows build on steps split into stacked tables;
  colour mixes become theme tints; a structural validator ships instead of vendoring Anthropic's
  `validate.py`; text wrap gets ~6% width slack and is judged visually (PX-06).
- **Trigger (presenter, 22 Nov):** the skill triggers on requests to build HTML slides / an HTML
  deck or presentation.
- **Second theme = palette only (presenter, 22 Nov):** it changes the colour scheme and nothing
  else (same components and style); style swaps come later.
- **Text-wrap drift in PPTX is judged visually (presenter, 22 Nov):** a screenshot-judge criterion,
  no numeric tolerance.

## Exclusions

- No hooks (process is instructed via the injected `AGENTS.md` and measured by the eval); no
  plugin packaging, agent definitions or API judge runner (for now).
- No new component designs or prototyped second visual language (for now).
- No generalised voice; no presenter-calibration set (for now).
- No speaker-timer/presenter view; no framework or build step for viewing the deck.

## Open questions

- Voice verdict sync: should the agent offer, at the end of a deck project, to copy its new
  verdict pairs back into `voice/profiles/twm.md`?
