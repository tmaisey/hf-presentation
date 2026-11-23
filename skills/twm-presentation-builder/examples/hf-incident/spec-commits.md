# Spec lines and their commit pattern (HF deck)

**Illustrates:** `process/PROCESS.md` (phases 6–9: spec, TDD red then green, screenshot look, done) and the process criteria in `evals/CRITERIA.md`
**Source:** HF deck docs/SPEC.jsonl (as accepted 22 Nov) and its git history, 22 Nov

**What to learn:** a spec line is a short kernel (built · why · not-built); the tests carry the
detail. The history then shows the order the process eval looks for: docs or spec first, a
`Red:` commit holding only tests plus the `todo`→`build` flip, a build commit, then the done flip
with docs current.

```json
{"id": "S-030", "status": "done", "name": "v2 always-on layout guard", "depends_on": ["S-017"], "description": "built: every slide at every step of the deck under build is checked at 1920×1080, 1280×720 and short-wide ~1288×598: no text clipped or off-slide, no body, step list, diagram or tile over any title, title clear of the bar; runs in the default suite during every build · why: v2's first draft shipped title overlaps while the suite was green (Nov 2026) · not-built: aesthetic judgement (screenshot review)"}
{"id": "S-031", "status": "done", "name": "v2 title bar and compact agenda", "depends_on": ["S-017"], "description": "built: v2 bar reads 'The Hugging Face Attack · Misaligned Agents' (italic subtitle); the deck title links home to s-1; agenda shows every chapter, current in green on a resting pill with a faint shadow, hover lifts one and softens the rest; when the row would crowd the title it collapses to the current chapter, opening a vertical list on hover/focus/click whose items still navigate · why: v1 dots were clunky and hid labels · not-built: changing v1's bar"}
{"id": "S-034", "status": "done", "name": "v2 title slide", "depends_on": ["S-017"], "description": "built: s-1 shows the approved title and subtitle (storyboard s-1, VOICE) with a bottom-left byline 'Tom Maisey, November 2026', sourced reader note and ambient background · why: frame the talk's claim up front (M1) · not-built: kicker/super-title; diagram; speaker timer"}
```

| Spec | Commit | Subject | Stage (what it holds) |
| --- | --- | --- | --- |
| S-030 | `d876296` | Red: S-030 always-on v2 layout guard (s-5, s-6, s-7, s-10 fault) | Red: layout-guard test + helper, spec → `build`; the run names the four faulty slides |
| S-030 | `e7d92d5` | S-030: layout guard green; s-5, s-6, s-7, s-10 listed in PENDING_SLIDES (strict xfail) | Green: known faults parked as strict xfail, so each slide's fix must remove itself |
| S-030 | `e757726` | S-030 done: layout guard documented | Done: AGENTS.md, PRD, STORYBOARD and the spec flip together |
| S-031 | `876cf56` | Docs: title bar home link and resting pill for the current chapter; reopen S-031 | Intent change: docs first, the done spec reopened in place |
| S-031 | `dcb29a3` | Red: S-031 home link and resting pill for the current chapter | Red: tests + `todo`→`build` |
| S-031 | `3f6c2fe` | S-031: title bar home link and resting pill for the current chapter | Green: the deck change |
| S-031 | `730b67c` | Done: S-029 notes (scroll clear, fade) and S-031 title bar | Done: DESIGN updated as built + flip |
| S-034 | `984ae89` | Red: S-034 title slide drops the kicker, adds an italic byline bottom-left | Red: tests only; the spec was **not** reopened |
| S-034 | `c9e7122` | S-034: title slide drops the July 2026 kicker | Green, with STORYBOARD, VOICE and README screenshot |

S-030 and S-031 are the pattern to copy. S-034 is the common slip: a presenter refinement went
red → green while the spec stayed `done`, and its kernel only caught up in a later docs sweep
(`79d347d`). Reopen the owning spec first; the process judge reads exactly this.
