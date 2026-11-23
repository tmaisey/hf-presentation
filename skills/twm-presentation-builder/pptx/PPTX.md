# PPTX hand-off

Turn an assembled deck into an **editable** PowerPoint file a colleague can keep working in:
native text in placeholders of named layouts, theme colours and fonts from the deck's tokens,
named native shapes, speaker notes, and build steps as native animations. Pixel fidelity is not
the goal. Read before converting a deck, changing a PPTX script, or judging a PPTX.

## 1 · Pipeline

Run from the skill folder (`${CLAUDE_SKILL_DIR}`). Needs Chrome for the measure step.

```bash
uv run scripts/assemble.py check deck.html                 # 1. an assembled, endpoint-safe deck
uv run pptx/scripts/scene.py deck.html -o deck.scene.json   # 2. measure (optional: emit does it)
uv run pptx/scripts/emit.py deck.html -o deck.pptx          # 3. emit: deck.pptx, deck.scene.json, deck.pptx-report.json
uv run pptx/scripts/check.py validate deck.pptx             # 4. package + timing structure
uv run pptx/scripts/check.py verdicts deck.pptx --out verdicts/   # 5. eval verdicts (PX criteria)
```

- **scene** (`scene.py`, schema `scene.schema.json`): every slide's final-state geometry, roles,
  text runs, palette roles, style effect bands and step timeline, measured in Chrome.
- **emit** (`emit.py`): scene → `.pptx` plus the sidecar `<name>.pptx-report.json`, which lists
  every approximated, lost or dropped item (`items[]`: slide, element, what, band, result, how)
  and which PPTX slides came from which HTML slide and steps.
- **check** (`check.py`): verdicts in the eval schema for every deterministic `pptx` criterion
  (PX-01 native text, PX-02 layouts/placeholders, PX-03 theme refs, PX-04 animations and Morph,
  PX-05 effect bands, PX-07 accessibility, PX-08 named diagram shapes, PX-09 notes); `validate`
  (zip, content types, relationships, timing); `reflow` (see §5). PX-06, text wrap, is judged by
  eye from renders (`soffice --headless --convert-to pdf` when LibreOffice is installed). In an
  eval run the gate runner calls `verdicts` for you (`evals/gates.py --pptx`, `evals/EVAL.md` §3).

Show the presenter the report's `counts` and every `dropped` item before handing the file over.

## 2 · What the file holds

**Seed template, generated per theme.** One master and six named layouts, built from the scene
(placeholder boxes and text styles from the first slide of each kind), on a 16:9 widescreen
slide (the 1920 px stage scales to 13.333 in). Theme `a:clrScheme` and `a:fontScheme` come from
`scripts/tokens.py pptx` for the deck's palette and style.

| Layout | Used for | Placeholders |
| --- | --- | --- |
| Title / lead | `slide--lead` | Title, Subtitle (lead body), Kicker, Byline |
| Standard | one body column | Title, Kicker, Body |
| Split | `body--split` | Title, Kicker, Left, Right |
| Three-column scene | live scene slides | Title, Kicker, Steps, Scene (picture) |
| Tile row | text-tile rows | Title, Kicker, Tile 1–3 (round-rect cards) |
| End | `slide--end` | Title |

Every shape is named by its element id (`c3-a`, `c3-e2`). Colours with a palette role are
`schemeClr` references (role-less mixes become a theme colour with `a:tint`); fonts are
`+mj-lt`/`+mn-lt`. Speaker notes carry each slide's reader notes with their sources as links.

## 3 · Native, approximated, lost

The style's `com.twm.pptx` bands (see `design/TOKENS.md`) decide each effect; the report
records what happened to each.

| HTML | PowerPoint | Band |
| --- | --- | --- |
| Title, kicker, body text, lists | Text in layout placeholders; points → bullets, steps → autonumber | native (marker circles approximated) |
| Cards (Insight, narration, message, pop-over, tile card, annotation, term) | Named round rectangle holding its text | native |
| Diagram tiles, edges, labels | Named `roundRect` + text; connectors or `cubicBezTo` freeforms with arrowheads; text boxes | native |
| Inline SVG illustrations (pop-over art, key glyphs) | Named native shapes, their words as text boxes (`<id>`, `<id>#n`) | native |
| Tables | Native table; split into stacked tables when rows build on separate steps | native / approximated |
| Shadows (`sys.shadow`), SVG lift | `a:outerShdw` (spread → shadow scale) | approximated: the inset highlight is lost |
| Frost (`sys.material.frost*`) | Translucent fill | approximated: backdrop blur and saturate lost |
| Bokeh orbs (`sys.ambient`) | Radial-gradient ellipse, `a:softEdge`, alpha; marked decorative | approximated: drift lost |
| Fonts (`sys.font`) | Theme major/minor names, not embedded | approximated: PowerPoint substitutes if missing |
| Deck chrome, notes pane, veil | Not exported | lost |
| Components-layer softening (scene backdrop blur), shape opacity | Opacity kept as alpha; blur dropped | `undeclared`, listed in the report |

## 4 · Steps

One click per HTML step, in order (`animations.py`, PB-022): entrances fade in or appear, exits
fade out or disappear, dimming is a Transparency emphasis, fills recolour (to a theme colour
reference when the new fill is a palette colour), moves are motion paths. Text inside a placeholder builds **by paragraph**. Policy for deltas with no native effect
(PRD *PPTX step-delta policy*):

- a scene **camera move** starts a duplicate slide with a **Morph** transition (`!!`-named shapes
  on both slides); the next click is the slide change;
- text and line colour changes (step-list current/done) and bullet marker fills are **dropped**:
  the slide keeps the look the scene measured; blur softening is **lost**;
- a step whose every change is dropped gets no click (listed in the report).

## 5 · Corporate templates (re-flow)

Placeholder text carries theme references, so it takes the destination's theme. In PowerPoint:
**Home → Reuse Slides** (or paste with **Use Destination Theme**), then **Reset** on each slide to
take the template layout's positions (assumed from PowerPoint's documented behaviour; confirm in
§6). Free shapes (cards, diagrams) keep their places, scaled to
the slide size. `check.py reflow deck.pptx -o out.pptx --template corporate.pptx` does the same
copy for a quick look and for tests (layouts matched by name, then type).

## 6 · Presenter check in PowerPoint

Open the `.pptx` and look, slide by slide (no tool replaces this):

1. Click into a title and a body paragraph and type: it is live text in a placeholder.
2. **Design → Variants → Colors**: pick another scheme; text, cards, tiles and edges recolour.
3. **Slide Show**: each click reveals what the HTML step did, in order; a camera move morphs.
4. **Animation Pane**: effects are named and ordered; nothing fires on its own.
5. Compare against the HTML at the same step for text wrap and overflow (PX-06).
6. Reuse two slides into a corporate template (§5): text takes its fonts and colours.
