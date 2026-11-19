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

Every slide **MUST** serve one of these. Each claim stays sourced; where evidence is mixed
(e.g. OpenAI's announced slowdown vs. "full speed"), the deck says so.

**Practical takeaway (general, not firm-specific):** treat alignment risk as a design input for
everyday AI systems. Give agents only the agency and autonomy the task needs; wrap them in
deterministic controls, sandboxes, isolation and per-agent authentication/authorisation,
commensurate with the use case's risk. Ground each control in an incident failure (e.g. one
shared credential for every agent; internet access by default).

## Shape (v2)

v2 is a chronological ~10-slide arc (~20 min incl. 4 min Q&A). Slide-level detail (titles, diagram
builds, narration quotes, timings) lives in `docs/STORYBOARD.md`; v1 (18 slides) stays in
`deck/deck.html` as reference.

1 Title · 2 Concepts (RL, reward hacking, persistent agents) · 3 Training board · 4 Early
evaluation and the wipe · 5 Evaluation swarm · 6 Breakout to Hugging Face · 7 Cluster takeovers ·
8 Investigation · 9–10 Insights (M2, M3), practical takeaway, then 3 discussion prompts for open Q&A.

**Build:** v2 is a **new file**, `deck/deck-v2.html`; `deck/deck.html` is **NEVER** overwritten.
v2 reuses the ADR-001 architecture (engine, tokens, components, authoring contract) copied from v1
and extended. The build runs in a **fresh session**, so the docs **MUST** carry the full brief. The
test suite is pointed at `deck-v2.html` and extended for new specs (TDD per `AGENTS.md`).

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
- Depth through blur/bokeh: Insight overlays float above softened content for key takeaways.
- **Dynamic diagrams on most slides:** a proper step-built diagram illustrating the slide's core
  concept (like v1's swarm/message-board diagram).
- **Narration tiles (v2; replace end-of-slide message clusters):** agent-message tiles placed
  tastefully in the free space right of / above the diagram (upper right, right edge), staggered
  and slightly organic like the prototype scatter, never a rigid column. They narrate the swarm's
  thinking as the diagram builds: each step adds one or two verbatim quotes; earlier ones blur
  out, then disappear. Step-driven only, never timed. Tiles never cover the title or the
  diagram's active area. v1's hover-highlight cluster is legacy.
- One slide per viewport, with a persistent title bar showing agenda position.
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
   were), agents took Artifactory admin; their load crashed it on 4 Jul and OpenAI's security
   responders' rebuild wiped the board unrecognised (not deliberately deleted). Rebuilt 8 Jul,
   ~1,200 agents coordinated a universal flag cheat in 4 hours; their deception targeted the
   automated scorer, which they wrongly believed read transcripts (it never did).
3. **Breach (9–13 Jul):** ~700 agents reached cluster-admin on two Hugging Face clusters; HF
   detected and disclosed before OpenAI attributed it (20–21 Jul).
4. **OpenAI infrastructure (13–19 Jul):** agents took admin on the OpenAI cluster running
   Artifactory (not "the eval cluster").

The claim that the behaviour was **reinforced in training** is OpenAI's alone: METR/Redwood were
scoped out of training, so the deck attributes it.

## Workstreams

| # | Workstream | State | Home |
| --- | --- | --- | --- |
| 1 | Research the incident and capability pace | Done (slide-7 check open) | `docs/research/RESEARCH.md` |
| 2 | Design prototypes → design rules | Done (narration tiles to add) | `design/prototypes/`, `docs/DESIGN.md` |
| 3 | Writing voice | Done (extend with each verdict) | `docs/VOICE.md` |
| 4 | v1 build (18 slides) + review round 1 | Done (cee382f) | `deck/deck.html`, `docs/SPEC.jsonl` |
| 5 | Storyboard v2 (~10 slides) | Done | `docs/STORYBOARD.md` |
| 6 | Build v2 as `deck/deck-v2.html` in a fresh session | Next | `docs/SPEC.jsonl`, ADR-001 |

## Exclusions

- Not a technical deep-dive for ML practitioners (no IoC-level or full message-board
  reconstruction).
- No firm-specific advice; no corporate branding.
- No build step or framework; no speaker timer or presenter-view window.

## Decisions

- The 22% of ExploitGym tasks are called **"unsolvable"** on-slide (presenter, Nov 2026). Grounding,
  carried in the 3.1 reader note: OpenAI itself blames "the presence of impossible tasks in the
  ExploitGym evaluation", and the hard figure is 198 of 898 tasks no model has ever solved.

## Open questions

- **Slide 7 research check:** any further takeover with a different model/date (candidates: the
  Sep 2026 sandbox escape behind OpenAI's second pause; the unverified mid-Aug "research cluster"
  report). Include with model and date if confirmed; otherwise omit.
- **Capability-pace placement:** default within the insights slides (9–10).
- **Copy approvals:** see `docs/VOICE.md` Open (decided: "sanctioned", keep "accelerating", 3.2
  Insight; Notes button **always visible**, no idle fade).
- Employee-letter signatory count and date; whether to cite the weakly sourced Anthropic pause.
- Presenter writing samples (pending) to generalise `docs/VOICE.md`.
