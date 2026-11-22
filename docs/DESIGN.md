# Design rules

Binding visual rules for the deck. **MUST / NEVER** are binding; deviate only with presenter
approval. Each rule links to the prototype code that shows it (`P1`–`P4` below). The prototypes
are **frozen references**: if one is edited, re-check every link here in the same commit.

Build architecture (define once, apply per slide): ADR: ADR-001 (`docs/ADR.jsonl`), implemented in
`deck/deck.html` (v1, frozen reference: 18 slides). **v2** is a new file, `deck/deck-v2.html`, that
**MUST** reuse the same ADR-001 layers (tokens, components, shared SVG defs, one engine, §10 contract):
copy v1's CSS/engine, then extend once. Rules marked *v1 only* / *v2* below apply to that deck;
everything else binds both. Slide authors need only §10.

| Key | Prototype |
| --- | --- |
| P1 | [`01-palette-type.html`](../design/prototypes/01-palette-type.html) |
| P2 | [`02-chapters-depth.html`](../design/prototypes/02-chapters-depth.html) |
| P3 | [`03-notes-spotlight.html`](../design/prototypes/03-notes-spotlight.html) |
| P4 | [`04-diagram-swarm.html`](../design/prototypes/04-diagram-swarm.html) |

## 1 · Tokens (defined once on `:root`)

| Token | Value | Use | Code |
| --- | --- | --- | --- |
| `--paper` | `#F6F3EC` | Page ground | [P2:11](../design/prototypes/02-chapters-depth.html#L11) |
| `--paper-deep` | `#EDE8DD` | Quiet fills, active nav pill, rules | [P2:11](../design/prototypes/02-chapters-depth.html#L11) |
| `--tile` | `#FDFCF9` | Diagram tile fill (new token; prototypes inline it) | [P3:24](../design/prototypes/03-notes-spotlight.html#L24) |
| `--ink` | `#2B2A27` (12.9:1) | Titles, body | [P1 swatches](../design/prototypes/01-palette-type.html#L85) |
| `--ink-2` | `#5C5A55` (6.2:1) | Secondary text, Insight label | [P2:80](../design/prototypes/02-chapters-depth.html#L80) |
| `--ink-3` | `#8A867E` (3.3:1) | Labels ≥ 24px, arrows, sources | [P3:27](../design/prototypes/03-notes-spotlight.html#L27) |
| `--accent` | `#86BC25` (2.0:1) | Glows, fills, strokes, progress. **NEVER** text | [P2:35](../design/prototypes/02-chapters-depth.html#L35) |
| `--accent-ink` | `#4B6E10` (5.4:1) | Accent *as text* (chapter kickers) | [P2:41](../design/prototypes/02-chapters-depth.html#L41) |
| `--loss` | `#7A1F2B` | Deep oxblood: sacrifice, irreversible loss. Sparingly | [P4:15](../design/prototypes/04-diagram-swarm.html#L15) |
| `--alarm` | `#D2392C` | Signal red: a status light that something is down (s-4 crash). Only for alarm lights, never text or fills | in situ (S-021, `deck-v2.html` s-4) |
| `--serif` / `--sans` | Newsreader / Inter | Titles / everything else | [P1 pairing A](../design/prototypes/01-palette-type.html#L19) |

- **NEVER** name or brand the accent after any organisation; no corporate branding anywhere.
- Paper feel comes from colour, **NEVER** texture/grain (dies in Teams compression).

## 2 · Type

- Titles: serif 500, tight leading (~1.04), optional *italic* on one key word. [P2:42](../design/prototypes/02-chapters-depth.html#L42)
- Kicker: sans 600, uppercase, +0.14em tracking, `--accent-ink`. [P2:41](../design/prototypes/02-chapters-depth.html#L41)
- On-slide minimum ≈ 24px at 1920 wide; size with `clamp()` so small Teams windows stay legible. [P1 scale](../design/prototypes/01-palette-type.html#L96)

## 3 · Layout & navigation

- One chapter = one viewport; scroll **snaps** and stops per chapter. [P2:38–39](../design/prototypes/02-chapters-depth.html#L38)
- One input = one step: →/↓/space/PgDn/click/wheel advance; in-chapter steps (Insight, diagram
  builds) run before leaving the chapter. Wheel is throttled to one step per gesture. [P2 `next()`](../design/prototypes/02-chapters-depth.html#L201), [wheel lock](../design/prototypes/02-chapters-depth.html#L227)
- Persistent frosted title bar + accent progress hairline. [P2:22–35](../design/prototypes/02-chapters-depth.html#L22)
  Title: Title Case serif, then a muted `·` and a softer *italic* subtitle (ink-2, weight 400). [P5:34–36](../design/prototypes/05-header-bar.html#L34)
- Agenda (v2): every chapter always labelled, **no dots**; current = `--accent-ink` label. Hover lifts
  the pointed-at chapter (tile pill, small scale, lift shadow) while the rest soften slightly
  (blur ≈0.6px, ~72% opacity, still readable). [P5:41–53](../design/prototypes/05-header-bar.html#L41)
- Compact agenda: when the row would come within 32px of the title (measured, not a breakpoint),
  show only the current chapter's name + chevron; hover, focus or click drops an **opaque** `--tile`
  vertical panel (`--shadow-soft`; a nested backdrop blur can't work inside the frosted bar)
  listing every chapter, same current/hover treatment. [P5:55–69](../design/prototypes/05-header-bar.html#L55), [fit](../design/prototypes/05-header-bar.html#L131)
  v1 keeps its dots + label pill.
- Content settles in on chapter entry (rise + fade, staggered). [P2:48](../design/prototypes/02-chapters-depth.html#L48)

## 4 · Depth & ambient

- Bokeh: three blur planes (far 48px / mid 22px / near 6px) of soft radial orbs, slow drift +
  slight mouse parallax. [P2:57–59](../design/prototypes/02-chapters-depth.html#L57), [drift](../design/prototypes/02-chapters-depth.html#L249)
- Ambient **only** on title / summary / Insight pages; **NEVER** on detail or diagram pages. [P2 detail chapter](../design/prototypes/02-chapters-depth.html#L123)
- Respect `prefers-reduced-motion` (no drift, no rise). [P2:93](../design/prototypes/02-chapters-depth.html#L93)

## 5 · Overlays (one frosted-card component, three variants)

Base: translucent paper + `backdrop-filter` blur, soft lift shadow, large radius, left-aligned
prose. While shown, the content beneath softens (blur 3px, 55% opacity). [P2:68](../design/prototypes/02-chapters-depth.html#L68), [P2:82](../design/prototypes/02-chapters-depth.html#L82)

| Variant | Header | Body | Code |
| --- | --- | --- | --- |
| **Insight** | "Insight", kicker style in `--ink-2`; **no** accent tab | Serif statement | [P2:80](../design/prototypes/02-chapters-depth.html#L80) |
| **Agent message** | Agent name (verified attribution; neutral label if none) | Verbatim message; paraphrase flagged | not yet prototyped: same base as Insight |
| **Note** (reader) | Serif heading only; **no** "Note n of m" | Body + source link | [P3:58](../design/prototypes/03-notes-spotlight.html#L58) |

- **Entry:** rise into place, sharp. **Exit: rack focus**: overlay blurs out (0→16px) and fades
  late while the slide sharpens, ~0.8s. [P2:72–78](../design/prototypes/02-chapters-depth.html#L72), [toggle](../design/prototypes/02-chapters-depth.html#L211)
- **Agent-message cluster** (*v1 only*; superseded in v2 by narration tiles below; **NEVER**
  author new clusters in `deck-v2.html`): at each pop-up event, 1–5 message cards appear in a loose staggered
  scatter, **all sharp and readable**; no card is auto-highlighted. On **hover** (or keyboard
  `:focus-visible`) one card pops forward (lift, slight scale, stronger shadow, top z) while the
  others blur and their text fades; leaving restores them all. A single card sits centred. Exit is
  the same rack focus. (Presenter decision, Nov 2026: replaces the timed key-card rise.)
- **Handover:** when an overlay replaces another, the newcomer's entry waits ~0.35s for the old
  one's rack focus, so two half-blurred cards never share a frame.
- **Agent voice vs report voice:** agent quotes always use the message-card look (cluster or the
  in-flow `msg-card`); report and commentator quotes stay italic `blockquote` + cite.
- Use agent-message clusters (v1) at a few key moments only; spaced out, never back to back.
- **Insight** overlays stay in v2 unchanged, for key takeaways.

### 5a · Narration tiles (v2; replaces the cluster)

> **Provisional (20 Nov 2026):** the v2 first draft built to this section and to the v2 component
> additions in §10 (zone, mix bar, cut, fence, flag tile, `body--layers`, stepped titles, narration
> column) fell below the v1 quality bar. Re-prototype with the presenter before reusing any of them
> (PRD workstreams 6–7).

Agent messages narrate the swarm's thinking **as the diagram builds**. Presenter decision, Nov 2026.

- **Placement:** tiles sit **tastefully in the free space** to the right: a narration column
  (≈25vw, 300–540px) spanning kicker → body beside the title, so title and body narrow to its left
  and tiles can never cover the title or the diagram. **NOT a rigid column or table:** the engine
  staggers each tile's width and left offset (a step's pair leans apart, deterministic per slide +
  step) and centres the step's tiles on the diagram parts that step reveals (the current focus),
  moving clear of tiles still exiting when there is room. Tiles **MUST NEVER** cover the title or
  the diagram's active area (the tiles/edges the current step reveals).
- **Step-driven only:** each build step adds **1–2** tiles; on the next step the previous tiles
  exit (rack focus: blur out, then disappear) as the new ones enter. **NEVER** timed auto-highlight,
  hover-to-focus or more than 2 tiles on screen. A step may carry no tiles.
- **Look:** the agent-message card (frosted base, `p.msg-agent` label, verbatim quote); quote rules
  as §10 and VOICE. Entry rises in sharp; exit is §5 rack focus, then the tile is gone (newcomers
  wait ~0.35s). Reduced motion: opacity fade only. Unlike Insight, tiles **MUST NOT** soften the
  body: focus stays on diagram + latest messages.
- An Insight on a narrated slide takes its own step after the last tiles (handover rule applies)
  and may span the full width, since no tile is shown then.

## 6 · Reader notes (shareable mode)

- Quiet corner toggle (`N`), **always visible** (presenter decision: no idle fade; v1's 3 s fade
  is removed in v2), placed so it never covers an overlay or narration tile. Notes mode: whole page veils (blur 7px) except a rounded window over
  the target; accent ring + glow marks it. [P3:38–48](../design/prototypes/03-notes-spotlight.html#L38)
- Numbered pins just outside each annotated element's top-right corner (never on its text);
  current pin turns accent; pins the callout would cover hide. The callout never rises under the
  title bar. [P3:51](../design/prototypes/03-notes-spotlight.html#L51)
- Prev / position / Next / Close live in a **static** bar on the lower periphery, never in the
  moving callout. [P3:69](../design/prototypes/03-notes-spotlight.html#L69)
- Geometry re-tracks every frame while open (survives reflow). [P3 `track()`](../design/prototypes/03-notes-spotlight.html#L158)

## 7 · Diagrams

- Style: **line-drawn**, editorial. [P4 style A](../design/prototypes/04-diagram-swarm.html#L49)
- Tiles: **no border**; shape from the shared two-layer `#lift` shadow on `--tile`. Text centred
  both ways. [P3:24–25](../design/prototypes/03-notes-spotlight.html#L24), [P3 `#lift`](../design/prototypes/03-notes-spotlight.html#L86), [P4 board](../design/prototypes/04-diagram-swarm.html#L54)
- **Layer order = importance** (SVG paints in DOM order, so groups are declared in this order):
  edges → ordinary nodes → key nodes (coordinators, tiles) → labels; overlays above the diagram.
  A more important object is **NEVER** occluded by a less important one. Tiles use a solid fill
  so converging lines vanish beneath them. [P4 layers](../design/prototypes/04-diagram-swarm.html#L96)
- Arrows: `--ink-3`, ≥ 2px on screen, round caps; **gap** at both ends; arrowhead with concave
  back, ≈6× the stroke (≥ 12px). [P3 `#arr`](../design/prototypes/03-notes-spotlight.html#L85)
- **Key tiles** (the slide's most important object): accent-tinted fill + soft accent glow,
  text stays ink, still no border. A few per deck; at most one or two per diagram.
- ~~Flagged tile~~ *retired* (unused since S-026 went text-led; CSS left in the deck). Context
  zones sit beneath edges. Markup: §10 Diagrams.
- **Screen-size floors:** diagram text never renders below ~15px at 1280 wide / ~20px at 1920,
  however small the SVG is drawn (the engine compensates per diagram).
- **NEVER** animated / marching dashed lines.
- Step builds: diagram advances one state per input, with a numbered step list (current = accent
  disc, done = filled `--ink-2` disc, waiting = hollow disc; all item text stays ≥ `--ink-2`). [P4 steps](../design/prototypes/04-diagram-swarm.html#L25), [`render()`](../design/prototypes/04-diagram-swarm.html#L152)
- State colours: active agent = accent-tinted fill + `--accent-ink` stroke; coordinator = solid
  `--ink`; sacrificed = `--loss`, and its links fade. [P4:49–51](../design/prototypes/04-diagram-swarm.html#L49)
- Illustrative scale stated on-slide (e.g. "each dot represents about 8 agents").
- **v2 is diagram-led:** most slides (all but title, insights and discussion) **MUST** carry a
  dynamic, step-built diagram of the slide's core concept (the v1 swarm on `s-3-1` is the bar),
  paired with narration tiles (§5a).

## 8 · Links & citations

- Every cited source is a real hyperlink. Style: underline only (1px, 3px offset) in the
  **surrounding** text colour; **NEVER** blue. [P3:66](../design/prototypes/03-notes-spotlight.html#L66)
- Open in a new tab (`rel="noopener"`): the engine sets this on every slide link, so markup never
  repeats it. [P3 `focus()`](../design/prototypes/03-notes-spotlight.html#L146)
- The same style holds for every `p.cite` link in any slide body (tiles, tables, quotes), not just
  in notes: one shared rule, never per slide.

## 9 · Teams-share constraints

- Big soft shapes survive compression; hairlines, grain and small low-contrast text don't.
- Animated blur may step on a low-frame-rate share; it must degrade to a readable fade.
- Verify every new component **over a real Teams share**, not just locally.

## 10 · Authoring contract (ADR: ADR-001)

Write slides in `deck/deck.html` (v1) or `deck/deck-v2.html` (v2) between `<!-- SLIDES:BEGIN -->` and `<!-- SLIDES:END -->` using
**only** the markup below. **NEVER** add `style`, `<style>`, `<script>` or colour literals there; if a
slide needs something new, extend the component CSS / engine once and document it here.

**Slide shell**
- `section.slide#s-C-N[data-chapter="<Chapter>"]`: the agenda is built from distinct `data-chapter`
  values in slide order, so every slide of a chapter repeats the same value.
- `[data-ambient]`: bokeh (title / summary / Insight slides only, §4). `.slide--lead`: big
  title, vertically centred (title and summary slides).
- Children in order: `p.kicker` (`0N · Chapter`), `h2.title` (VOICE rules, ≤1 `<em>`), one
  `div.body`, then overlays, then notes. The body sits in the area below the title; overlays share
  that area, so they can never cover the title.
- Stepped titles: a slide with build phases may carry one `h2.title` per phase, swapped with
  `data-show-at` / `data-hide-at` (title rules apply to each). Notes on a phase's content show that phase (Reader notes below).

**Body layouts** (only ever on the slide's one `div.body`, never nested): `div.body` (flow, centred
vertically in the body area) · `div.body.body--split` (left ≈36%, right ≈64%; a `div` column stacks
its blocks with even spacing) · `div.body.body--split.body--flip` (64 / 36: wide content left, quotes
right) · `div.body.body--stack` (centred column: diagram then quote/cite) ·
`div.body.body--layers` (children share one grid cell and swap by step via `data-show-at` /
`data-hide-at`: build phases that can't fit together, e.g. s-10 pace → controls → prompts; a phase
of several blocks is one wrapper `div[data-show-at][data-hide-at]`, e.g. table + `blockquote` +
`p.cite`; a quote under a table keeps clear of its last rule, and on short screens table rows
tighten so a phase fits under its title) ·
`div.body.body--tiles` (tile row, S-026; s-8, s-9; built in situ: 2–4 equal-width, equal-height
frosted `article.text-tile[data-show-at]`, one per step, earlier tiles stay; each `h3` heading +
`p` lines (2–3 short) + optional `blockquote` + `p.cite` (report voice; italic, CSS quote marks)
and/or in-flow `div.msg-card` (agent voice); links in text colour, underlined. On short screens
(≤ 660px high) gaps tighten and the heading shrinks. Fit is tightest at 1288×598: trim a tile,
moving detail to its note, rather than overflow).
In a `body--stack` with a caption the diagram takes the remaining height (`flex: 1 1 0;
min-height: 0`) so the stack never rises over the title (slide-scoped on `#s-3` today; generalise
in S-028).
**Quotes MUST sit below or to the right of the slide's core content**, never before it.
Content classes: `p` (≤46ch), `ul.points > li` (accent dash bullets), `ol.steps > li` (numbered step
list), `dl.terms > div > dt + dd` (terms flow into columns), `blockquote` + `p.cite` (report voice),
`div.msg-card > p.msg-agent + blockquote.msg-text + p.cite?` (agent voice, in flow), `p.stat >
strong + text` (one big number with its label), `p.caption` (scale notes, sources; ≤70ch),
`ol.prompts > li.prompt` (numbered serif discussion questions), `table` (`th` header row, `td` rows;
first column emphasised; rows may carry `data-show-at`), `table.compare` (equal-weight columns).

**Steps**: a slide's step count = max `data-show-at` / `data-at` on it; it is left only after its last
step. `[data-show-at=n]` is visible from step n (`.is-visible`); works on HTML and SVG elements.
`[data-hide-at=n]` hides an element from step n (e.g. an edge re-routed through a new tile).
**Swap** (change state at step n): pair the outgoing element `[data-hide-at=n]` with its replacement
`[data-show-at=n]` at the same place: a tile for another tile at the same rect (s-4 board → wipe),
a plain edge for an `.edge--reinforced` copy. `text.tile-sub[data-show-at=n]` adds a tile line later.
`ol.steps > li[data-show-at]` stay visible but dim, and get `.is-current` / `.is-done`.

**Overlays** (§5)
- Insight: `aside.overlay.overlay--insight[data-at=n] > p` (label "Insight" is added by CSS). Shown
  only at step n; the body softens; rack-focus exit.
- Agent messages (*v1 only*): `div.cluster[data-at=n] > article.overlay.overlay--msg` ×1–3 (fits 1280×720; 4–5
  only with short quotes), each `p.msg-agent` (label from `quotes.md`) + `blockquote.msg-text`
  (verbatim, **no** quote marks: CSS adds them; mark our own cuts `[…]`). One card carries
  `data-key` as authoring metadata (the KEY quote in `quotes.md`); it gets no default emphasis.
- One overlay per step; put an Insight on its own step after a cluster.

**Narration tiles** (§5a; *v2*). `div.narration > article.narr-tile[data-at=n]`, ×1–2 per step
(**NEVER** 3+), each `p.msg-agent` + `blockquote.msg-text` (same verbatim/quote-mark rules as the
cluster). A step may carry none; a neutral fact tile uses the same markup with a neutral label.
Where no agent quote exists, a tile may carry a verbatim report/investigator quote, `p.msg-agent`
naming the source neutrally (e.g. "OpenAI · technical report", "METR investigation").
- Layout: `div.narration` is a slide child right after `div.body` (**NEVER** nested in the body).
  Its presence gives the slide a right-hand column (≈25vw, 300–540px) spanning kicker → body; the
  kicker, title and body take the remaining width to its left. The engine positions tiles; markup
  carries no position. So a narrated `body--split` diagram gets ≈35% of the slide width: prefer a
  flow / `body--stack` diagram (viewBox ≈1000–1200 wide) when the diagram needs room.
- Fit (1280×720): a step's pair holds ≈200 characters per quote; a lone tile ≈400. Cut longer
  quotes with `[…]`.
- Engine: a tile is shown only at its step `n` (rise in sharp; rack-focus exit, then gone;
  newcomers wait for it); `data-at` counts toward the step total; tiles **NEVER** set the slide's
  `is-overlaid` softening; notes mode hides them like other overlays. Put an Insight on its own
  step after the last tiles.

**Reader notes** (§6): `aside.note[data-for="#id"]` with `h3` + `p` + `a.src[href]` (real source,
link text = source name). `#id` **MUST** be an element on the same slide (HTML or SVG `g.tile`).
Notes mode hides overlays, so target body content, not overlays. v2: each note shows its slide at
the last step where its target (and its ancestors) is revealed by `data-show-at`/`data-hide-at`;
pins for targets not on screen at that step hide (v1: always the last step).

**Diagrams** (§7): `svg.diagram[viewBox]` with groups in this order: `g.layer-edges`,
`g.layer-nodes`, `g.layer-key`, `g.layer-labels`.
- Tile: `g.tile#id > rect[x y width height] + text.tile-title + text.tile-sub*`. Give text no
  coordinates: the engine centres all lines in the rect, and tiles sharing a row (same `y` and
  height) share one title baseline. Fill, radius and `#lift` come from CSS. `g.tile.tile--key` for a
  key tile (§7); put it in `.layer-key`.
- Edge: `path.edge[data-from="#a"][data-to="#b"][marker-end="url(#arr)"]` (no `d`): the engine draws
  a gapped straight or curved connector between the two tiles. A hand-drawn `d` is allowed when
  routing must bend; keep the gaps.
- `path.edge.edge--reinforced`: thicker `--ink-2` edge (≈2.2× base, same floors) for a route
  strengthened by training; thicken a route at step n by a swap (Steps).
- Labels: `text.label` (dates, axis words) and `text.tag` / `text.tag.tag--loss` (state captions).
- Zone: `g.zone#id > rect + text.label`, painted first in `.layer-edges` (soft context region);
  `g.zone.zone--lit` = accent-tinted fill + glow for a persistent lit context. *Unused* since s-6/s-7 moved onto the incident world, where a
  `g.domain` box does that job.
- *Retired* (unused since S-026 went text-led; CSS left in the deck, **NEVER** reuse without
  re-prototyping): scope fence `rect.fence`, flagged tile `g.tile.tile--flag`, `.edge--reinforced`.
- Coloured edges (S-019, s-2): `.edge--ok` (accent) / `.edge--loss` (`--loss`), each with its own
  arrowhead marker (`#arr-ok` / `#arr-loss`, same shape as `#arr`); a verified success = the
  `.cred-badge.tick-badge` disc on the edge. A figure with annotations: `div.fig > svg.diagram +
  div.fig-notes > p.annot[.annot--loss]` (callout on `--tile`, 4px accent or `--loss` left edge);
  annotations swap by step in one shared cell. `.keep` = never break inside a phrase (embedded
  fonts lack U+2011).
- Mix bar: `g.mix > text.label + rect.mix-major + rect.mix-minor + text.mix-label` (`.mix-label--end`
  right-aligns), for a share-of-total split. *Unused* since S-023 moved s-6 onto the incident world
  (CSS left in the deck for reuse).
- Cut: `g.cut > path.cut-mark[d] + text.tag.tag--loss`, paired with `data-hide-at` on the severed
  edge at the same step.
- SVG units: tile text is 26/20 units, but the engine raises it (and edge width) to the §7
  screen floors when the SVG is drawn small, so size tiles for the floor: in `body--split` keep the
  viewBox ≈1000 wide; full-width diagrams ≈1400.
- Swarm: `svg.diagram[data-diagram="swarm"]` with the four empty layer groups plus the board tile in
  `.layer-key` and tags in `.layer-labels`; the engine adds agents. Its five stages (note → replies
  → gather → coordinators → sacrificed) follow slide steps 1–5 by default; an optional
  `data-stages="s1,…,sN"` on the SVG maps step k to stage sk (step 0 = empty; later steps keep sN),
  so the diagram can follow the storyboard order. No v2 slide uses it since S-022 moved s-5 onto
  the incident world (below); the module stays for reuse. Pair it with one
  `ol.steps > li[data-show-at]` per step. Extra tiles (e.g. a scorer key tile) and tags may join
  `.layer-key` / `.layer-labels` with `data-show-at`, outside the gathered ring (|x| ≤ ~370 units).

- Incident world (S-032; built in situ, judged by eye per step, PRD *Decisions*): one
  `div.world` (`svg.diagram` + `p.world-key`, green dot = agent run; later entries, e.g. s-6's hollow
  ring = agent activity on Hugging Face, sit to its right on the same row) sits once at the top of the
  slide region; parts carry `data-world-at="<slide>:<step>"` (optional `data-world-until`) and
  stay for every later world slide. A world slide is `section.slide[data-world]`: title spans the
  top, then `div.body.body--timeline > ol.steps` (one dated entry per step, **dates live here, not
  on the diagram**) · empty `div.world-slot` · `div.narration`, at ~30 / 40 / 30%. The engine fits
  the world to the slot, and every world slide's title reserves the tallest world title's height,
  so the world **never moves or rescales between world slides** (PRD *Decisions*). On short
  screens (≤ 660px high) timeline entries tighten so the longest timeline fits its row. World units ≈ screen px at 1920 (viewBox ~640 × 520), so text floors
  stay in proportion; keep tile labels short (stack words) as the world shrinks. Soft-toned
  `g.domain` boxes (label top-left, uppercase) name where things run ("OpenAI servers", "Public
  Internet"). `data-split` on `.world` lists layout stage points (e.g. `"s-3:6 s-6:0 s-7:1"`); reaching
  each re-arranges the scene with a tween that keeps run–mirror lines, `data-end` points, pulses and
  note flights attached. Stage 1: swarm left, mirror right, OpenAI box narrows. Stage 2 (s-6): OpenAI
  narrows to a column (swarm compressed above the mirror group, which moves and scales into it), the
  internet becomes a middle strip and a new domain takes the rest (s-6: ~22 / 24 / 50% of the world,
  set by label fit at 1288×598). Stage 3 (s-7): the stage-2 domains dissolve (`data-world-until`),
  OpenAI widens back to the whole world, the swarm keeps its column and the mirror group slides right
  to become the hub. Parts that arrive with a stage fade in after the tween lands. Runs (`g.runs[data-runs=N][data-seed]`,
  one seeded swarm per group) are drawn by the engine in P4 line-drawn style;
  `g.runs[data-place="cx cy sx sy"]` stands a group at a fixed spot and scale, outside the layout
  tween: use it for a second model's runs that arrive after the stages and must not move with them
  (s-7: the Astra-family runs). A different model is named by a `text.w-tag`, never a new colour: same
  run dot; `[data-of="<runs id>"]`
  on a part (or an ancestor) picks its group (default: the first); `[data-run]` follows a run (`first`
  = the group's outermost upper-right run, or an index). `.run-links[data-share="f"]` links only an
  evenly spread fraction f of its group (the runs that joined a board; `.run-links--lit` = accent);
  `line[data-run][data-end="x,y"]` ends at a point (mirror-group units) instead of the mirror, for a
  run reaching a part beside it (`.w-link--probe`; s-5 dropped its run → scorer lines as clutter:
  show agents acting on a part with a flying note glyph, e.g. s-4's skull note, instead). Run roles follow §7:
  coordinator = solid-ink `circle.run-coord[data-run]` + heavy `.w-link--coord`, standing about
  halfway between its group's median distance and the mirror tile with its board (opt-in: marking
  coordinators turns grouping on; it is recomputed round the mirror on every later layout stage); once coordinators appear, the group's runs keep their
  distance from the mirror but ease partway round, by angle, towards the nearest coordinator, so
  each reads as a coordinator with its fan (s-5:5, kept on every later slide); sacrificed = `--loss`
  on existing runs, never new dots: several runs spread across the fan turn one at a time (~2 s
  in all; `circle.run-sac[data-run]`, ordered by the engine's `--sac`) and their lines fade. `g.pulses` travel run→mirror (load); `g.pulses--out` flow mirror→runs
  (assignments from the board); `g.w-tw` (`line.tw-line` + `circle.tw-pulse`) sends messages from a
  part up to the mirror (s-5: tripwires, scorer → board). A board's glyph says what it is made of:
  notes (`.note-glyph`) or cache folder names (`.folder-glyph`, s-5). A checker's state is a
  `g.eye-badge` on its tile: open eye = it reads; `.eye-badge--off` + `path.eye-slash` = it never
  did, captioned by `text.w-tag`. `.note-fly[data-note-for="first"|"lit-k"]` glyphs sit at their target (pinned on the mirror) and fly in from their run, where it stands when
  their group appears. A new setup dissolves the old one completely (`data-world-until`), never
  greyed ghosts. `data-world-is="<name> <slide:step> [until]"` adds `.is-<name>` over a range:
  `dim` (a box fades back, as history), `zeroday` (timed key → open-padlock swap), `down` (mirror
  and notes grey after the 4 s flood), `blind` (glyphs a checker ignored grey out, s-5). Timed
  beats within one step start after a pop-over has gone (+0.5 s) and show their end state under reduced motion (s-4: ring → skull note → open
  padlock pops; bell rings ~2 s then is silenced; load pulses travel run→mirror faster and faster,
  the flood lands, then the crash light flashes `--alarm`). Mirror badge = its access state: green
  key (shared credential), oxblood open padlock (admin taken), green closed padlock (secured); the
  same badges mark any other part's access (s-6: a leaked key on the Hugging Face box edge; clusters
  taken = open padlocks that pop (`.hf-lock`) after the rings reach them; closed padlocks at the cut). A cut connection is an unplugged plug and socket (`g.unplug`, line
  art: each head in a positioned `g` carries its own cable, and the heads slide apart from touching;
  placed across where the path ran), never a bare cut mark. An infrastructure target is an icon, not a
  tile: a server rack (`g.rack`: `.rack-body`, `.rack-unit` with slots and a status dot, `.rack-net`;
  a `text.w-tag` label) with its access badge, and what was read off it overlaps a corner as a glyph
  (s-7: `g.secret-file`, a folded-corner doc with an oxblood "SECRET" band, plus a `text.w-tag`
  count). Glyph strokes scale with `--k`. A group that arrives as a body of runs, not a fan, may
  fill a disc (`g.runs[data-shape="disc"]`; s-7 Astra). Attacking runs among many links get the
  bold ring (`run-ring--bold`) so their lines read.
  A checker silenced earlier rests as `.bell-quiet` (slashed, `--ink-3`; its ringing never replays)
  when a layout stage moves it. Signed board messages: `g.seal` (accent disc + `path.seal-tick`) pops
  onto some of the board's glyphs, staggered. **Activity, not runs:** where agents act in a domain
  their runs don't live in (s-6: Hugging Face; the runs stay on OpenAI's servers), draw hollow
  `--accent-ink` rings (`.act`), never new runs. `g.acts[data-acts=N][data-seed][data-around="#tile or
  group"][data-in="#domain"][data-from="x,y"]` scatters N seeded rings just outside the target tile(s),
  inside the domain below its label, clear of every tile shown by then (later slides' tiles never push rings) and of each other, flying in from the point
  where the activity entered; `g.act-stream[data-acts][data-along="#path"][data-dur=ms]` loops rings
  along a path (an entry edge) for sustained traffic, resting spread along it under reduced motion.
  A legend entry introduced later is a `span.world-key-item[data-world-at]` (optional
  `data-world-until`) in the key, hidden on earlier world slides; the key wraps within the world
  column and hidden entries keep their space, so its height (and the world) never changes between world slides: a run role gets one when it
  first appears (s-5: research coordinator, sacrificed agent); keep labels short ("HF activity"). Moving dots, never marching dashes. The timeline
  builds: an entry shows at its step, never ahead; a dated entry's date (month in full) carries a quiet day count
  from day 0 (`+49 d`; PRD *Decisions*), derived from the date itself so it is never typed twice;
  date and tag form the entry's first line and the event starts on the next (undated entries too);
  the timeline may use the full height of the world beside it (top to bottom of the diagram area);
  `li.sub` = un-numbered sub-point (dash);
  `span.tl-aside` = a quieter second line. A world slide may close with an Insight
  (`.overlay--insight`, spans world + narration; the world and timeline soften). A statement that
  is not a quote uses `.narr-tile--fact` (no quote marks), e.g. "messages … were not made public".
  Notes may target world parts by id, never an overlay (notes mode hides overlays).
- Backdrop world (S-026; s-8, s-9): `section.slide[data-world="backdrop"]` with an empty
  `div.world-slot` and a `body--tiles` body under the title (no timeline, no narration). The world
  stays frozen at the end state of the last preceding world slide, heavily blurred and faded
  (`.is-backdrop`: blur 12px, opacity .42; stronger than pop-over softening): backdrop, not content.
  It keeps the camera of the last non-backdrop world slide unless it sets its own `data-camera`.
  Step 0 is the title over the blurred world. Parts that ended (`data-world-until`) before the
  backdrop slide are hidden there, so it shows the end state, not the history.
- Pop-over: `div.popover[data-show-at][data-hide-at]` > `figure.pop-panel` cards (opaque `--tile`,
  `--shadow-overlay`), each `figcaption` (`span.pop-tag` + task) + `svg.pop-art` (small P4-style
  scene) + `p.pop-note`. While shown the world and caption soften (as under an Insight); exit is the
  overlay rack focus; a pop-over replacing another follows the §5 handover. On a world slide
  `div.popover--left` spans timeline + world and leaves the narration column sharp, so one step can
  carry a pop-over and a narration tile. `figure.pop-panel--wide` is a single card spanning the
  pop-over, for a wide scene (s-5: a coordinator branching into three workstreams). A curved pop-art arrow's head
  follows its curve's end tangent (back of the head centred on the line). Pop-art draws
  from the shared `pa-*` vocabulary (agent, flag, chip, doc, thought, imagined outcome, coordinator,
  branch, workstream): reuse it before adding parts. Motion in pop-art (quivering agent, attempts
  that curve at the wall from several directions, fail and fade) stops under `prefers-reduced-motion`.

**Engine API** (tests and tooling): `window.deck = {ready, state(), goto(id, step), next(), prev(),
plan()}`; `plan()` returns `[[slideId, maxStep], …]`.

## Known prototype drift (fix in build, not in prototypes)

- `#lift` shadow opacity differs (P3 `.11`, P4 `.14`): canonical **`.12`**, defined once.
- Tokens, `#lift`, `#arr` and step/keyboard JS are re-declared per prototype: build defines each once (ADR-001).
