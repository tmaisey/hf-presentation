# Prototypes index

Spec-free single-HTML files to *see* design options before writing design rules.
Open directly in a browser (fonts load from Google Fonts, so online for now). Judge them
**through a Teams screen-share**, not just locally.

| File | Tests | Verdict |
| --- | --- | --- |
| `01-palette-type.html` | Paper tone, charcoal text, green accent usage, 3 serif/sans pairings, type scale at share size | **Pairing A** (Newsreader + Inter) chosen |
| `02-chapters-depth.html` | Snapping chapter scroll, persistent title bar + agenda nav, bokeh depth, insight frosted overlay | Canvas fireflies dropped (imperceptible); drifting bokeh *is* the ambient layer, title/summary pages only. Overlay = "Insight", label in ink, no accent tab. Settled |
| `03-notes-spotlight.html` | Reader-notes overlay: blur-everything-but-target spotlight + callouts + citations | Liked. Callout = heading + body + source only; position/nav lives in a static bar on the lower periphery. v3: borderless shadowed tiles, gapped curved-back arrows, centred tile text, source = underlined link in surrounding ink. Settled |
| `04-diagram-swarm.html` | Dynamic message-board swarm diagram in two styles (line-drawn vs soft-node) with step builds | **Line-drawn** chosen. Nodes sit in front of edges. Loss/sacrifice = deep oxblood `#7A1F2B` (approved). v3: board tile shadow-only. Settled |
| `05-header-bar.html` | v2 title bar: Title-Case title with italic subtitle; agenda always expanded, no dots (current label green), hover pops the section forward while the others soften slightly; when the row would crowd the title it compresses to the current section's name, which drops down a frosted vertical panel on hover/click. ←/→ step, C forces compact | **Approved** (21 Nov): rules to DESIGN §3, then build into v2 |

**Palette constraint carried by every prototype:** accent `#86BC25` is 2.0:1 on paper, so it's
for fills, glows, strokes, never text. Accent-as-text uses deep green `#4B6E10` (5.4:1).

**Status: settled and frozen.** Agreed rules live in `docs/DESIGN.md`, which links to lines in
these files: if you edit a prototype, re-check those links in the same commit.
