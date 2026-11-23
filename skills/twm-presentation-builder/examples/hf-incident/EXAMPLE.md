# Worked example: the HF incident deck

A 20-minute talk on the 2026 OpenAI agent-swarm incident that reached Hugging Face, built as one
HTML file over 19–22 Nov 2026 by the presenter twm with agents, using the process this skill now
encodes. Its first v2 draft was rejected; the rebuild was accepted. Read an excerpt when its part
is the one you are applying; every quote is verbatim and cited to the HF deck's own docs.

| Skill part | Excerpt | What to learn |
| --- | --- | --- |
| `process/PROCESS.md` phase 1 · `content/STORYBOARD.md` codes | [prd-core-message.md](prd-core-message.md) | Three numbered beliefs (M1–M3) every slide must serve; mixed evidence named, not smoothed |
| `content/STORYBOARD.md` | [storyboard-rows.md](storyboard-rows.md) | One row per slide with message codes and time; per-slide sections with approval marks and replaced titles kept |
| `voice/VOICE.md` · `voice/profiles/twm.md` | [voice-pairs.md](voice-pairs.md) | Six rejected/approved pairs: hooks, aphorisms, "X, not Y" and overclaims turned into findings |
| `design/TOKENS.md` · `design/LAYOUT.md` · phase 5 | [design-decisions.md](design-decisions.md) | Prototype verdicts that became rules (type pairing, line-drawn diagrams, accent never text), and an in-situ choice recorded |
| `architecture/ARCHITECTURE.md` | [adr-001.md](adr-001.md) | The define-once, four-layer constraint the skill's architecture still follows, and why it held |
| `process/PROCESS.md` phases 6–9 · `evals/CRITERIA.md` process | [spec-commits.md](spec-commits.md) | Three spec kernels and their docs → red → green → done commits; one slip to avoid |
| `process/PROCESS.md` lessons | [first-draft-failure.md](first-draft-failure.md) | Why a green suite shipped a rejected deck: five causes, four rules, before/after screenshots |

**The deck itself, rebuilt with this skill** (a representative subset, PB-007): [slides.html](slides.html)
is the slide markup under the authoring contract; [deck.html](deck.html) is the assembled,
self-contained deck. Open `deck.html` in a browser to see the target quality; read `slides.html` to
see how little markup a slide needs.

**Not here:** the full 12-slide deck, the research corpus and reader notes. The excerpts teach the
method; the facts belong to that talk.
