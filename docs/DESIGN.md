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
- **Flagged tile** (a caution): `--loss`-tinted fill, ink text, no border; ≤ 1 per diagram. Context
  zones and scope fences sit beneath edges. Markup: §10 Diagrams.
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
`data-hide-at`: build phases that can't fit together, e.g. s-10 pace → controls → prompts).
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
  `g.zone.zone--lit` = accent-tinted fill + glow for a persistent lit context (the s-6/s-7
  "agents running on OpenAI's servers" band: one component on both slides).
- Scope fence: `rect.fence#id` first in `.layer-edges`: soft `--paper-deep` fill + static dashed
  `--ink-3` stroke (never animated; edges stay undashed); scope stated in `text.label`s; may be a
  note target.
- Flagged tile: `g.tile.tile--flag` in `.layer-key` (§7); ≤ 1 per diagram.
- Mix bar: `g.mix > text.label + rect.mix-major + rect.mix-minor + text.mix-label` (`.mix-label--end`
  right-aligns), for a share-of-total split.
- Cut: `g.cut > path.cut-mark[d] + text.tag.tag--loss`, paired with `data-hide-at` on the severed
  edge at the same step.
- SVG units: tile text is 26/20 units, but the engine raises it (and edge width) to the §7
  screen floors when the SVG is drawn small, so size tiles for the floor: in `body--split` keep the
  viewBox ≈1000 wide; full-width diagrams ≈1400.
- Swarm: `svg.diagram[data-diagram="swarm"]` with the four empty layer groups plus the board tile in
  `.layer-key` and tags in `.layer-labels`; the engine adds agents. Its five stages (note → replies
  → gather → coordinators → sacrificed) follow slide steps 1–5 by default; an optional
  `data-stages="s1,…,sN"` on the SVG maps step k to stage sk (step 0 = empty; later steps keep sN),
  so the diagram can follow the storyboard order (s-5: `3,3,4,4,4,5`). Pair it with one
  `ol.steps > li[data-show-at]` per step. Extra tiles (e.g. a scorer key tile) and tags may join
  `.layer-key` / `.layer-labels` with `data-show-at`, outside the gathered ring (|x| ≤ ~370 units).

**Engine API** (tests and tooling): `window.deck = {ready, state(), goto(id, step), next(), prev(),
plan()}`; `plan()` returns `[[slideId, maxStep], …]`.

## Known prototype drift (fix in build, not in prototypes)

- `#lift` shadow opacity differs (P3 `.11`, P4 `.14`): canonical **`.12`**, defined once.
- Tokens, `#lift`, `#arr` and step/keyboard JS are re-declared per prototype: build defines each once (ADR-001).
