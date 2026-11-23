# Storyboard: method and template

The storyboard is the deck's **content plan**: one file (`docs/STORYBOARD.md` in the deck
project) that says what each slide claims, shows, cites and serves, and how long it takes. Write
it after the PRD's core message is agreed and before any slide is built; every slide build reads
its row first. It holds content only: visual rules live in the design parts, wording rules in the
voice profile, facts in the research notes.

## Method

1. **Core message first.** Agree with the presenter 2–4 things the room should leave believing
   (in the PRD). Code them **M1, M2, M3…**, plus **T** for a practical takeaway if the talk has
   one. Every slide **must** serve at least one code, or be a structural slide (title, close)
   marked `—`. A slide that serves nothing is cut, not polished.
2. **Arc and chapters.** Choose an arc that carries the message (chronological, problem →
   cause → fix, claim → evidence → implication). Group slides into chapters; each chapter opener
   is a slide and follows the same title rules.
3. **Timings.** Give every slide a time (m:ss) and keep a running total against the slot,
   Q&A included. When the total overruns, ask the presenter what to cut or whether to accept the
   longer talk, and record the answer next to the total.
4. **Per-slide entry.** For each slide record: title (with approval mark), codes served, time,
   visual (layout and what the diagram shows), build steps (what each step adds, one state per
   step, numbered from 0), overlays (Insight, narration/quote tiles, pop-overs), sources for
   every claim on the slide, and reader-note content.
5. **Title approval marks.** Titles are findings (voice profile) and the presenter approves each
   one. Mark every title: **✓** approved (add who and when) · **◇** carried over, pending approval
   · **✎** new, needs approval. Never mark a title ✓ yourself. Record rejected wordings beside the
   approved one (✗ …) so the reason survives; the voice profile gets the pair too. With no
   presenter available (a test build, or the presenter unavailable), draft titles to the voice
   profile and leave them ✎: a slide can be done with ✎ titles, but the deck is not presentable
   until every title is ✓.
6. **Sources inline.** Each fact on the slide names its source in the entry using short codes
   defined in the header (e.g. `R` = research report, `N` = note, page refs `p12`). Flag thin
   evidence **⚠ thin** and disputed or single-sourced claims as the research part requires.
7. **Visible words.** When a word cap applies (the brief, or the eval profile's CN-04
   `max_words`), count per **step**: every word on screen at that step, and the slide's wordiest
   step must be within the cap. Counted: kicker, title, body text, list items, cite lines, card
   sender lines, tile and table text, diagram text (tile titles, labels, tags, values), and any
   Insight, narration tile or pop-over shown at that step, softened or not. Not counted: reader
   notes, the chrome (title bar, agenda, Notes button), parts not shown at that step, and a
   shared scene's own diagram text. A word is any space-separated run with a letter or digit
   (so "·" and "—" are not words). When the cap fights the voice profile (fuller titles, 1–2
   sentence Insights), the voice wins on wording: move detail to the reader note, let the
   diagram carry it, split the beat into steps that replace each other, or split the slide; never
   cut a title below a complete finding. If it still runs over, record the accepted overrun in
   PRD *Decisions*, and the eval will report it.
8. **Decisions in place.** When the presenter decides something about a slide, write it in that
   slide's entry with "(presenter, date)". The storyboard is the single home for slide content;
   don't repeat it in specs or code comments.

**Worked example (described, not linked).** The incident talk this skill was built from used a
chronological 12-slide arc of ~21 minutes including 4 minutes of Q&A. Three message codes plus
`T` were defined in the header; each slide entry gave its build as numbered steps ("0 opening ·
1 pop-over card · 2 second card · 3 first dated event…"), named every narration tile's quote with
its page reference, and noted what a slide must **not** reveal yet because a later slide owns
that reveal. The running-order table recorded that the presenter accepted a talk one minute over
the slot.

## Template

Copy into the deck project as `docs/STORYBOARD.md` and fill in. Keep entries terse: the steps
describe beats, not final copy.

```markdown
# Storyboard

<N>-slide <arc> arc, ~<total> min incl. <q&a> min Q&A. Copy follows the voice profile; visuals
follow the design parts.

**Codes.** Core message (PRD): **M1** <belief 1> · **M2** <belief 2> · **M3** <belief 3> ·
**T** practical takeaway. **Ins** = Insight overlay. **Narr** = narration/quote tiles.
**⚠ thin** = little evidence for this beat. Sources: **R** = <research report> ·
**N** = <note file> · <other source codes and page-ref format>.

**Titles:** finding-first, one sentence, no full stop. ✓ = approved · ◇ = pending approval ·
✎ = new, needs approval.

| # | Slide | Chapter | Serves | Time |
| --- | --- | --- | --- | --- |
| s-1 | Title | — | — | 0:30 |
| s-2 | <short name> | <chapter> | M1 | 1:30 |
| | **Total** (<slot, any accepted overrun>) | | | **<m:ss>** |

---

## s-2 · <short name> (<m:ss>) · <codes served>

✎ *<Title: the slide's finding as one declarative sentence>*
- **Visual:** <layout; what the diagram or image shows; what persists from the previous slide>
- **Steps (<n> states, 0–<n-1>):** 0 <opening state> · 1 <what is added> · … ·
  <last> **Ins**: "<Insight text, finding-first>"
- **Overlays:** Narr <step>: <label> "<verbatim quote>" (<source + page>) · pop-over: <card>
- **Sources:** <claim> (<source code + page>) · <flag: ⚠ thin / single-sourced / disputed>
- **Notes:** <reader-note content: caveats, attribution, detail cut from the slide>
- **Decisions:** <what the presenter decided, (presenter, date)> · ✗ <rejected wording>
```
