# Architecture contract

The stable API beneath every design layer: one single-file deck, a fixed layer order, a
data-attribute authoring contract, a component API (class names, slots, states) and shared SVG defs,
all driven by one define-once engine. Read before writing slide markup, styling a design layer,
writing an engine module, or assembling a deck. Design layers **style** this contract; they never
change it. A change here is a contract change: update this file, the engine and its tests together.

Files (copied into the deck, never loaded into context):
`assets/templates/deck-skeleton.html` (the shell), `assets/engine/arch.css` (`@layer arch`
mechanics), `assets/engine/engine.js` (the core engine), `assets/engine/modules/` (optional modules, §9).

**Contents:** 1 Guarantees · 2 File anatomy and layer order · 3 Slide authoring contract ·
4 Steps · 5 Component API · 6 Shared SVG defs · 7 Engine API and modules · 8 Motion ·
9 Optional modules · 10 Never

## 1 · Guarantees

- **Single file:** the deck is one self-contained HTML file: fonts embedded as base64, CSS and JS
  inline, no build step to view. Exactly one `<script>` element (modules, then the engine).
- **Offline:** it makes no network request when opened (fonts, images and icons are inline); remote
  URLs appear only as citation link targets (`a.src[href]`), which open in a new tab.
- **Endpoint-safe:** nothing that trips endpoint or mail-gateway heuristics: no remote scripts,
  stylesheets, `@import`, iframes, forms or objects; no `eval`, `new Function`, `atob`,
  `document.write`, `innerHTML`/`outerHTML`, `fetch` or dynamic `import`. The engine builds DOM with
  `createElement`, `cloneNode` and `textContent` only.
- **Define once:** slides carry only semantic content plus the attributes below: **no** `style`
  attributes, `<style>`, `<script>` or colour literals in slide markup. Anything new is added once
  to a layer or the engine and documented here.

## 2 · File anatomy and layer order

```css
@layer arch, components, palette, style, deck;
```

Declared first in the one `<style>`; a later layer overrides an earlier one regardless of
specificity, and an `!important` in an earlier layer beats a later one (used only by `arch`'s
notes-mode rule, §8). Each block below is filled once, between its markers, by the assembler; a
theme swap replaces only `PALETTE`/`STYLE` (and `COMPONENTS` for a layout swap), never `SLIDES`.

| Block (markers) | Holds | Owner |
| --- | --- | --- |
| `/* FONTS:BEGIN */ … /* FONTS:END */` | `@font-face` rules with base64 woff2 (unlayered) | style |
| `/* ARCH:BEGIN */ … /* ARCH:END */` | `assets/engine/arch.css`, then the included modules' CSS (§9): `@layer arch` mechanics | architecture |
| `/* COMPONENTS:BEGIN */ … /* COMPONENTS:END */` | `@layer components`: layout and component CSS; reads only sys/comp tokens | layout |
| `/* PALETTE:BEGIN */ … /* PALETTE:END */` | `@layer palette`: colour-role custom properties | palette |
| `/* STYLE:BEGIN */ … /* STYLE:END */` | `@layer style`: type, depth (shadow, frost, ambient look), motion tokens | style |
| `/* DECK:BEGIN */ … /* DECK:END */` | `@layer deck`: deck-wide overrides, rare and justified | deck author |
| `<!-- DEFS:BEGIN --> … <!-- DEFS:END -->` | shared SVG defs (§6) inside the hidden `svg.defs` | architecture |
| `<!-- SLIDES:BEGIN --> … <!-- SLIDES:END -->` | the slides, inside `main.deck` | content |
| `/* MODULES:BEGIN */ … /* MODULES:END */` | the included optional modules (§9), before the engine | architecture |
| `/* ENGINE:BEGIN */ … /* ENGINE:END */` | `assets/engine/engine.js` | architecture |

`{{title}}` and `{{subtitle}}` in the skeleton are the deck title and its subtitle (bar and
`<title>`). The skeleton also carries the fixed chrome: `header.bar`, the notes chrome and the
`svg.defs` host (§5).

`arch.css` holds only what the engine relies on (fixed chrome positions, snapping, hidden-until-step
states, the veil mask, notes-mode instant). It uses CSS system colours (`Canvas`, `CanvasText`,
`Highlight`, `GrayText`) so an unthemed deck still works; it holds no palette, type, depth or motion.

## 3 · Slide authoring contract

Each slide is `section.slide#<id>` directly inside `main.deck`, between the SLIDES markers. The
engine discovers everything from these attributes:

| Attribute | On | Meaning |
| --- | --- | --- |
| `data-chapter="<Chapter>"` | `section.slide` | Chapter name. The agenda lists distinct values in slide order, so every slide of a chapter repeats the same value |
| `data-ambient` | `section.slide` | Build the ambient layer (`div.ambient` of orbs) behind this slide; drifts only while the slide is current. Value reserved (empty = default effect) |
| `data-show-at="n"` | any element, HTML or SVG | Hidden before step `n`, revealed (`.is-visible`) from step `n`. Keeps its layout space while hidden |
| `data-hide-at="n"` | any element, HTML or SVG | Hidden from step `n`. Pair with `data-show-at` on a replacement at the same place to **swap** at step `n` |
| `data-at="n"` | step-only element, e.g. an `.overlay` | Shown (`.is-shown`) at exactly step `n`, never before or after, never in notes mode |
| `data-for="#id"` | `aside.note` | Reader note for the element `#id` on the same slide (a module may resolve other targets, §7) |
| `data-from="#a"` `data-to="#b"` | `path.edge` in `svg.diagram` | The engine draws a gapped straight or curved connector between the two tiles' rects (omit `d`) |
| `data-notes="prev\|next\|close"` | buttons in `nav.notes-nav` (skeleton chrome) | Notes-bar actions; not for slides |

Slots (styled by the layout layer): `p.kicker`, `h2.title` (one per build phase allowed, swapped
with `data-show-at`/`data-hide-at`), one `div.body` (or stepped sibling bodies), then step-only
elements, then `aside.note`s. Modifiers such as `.slide--lead` and body layouts belong to the layout
part, not this contract.

Reader notes: `aside.note[data-for] > h3 + p… + a.src[href]` (the real source; link text = source
name). Notes are never displayed in place (`.note` is `display: none`); notes mode copies their
children into the callout and gathers the `a.src` links into a `p.cite` line.

Diagrams: `svg.diagram[viewBox]` with groups `g.layer-edges`, `g.layer-nodes`, `g.layer-key`,
`g.layer-labels` in that order. A tile is `g.tile#id > rect[x y width height] + text…` with no text
coordinates: the engine centres the lines as one block in the rect, and tiles sharing a row (same
`y` and height) share one title baseline. Edges carry `marker-end="url(#arr)"`.

## 4 · Steps

- A slide's step count = the largest `data-show-at` or `data-at` on it; step 0 is the slide on entry.
- **One input = one step:** →, ↓, Space, PageDown, a click on the slide and one wheel gesture
  advance; ←, ↑, PageUp go back; Home/End jump to the first/last slide. A slide is left only after
  its last step; going back onto a slide lands on its last step. The deck's ends are stops.
- A wheel gesture (a burst of events) steps once; a click on a link or button does not step.
- `ol.steps > li[data-show-at]`: the latest revealed item gets `.is-current`, earlier ones `.is-done`
  (the layout layer may keep unrevealed items visible but dim by overriding the hidden state).
- Step-only elements (`[data-at]`): when one replaces another, the newcomer gets `.is-delayed` so the
  design can hold its entry until the outgoing one has gone; the outgoing one gets `.was-shown` for
  ~0.9 s so its exit can differ from its entry. While an `.overlay[data-at]` is shown, its slide gets
  `.is-overlaid` (the design softens the body); other step-only elements do not soften.

## 5 · Component API

Classes the design layers style. **Author-side** classes are written in slide markup; **chrome** is
fixed markup in the skeleton; **engine-built** elements are created at load.

| Component | Markup / class names | States set by the engine |
| --- | --- | --- |
| Slide | `section.slide` · slots `.kicker`, `.title`, `.body` | `.is-active` (current slide), `.is-overlaid` (an overlay shown) |
| Revealed part | `[data-show-at]`, `[data-hide-at]` | `.is-visible` |
| Step list | `ol.steps > li` | `.is-current`, `.is-done` |
| Overlay (Insight etc.) | `aside.overlay.overlay--<variant>[data-at]` | `.is-shown`, `.is-delayed`, `.was-shown` |
| Title bar (chrome) | `header.bar > p.bar-title > a.bar-home (title, span, em)`, `nav.nav > button.nav-current + ol.agenda`, `div.progress` | `.bar--compact` (row would come within 32 px of the title: measured, not a breakpoint), `.nav.is-open` (compact list opened by click) |
| Agenda item (engine-built) | `ol.agenda > li[data-chapter] > button` | `li.is-current` + `button[aria-current]`, `li.is-done`; progress width as a percentage |
| Ambient (engine-built) | `div.ambient > div.orb.orb--far\|orb--mid\|orb--near.orb--1…5` (5 far, 6 mid, 6 near; seeded placement) | inline `transform` drift on the current slide only |
| Diagram | `svg.diagram`, `g.tile > rect + text.tile-title + text.tile-sub`, `path.edge` | `--k` custom property (SVG units per screen px, for screen-size floors), tile text `x`/`y`, edge `d` |
| Notes toggle (chrome) | `button.notes-btn` | `aria-pressed`; `body.notes-on` |
| Notes chrome | `div.veil` (mask window via `--x --y --w --h`), `div.ring`, `div.callout` (`h3`, `p`, `p.cite > a.src`), `nav.notes-nav > button[data-notes] + span.notes-pos` | `body.notes-focus` (a note is focused), `.callout.fade-t` / `.fade-b` (more to read above/below) |
| Pin (engine-built) | `button.pin` (number) | `.is-current`, `.is-covered` (under the callout or no free spot), `.is-offstage` (target not on screen at the shown step) |
| Root | `html` | `:root.still` (reduced motion or notes mode), `:root.instant` (notes mode), `--notes-shift` |

## 6 · Shared SVG defs

One hidden `svg.defs` (kept renderable, never `display: none`, so `url(#id)` resolves) holds, between
the DEFS markers: filters `#lift` (tile drop shadow) and `#lift-key` (with a `.glow` drop shadow, for
key tiles), and markers `#arr` (default arrowhead, scales with stroke width), `#arr-ok` and
`#arr-loss` (the same head sized for heavier coloured edges). Diagrams reference them with
`filter: url(#lift)` (from CSS) and `marker-end="url(#arr)"`; the palette colours them via
`#lift feDropShadow`, `#arr path` etc. Never copy a def into a slide.

## 7 · Engine API and modules

`window.deck = { ready, state(), goto(id, step), next(), prev(), plan() }` for tests and tooling:
`state()` → `{ slide, index, step, steps }`; `plan()` → `[[slideId, maxStep], …]`.

**Modules** are optional behaviours in the MODULES block. Each pushes one object onto
`window.deckModules` before the engine runs:

```js
(window.deckModules = window.deckModules || []).push({ name: 'example', init(api) {}, render(s, k, ctx) {} });
```

Every hook is optional; `s` is a slide record `{ node, id, chapter, steps }`, `k` a step.

| Hook | Called | Use |
| --- | --- | --- |
| `init(api)` | once, before the first render | build DOM, read attributes; may raise a slide's `steps`. `api`: `slides`, `$`, `$$`, `el`, `seeded`, `clamp`, `layoutDiagram(svg)` (re-lay a diagram after resizing it), `state()`, `show`, `goto`, `next`, `prev`, `render`, `settle`, and getters `still`, `instant`, `notesOn` |
| `place(s, k, ctx)` | before newcomers in `ctx.entering` are shown | position step-only elements (e.g. tiles) |
| `render(s, k, ctx)` | after every render of a slide | update the module's state; `ctx = { quiet, current, entering, instant, still }` (`quiet` = notes mode) |
| `overlaid(s, k, ctx)` | each render | return true to soften the slide (`.is-overlaid`) |
| `settle()` | in notes mode, after a render | finish timed sequences at their end state |
| `instant(on, still)` | notes mode toggles | stop or resume looping motion |
| `noteTarget(sel, s)` | a note's `data-for` matches nothing on its slide | return the target element |
| `noteRange(target, s)` | per note | return `[lo, hi)`: steps at which the target is on screen |
| `noteFrame(target)` | placing pins | return a rect that frames the target (pins it covers are clipped) |

A deck that declares no module carries none: the core works on its own. Module files, the inclusion rule and each module's contract: §9.

## 8 · Motion

- `prefers-reduced-motion: reduce` sets `:root.still` at load: slide changes land without a smooth
  scroll and the ambient layer never drifts. Design layers **MUST** scope their reduced-motion rules
  to `:root.still` (fades allowed; no travel, scale or blur motion).
- Notes mode sets `:root.still` and `:root.instant`: every transition and animation in `.deck`
  lands at its end at once (arch's `!important` zero-duration rule), and the engine finishes any
  running ones, so the spotlit target is fully drawn when the spotlight lands. Chrome (veil, ring,
  callout) may still fade.

## 9 · Optional modules

<!-- modules:begin -->
Behaviours beyond the core, each an optional module the deck carries only when its slides use it.

**Files:** `assets/engine/modules/<name>.js` (registers on `window.deckModules`, §7) plus, when it
needs mechanics, `assets/engine/modules/<name>.css` (one `@layer arch` block, system colours only, no
palette, type, depth or motion beyond the functional defaults named below). Each JS file's header
carries a `Triggers:` line of simple selectors (`[data-attr]` or `.class`).

**Inclusion rule (assembler):** a module ships in a deck only when one of its triggers appears in the
SLIDES block; its JS then goes in the MODULES block (modules in name order, before the engine) and its
CSS after `arch.css` in the ARCH block. A deck with no trigger carries no module code. Modules never
call each other: they meet only through core state (e.g. `.is-overlaid`).

Look, entry/exit motion and the place of a module's columns or slots in the slide grid belong to the
design layers. A design layer **MUST** scope a module part's look to its shown state (e.g.
`.is-dim.is-visible`), since any later layer beats arch's hidden state.

### Scene · `modules/scene.js` + `modules/scene.css`

One persistent diagram shared by consecutive scene slides; it moves between their states like a camera.
Triggers: `[data-scene]`, `.scene`. Hooks: `init`, `render` (current slide only), `noteTarget`, `noteRange`.

| Markup / attribute | On | Meaning |
| --- | --- | --- |
| `div.scene > svg.diagram > g.cam > …` | one per deck, in `main.deck` before the slides | The scene, fixed on screen behind slide text; diagram kit rules (§3) apply. `g.cam` is the camera group |
| `data-scene` | `section.slide` | A live scene slide: the scene is on and fitted to its slot |
| `data-scene="backdrop"` | `section.slide` | Backdrop slide: the scene stays at the state reached so far, softened behind the body |
| `div.scene-slot` | child of a scene slide | Empty placeholder the layout layer places; the scene takes its box |
| `data-scene-at="slide:step"` | any scene part | Shown from that slide-point on, across later scene slides. A point on a slide raises that slide's step count |
| `data-scene-until="slide:step"` | any scene part | Hidden from that slide-point on |
| `data-scene-is="name slide:step [slide:step], …"` | any scene part | Adds `.is-<name>` from the first point until the optional second |
| `data-camera="x y scale, step: x y scale, …"` | scene slide | Camera per step: the entry with the largest step ≤ the current one wins (no step = 0). Translate in viewBox units, scale about the viewBox centre. Unset: `0 0 1`; a backdrop without it keeps the last live scene slide's camera at that slide's last step |

States: `.scene.is-on` (the current slide is a scene slide), `.is-soft` (its slide is `.is-overlaid`:
a pop-over or Insight has focus), `.is-backdrop`; parts `.is-visible`, `.is-settled` (carried on screen
by a jump, not at its own point: the design may skip its entrance), `.is-<name>`. Every scene slide's
`.title` gets a `min-height` equal to the tallest scene title, so the slot (and the scene's place and
scale) never moves with title length. Notes: a `data-for` on a scene slide may name a scene part; its
step range comes from its scene points. Functional defaults in arch: soft = blur 3px at .55 opacity,
backdrop = blur 12px at .42; the style layer re-tunes them and adds every transition (the camera's
tween is `.scene .cam { transition: transform … }`). Slides stay transparent so the scene shows.

### Narration tiles · `modules/narration.js` + `modules/narration.css`

Short message tiles that narrate a build, in free space beside it. Triggers: `.narration`,
`.narr-tile`. Hooks: `init` (re-place on resize), `place`.

Markup: `div.narration > article.narr-tile[data-at]` (any content, e.g. a sender line and a quote).
The core shows a tile at exactly its `data-at` step; **1–2 tiles per step** (a step may carry none);
the focus is read from the slide's `data-show-at` parts. Before
newcomers enter, the module sets each tile's `left`, `top` and `width` in the column: staggered (a
pair leans apart; seeded per slide + step), centred on the slide parts that step reveals, inside the
column's free band (below any `.title`/`.kicker` or `.bar` over its upper half, above the `.notes-btn`
or anything over its lower half), clear of tiles still leaving when there is room, and at full column
width when the band is short. States (core): `.is-shown`, `.is-delayed`, then `.was-shown` (~0.9 s:
the design softens it out), after which arch hides it (`visibility: hidden`). Tiles never soften the
slide or the scene.

### Pop-overs · `modules/popover.js` + `modules/popover.css`

An illustration on a lifted tile over the slide and scene for a step range. Triggers: `.popover`.
Hooks: `overlaid`, `noteFrame`.

Markup: `div.popover[data-show-at][data-hide-at]` (any content, e.g. `figure` panels); the core
reveals it (`.is-visible`) at its `data-show-at` step and hides it at its `data-hide-at` exit step,
where the design dissolves it. While one is
revealed the slide is `.is-overlaid` (the body softens; a scene goes `.is-soft`). In notes mode a
target inside a pop-over frames pins by the whole pop-over: pins behind it are clipped where it covers
them. Arch: it paints above the slide's other children.

### Tile row · `modules/tile-row.js` + `modules/tile-row.css`

A row of 2–4 equal text tiles, often over a backdrop scene. Triggers: `.body--tiles`. Hooks: `init`
(re-measure on resize and font load), `render` (current slide).

Markup: `div.body.body--tiles > article.text-tile[data-show-at]` (heading, points or a quote); the
core reveals the tiles by their `data-show-at` steps. Arch: equal-width columns that may shrink. The module sets
`.body--tiles.is-tight` when the tiles overflow the row at their natural spacing (measured, not a
breakpoint) so the layout layer can tighten them, and clears it when they fit.

Left out of the reference deck's versions (content-specific, not reusable): seeded crowds of dots,
links and pulses drawn from counts, multi-stage re-layouts of the scene, a one-row key that shrinks to
fit, and timeline day counts.
<!-- modules:end -->

## 10 · Never

- **NEVER** put `style`, `<style>`, `<script>` or colour literals in slides; extend a layer once.
- **NEVER** read `--ref-*` tokens or colour literals in the components layer, or put palette, type
  or motion in `arch`.
- **NEVER** add an engine behaviour that a slide's markup can't declare through an attribute in §3
  or a module (§7, §9).
- **NEVER** add an attribute or state class without a row here and a test.
