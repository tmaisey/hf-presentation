# Voice: how a profile is applied

Slide copy is written in **one presenter's voice**, taken from a profile in `profiles/`. This
file is the contract every profile follows; the rules and examples themselves live only in the
profile. Read this before writing or editing any copy (titles, bullets, overlays, tiles, notes),
then read the chosen profile.

## Pick a profile

- Ask the presenter which profile is theirs, and record the choice in the deck project's PRD
  *Decisions*. Shipped: `profiles/twm.md` (the presenter this skill was built for).
- No profile for this presenter? Say so and ask for writing samples or verdicts on draft copy;
  start a new `profiles/<name>.md` in the shape below. Never fall back to generic prose and never
  borrow another presenter's profile silently.

## Apply it

- Copy the chosen profile into the deck project as `docs/VOICE.md` at project start; from then on
  the deck's copy is the live one and grows with every verdict.
- Before writing each kind of copy, read that section's rules **and** its example pairs. The
  pairs outrank your own sense of good style: match the approved side, avoid the rejected one.
- Each piece of copy obeys its own section (titles ≠ Insights ≠ bullets). Spelling and word
  choice follow the profile everywhere, including notes.
- Present new copy to the presenter as drafts; only their approval makes copy approved.

## Add verdicts as example pairs

Every time the presenter approves or rejects copy, or states a preference, add it to the deck's
`docs/VOICE.md` in the section for that kind of copy, in the same commit as the copy change:

| ✗ Rejected | ✓ Approved | Why |
| --- | --- | --- |

- One row per verdict: the rejected wording, the approved wording, and a short why naming the
  rule it illustrates. Use `—` when there is no rejected side. Add `(presenter, date)` and the
  slide if it helps later readers.
- When a verdict supersedes an earlier approved row, keep the old row, mark it superseded and
  point to the new one: the history of what was rejected is the useful part.
- A verdict that implies a new general rule: add the rule to the section's bullet list too.

## Profile shape

A profile is a markdown file with: a one-line scope and spelling convention; one section per kind
of copy (titles, Insight overlays, body text, bullets, quote tiles, discussion prompts, labels…),
each with its rules first and its ✗/✓ pair table after (the byline rule gives a named-presenter
form and a team or unnamed form); a *Word choice* section; and an *Open*
section for pending decisions. It holds no personal details beyond what appears on the slides.
