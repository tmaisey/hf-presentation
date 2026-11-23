# Design decisions and prototype verdicts (HF deck)

**Illustrates:** `design/TOKENS.md` (palette roles, contrast gate), `design/LAYOUT.md` (diagram and component looks) and `process/PROCESS.md` (phase 5, prototype or in-situ)
**Sources:** HF deck design/prototypes/PROTOTYPES.md (verdicts 19–21 Nov); HF deck docs/DESIGN.md (tokens, 22 Nov); HF deck docs/PRD.md (*Decisions*, 21–22 Nov)

**What to learn:** each visual choice was settled by a throwaway prototype judged by eye (through a
Teams screen-share), and the verdict, not the prototype, became a binding rule. Where the presenter
skipped the prototype, the PRD says so.

## 1 · Type pairing: chosen from three, at share size

> | `01-palette-type.html` | Paper tone, charcoal text, green accent usage, 3 serif/sans pairings, type scale at share size | **Pairing A** (Newsreader + Inter) chosen |

Became the editorial style's type tokens (serif titles, sans everything else).

## 2 · Diagram style: two styles built, one kept

> | `04-diagram-swarm.html` | Dynamic message-board swarm diagram in two styles (line-drawn vs soft-node) with step builds | **Line-drawn** chosen. Nodes sit in front of edges. Loss/sacrifice = deep oxblood `#7A1F2B` (approved). v3: board tile shadow-only. Settled |

Became the line-drawn diagram kit and the `--loss` role: one sparing colour for irreversible loss.

## 3 · The accent is never text: a contrast constraint every prototype carried

> **Palette constraint carried by every prototype:** accent `#86BC25` is 2.0:1 on paper, so it's
> for fills, glows, strokes, never text. Accent-as-text uses deep green `#4B6E10` (5.4:1).

> | `--accent` | `#86BC25` (2.0:1) | Glows, fills, strokes, progress. **NEVER** text |

This is why the palette layer has separate `accent` and `accent-ink` roles and a contrast gate.

## In situ instead of a prototype, recorded

> **s-1 and s-2 rebuilt in situ (presenter, 22 Nov):** new title and subtitle; s-2's reward-loop
> diagram is PowerPoint-style boxes and arrows, built straight into the deck and judged by eye step
> by step, no throwaway prototype (Workflow phase 4 exception).
