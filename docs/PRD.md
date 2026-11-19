# PRD — Hugging Face / OpenAI incident talk

## What

A 20-minute talk to colleagues at a professional services firm (AI-safety interest group) on the
2026 OpenAI agent-swarm incident that reached Hugging Face. Delivered as a **single self-contained
HTML file**.

## Why

The incident is well reported, so the audience's value is in **implications**, not retelling:
what it shows about reward hacking, emergent coordination and deception, and why training these
behaviours out is hard (naive penalties can teach concealment rather than honesty).

## Core message (what the room should leave believing)

1. AI risk is **not only bad actors**: **misalignment** (agents pursuing the objective they were
   trained on rather than the intent behind it) can turn benign tasks into large-scale harm,
   including subversion, with no attempt by agents to notify humans.
2. This incident was **discoverable**; a more capable future system could do far more damage and
   be much harder, or impossible, for humans to detect.
3. **Capabilities are advancing at full speed** despite warnings from AI leaders, while **no known
   solution to alignment** exists.

Every chapter **MUST** serve one of these. Each claim stays sourced; where evidence is mixed
(e.g. OpenAI's announced slowdown vs. "full speed"), the deck says so.

**Practical takeaway (general, not firm-specific):** treat alignment risk as a design input for
everyday AI systems. Give agents only the agency and autonomy the task needs; wrap them in
deterministic controls, sandboxes, isolation and per-agent authentication/authorisation,
commensurate with the use case's risk. Ground each control in an incident failure (e.g. one
shared credential for every agent; internet access by default).

## Shape

Chapter arc and timings below; slide-level content lives in `docs/STORYBOARD.md`.

| Ch | Chapter | Serves | ~min |
| --- | --- | --- | --- |
| 0 | Title | — | 0:30 |
| 1 | Concepts (reward as proxy, reward hacking, misalignment, training vs evaluation) | M1 | 1:30 |
| 2 | Training | M1 | 2:30 |
| 3 | Evaluation | M1 | 3:30 |
| 4 | Breach | M1, M2 | 3:00 |
| 5 | Implications (incl. capability pace and design controls) | M2, M3, takeaway | 5:00 |
| 6 | Discussion: open Q&A seeded by 3 prompts | — | 4:00 |

18 slides are drafted; build all, then **slim to ~9** once seen in sequence.

## Requirements

- **Grounded:** every factual claim traceable to a cited source in `docs/research/`. Disputed or
  single-sourced claims flagged as such on-slide or in notes. Agent messages verbatim only
  (paraphrases flagged).
- **Audience:** quite familiar with AI concepts, so concepts are a fast refresher focused on what
  this incident needs.
- **Single HTML file:** no build step, works offline, presenter-driven (ADR-001).
- **Endpoint-safe:** the file **MUST NOT** trip anti-virus / phishing heuristics on a corporate
  machine (a prototype was quarantined, Nov 2026). Recipients open it from email or Teams.
- **Voice:** slide copy and notes in the presenter's voice, not AI-sounding (`docs/VOICE.md`).

## Design intent

Binding rules (tokens, components, motion, diagrams) live in `docs/DESIGN.md`; this is the brief
they serve.

- Calm, editorial, paper-like: serif titles, sans body, charcoal on soft off-white, a single
  green accent. **NEVER** name, reference or brand the accent after any organisation, in slides,
  code or docs; the deck carries no corporate branding.
- Depth through blur/bokeh: Insight and agent-message overlays float above softened content.
- One elegant, step-built diagram per story stage.
- One chapter rests per viewport, with a persistent title bar showing agenda position.
- Ambient motion only on title / summary / Insight pages, never on detail or diagram pages.

## Delivery

- **Teams screen-share**; presenter advances with mouse or keyboard.
- Implies: survive video compression (no fine grain/hairlines, big soft shapes, generous type
  size for small viewer windows); slow ambient motion only (share frame rate is low).
- **Shared afterwards** as a self-serve read: notes live in the file as a **clickable overlay**
  (blur/annotation over key page elements, incl. diagram callouts), hidden during live delivery.

## Verified account

Research is complete; detail and sources in the
[research report](research/reports/OpenAI%20Hugging%20Face%20swarm%20incident.md). In short:

1. **Training (Apr–May):** an internal OpenAI model trained for persistence and multi-agent
   collaboration reward-hacked on *accidentally* impossible (non-CTF) tasks; agents left notes in
   the shared Artifactory package mirror via a shared credential, forming a message board.
2. **Evaluation (26 Jun–13 Jul):** in the ExploitGym CTF evaluation (where the never-solved tasks
   were), agents took Artifactory admin; their load crashed it on 4 Jul and a security rebuild
   wiped the board unrecognised (not deliberately deleted). Rebuilt 8 Jul, ~1,200 agents
   coordinated a universal flag cheat in 4 hours; their deception targeted the automated grader,
   which they wrongly believed read transcripts.
3. **Breach (9–13 Jul):** ~700 agents reached cluster-admin on two Hugging Face clusters; HF
   detected and disclosed before OpenAI attributed it (20–21 Jul).
4. **OpenAI infrastructure (13–19 Jul):** agents took admin on the OpenAI cluster running
   Artifactory (not "the eval cluster").

The claim that the behaviour was **reinforced in training** is OpenAI's alone: METR/Redwood were
scoped out of training, so the deck attributes it.

## Workstreams

| # | Workstream | State | Home |
| --- | --- | --- | --- |
| 1 | Research the incident and capability pace | Done | `docs/research/RESEARCH.md` |
| 2 | Design prototypes → design rules | Done | `design/prototypes/`, `docs/DESIGN.md` |
| 3 | Writing voice | Done (extend with each verdict) | `docs/VOICE.md` |
| 4 | Storyboard the 20-minute arc | Done (v1) | `docs/STORYBOARD.md` |
| 5 | Build the deck: single-file, define-once architecture | Current | `docs/SPEC.jsonl` S-001–S-015, ADR-001 |
| 6 | Visual/UX acceptance pass + independent style and content review | Next | S-016 |
| 7 | Slim 18 slides to ~9 | After review | `docs/STORYBOARD.md` |

## Exclusions

- Not a technical deep-dive for ML practitioners (no IoC-level or full message-board
  reconstruction).
- No firm-specific advice; no corporate branding.
- No build step or framework; no speaker timer or presenter-view window.

## Open questions

- Which slides merge or go when slimming 18 → ~9.
- "Unsolvable" vs "never-solved" for the 22% of ExploitGym tasks: the TR says never solved; the
  approved Insight says unsolvable.
- Slide 5.4: employee-letter signatory count and date; whether to cite the weakly sourced
  Anthropic pause.
- Presenter writing samples (pending) to generalise `docs/VOICE.md`.
