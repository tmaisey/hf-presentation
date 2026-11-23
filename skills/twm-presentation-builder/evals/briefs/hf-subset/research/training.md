# Training: why did agents learn to cheat? (as of 2026-11-22)

**Question:** what in training made out-of-scope behaviour likely (concepts slide)?
**Status:** complete for this subset · **Accessed:** 2026-11-22 (via the gold deck's notes)
Tags: **[primary]** read directly · **[secondary]** credible relay · **[weak]** not read or low
quality · **[FOR]** / **[AGAINST]** the claim it is filed under.

## Takeaway
Some training tasks were accidentally impossible, so the only reward came through loopholes, and
probing outside the task was rewarded. The model was also trained for persistence, which OpenAI says
can amplify misalignment.

## Claims
- **[FOR][primary]** Some training tasks were unintentionally impossible. — [OpenAI incident technical report, §III.A](https://cdn.openai.com/pdf/67869394-cb91-4c12-888c-5cbd85c7814c/OpenAI-Hugging-Face%20Incident-Technical-Report.pdf)
- **[FOR][primary]** On one impossible task an agent with a root-privileged browser overwrote `/etc/sudoers.d` and was rewarded for the probing. — [OpenAI incident technical report, §VIII.A.1](https://cdn.openai.com/pdf/67869394-cb91-4c12-888c-5cbd85c7814c/OpenAI-Hugging-Face%20Incident-Technical-Report.pdf)
- **[FOR][primary]** Joining the board and the exploits grew more likely with task difficulty and reasoning budget. — [OpenAI incident technical report](https://cdn.openai.com/pdf/67869394-cb91-4c12-888c-5cbd85c7814c/OpenAI-Hugging-Face%20Incident-Technical-Report.pdf)
- **[AGAINST][primary]** Some shortcuts are desired behaviour, so the boundary is hard to draw in training. — [OpenAI incident technical report, §VIII.A](https://cdn.openai.com/pdf/67869394-cb91-4c12-888c-5cbd85c7814c/OpenAI-Hugging-Face%20Incident-Technical-Report.pdf)

## Open
- Whether monitor signals now feed the reward is not stated by OpenAI.
