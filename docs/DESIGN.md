# Design rules

Binding visual rules for the deck. **MUST / NEVER** are binding; deviate only with presenter
approval. Each rule links to the prototype code that shows it (`P1`–`P4` below). The prototypes
are **frozen references**: if one is edited, re-check every link here in the same commit.

Build architecture (define once, apply per slide): ADR-001 in `docs/ADR.jsonl` (proposed; the
`ADR:` marker is added where the build implements it).

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
- Persistent frosted title bar; top-right agenda dots (active = accent dot + label pill, done =
  darker dot) and accent progress hairline. [P2:22–35](../design/prototypes/02-chapters-depth.html#L22)
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
- Use agent-message overlays at a few key moments, not in runs (avoid gimmick).

## 6 · Reader notes (shareable mode)

- Quiet corner toggle (`N`). Notes mode: whole page veils (blur 7px) except a rounded window over
  the target; accent ring + glow marks it. [P3:38–48](../design/prototypes/03-notes-spotlight.html#L38)
- Numbered pins on every annotated element; current pin turns accent. [P3:51](../design/prototypes/03-notes-spotlight.html#L51)
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
- Arrows: `--ink-3`, ~1.75px, round caps; **gap** at both ends; arrowhead with concave back. [P3 `#arr`](../design/prototypes/03-notes-spotlight.html#L85)
- **NEVER** animated / marching dashed lines.
- Step builds: diagram advances one state per input, with a numbered step list (current = accent
  disc, done = `--ink-2`). [P4 steps](../design/prototypes/04-diagram-swarm.html#L25), [`render()`](../design/prototypes/04-diagram-swarm.html#L152)
- State colours: active agent = accent-tinted fill + `--accent-ink` stroke; coordinator = solid
  `--ink`; sacrificed = `--loss`, and its links fade. [P4:49–51](../design/prototypes/04-diagram-swarm.html#L49)
- Illustrative scale stated on-slide (e.g. "each dot ≈ 8 agents").

## 8 · Links & citations

- Every cited source is a real hyperlink. Style: underline only (1px, 3px offset) in the
  **surrounding** text colour; **NEVER** blue. [P3:66](../design/prototypes/03-notes-spotlight.html#L66)
- Open in a new tab (`rel="noopener"`). [P3 `focus()`](../design/prototypes/03-notes-spotlight.html#L146)

## 9 · Teams-share constraints

- Big soft shapes survive compression; hairlines, grain and small low-contrast text don't.
- Animated blur may step on a low-frame-rate share; it must degrade to a readable fade.
- Verify every new component **over a real Teams share**, not just locally.

## Known prototype drift (fix in build, not in prototypes)

- `#lift` shadow opacity differs (P3 `.11`, P4 `.14`): canonical **`.12`**, defined once.
- Tokens, `#lift`, `#arr` and step/keyboard JS are re-declared per prototype: build defines each once (ADR-001).
