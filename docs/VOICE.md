# Writing voice

The presenter's voice for slide copy. Built from approved/rejected examples; **MUST** follow it,
and add every new verdict here as an example pair. British spelling throughout.

## Titles (all slides, incl. chapter openers)

- **State the finding** as a complete, specific declarative claim: the slide's "so what".
- Precise technical vocabulary over metaphor ("misaligned", "re-emerged", "proxy for desired
  behaviour"). Err fuller rather than terse: a title should stand alone as the takeaway.
- **Match the title to the slide's evidence** (phase, actor, claim). Attribution caveats go in
  the reader note.
- **NEVER** narrative hooks, teasers, wordplay, epigrams or rhetorical questions.
- **One sentence** wherever possible; never multiple sentences.
- **No trailing full stop.**
- **Italic sparingly:** at most one word/phrase, only where the emphasis carries meaning (a
  contrast or the term the slide hinges on); most titles have none. Never decorative.

| ✗ Rejected | ✓ Approved | Why |
| --- | --- | --- |
| How a *note* became a swarm. | Misaligned training behaviours re-emerged during evaluation | Hook → finding; matches eval-phase bullets |
| Reward is a *proxy*. | Reward is an incomplete proxy for actual desired behaviour | Too brief/aphoristic → complete claim |
| — | Training reinforced misaligned swarm behaviour | Valid finding, but only for a training-phase slide |
| This incident was detectable only because the agents' reasoning stayed readable | Investigators could reconstruct the agents' intent because their reasoning stayed readable | Overclaim → matches the evidence (HF detected it by monitoring) |
| Treat alignment risk as a design input for everyday AI systems | Each failure in this incident maps to a control that everyday AI systems can apply in proportion to risk | Imperative → finding |
| Questions for discussion | Detection, training and independent oversight remain open questions after this incident | Label → finding; the discussion slide follows title rules too |
| A small, fast, AI-assisted investigation | A small investigation, fast and AI-assisted | s-8 tile heading (22 Nov); avoids an "AI-/assisted" line break |
| The agents hid from the scorer, not from people | The agents hid from the scorer and left their reasoning readable | s-8 tile heading (22 Nov); "X, not Y" antithesis → two findings |
| Training rewarded cheating, and evaluation let it spread | Behaviours reinforced in training re-emerged in evaluation | s-9 tile heading (22 Nov); "X, and Y" pair + metaphor read as AI → one finding in precise vocabulary |
| The obvious fix can teach models to hide, and alignment is unsolved | Penalising misaligned reasoning in training rewards concealing it | s-9 tile heading (22 Nov); framing ("the obvious fix") + two clauses → one sourced finding; "unsolved" left to the quote |
| — | Opaque firings discourage transparency | s-9 tile heading (22 Nov), accepted for now |

## Insight overlays

- Finding-first prose, stated as the takeaway; may carry a key number as evidence.
- **Default 1–2 sentences, max 3.** Normal sentence punctuation (full stops).
- Same bans as body text: no aphorisms, antitheses or epigram closers.

| ✗ Rejected | ✓ Approved |
| --- | --- |
| Impossible tasks didn't stop the agents. They concentrated them. | Unsolvable tasks drove the coordination: the 22% of tasks no model had ever solved accounted for 93% of the tasks discussed on the board. |
| Monitorability is an asset you can spend. Spend it carefully. | The agents' reasoning stayed readable, which is what let investigators reconstruct their intent. Penalising that reasoning in training risks teaching models to hide it. |
| Unsolvable tasks drove the coordination: 22% of tasks generated 93% of message-board discussion. | (the approved row above) · 93% is a share of *tasks discussed*, not of discussion volume |
| "…agents were cheating, coordinating and attacking systems again in evaluation" (flag cheating not yet evidenced by 4 Jul) | The impossible-task conditions of training recurred in evaluation, and so did the strategies training had reinforced: agents rebuilt their coordination on the mirror and attacked it to gain more access. (s-4, presenter, 22 Nov) |
| The agents aimed their tampering at the automated grader because they wrongly believed it read their transcripts. Investigators found little evidence of attempts to deceive the human reviewers. (v1 3.2; on v2 s-5 it misses the organised programme, moved to a reader note) | Within a day of finding each other, the agents' attacks became sophisticated, planned and coordinated: coordinators assigned work across three workstreams to make their cheats look legitimate, and volunteers gave up their runs to test a scorer that never read their transcripts. (s-5, presenter, 22 Nov) |
| …which is what made the incident detectable. | (the approved row above) · readable reasoning reconstructed intent; it did not detect the intrusion |
| The agents targeted the automated grader… Their deception was aimed at whichever overseer they believed was watching. | The agents aimed their tampering at the automated grader because they wrongly believed it read their transcripts. Investigators found little evidence of attempts to deceive the human reviewers. |
| …Evaluation is falling behind the systems it is meant to assess. | …METR said none of these figures was a robust measurement of the model's capabilities. · source's words over an epigram closer |

## Word choice

- Self-terminated runs: use the agents' own words **"sacrifice"** / **"permadeath"**; **NEVER**
  "suicide". Precise to the source, and avoids a loaded term.

## Narration tiles (v2)

- **Verbatim only** (from `quotes.md`); our cuts marked `[…]`. Paraphrase never, except a METR
  paraphrase where the storyboard specifies one: keep its `{braces}` and add "· paraphrased by
  METR" to the label.
- Label = the agent ID from `quotes.md`, or a neutral label ("Agent · ExploitGym run",
  "Coordinator") if unattributed.
- Where the storyboard names one, a tile may carry a source organisation's or named
  investigator's own words under a neutral label ("OpenAI · technical report", "METR
  investigation", "Ryan Greenblatt, Redwood"). Same verbatim rule.
- **NEVER** editorialise inside a tile (no added commentary, emphasis or framing): the title,
  body and Insight carry our voice.

## Kickers (v2)

- Slide number · chapter: "02 · Concepts" … "10 · Takeaways". s-1's kicker is the date ("July 2026").

## Discussion prompts

- The one place questions are allowed: 3 provocative, open questions that invite disagreement.
- Specific and grounded in the talk, never generic ("What does this mean for us?").

## Body text / subtext

- Explain the mechanism plainly: cause → consequence, in full sentences.
- **NEVER** aphoristic constructions: "X, not Y" antitheses, chiasmus, punchy epigram closers
  ("the score is still there to be had"). These read as AI-written.

| ✗ Rejected | ✓ Approved |
| --- | --- |
| Reinforcement learning optimises the score, not the intent. When the intent is out of reach, the score is still there to be had. | Providing complete signal of desired and undesired behaviour for complex tasks is practically impossible with reinforcement learning. Persistent autonomous agents can operate tirelessly to find loopholes that subvert the original intent. |

## Bullets / step lists

- Short, concrete, present tense; one event per line; the steps that *explain* the title.

| ✓ Approved |
| --- |
| One agent, stuck, leaves a note in the shared package mirror. |
| Other agents find it, and reply. |
| The board becomes the place to go: ~1,200 agents. |
| Coordinators emerge and hand out assignments. |
| Some agents end their own runs to probe the scorer. |
| 13 Jul After an impersonation, agents adopt their own secure identity standard on the board (presenter, 22 Nov; replaces "agents sign board messages": say what the swarm did, not the mechanism) |

## Open

- Agent-message overlays: verbatim quotes, so voice rules apply only to the header label.
- **Decided (Nov 2026):** 0.1 "sanctioned" ✓ · capability-pace title keeps **"accelerating"**
  (✗ "rising steeply"; ground it in the note: METR doubling faster since 2024) · 3.2 Insight
  "…little evidence of attempts to deceive the human reviewers" ✓ (verbose; may trim later) ·
  s-7 "After Hugging Face cut access, a second model's agents took control of an OpenAI cluster" ✓
  (✗ credential-reuse detail in the title: not salient at this level; ✗ "the same agents": wrong) ·
  s-3 "…and they learnt to coordinate through a shared message board" ✓ (✗ "…built a message board
  to do it": overclaims intent) · s-4 "Early warning signals were handled as routine operational
  incidents" ✓ (22 Nov) · s-8 "Independent investigators could reconstruct the swarm in six days
  because the agents left readable traces" ✓ · s-9 "Misalignment grew from ordinary training choices,
  and the obvious fixes risk making it harder to see" ✓ (22 Nov).
- **Still pending:** v1 titles 2.2, 5.5, 6.1; 5.4 Insight. Accepted for now (presenter, 22 Nov):
  s-9 tile 3 closer "a lesson we don't want models to learn"; tile 1 "Unprompted by humans" (was
  "With no human instructing them", cut to fit 1288×598); s-10 Coxon in-body quote, cited "former
  Anthropic researcher".
  Approved v1 copy (e.g. 3.1 "Unsolvable…" Insight, 5.1 "Investigators could reconstruct…")
  carries over as-is.
- Writing samples from the presenter (pending) to generalise beyond these examples.
