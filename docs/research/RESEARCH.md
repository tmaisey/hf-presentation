# Research index

Sourced research on the 2026 OpenAI – Hugging Face incident. **Report = canonical synthesis**;
notes = raw evidence behind it (quotes, URLs, per-claim sourcing).

| File | Description | When to use | When to update |
| --- | --- | --- | --- |
| `reports/OpenAI Hugging Face swarm incident.md` | Synthesis: reconciled timeline, claim-by-claim verdicts on presenter's account, slide-safe quotes, disputes table, implications | First stop for any factual slide, storyboard beat or speaker note | When new facts land or a dispute resolves. Not for raw evidence: that's notes |
| `research_notes/OpenAI Hugging Face swarm incident/` | Raw notes: `training_phase`, `eval_phase_and_hf`, `forensics`, `implications`; `firings` = Oct 2026 dismissal of OpenAI staff who worked on the investigation (sourced, reason disputed); `quotes` = verified agent-message overlays per pop-up event (verbatim vs `{}` paraphrase, page refs); `other_takeovers` = S-024 verdicts on further takeovers (Sep DNS escape, mid-Aug "research cluster", 19 Jul model) | Verifying a specific claim/quote or chasing a source the report cites. **Read `quotes` before putting any agent message on a slide** | Only when re-researching that strand. Record new strands as a new file + mention here |
| `research_notes/AI capability pace 2026/capability_pace.md` | Capability/compute/spend trends vs pauses and pledges (for/against tagged), for storyboard slide 5.4 | Writing or checking the capability-pace slide | When re-researching pace |
| `research_notes/AI capability pace 2026/public_sentiment.md` | US public sentiment on AI benefits vs risks (polls), AI in the Nov 2026 midterms, AI-linked market drops, and industry calls for pacing/transparency after the incident; quality-tagged, dated, cited | Writing or checking s-10's takeaway tiles 2 and 3 | When a sentiment, election, market or transparency claim is added or corrected |

**Caveats:** `quotes.md` supersedes the report's *Slide-safe quotes* table and the report
wherever they differ, e.g. the credentials line is a paraphrase; the DryRun line was not verbatim;
"OpenAI's scorer did not review transcripts" is not in the METR PDF (see its *Corrections*).
 OpenAI blog posts were unreadable (403); OpenAI's technical report PDF was read
directly. METR braces `{}` mark paraphrase — check agent quotes against the METR PDF before
putting them on a slide.

**Slide-7 takeover check (S-024, settled):** no further cluster takeover is confirmed. The Sep 2026
escape was DNS-only internet access (no cluster or admin access); the mid-Aug "research cluster"
report has no primary support. OpenAI's own report attributes the 19 Jul OpenAI-cluster takeover to
a different, Astra-family model, not the HF agents. See `other_takeovers.md`.
