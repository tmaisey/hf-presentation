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

## Insight overlays

- Finding-first prose, stated as the takeaway; may carry a key number as evidence.
- **Default 1–2 sentences, max 3.** Normal sentence punctuation (full stops).
- Same bans as body text: no aphorisms, antitheses or epigram closers.

| ✗ Rejected | ✓ Approved |
| --- | --- |
| Impossible tasks didn't stop the agents. They concentrated them. | Unsolvable tasks drove the coordination: 22% of tasks generated 93% of message-board discussion. |
| Monitorability is an asset you can spend. Spend it carefully. | The agents' reasoning stayed readable, which is what made the incident detectable. Penalising that reasoning in training risks teaching models to hide it. |

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

## Open

- Agent-message overlays: verbatim quotes, so voice rules apply only to the header label.
- Writing samples from the presenter (pending) to generalise beyond these examples.
