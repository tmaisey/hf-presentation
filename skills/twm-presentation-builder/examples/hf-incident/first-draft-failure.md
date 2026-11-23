# The rejected v2 first draft, and the fix (HF deck)

**Illustrates:** `process/PROCESS.md` (phases 5 and 8, *Lessons from the worked example*) and the layout guard and screenshot tools it runs
**Sources:** HF deck retro docs/261120-v2-quality-retro.md at commit 9c26b68, 20 Nov (since folded into the PRD and AGENTS.md); HF deck docs/PRD.md, workstream 6, 22 Nov; HF deck AGENTS.md, 22 Nov

**What to learn:** a green suite and nine busy agents produced a deck the presenter rejected on
sight. Nothing was broken in code; the stages *around* the build were missing. Each cause became a
binding rule, and those rules are now the skill's process.

## What was wrong

> **Verdict (presenter):** v2 (`deck/deck-v2.html`, S-017–S-029) "hasn't worked very well". Don't build
> further. First **prototype the key visuals** with the presenter (the brief didn't convey the vision
> well enough), and get quality back to v1's level. Example defect: s-7's step list renders over its
> title; diagram sparse (half-empty band, "CUT" label colliding with the Hugging Face tile, narration
> tile floating far from what it narrates).

> | v2 | 5 / 60 (s-7 title overlap) | 5 / 60 (s-7) | 26 / 60 (s-5, s-6, s-7, s-10: off-slide + title overlap) |

> The suite was green (158 passed) throughout.

Before (first draft, 19 Nov build, re-rendered from git with `scripts/shoot.py`), s-7 last step:

![Before: s-7 at 1920×1080, step list touching the title, CUT label colliding, sparse band, narration tile far right](images/before-s-7-1920x1080.png)

![Before: s-7 at 1288×598, step list printed over the three-line title](images/before-s-7-1288x598.png)

After (accepted rebuild, 22 Nov), the same slide:

![After: s-7 at 1920×1080, two-line title, dated step list, the incident world filling its space, quote tile beside it](images/after-s-7-1920x1080.png)

![After: s-7 at 1288×598, nothing colliding at the short-wide size](images/after-s-7-1288x598.png)

## Causes

Ranked as the retro recorded them; the PRD keeps the same five.

1. **Layout tests switched off for v2:**

   > **The layout guard was switched off for v2.** S-017 marked `tests/test_visual.py` v1-only and
   > deferred v2 layout checks to S-028 acceptance, so no test caught title overlap, clipping or
   > off-slide text while slides were built. Green became the goal; it no longer measured what matters.

2. **Only per-slide component screenshots**, taken before the shared narration column existed:

   > Slide agents screenshotted their slide
   > before S-018's narration column existed (most hid narration to do it). […] After merging, only tests ran; nobody looked.

3. **No prototypes for the new visuals:**

   > v2's new language (narration tiles, 8 new
   > diagrams) went from spec straight to 9 parallel agents, each inventing components (zone, mix
   > bar, fence, flag tile, cut mark, `body--layers`, stepped titles) with no art direction.

4. **Agent briefs led by merge-safety, not quality:**

   > **The agent brief optimised for merge-safety and test-greenness, not quality.** Under fit pressure
   > agents cut copy and added step lists that restate the diagram in prose.

5. **16:9-only tests:** the presenter's window is ~2.15:1.

   > **Tests use 16:9 only.** The presenter's window is ~2.15:1; v1 degrades there a little, v2 a lot.

> Parallelism itself was not the cause: v1 was also built by parallel worktree agents.

## Rules it produced

- **Always-on layout guard** at three sizes including short-wide (spec S-030, now
  `scripts/layout_guard.py`), with known faults parked as strict xfail so a fix must clear them.
- **Look at the assembled deck**, never only component screenshots:

  > **visual work:** the deck's layout guard (S-030, `tests/test_v2_layout_guard.py`) is green with the slide out of `PENDING_SLIDES`, and screenshots of the
  > **assembled** deck at every affected step were looked at, never only component screenshots.

- **Prototype first** for new visual language, or a recorded in-situ choice:

  > **MUST** precede spec/build of any new component, diagram style or layout, judged by eye with the presenter: v2's first draft skipped this and fell below v1's quality (Nov 2026).

- **Briefs lead with quality**, and builders never invent components per slide:

  > every builder works to those prototypes and `DESIGN.md` rules, never inventing
  > components per slide (propose them instead), and briefs lead with the design and quality targets,
  > not just file-slot rules; after every merge, re-run the layout guard and re-screenshot the assembled
  > deck

## The fix

Reopened slide specs were rebuilt one at a time on a shared "incident world" diagram, prototyped in
situ with the presenter judging each step by eye (21–22 Nov), behind the layout guard. Carried over
untouched: reader notes and sources, the engine, the test harness, recorded presenter decisions.

> **Carried into the rebuild:** reader notes + sources (fact-checked), engine incl. notes-at-step (S-029) and swarm `data-stages`, test harness (S-017), recorded presenter decisions
