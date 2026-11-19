# Prototypes index

Throwaway, spec-free single-HTML files to *see* design options before writing design rules.
Open directly in a browser (fonts load from Google Fonts, so online for now). Judge them
**through a Teams screen-share**, not just locally.

| File | Tests | Verdict |
| --- | --- | --- |
| `01-palette-type.html` | Paper tone, charcoal text, green accent usage, 3 serif/sans pairings, type scale at share size | **Pairing A** (Newsreader + Inter) chosen |
| `02-chapters-depth.html` | Snapping chapter scroll, persistent title bar + agenda nav, bokeh depth, insight frosted overlay | Canvas fireflies dropped (imperceptible); drifting bokeh *is* the ambient layer, title/summary pages only. Overlay = "Insight", label in ink, no accent tab. v2 awaiting review |
| `03-notes-spotlight.html` | Reader-notes overlay: blur-everything-but-target spotlight + callouts + citations | Liked. Callout = heading + body + source only; position/nav lives in a static bar on the lower periphery. v3: borderless shadowed tiles, gapped curved-back arrows, centred tile text, source = underlined link in surrounding ink. Awaiting review |
| `04-diagram-swarm.html` | Dynamic message-board swarm diagram in two styles (line-drawn vs soft-node) with step builds | **Line-drawn** chosen. Nodes sit in front of edges. Loss/sacrifice = deep oxblood `#7A1F2B` (approved). v3: board tile shadow-only. Awaiting review |

**Palette constraint carried by every prototype:** accent `#86BC25` is 2.0:1 on paper, so it's
for fills, glows, strokes, never text. Accent-as-text uses deep green `#4B6E10` (5.4:1).

**Diagram rules agreed so far** (to graduate into the design-rules doc):
- **NEVER** animated/marching dashed lines.
- Tiles: no border; shape comes from a soft two-layer drop shadow on a near-white fill.
- Tile text centred both ways. (Not Insight / Note / agent-message overlays: those are left-aligned prose.)
- Arrows: gap between arrow and tiles at both ends; arrowheads with a concave (curved) back.
- Links to sources: underline only, in the surrounding text colour, **NEVER** blue.
