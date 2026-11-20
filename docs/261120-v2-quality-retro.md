# Retro · v2 first draft below v1 quality (20 Nov 2026)

**Verdict (presenter):** v2 (`deck/deck-v2.html`, S-017–S-029) "hasn't worked very well". Don't build
further. First **prototype the key visuals** with the presenter (the brief didn't convey the vision
well enough), and get quality back to v1's level. Example defect: s-7's step list renders over its
title; diagram sparse (half-empty band, "CUT" label colliding with the Hugging Face tile, narration
tile floating far from what it narrates).

## Evidence

v1's own visual acceptance check (`tests/test_visual.py` CHECK) plus a step-list/body-vs-title
collision check, run on every slide × step (probe script, not committed):

| Deck | 1920×1080 | 1280×720 | 1288×598 (presenter's window, ~2.15:1) |
| --- | --- | --- | --- |
| v1 | 0 / 94 states with problems | 0 / 94 | 9 / 94 (s-5-1 off-slide, s-5-2 title overlap) |
| v2 | 5 / 60 (s-7 title overlap) | 5 / 60 (s-7) | 26 / 60 (s-5, s-6, s-7, s-10: off-slide + title overlap) |

The suite was green (158 passed) throughout.

## Causes (ranked)

1. **The layout guard was switched off for v2.** S-017 marked `tests/test_visual.py` v1-only and
   deferred v2 layout checks to S-028 acceptance, so no test caught title overlap, clipping or
   off-slide text while slides were built. Green became the goal; it no longer measured what matters.
2. **Components were verified, the assembled deck was not.** Slide agents screenshotted their slide
   before S-018's narration column existed (most hid narration to do it). S-018 then gave every
   narrated slide a right-hand column, narrowing title and body (s-7's title went to 3 lines, its
   step list rose into it). After merging, only tests ran; nobody looked. The orchestrator called v2
   "presentable" without seeing a screenshot.
3. **No prototype stage for new visual language.** v1 went prototypes → DESIGN rules → build →
   independent reviewers → presenter review round. v2's new language (narration tiles, 8 new
   diagrams) went from spec straight to 9 parallel agents, each inventing components (zone, mix
   bar, fence, flag tile, cut mark, `body--layers`, stepped titles) with no art direction. Result:
   inconsistent, sparse diagrams. Prototyping was "optional, off by default" and wasn't proposed.
4. **The agent brief optimised for merge-safety and test-greenness, not quality.** Under fit pressure
   agents cut copy and added step lists that restate the diagram in prose. v2 slides carry title +
   step list + diagram + narration column + notes in narrower space; v1 spread similar content over
   18 slides.
5. **Tests use 16:9 only.** The presenter's window is ~2.15:1; v1 degrades there a little, v2 a lot.

Parallelism itself was not the cause: v1 was also built by parallel worktree agents. The difference
was the stages around the build (prototypes before; visual tests and real screenshot review after).

## Rules adopted (binding homes: `AGENTS.md` workflow + Definition of done; spec S-030)

- Prototype any new visual language before spec/build, and judge it by eye with the presenter.
- The deck under build keeps an always-on layout guard (several aspect ratios incl. short-wide).
- Done for visual work = screenshots of the **assembled** deck seen, not component screenshots.
- Parallel building stays: builders work to the agreed prototypes + DESIGN rules (no per-slide
  component invention) behind the layout guard; re-screenshot the assembled deck after every merge.

## State left behind (what's reusable)

- **Sound, keep:** S-017 deck selection + v1 freeze hash + parallel suite; S-024 research (no further
  takeovers; 19 Jul OpenAI cluster = different Astra-family model); S-029 notes show the target's
  step; swarm `data-stages` engine option; all reader notes and sources (fact-checked per slide);
  presenter decisions recorded in `VOICE.md` / `STORYBOARD.md` (s-3, s-5 order, s-7 titles, s-6
  "10–11 Jul").
- **First draft, reopened (`todo`):** S-018 narration tiles and slide specs S-019–S-023, S-025–S-027.
  Their markup in `deck-v2.html` is raw material for the rebuild, not an approved design. The v2
  component additions in `DESIGN.md` §5a/§10 are provisional until prototypes settle them.
- **Presenter review still pending** (from the decision list): report/investigator quotes as
  narration tiles (s-4, s-7, s-8, s-10); s-8 flagged-tile colour (loss tint vs a new muted amber);
  s-10 stepped titles vs one title vs split slide; s-10 Nov-2026 releases row and 5.4 Insight
  length; agent-written diagram labels and short step lists (s-2, s-4, s-5, s-6, s-8).

## Next

Presenter explains the vision for the key visuals → throwaway prototypes in `design/prototypes/`
(narration tiles; one or two hero diagrams) judged by eye, incl. at ~1288×598 → DESIGN rules →
re-spec reopened slides → build behind the S-030 layout guard → S-028 review.
