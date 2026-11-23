# Layout and components

The **layout** design layer: how every component in the architecture's component API looks and
where it sits, as one CSS file in `@layer components`. Read before writing slide markup that picks a
layout variant, before styling or reviewing a component, and before adding a component. Colour and
material come from the palette and style tokens (see the tokens part); this layer only decides
geometry, which role each part uses, and motion shape.

File: `assets/components/components.css`, pasted between the skeleton's `COMPONENTS` markers by the
assembler. It is the deck's calm editorial look: serif titles over sans body, charcoal on paper, one
accent, frosted cards (opaque, shadowed pop-over tiles), line-drawn diagrams and illustrations, generous
type for screen-share. A worked example built with it (`examples/hf-incident/`) is checked against the
reference deck it came from; `deck-bright.html` beside it is the same deck after `swap --palette
bright-primaries` (slides byte-identical), proof the layer reads roles only.

## 1 · Rules (binding)

- **Tokens only.** Read `--sys-*` roles and this layer's own `--comp-*` aliases (all defined on
  `:root` at the top of the file, except `--comp-orb-tint`, set per `.orb--N`), plus the engine's
  `--k`. **NEVER** read `--ref-*`, never write a colour literal (hex, `rgb()`/`hsl()`/`color()`,
  named or system colours). `transparent` and `currentColor` carry no hue and are allowed (fades in
  `color-mix`, mask stops use an opaque role since masks read only alpha).
- **Define once.** A new look is a new rule here (or a new `--comp-*`), never a slide `style`.
  Never invent a component for one slide: propose it, prototype it, then add it here and below.
- **Motion** reads the style's durations/curves (or `--comp-motion-*` multiples of them).
  Reduced motion lives under `:root.still` only: fades, no travel, scale or blur motion.
- **Module parts** (scene, narration, pop-overs, tile row) are styled scoped to their shown state
  (`.is-visible`, `.is-shown`, `.scene.is-on…`): arch's hidden state must still win when hidden.
- **Fit:** nothing collides at 1920×1080, 1280×720 and 1288×598; short screens (≤ 660px high)
  tighten via `@media (max-height: 660px)`, never by shrinking titles.
- Checked by the skill's tests: token lint, computed-style parity with the reference deck, and a
  layout guard over every fixture slide × step × review size.

## 2 · Layout variants

| Variant | Markup | Use when |
| --- | --- | --- |
| Standard | `section.slide` · grid `kicker / title / body`, padding below the bar | Use when a slide has a kicker, a title and one body: the default |
| Lead (title) | `section.slide.slide--lead` (+ `data-ambient`, `p.byline`) | Use when opening the deck or a summary: big lead title (≤ 20ch), body below, vertically centred; byline pinned bottom-left |
| Closing | `section.slide.slide--lead.slide--end` | Use when closing: one lead-size line centred on the whole page, no kicker |
| Closing with prompts | `section.slide.slide--lead.slide--end > h2.title + div.body > ol.prompts` | Use when the close asks the room questions: the closing finding drops to title size, centred and clear of the bar, over the numbered prompts (centred block, left-aligned text); prompts may arrive by step |
| Flow body | `div.body` | Use when the body is text, a list, a table or terms: centred in the body area |
| Split | `div.body.body--split` (36 / 64) | Use when text or a step list sits beside a diagram (narrow left, wide right); a `div` column stacks its blocks evenly |
| Split, flipped | `div.body.body--split.body--flip` (64 / 36) | Use when wide content sits left and a quote or message card right |
| Stack | `div.body.body--stack` | Use when a diagram takes the width with a quote or caption under it (diagram takes the free height) |
| Layers | `div.body.body--layers` | Use when build phases can't fit together: children share one cell and swap by `data-show-at`/`data-hide-at` |
| Figure column | `div.fig > svg.diagram + div.fig-notes > p.annot…` (inside a split) | Use when a diagram needs short annotation cards under it that swap by step |
| Narration column | slide with a `div.narration` child | Use when message tiles narrate a build: a right column (`--comp-narr-width`) spans kicker → body; an Insight or pop-over may span both |
| Three-column scene | `section.slide[data-scene]` + `div.scene-slot` | Use when one shared diagram persists across slides: body (≈30%, step list at small size) · scene slot (≈40%) · narration (≈30%), title spanning the top; pop-overs and Insights span slot → narration (`.popover--left`: body → slot, so a step can carry a pop-over and a narration tile), a tile row spans all three |
| Timeline | `div.body.body--timeline > ol.steps > li` (`strong` date, then the event; `li.sub` sub-entries) | Use when a body is a dated sequence, on any slide (standard, split column or a scene's body): each entry appears at its step (none shown ahead), the date on its own line in ink |

Stepped titles and bodies (one `h2.title` or `div.body` per phase, swapped by step) share their grid
cell.

**Fitting diagram text.** SVG text never wraps and grows to its floor on small screens, so a label
that fits at 1920 can spill at 1288. Anchor a label at the edge it grows away from
(`.label--start` / `.label--end`), keep it inside the diagram's `viewBox` at every review size
(the layout guard flags text outside it as `outside diagram`), and break a long one into lines
yourself with `<tspan x="…" dy="1.2em">`, splitting where the words allow: a name that must stay
together ("12 Cross-town") stays on one line. In HTML copy, join such a name with a no-break space
(`&nbsp;`), never a span class. Too long still: reword shorter (voice profile), never shrink the
type. Overlays, pop-overs, tile rows and narration stop above the always-visible Notes button
(`--comp-notes-clear`).

## 3 · Components

Each row: classes and states (from the architecture's component API), what it looks like, and the
tokens it reads. `--sys-type-<role>-*` means that role's family/size/weight/leading/tracking.

| Component | Classes · states | Look | Tokens |
| --- | --- | --- | --- |
| Page | `html`, `body` | Paper ground, ink text, body type | `--sys-color-paper`, `--sys-color-ink`, `--sys-type-body-*` |
| Title bar | `.bar`, `.bar-title` (`span` dot, `em` subtitle), `.bar-home` | Frosted chrome strip `--comp-bar-height` high; serif title, muted dot, italic ink-2 subtitle; home link dims on hover | `--sys-material-chrome*`, `--sys-type-title-family`, `--sys-type-title-weight`, `--sys-color-ink-2`, `--sys-color-ink-3`, `--comp-bar-*` |
| Agenda | `.nav`, `.agenda li button`, `li.is-current`, `.agenda:hover` | Every chapter labelled, no dots; current = accent-ink label on a resting tile pill; hover lifts one, softens the rest | `--sys-color-accent-ink`, `--sys-color-tile`, `--sys-shadow-rest`, `--sys-shadow-lift`, `--sys-font-sans`, `--sys-motion-duration-fast`, `--comp-agenda-size`, `--comp-radius-pill` |
| Compact agenda | `.bar--compact`, `.nav-current` (+ chevron), `.nav.is-open` | Current chapter + chevron; drops an **opaque** tile panel (a nested backdrop blur fails inside the frosted bar) | `--sys-color-tile`, `--sys-shadow-soft`, `--comp-radius-panel` |
| Progress | `.progress` | Accent hairline under the bar, width eases | `--sys-color-accent`, `--sys-motion-reveal` |
| Kicker | `p.kicker` | Sans 600 uppercase, tracked, accent-ink | `--sys-type-kicker-*`, `--sys-color-accent-ink` |
| Title | `h2.title` (≤ 1 `em`), `.slide--lead .title` | Serif 500, tight leading, balanced wrap, ≤ 34ch (lead ≤ 20ch at lead size) | `--sys-type-title-*`, `--sys-type-lead-size`, `--sys-type-lead-leading`, `--sys-type-lead-tracking`, `--comp-measure-title`, `--comp-measure-lead` |
| Byline | `p.byline` | Small italic serif, ink-2, bottom-left, sharp | `--sys-font-serif`, `--comp-byline-size` |
| Body text | `.body p`, `p.caption`, `p.stat > strong`, `blockquote` + `p.cite` | Text size in ink-2, ≤ 46ch; caption small; stat = one huge serif number over an overlay-size label; quote = italic serif | `--sys-type-text-size`, `--sys-type-small-size`, `--sys-type-stat-*`, `--sys-type-overlay-*`, `--comp-measure-text`, `--comp-measure-wide` |
| Points | `ul.points > li` | Accent dash bullets at text size | `--sys-color-accent`, `--sys-type-text-size` |
| Step list | `ol.steps > li`, `.is-current`, `.is-done`, `li.sub` | Numbered discs: waiting = hollow ink-3 ring, current = accent disc + ink text, done = filled ink-2 disc; text never below ink-2; unrevealed items stay visible (except in a timeline); a sub-entry is un-numbered, marked by a short ink-3 dash | `--sys-color-accent`, `--sys-color-ink*`, `--sys-type-text-*`, `--comp-motion-state` |
| Terms | `dl.terms > div > dt + dd` | Columns, each topped by a soft rule; serif term | `--comp-rule`, `--sys-font-serif` |
| Prompts | `ol.prompts > li.prompt` | Numbered serif questions on accent discs | `--sys-type-overlay-*`, `--sys-type-kicker-*`, `--sys-color-accent` |
| Table | `.body table`, `th`, `td`, `table.compare` | Kicker-style header, soft row rules, first column emphasised; tighter on short screens | `--comp-rule`, `--sys-type-kicker-*`, `--sys-type-text-*` |
| Entry | `.slide.is-active > .kicker/.title/.body` | Content rises and fades in, staggered | `--comp-motion-entry`, `--comp-motion-entry-rise`, `--sys-motion-duration-slow`, `--sys-motion-ease`, `--sys-motion-ease-rack` |
| Revealed part | `[data-show-at]`, `[data-hide-at]`, `.is-visible` | Rises `--sys-motion-rise` into place | `--sys-motion-duration-base`, `--sys-motion-rise`, `--sys-motion-ease` |
| Insight overlay | `aside.overlay.overlay--insight`, `.is-shown`, `.is-delayed`, `.was-shown`; slide `.is-overlaid` | One frosted card (label "Insight" in kicker style, serif statement), bottom-right, `--comp-overlay-width`; rises in sharp, exits by rack focus; the body softens beneath | `--sys-material-frost`, `--sys-material-blur`, `--sys-material-saturate`, `--sys-shadow-overlay`, `--sys-type-overlay-*`, `--comp-frost-filter`, `--comp-overlay-pad`, `--comp-radius-overlay`, `--comp-rack-blur`, `--comp-soften-blur`, `--comp-soften-opacity`, `--comp-motion-handover`, `--sys-motion-ease-late` |
| Message card | `div.msg-card > p.msg-agent + blockquote.msg-text + p.cite` (`p.msg-from` = same as `.msg-agent`) | In-flow agent voice: dense frost card, kicker-style sender, serif quote with CSS quote marks | `--sys-material-frost-dense`, `--sys-type-msg-*`, `--comp-card-pad`, `--comp-radius-card` |
| Ambient | `div.ambient > .orb.orb--far/mid/near.orb--1…5` | Soft radial orbs in three blur planes, tinted per index | `--sys-ambient-*`, `--comp-orb-tint` |
| Diagram tile | `g.tile > rect + text.tile-title + text.tile-sub`, `g.tile.tile--centred` | Borderless tile fill, `#lift` shadow, `--comp-radius-tile` corners; sans title ink, sub ink-2. Tiles in a row share one title baseline; `.tile--centred` centres its own text block instead (a one-line tile among two-line siblings). Never use tiles as chart bars: use the chart parts | `--comp-tile-fill`, `--sys-type-d-title-*`, `--sys-type-d-sub-*`, `--comp-tile-title-floor`, `--comp-tile-sub-floor` |
| Key tile | `g.tile.tile--key` (in `.layer-key`) | Accent-tinted fill, `#lift-key` glow, ink text | `--comp-key-fill` |
| Edge | `path.edge`, `.edge--reinforced`, `.edge--ok`, `.edge--loss` | Ink-3 line, round caps, gapped; reinforced = thicker ink-2; ok/loss = heavier accent/loss with matching heads (`#arr-ok`, `#arr-loss`) | `--comp-edge-stroke`, `--comp-edge-width`, `--comp-edge-floor`, `--comp-edge-strong`, `--comp-edge-strong-floor`, `--comp-edge-reinforced`, `--sys-color-loss` |
| Labels | `text.label`, `text.tag`, `.tag--loss`, `.label--start`, `.label--end` | Tracked sans caps: label ink-2, tag accent-ink (loss: loss); middle-anchored at `x` by default, `--start` grows right from `x`, `--end` grows left (for an edge or axis). Fit rules below the table | `--comp-label-floor`, `--comp-tag-floor` |
| Chart parts | `rect.chart-bar` (`.chart-bar--key` = the focus series), `rect.chart-swatch` (`.chart-swatch--key`), `line.chart-axis`, `line.chart-grid`, `line.chart-target`; values and ticks are `text.label` | Bars and legend swatches: flat comparison fill or accent for the key series, 3px corners (swatches stay square), **no lift**; axis ink-3, gridline paper-deep, target a dashed accent-ink line, all at edge widths. Bars in `.layer-nodes`, swatches in `.layer-key`, lines in `.layer-edges`; drawn to scale from a stated baseline | `--comp-chart-fill`, `--comp-chart-radius`, `--sys-color-accent`, `--sys-color-accent-ink`, `--sys-color-ink-3`, `--sys-color-paper-deep`, `--comp-edge-*` |
| Domain | `g.domain > rect + text.domain-label`, `.domain--out` (in `.layer-edges`) | Soft paper-deep region naming where things run, borderless; `--out` = lighter (outside); tracked sans caps label in ink-2 | `--comp-domain-fill`, `--comp-domain-out-fill`, `--comp-domain-label-floor`, `--sys-type-kicker-size` |
| Dot · ring · link | `circle.dot` (`.dot--ink`, `.dot--loss`, `.dot--alarm`), `circle.dot-ring` (`.dot-ring--bold`), `line.link` (`.link--lit`, `.link--bold`, `.link--ink`) | Line-drawn actor: accent-tinted disc, accent-ink outline; ink = a leading role, loss = lost, alarm = fault light; ring = an actor singled out; link = hairline ink-3 at 40%, lit = accent-ink, bold = privileged path, ink = a leading role's | `--comp-dot-fill`, `--sys-color-accent-ink`, `--sys-color-loss`, `--sys-color-alarm` |
| Badge | `g.badge > circle + path… (+ rect, .badge-dot)`, `.badge--loss`, `.badge--off` | Status disc on a tile's corner: accent-tinted disc with ink line marks (tick, key, padlock); loss = loss disc, paper marks; off = paper-deep disc, ink-3 | `--comp-dot-fill`, `--sys-color-loss`, `--sys-color-paper-deep` |
| Glyph · icon | `path.glyph` (`.glyph--folder`), `g.icon` | Small lifted document/folder shapes (messages, files); a quiet ink-3 line drawing (globe, bell) | `--comp-glyph-folder-fill`, `--sys-color-tile`, `--sys-color-ink-3` |
| Diagram scale | `svg.diagram` `--k`, `.diagram--compact` | Every diagram size is `max(floor, --k × screen size)`, so text never drops below the type role on screen; compact = titles at the sub size | `--k`, `--sys-type-d-sub-size` |
| Shared defs | `#lift`, `#lift-key .glow`, `#arr`, `#arr-ok`, `#arr-loss` | Shadows tinted ink, glow accent, heads ink-3 / accent / loss | `--sys-color-ink`, `--sys-color-accent` |
| Annotation | `p.annot` (+ `strong.annot-lead`, `.annot-lead--loss`) | Plain lifted tile card, coloured run-in label, never a side bar | `--sys-shadow-lift`, `--comp-radius-panel` |
| Links | `a.src`, `.body .cite a` | Underline 1px, 3px offset, in the surrounding text colour; never blue | — |
| Notes toggle | `button.notes-btn`, `body.notes-on` | Chip-frost pill with an italic "i" disc; ink when notes are on | `--sys-material-chip`, `--sys-material-chip-blur`, `--comp-chrome-size` |
| Veil | `div.veil` | Paper veil, blurred, desaturated, with a window over the target | `--sys-material-veil`, `--sys-material-veil-blur`, `--sys-material-veil-saturate` |
| Spotlight ring | `div.ring` | Accent ring + soft accent glow, glides between targets | `--comp-ring`, `--comp-motion-glide` |
| Pins | `button.pin`, `.is-current` | Ink disc with an accent halo; current = accent | `--comp-pin-size`, `--comp-pin-halo` |
| Callout | `div.callout` (`h3`, `p`, `p.src-unlinked`, `p.cite > a.src`), `.fade-t`, `.fade-b` | Pane-frost card: serif heading, body text, a ruled cite line; soft fade at a scrolling edge | `--sys-material-pane`, `--sys-material-pane-blur`, `--sys-shadow-soft`, `--comp-note-title-size`, `--comp-note-text-size`, `--comp-note-cite-size` |
| Notes bar | `nav.notes-nav button`, `.notes-pos` | Static Prev / position / Next / Close, pill hover | `--comp-chrome-size`, `--sys-color-paper-deep` |
| Scene | `div.scene`, `.is-on`, `.is-soft`, `.is-backdrop`, `.cam`, parts `[data-scene-at].is-visible`, `.is-settled`, `.is-dim`, `.is-muted` | On: fades in; soft (focus elsewhere) = body softening; backdrop = heavy blur, faded, desaturated; camera glides; parts fade; dim (history) = 35%; muted (out of action) = glyphs and tiles grey | `--comp-soften-blur`, `--comp-backdrop-blur`, `--comp-backdrop-opacity`, `--sys-motion-duration-camera` |
| Scene key | `p.scene-key` (last child of `div.scene`) `> svg + text`, `span.scene-key-item[data-scene-at]` | One-row legend under the scene diagram, small ink-2 text, a dot per entry; entries may arrive by scene point | `--sys-type-small-size`, `--sys-color-ink-2` |
| Narration tile | `div.narration > article.narr-tile`, `.narr-tile--fact`, `.is-shown`, `.is-delayed`, `.was-shown` | Frosted message card (`--comp-card-frost`), placed by the module; rises in sharp, racks out; a fact tile drops the quote marks | `--comp-card-frost`, `--comp-narr-pad`, `--comp-narr-width`, `--comp-gap-narr` |
| Pop-over | `div.popover > figure.pop-panel` (`figcaption` with `span.pop-tag`, `svg.art`, `p`), `.pop-panel--wide`, `.popover--left`, `.is-visible` | Up to two **opaque**, shadowed tile cards over the softened scene (presenter, 23 Nov: never frosted); kicker-style tag over a serif caption, an illustration, a small note; wide = one spanning both; rack-focus exit; a successor waits the handover | `--sys-color-tile`, `--sys-shadow-overlay`, `--comp-pop-pad`, `--comp-radius-overlay`, `--sys-type-msg-*`, `--sys-type-kicker-*` |
| Illustration | `svg.art` parts: `.art-frame`, `.art-box`, `.art-chip`, `.art-card`, `.art-text`, `.art-title`, `.art-sub`, `.art-lead`, `.art-actor` (`.art-actor--ink`), `.art-path` (`.art-path--soft`), `g.art-try` (`path[pathLength=1]` + `.art-cross`), `.art-cross`, `.art-wall`, `g.art-pill` (rect + text), `.art-mark`, `g.art-flag` (`.art-flag--sealed`), `.art-doc`, `.art-doc-line`, `g.art-bubble`, `g.art-group` (an unstyled group of parts) | Small line-drawn scene in a pop-over (SVG units): paper frame, paper-deep boxes, an accent-tinted actor, ink-2 paths, accent pill with an ink tick, loss crosses; tries draw, fail and fade in turn (static at 50% under reduced motion) | `--comp-dot-fill`, `--sys-color-*`, `--sys-font-sans`, `--sys-motion-duration-slow` |
| Tile row | `div.body.body--tiles > article.text-tile`, `.is-tight` | 2–4 equal frosted tiles, one per step: serif heading, dot bullets, quote and cite at the foot, inset message card; tighter when `.is-tight` or on short screens | `--comp-tile-frost`, `--comp-tile-pad`, `--comp-inset-fill` |

## 4 · Component tokens (`--comp-*`)

Geometry and aliases owned by this layer. Colours are always `--sys-color-*` roles or mixes of them.

| Token | Holds |
| --- | --- |
| `--comp-bar-height`, `--comp-bar-pad-x` | Title bar height and side padding |
| `--comp-slide-pad-top`, `--comp-slide-pad-x`, `--comp-slide-pad-bottom` | Slide padding (top clears the bar) |
| `--comp-notes-clear` | Bottom margin that keeps cards above the Notes button |
| `--comp-gap-col`, `--comp-gap-stack`, `--comp-gap-narr` | Column gap (split), stack gap, narration/scene column gap |
| `--comp-measure-text`, `--comp-measure-title`, `--comp-measure-lead`, `--comp-measure-wide` | Line lengths |
| `--comp-radius-pill`, `--comp-radius-overlay`, `--comp-radius-card`, `--comp-radius-tile`, `--comp-radius-panel` | Corner radii |
| `--comp-overlay-width`, `--comp-overlay-pad`, `--comp-card-pad`, `--comp-narr-pad`, `--comp-pop-pad`, `--comp-tile-pad`, `--comp-narr-width` | Card sizes and padding |
| `--comp-rule` | Soft 2px paper-deep rule (terms, tables) |
| `--comp-bar-title-size`, `--comp-agenda-size`, `--comp-byline-size`, `--comp-chrome-size`, `--comp-note-title-size`, `--comp-note-text-size`, `--comp-note-cite-size`, `--comp-pin-size` | Chrome type and pin size (fixed chrome, not slide roles) |
| `--comp-edge-width`, `--comp-edge-floor`, `--comp-edge-strong`, `--comp-edge-strong-floor`, `--comp-edge-reinforced` | Edge widths (× `--k`) and their floors |
| `--comp-tile-title-floor`, `--comp-tile-sub-floor`, `--comp-label-floor`, `--comp-tag-floor` | Diagram text floors in SVG units |
| `--comp-tile-fill`, `--comp-key-fill`, `--comp-edge-stroke` | Diagram colour aliases (tile, accent-tinted key, ink-3) |
| `--comp-domain-fill`, `--comp-domain-out-fill`, `--comp-domain-label-floor` | Domain region tints (paper-deep 55% / 30% on paper) and label floor (SVG units) |
| `--comp-dot-fill`, `--comp-glyph-folder-fill` | Accent-tinted actor fill (dots, badges, illustration actors); folder glyph fill |
| `--comp-chart-fill`, `--comp-chart-radius` | Chart comparison-series fill (ink-3 into paper-deep) and bar/swatch corner radius (SVG units) |
| `--comp-card-frost`, `--comp-tile-frost`, `--comp-inset-fill` | Narration card frost (paper 84%), tile-row frost (paper 62%), inset message fill |
| `--comp-frost-filter` | Backdrop filter of frosted cards (style blur + saturate) |
| `--comp-soften-blur`, `--comp-soften-opacity`, `--comp-rack-blur`, `--comp-backdrop-blur`, `--comp-backdrop-opacity` | Softening beneath focus, rack-focus exit blur, scene backdrop |
| `--comp-ring`, `--comp-pin-halo` | Spotlight ring and pin halo (accent) |
| `--comp-motion-hover`, `--comp-motion-state`, `--comp-motion-handover`, `--comp-motion-glide`, `--comp-motion-entry`, `--comp-motion-entry-rise` | Motion aliases of the style's durations |
| `--comp-orb-tint` | Orb tint, set per `.orb--N` from `--sys-ambient-tint-N` |

## 5 · Adding or changing a component

1. Check the architecture's component API: the class and states must exist there (add them there
   first, with the engine and its test, if the engine sets them).
2. Prototype new visual language and get the presenter's verdict before building.
3. Add the rule here once, reading only sys/comp tokens; add any `--comp-*` to §4 and a row to §3.
4. Run the components tests (lint, parity, layout guard) and look at the assembled deck at every
   affected step and review size.
