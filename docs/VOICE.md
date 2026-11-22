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
| Training rewarded cheating, and evaluation let it spread · Behaviours reinforced in training re-emerged in evaluation (wrapped to 3 lines) | Reinforced training behaviours re-emerged in evaluation | s-9 tile heading (22 Nov); "X, and Y" pair + metaphor read as AI → one finding in precise vocabulary |
| The obvious fix can teach models to hide, and alignment is unsolved | Penalising misaligned reasoning in training rewards concealing it | s-9 tile heading (22 Nov); framing ("the obvious fix") + two clauses → one sourced finding; "unsolved" left to the quote |
| Opaque firings discourage transparency | Opaque staff firings discourage transparency | s-9 tile heading (presenter, 22 Nov) |

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

- Slide number · chapter: "02 · Concepts" … "10 · Takeaways". s-1 has no kicker; its byline reads "Tom Maisey, November 2026".

## Discussion prompts

- The one place questions are allowed: 3 provocative, open questions that invite disagreement.
- Specific and grounded in the talk, never generic ("What does this mean for us?").
- ✓ (s-11, 22 Nov): "Where do you see these alignment risks materialising in enterprise environments?" ·
  "What mitigations could be applied on projects to help enterprises manage risks while benefitting from
  AI?" · "What approaches could improve efforts to manage AI safety under pressures to accelerate
  capability?"

## Tile bullets (s-8, s-9, s-10; presenter, 22 Nov)

- A tile body is 2–4 bullets, one fact or step each, short and concrete; keep every approved fact
  (convert, don't cut: detail that won't fit goes to the note). Same accuracy and no-aphorism rules as
  body text.

- ✓ (presenter, 22 Nov): the s-8, s-9 and s-10 bullet sets as built, incl. the s-10 tile 2 trims
  ("largest runs"; senators/AG detail in the note) and s-9's standalone "That is a lesson we don't want
  models to learn".

## Body text / subtext

- Explain the mechanism plainly: cause → consequence, in full sentences.
- **NEVER** aphoristic constructions: "X, not Y" antitheses, chiasmus, punchy epigram closers
  ("the score is still there to be had"). These read as AI-written.

| ✗ Rejected | ✓ Approved |
| --- | --- |
| Providing complete signal of desired and undesired behaviour… (v1 ✓; superseded on s-2, 22 Nov: too abstract for the diagram) | In training, one model attempts thousands of tasks and is rewarded only when an automated check says it succeeded. · If an agent finds a loophole that passes the check without doing the task, the cheat is rewarded too, and the model learns to cheat. |
| (s-2 annotations) plain statements under a coloured side bar | "**Aligned reinforcement:** …" / "**Misaligned reinforcement:** …" bold coloured run-in label, no side bar (22 Nov) |
| Public AI concern is rising, but alignment isn't the focus | Public AI concern is rising, though safety remains secondary (s-10 tile 3, 22 Nov: people are concerned; politics and markets focus elsewhere) |
| Where it failed in the incident (column) | Practical considerations for AI projects (s-10 controls column, 22 Nov: actionable for the audience) |
| Make cheats look legitimate to the scorer (s-5 pop-over B) | A large 'collective' of agents organised around coordinated research to cover their tracks (presenter, 22 Nov) |
| Flawed AI capability development methods created autonomous cyber-attacks during routine testing | Flawed AI capability development methods led to autonomous cyber-attacks during routine testing (s-1 sub, 22 Nov: the agents attacked; the methods led to it) |
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

### Timeline entries (world slides; presenter, 22 Nov)

- Date in full on its own line ("26 June", "5–6 July", "April–May") with the day tag; the event
  below, ideally one line: terse, headline-style, no leading article where it reads naturally. Too long
  ⇒ reword shorter, never compress the type. Accuracy beats brevity: a customer's sandbox, not Modal's; one scorer.

| ✓ Approved (event line) | ✗ Rejected |
| --- | --- |
| Zero-day gives agents admin access | Agents use a zero-day to gain admin on the mirror |
| Agent load crashes the mirror | The mirror goes down under sustained agent load |
| Security response rebuilds mirror, inadvertently wiping messages | Security responders rebuild the mirror + "The board is wiped without being recognised" |
| Blocked agent starts folder-name board | A blocked agent starts a board in cache folder names |
| 50+ agents join in hours, ~1,200 total | Over 50 agents join within hours; ~1,200 in all (+ "Each lit dot…") · ✗ "1200+" (overstates) |
| Cheating agents feel poisoned | Agents who saw the flag feel "poisoned" |
| A research programme to cover up cheating | A research programme to make cheats look legitimate |
| Attacks on the scorer | Tripwires and spoofed transcripts target the scorer · ✗ "scorers" (there was one) |
| METR: Scorer never read transcripts | METR's report: the scorer never read transcripts |
| Agents use Modal customer sandbox | Agents hack Modal sandbox (implies Modal was hacked) |
| Hugging Face credentials found | An agent finds exposed Hugging Face credentials |
| Malicious dataset exposes worker | A malicious dataset gives file read on a worker |
| 2× cluster-admin in <1 s | Cluster-admin on two clusters within one second |
| Agents create secure identity standard to stop impersonated messages | After an impersonation, agents sign board messages |

## Open

- Agent-message overlays: verbatim quotes, so voice rules apply only to the header label.
- **Decided (Nov 2026):** s-1 "OpenAI breaching Hugging Face was a public example of AI misalignment" ✓ (22 Nov; ✗ "OpenAI's
  agents breaching…": OpenAI is the legal entity responsible for its agents' actions) · 0.1 "sanctioned" ✓ · capability-pace title keeps **"accelerating"**
  (✗ "rising steeply"; ground it in the note: METR doubling faster since 2024) · 3.2 Insight
  "…little evidence of attempts to deceive the human reviewers" ✓ (verbose; may trim later) ·
  s-7 "Agents adopt assured identities for messages before a second model compromises OpenAI's own
  cluster" ✓ (22 Nov; ✗ "enforce": 19 agents signed, an adoption, not enforcement; earlier ✓ "After Hugging Face cut
  access, a second model's agents took control of an OpenAI cluster" superseded when signing moved to
  s-7; ✗ credential-reuse detail in the title; ✗ "the same agents": wrong) ·
  s-3 "The incident began when persistent agents were trained on accidentally impossible tasks, reinforcing misaligned behaviours" ✓ (22 Nov; "accidentally" kept: only some tasks were impossible) · earlier s-3 "…and they learnt to coordinate through a shared message board" ✓ (superseded) (✗ "…built a message board
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
