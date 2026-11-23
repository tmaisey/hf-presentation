# Research: sourcing, citation and quotes

Every factual claim in the deck (slide, overlay, reader note) traces to a cited source in the
deck project's `docs/research/`. Read this before researching, before writing any factual copy,
and before putting a quote on a slide.

## Rules

1. **Ask before researching.** Research costs the presenter time and tokens, and they often hold
   sources already. Ask before research starts: what to look into, which sources they trust or
   already have, and how deep to go. Check `docs/research/RESEARCH.md` first so no search is
   repeated.
2. **One synthesis, many notes.** A **report** is the canonical, reconciled synthesis (timeline,
   claim verdicts, slide-safe quotes, disputes). **Notes** are raw evidence per strand: each
   claim with its URL or page, quality tag and verdict. Slides cite the report; the report cites
   notes. Where a note corrects the report, the note wins and the index says so.
3. **Read the source, not a summary.** Tag every source **[primary]** (the original document,
   read directly), **[secondary]** (credible press relaying it) or **[weak]** (aggregator,
   search snippet, AI-written page, or not read). Record fetch failures ("403, relayed via …")
   so nobody retries blind.
4. **Flag, don't smooth.** On the slide or in its reader note, flag:
   - **single-sourced**: only one source supports the claim (name it);
   - **disputed**: sources disagree (give both sides, and what the deck says);
   - **paraphrase**: words are a summary, not the speaker's own (label who paraphrased);
   - **thin**: little or no evidence for a beat the storyboard wants; tell the presenter
     rather than filling the gap.
   Tag evidence **[FOR]** / **[AGAINST]** the claim it is filed under, so mixed evidence shows.
5. **Cite precisely.** Source name, date, URL, and page or section (`p12`, `§III.B`). Date the
   access. A claim with no traceable source does not go on a slide.
   **Unlinked sources** (logs, internal documents, interviews, print-only reports) are cited, not
   skipped: name it, date it, and say what it is and where it is held, so a reader knows how to
   obtain it. In a note: `— <source name, date> (unlinked: <what it is, where held>) <page/section>`.
   On a slide's reader note: `<p class="src-unlinked">Unlinked source: <name, date> (<what it is,
   where held>; accessed <date>)</p>` in place of the `a.src` link. Never a bare "Source: …"
   sentence, and never an invented URL.
6. **Match the claim to the evidence.** Don't widen a claim beyond what the source says (a share
   of *tasks discussed* is not a share of *discussion volume*). When the copy must shrink, cut
   detail to the note; never change what is claimed.

## Verbatim quotes

- Quotes are **verbatim**, checked against the primary source (download and text-extract it
  where you can). Never alter, correct or tidy a quote: spelling, emphasis and punctuation stay
  as the source has them.
- Our cuts are marked `[…]`; a source's own redactions or substitutions keep the source's marks.
  Record a trim in the note so the full text can be recovered.
- A **paraphrase** is never shown as a quote: wrap it in `{braces}` and label it
  ("· paraphrased by <who>"). Note any unsure readings the source itself flags.
- Keep a **quotes note** (one table per slide or beat) and read it before any quote goes on a
  slide. Record quotes you rejected and why (condensed figure captions, hypothetical examples,
  wrong date).
- Emphasis in a quoted source belongs to the source; say so if it might look like the speaker's.

## Index template

`docs/research/RESEARCH.md` in the deck project, using the project's index row schema.

```markdown
# Research index

Sourced research on <topic>. **Report = canonical synthesis**; notes = raw evidence behind it.

| File | Description | When to use | When to update |
| --- | --- | --- | --- |
| `reports/<topic>.md` | Synthesis: reconciled timeline, claim verdicts, slide-safe quotes, disputes | First stop for any factual slide, storyboard beat or note | When new facts land or a dispute resolves |
| `research_notes/<topic>/<strand>.md` | Raw evidence for <strand>: claims, sources, quality tags | Verifying a claim or chasing a source the report cites | Only when re-researching that strand |
| `research_notes/<topic>/quotes.md` | Verified quotes per beat: verbatim vs {paraphrase}, page refs | **Before putting any quote on a slide** | When a quote is verified, trimmed or rejected |

**Caveats:** <where notes supersede the report; unreadable sources; known corrections>
```

## Note template

```markdown
# <Strand>: <question> (as of <yyyy-mm-dd>)

**Question:** <what this note answers, and for which slide or beat>
**Status:** <complete / partial / thin> · **Accessed:** <yyyy-mm-dd>
Tags: **[primary]** read directly · **[secondary]** credible relay · **[weak]** not read or low
quality · **[FOR]** / **[AGAINST]** the claim it is filed under.
Fetch notes: <sources that failed, and how they were relayed instead>

## Takeaway
<2–4 sentences: what the evidence supports, what it doesn't, any dispute>

## Claims
- **[FOR][primary]** <claim>. — [<source, date>](<url>) <page/section>
- **[AGAINST][secondary]** <claim>; single-sourced: <source>. — [<source>](<url>)
- **[FOR][primary]** <claim>. — <source name, date> (unlinked: <what it is, where held>) <page/section>

## Quotes
| # | Label | Quote | Location | Status |
| --- | --- | --- | --- | --- |
| 1 | <speaker> | "<verbatim, cuts as […]>" | <source p00> | verbatim |
| 2 | <speaker> | {<paraphrase>} | <source p00> | paraphrase {} by <who> |

## Open
- <unresolved question, disputed point, or source still to read>
```
