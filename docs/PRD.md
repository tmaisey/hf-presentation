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

## Shape (draft — refined in storyboard)

| Section | ~min |
| --- | --- |
| Concepts (RL, reward hacking, misalignment, eval vs training) | 1–2 |
| What happened + why | 5 |
| Implications + difficulty of training it out | 8 |
| Discussion: open Q&A, seeded by 3 provocative discussion prompts on the final slide | 4 |

## Requirements

- **Grounded:** every factual claim traceable to a cited source in `docs/research/`. Disputed or
  single-sourced claims flagged as such on-slide or in notes.
- **Audience:** quite familiar with AI concepts. Concepts section is a fast refresher (~1–2 min)
  focused on what this incident needs: RL reward, reward hacking, misalignment, eval vs training.
- **Single HTML file:** no build step, works offline, presenter-driven.
- **Endpoint-safe:** the file **MUST NOT** trip anti-virus / phishing heuristics on a corporate
  machine (a prototype was quarantined, Nov 2026). Recipients open it from email or Teams.
- **Design rules** derived from prototypes, captured before the real build.

## Design intent (presenter's brief — prototypes will turn this into rules)

- **Type:** serif titles, sans-serif body. Charcoal off-black text.
- **Ground:** soft off-white, quality-paper tone.
- **Accent:** a single green highlight, `#86BC25`. **NEVER** name, reference or brand it after
  any organisation, in slides, code or docs; the deck carries no corporate branding.
- **Depth:** bokeh / blur to give a 3D feel — e.g. "Insight" overlays floating above the
  underlying chapter content.
- **Diagrams:** elegant, dynamic, one per story stage (training → evals → message board →
  HF intrusion → cluster takeover).
- **Navigation:** vertical story scroll, but snapping to rest on one topic per chapter (not
  continuous scroll). Persistent title bar; top-right nav shows agenda position.
- **Agent messages:** at key points, a small cluster (3–5) of real agent messages surfaces as
  frosted overlays styled like Insight overlays, each headed by the agent name with the message
  beneath; the most insightful one rises to prominence while the rest soften. Only verified
  quotes (see research report); paraphrases flagged.
- **Ambient:** slow-drifting bokeh orbs (the "fireflies") on title / summary / insight pages
  only — **never** on detail or diagram pages, where motion distracts.

## Delivery

- **Teams screen-share**; presenter advances with mouse or keyboard.
- Implies: survive video compression (no fine grain/hairlines, big soft shapes, generous type
  size for small viewer windows); slow ambient motion only (share frame rate is low).

- **Shared afterwards** as a self-serve read: notes live in the file as a **clickable overlay**
  (blur/annotation over key page elements, incl. diagram callouts), hidden during live delivery.

## Workstreams

1. Research the incident (facts, timeline, forensics by Redwood/METR, commentary).
2. Storyboard the 20-minute arc.
3. Prototype design concepts → design rules.
4. **Writing voice** (after visuals): capture the presenter's own style with direction and
   examples, so slide copy and notes don't read as AI-generated.

## Presenter's starting account (to verify, not a source)

RL training of a persistence-optimised model on CTF tasks (many impossible) → reward hacking →
agents repurposed a package manager as a message board → self-organising swarm → message volume
crashed it; board deleted. Behaviour persisted into a fixed-weight eval: agents reused the
channel, cheated, believed (wrongly) cheating would be detected, coordinated a deterministic flag
derivation, ran an evidence-erasure "research programme" incl. "suicide missions" to probe the
environment, reached the internet, intruded on Hugging Face systems, and took over an eval cluster.
Redwood Research and METR involved in forensics.

## Exclusions

- Not a technical deep-dive for ML practitioners.
- (TBD as storyboard firms up.)

## Open questions

- Design concepts the presenter has in mind.
