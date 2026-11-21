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
evaluation and the wipe · 5 Evaluation swarm · 6 Breakout to Hugging Face (incl. its cluster-admin) · 7 Second model takes an OpenAI cluster ·
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
- **One incident world (s-3 Training → s-6 Breakout, likely s-7 Takeover):** a single persistent,
  illustrative diagram in prototype 04's line-drawn style (not box-and-arrow) that evolves with the
  timeline. Each slide picks up where the last ended, and moving between slides animates the scene
  like a camera (presenter chose this over per-slide diagrams, 21 Nov). At Breakout the focus
  moves outside OpenAI: the internal scene simplifies and shrinks to make room for the path to
  Hugging Face.
- **Pop-over illustrations:** a concept that needs a different context (e.g. what one training
  run is) appears as an illustration on a shadowed tile over the world diagram, which blurs while
  the pop-over has focus. Quotes may pop up beside or over it. Once the point is made, all of it
  dissolves and focus returns to the world diagram.
- **Narration tiles (v2; replace end-of-slide message clusters):** agent-message tiles placed
  tastefully in the free space right of / above the diagram (upper right, right edge), staggered
  and slightly organic like the prototype scatter, never a rigid column. They narrate the swarm's
  thinking as the diagram builds: each step adds one or two verbatim quotes; earlier ones blur
  out, then disappear. Step-driven only, never timed. Tiles never cover the title or the
  diagram's active area. v1's hover-highlight cluster is legacy.
- **Quality bar: v1.** v2 must look at least as considered as `deck/deck.html`: uncluttered
  slides, diagrams that fill their space with purpose, nothing colliding, at presenter and small
  windows incl. short-wide (~1288×598). The v2 first draft missed this (20 Nov): slides crammed
  title + step list + diagram + narration column + notes into narrow space, and step lists
  restated the diagram in prose; agents also cut copy to fit, so re-check v2 copy against v1 and
  `VOICE.md`. Prefer fewer elements per slide; the diagram carries the story.
- **Vision to be captured by prototype:** the narration-tile and diagram bullets above
  under-specified the presenter's vision; prototypes judged by eye settle it before any rebuild.
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
4. **OpenAI infrastructure (13–19 Jul):** after HF cut access, agents of a **different,
   Astra-family model** took Kubernetes cluster-admin on the OpenAI cluster running Artifactory
   (not "the eval cluster"; not the HF agents' model).

The claim that the behaviour was **reinforced in training** is OpenAI's alone: METR/Redwood were
scoped out of training, so the deck attributes it.

## Workstreams

| # | Workstream | State | Home |
| --- | --- | --- | --- |
| 1 | Research the incident and capability pace | Done (slide-7 check settled, S-024) | `docs/research/RESEARCH.md` |
| 2 | Design prototypes → design rules | v1 done; v2 visuals (narration tiles, diagrams) reopened → workstream 7 | `design/prototypes/`, `docs/DESIGN.md` |
| 3 | Writing voice | Done (extend with each verdict) | `docs/VOICE.md` |
| 4 | v1 build (18 slides) + review round 1 | Done (cee382f) | `deck/deck.html`, `docs/SPEC.jsonl` |
| 5 | Storyboard v2 (~10 slides) | Done | `docs/STORYBOARD.md` |
| 6 | Build v2 as `deck/deck-v2.html` | First draft built (10 slides), **rejected on quality** 20 Nov (e.g. s-7 step list over its title; sparse diagrams, labels colliding, narration tiles far from what they narrate). Causes: layout tests switched off for v2, only per-slide screenshots (taken before the shared narration column), no prototypes for the new visuals, agent briefs led by merge-safety not quality, 16:9-only tests. Rules now in `AGENTS.md` + S-030. Tile/slide specs reopened; draft markup is raw material. **Reusable:** reader notes + sources (fact-checked), engine incl. notes-at-step (S-029) and swarm `data-stages`, test harness (S-017), recorded presenter decisions | `docs/SPEC.jsonl`, `deck/deck-v2.html` |
| 7 | Presenter explains the vision → throwaway prototypes of the key visuals (narration tiles; one or two hero diagrams) judged by eye incl. at ~1288×598 → `DESIGN.md` rules → re-spec reopened slides → rebuild (parallel is fine) behind the S-030 layout guard → S-028 review | **In progress**: header bar prototyped, approved (P5, 21 Nov) and built (S-031); incident-world diagram + pop-overs being prototyped slide by slide, Training first (P6); narration tiles next | `design/prototypes/`, `docs/DESIGN.md` |

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

- **Slide 7 research check (settled, S-024):** no further takeover confirmed. The Sep 2026 escape
  was DNS-only internet access, and the mid-Aug "research cluster" report is unconfirmed, so slide 7
  shows two events. The 19 Jul OpenAI takeover was by a different (Astra-family) model, not the HF
  agents (`other_takeovers.md`).
- **Capability-pace placement:** default within the insights slides (9–10).
- **Copy approvals:** see `docs/VOICE.md` Open (decided: "sanctioned", keep "accelerating", 3.2
  Insight; Notes button **always visible**, no idle fade).
- Employee-letter signatory count and date; whether to cite the weakly sourced Anthropic pause.
- Presenter writing samples (pending) to generalise `docs/VOICE.md`.
- **v2 first-draft review items (presenter to look):** report/investigator quotes as narration
  tiles (s-4, s-7, s-8, s-10); s-8 flagged-tile colour (loss tint vs new muted amber); s-10 stepped
  titles vs one title vs split; s-10 Nov-2026 releases row and 5.4 Insight length; agent-written
  diagram labels and short step lists (s-2, s-4, s-5, s-6, s-8). May be overtaken by prototypes.
