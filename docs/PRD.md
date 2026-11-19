# PRD — Hugging Face / OpenAI incident talk

## What

A 20-minute talk to colleagues at a professional services firm (AI-safety interest group) on the
2026 OpenAI agent-swarm incident that reached Hugging Face. Delivered as a **single self-contained
HTML file**.

## Why

The incident is well reported, so the audience's value is in **implications**, not retelling:
what it shows about reward hacking, emergent coordination and deception, and why training these
behaviours out is hard (naive penalties can teach concealment rather than honesty).

## Shape (draft — refined in storyboard)

| Section | ~min |
| --- | --- |
| Concepts (RL, reward hacking, CTF, eval vs training) | 3 |
| What happened + why | 5 |
| Implications + difficulty of training it out | 8 |
| Discussion | 4 |

## Requirements

- **Grounded:** every factual claim traceable to a cited source in `docs/research/`. Disputed or
  single-sourced claims flagged as such on-slide or in notes.
- **Accessible:** concepts introduced briefly for a non-ML professional audience.
- **Single HTML file:** no build step, works offline, presenter-driven.
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
- **Agent messages:** at key points, real agent messages surface as frosted overlays styled
  like Insight overlays, headed by the agent name with the message beneath. Only verified
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

- Audience familiarity with RL / LLM agents.
- Design concepts the presenter has in mind.
