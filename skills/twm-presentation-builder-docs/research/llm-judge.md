# LLM-as-judge reliability: evidence for the skill's eval

Researched 2026-11-22. Scope: how to make subjective-criterion judging reliable when the judges are
Claude Code subagents (no API, so no logprobs and no temperature control; model pinnable), blind to
the builder's context, and gated by deterministic checks. Claims are cited inline as [n]. Each was
checked against the paper's abstract or full text, or against the practitioner post itself. Where only a
summary or snippet was available, the claim is marked *(secondary)*.

## 1. TL;DR for our design

1. **Use an analytic rubric with one isolated judge call per criterion.** Specific criteria agree with
   humans better than general ones, and one dimension per prompt beats several at once [21][22].
   Prefer **binary checklist items** where a criterion can be decomposed: this raised inter-judge
   agreement across 12 judge models [10] and is the practitioner default [20]. Where a graded scale is
   truly needed, use a **short 0–5 / 1–5 scale with a descriptor for every level** [3][9]. Avoid 0–10 [9].
2. **Anchor every criterion with exemplars.** Give a reference "top-score" example plus a few
   presenter-labelled examples with written critiques. In Prometheus, removing the reference answer
   caused the largest correlation drop (0.86 to 0.64) [3]. Reference-guided grading cut GPT-4's failure
   rate on maths grading from 70% to 15% [1]. Critiques double as few-shot material [20].
3. **Score pointwise against the anchors by default. Use pairwise only for A/B tests of skill versions,
   always run in both orders.** Pairwise judging flips about 35% of the time under planted distractor
   features, against about 9% for absolute scoring [11]. Pairwise needs order-swapping, with
   inconsistent verdicts counted as ties [1]. A gold reference deck works best as an **anchor inside a
   pointwise rubric**, not as a pairwise opponent. Similarity to a reference does not make a
   presentation effective [13].
4. **Require evidence, then rationale, then score, and allow "insufficient evidence".** Feedback
   before score improved Prometheus, and score-only training hurt it [3]. Anthropic recommends an
   explicit "Unknown" option to curb invented verdicts [22]. Evidence should cite slide, step and
   region. Do **not** add elaborate multi-step reasoning for visual criteria: it reduced hallucination
   but did not improve agreement with humans [12]. GPT-4 judges improved when told "don't
   overthink" [5].
5. **Replace temperature control with repetition.** Run k = 3–5 independent judge subagents per
   criterion, take the **median**, and send high-spread items to a human. G-Eval sampled 20 times to
   estimate the score distribution when token probabilities were unavailable [2]. MLLM-as-a-Judge
   recommends human review of judgments that are inconsistent across repeats [12].
6. **Treat self-preference as the main structural risk.** Claude builds and Claude judges. Models
   recognise and favour their own outputs [6], and Claude-3.5 had the highest self-enhancement error
   rate in CALM (7.5% against 1.7% for GPT-4o) [7]. A diverse-family panel (PoLL) is the strongest
   documented fix [5], but Claude Code subagents cannot provide one. Instead: calibrate against human
   labels, include deliberately flawed anchor decks, and mix pinned model tiers. Mixing tiers is
   weaker, unproven mitigation.
7. **Build a calibration set and measure the judge as a classifier.** For each key criterion, collect
   about 30–50 presenter labels per class with critiques, split into train/dev/test. Report TPR/TNR
   (not raw agreement) and Cohen's κ, or ICC/Spearman for ordinal scales. Target human–human
   agreement [20][21][9][1]. Re-run whenever the rubric, anchors or pinned model change.
8. **Visual criteria need per-slide design scoring, deck-level coherence scoring, and taste anchors
   from the presenter.** Scoring slide images is the documented approach for decks [13], but
   agreement on design is moderate and designers disagree with each other (α ≈ 0.25) [14][15][16].
   Generic "good design" judges therefore regress to an average taste, and anchors from this
   presenter matter more than for text criteria.
9. **Judge the process as an agent with tools, and verify claims against artefacts.**
   Agent-as-a-Judge, which reads files and locates evidence, matched human consensus at about 90%,
   against 60–84% for plain LLM judges [17]. Trajectory judges are fooled by agents' own success
   claims, with precision of 70% or less [18]. Process judges must therefore check commit messages,
   SPEC flips and "done" claims against the diff and tests. Grade outcomes and requirements, not one
   prescribed path [22].

## 2. Findings by topic

### Rubric design and anchoring

- **Analytic beats holistic for agreement.** EvalLM found the highest human agreement for specific
  criteria and the lowest for general ones [21] *(secondary)*. CheckEval breaks criteria into yes/no
  questions, which raised average inter-evaluator agreement by 0.45 across 12 judge models and reduced
  score variance [10]. Anthropic advises one isolated judge per rubric dimension [22].
- **Scale length.** Across six benchmarks, a 0–5 scale gave the highest human–LLM absolute agreement
  (ICC), and the choice of scale shifted alignment even when within-group reliability stayed high [9].
  Husain argues 1–5 scores are not actionable (no one can say what separates a 3 from a 4) and
  recommends pass/fail with a critique [20]. A compromise: binary checklist items roll up into a
  criterion score.
- **Anchored descriptors and references.** Prometheus rubrics pair a criterion with a description for
  each score from 1 to 5, plus a score-5 reference answer. In ablation, removing the rubric hurt most on
  unseen data (Vicuna Bench 0.457 to 0.355), and removing the reference hurt most overall [3].
  Prometheus 2 keeps user-defined criteria for both direct and pairwise modes [4].
- **Prompt-format sensitivity.** Rubric order, score labels and the score attached to a reference
  answer all shift absolute scores, even in frontier models [8]. Fix the rubric's presentation and test
  for perturbation sensitivity once.
- **Criteria drift.** People refine criteria while grading outputs [19]. Expect the rubric to change
  during calibration, and version it.

### Known biases and mitigations

- **Position.** GPT-4 was order-consistent in only 65% of swaps. Three few-shot examples raised this to
  77.5%. The fix is swap-and-tie [1]. Position bias grows with more candidates [7].
- **Verbosity and length.** A "repetitive list" padding attack fooled GPT-3.5 and Claude-v1 in 91% of
  cases, against 8.7% for GPT-4 [1]. CALM found verbosity largely solved for frontier models [7]. MLLM
  judges still gave longer content about 0.6–0.75 extra points [12]. Mitigation: state concision in the
  rubric explicitly and probe with padded decks.
- **Self-preference.** GPT-4 and Claude-v1 rated their own answers about 10% and 25% above human
  ratings [1]. Self-recognition correlates linearly with self-preference, and the authors argue it is
  causal [6]. G-Eval preferred LLM-written summaries over human-written ones that humans preferred [2].
  In PoLL, each model's largest scoring gain came when it judged itself [5].
- **Leniency and distraction.** Generator models can plant features that win pairwise judgments [11].
  CALM found sentiment, bandwagon, authority (fake citations) and distractor text still move GPT-4o and
  Claude-3.5. Bandwagon cues hit Claude hardest (robustness 0.56–0.64) [7]. This matters for us: deck
  text or reader notes that praise the deck could sway a judge. Tell judges to ignore self-assessment
  in the artefact. Evidence for absolute-score leniency as a separate effect is mostly from
  less-established preprints. Treat it as a hypothesis to test on the calibration set.

### Evidence before score

Rationale-first helped the trained Prometheus judge [3], and G-Eval's auto-generated evaluation steps
beat no-CoT on every SummEval dimension [2]. The evidence is not uniform. Multi-step CoT did not
improve MLLM judges' agreement with humans [12], and GPT-4 over-reasoned without a "don't overthink"
instruction (κ ranged from 0.52 to 0.73 across prompt wordings) [5]. Our reading: ask for short,
grounded evidence and rationale, not open-ended deliberation.

### Number of judges and aggregation

PoLL used three small models from different families, with max-vote for binary items and averaging for
1–5 scores. It beat a single GPT-4 judge: κ 0.76 against 0.63 on NQ, and Pearson 0.92 against 0.82
against the Arena ranking. It also cost 7–8 times less [5]. The benefit comes from **disjoint model
families**. No source we found tests panels made of tiers from a single family. For integer scores,
take the median over repeats. It resists the occasional outlier better than the mean, which PoLL did
not test.

### Pairwise vs pointwise

Pairwise picks up subtle differences, but the number of pairs grows quadratically. Single-answer
grading scales and keeps a stable rubric, with similar agreement (85% against 85%, excluding ties)
[1]. Pairwise suits subjective criteria better [21] *(secondary)* and is where MLLM judges align best
with humans [12]. It is also far more manipulable [11]. For us: pointwise scoring for deck quality
across profiles, and pairwise (swapped) only when comparing two skill versions on the same brief.

### Measuring judge reliability

- Strong judges reach about 80–85% agreement with humans, close to human–human agreement, but only
  when ties are excluded. Counting ties drops this to 60–66% [1].
- Use chance-corrected or classifier metrics. Raw agreement misleads when failures are rare: report
  TPR/TNR on a held-out test set [20]. κ separates judges that raw agreement does not [21]
  *(secondary)*.
- Husain's protocol: one principal expert, critiques, a 10–20/40–45/40–45 split, about 30–50 examples
  per label, and iteration until agreement converges (over 90% in three rounds at Honeycomb) [20].
  Anthropic: calibrate closely to human experts, then fall back to spot checks, and read transcripts
  to catch a bad grader [22].

### Multimodal judging of screenshots and visual design

- GPT-4V judges reached Pearson 0.49 on scoring and about 0.77 accuracy on pair comparison (no ties),
  with length bias and more hallucination in batch ranking [12].
- PPTEval scores slide *images* per slide for Content and Design and the whole deck for Coherence, on
  1–5 with rationales. Its LLM–human Pearson was 0.70 for content, 0.90 for design and 0.55 for
  coherence, against human Fleiss κ of 0.59 [13]. Coherence, which corresponds to our narrative arc,
  is the weakest.
- UI-design judging is moderate at best. MLLMs track crowd perception on some dimensions and not
  others [16]. Professional designers agree at only α ≈ 0.25, and personalised models beat aggregated
  ones with about 20 times less data [14]. Expert UI critiques show only fair agreement [15]
  *(secondary)*. Deterministic checks (overlap, contrast, overflow) should carry what they can.

### Judging agent process and trajectories

- Agent-as-a-Judge (DevAI: 55 tasks, 365 hierarchical requirements) aligned with human consensus at
  about 87–92%, against 60–84% for LLM-as-a-Judge. Individual humans scored 76–93%. The biggest gains
  came from the judge building a graph of the workspace and locating evidence. Trajectory access gave
  mixed gains [17].
- On web-agent trajectories, no judge exceeded about 70% precision. The failure modes were trusting the
  agent's own reasoning and claims, missing incomplete steps, and grounding mismatches. Screenshots
  alone beat screenshots plus accessibility tree, so extra input can distract [18].
- Grade outcomes and requirement coverage, not one fixed path, and allow partial credit [22].

## 3. Open questions / where evidence is thin

- **Single-family panels.** No source tests whether Opus/Sonnet/Haiku panels reduce self-preference
  the way PoLL's cross-family panels do. Self-preference of Claude judging Claude-built decks needs
  direct measurement on our calibration set.
- **Repeat-sampling without temperature control.** How much run-to-run variance subagents actually
  have is unknown. Measure it before choosing k.
- **Deck-level narrative and coherence judging** has the weakest agreement in the only deck-specific
  study [13], and that study used a single judge model with four human raters.
- **Taste vs quality.** Design-preference data shows that much "quality" is individual taste [14].
  For an editorial-talk profile, whose taste do the anchors encode?
- **Process judging from git and docs** (as opposed to code workspaces or web trajectories) has no
  dedicated benchmark. [17] and [18] are the nearest analogues.
- **Rationale-first ordering** is supported by trained-judge ablations [3]. For prompted frontier
  judges the evidence is mixed [5][12].
- Survey coverage: [23] catalogues reliability strategies and meta-evaluation. It is not a source for
  specific numbers.

## 4. Sources

1. *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena*. Zheng, Chiang et al., 2023 (NeurIPS D&B). https://arxiv.org/abs/2306.05685
2. *G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment*. Liu, Iter, Xu, Wang, Xu, Zhu, 2023. https://arxiv.org/abs/2303.16634
3. *Prometheus: Inducing Fine-grained Evaluation Capability in Language Models*. Kim, Shin, Cho et al., 2023 (ICLR 2024). https://arxiv.org/abs/2310.08491
4. *Prometheus 2: An Open Source Language Model Specialized in Evaluating Other Language Models*. Kim, Suk, Longpre et al., 2024 (EMNLP). https://arxiv.org/abs/2405.01535
5. *Replacing Judges with Juries: Evaluating LLM Generations with a Panel of Diverse Models*. Verga, Hofstätter, Althammer et al. (Cohere), 2024. https://arxiv.org/abs/2404.18796
6. *LLM Evaluators Recognize and Favor Their Own Generations*. Panickssery, Bowman, Feng, 2024. https://arxiv.org/abs/2404.13076
7. *Justice or Prejudice? Quantifying Biases in LLM-as-a-Judge* (CALM). Ye, Wang, Huang et al., 2024. https://arxiv.org/abs/2410.02736
8. *Evaluating Scoring Bias in LLM-as-a-Judge*. Li, Dou, Shao, Chen, Hu, 2025 (DASFAA 2026). https://arxiv.org/abs/2506.22316
9. *Grading Scale Impact on LLM-as-a-Judge: Human-LLM Alignment Is Highest on 0-5 Grading Scale*. Li, Zhao, Dong et al., 2026. https://arxiv.org/abs/2601.03444
10. *CheckEval: A reliable LLM-as-a-Judge framework for evaluating text generation using checklists*. Lee, Kim, Kim et al., 2024 (EMNLP 2025). https://arxiv.org/abs/2403.18771
11. *Pairwise or Pointwise? Evaluating Feedback Protocols for Bias in LLM-Based Evaluation*. Tripathi, Wadhwa, Durrett, Niekum, 2025 (COLM). https://arxiv.org/abs/2504.14716
12. *MLLM-as-a-Judge: Assessing Multimodal LLM-as-a-Judge with Vision-Language Benchmark*. Chen et al., 2024 (ICML). https://arxiv.org/abs/2402.04788
13. *PPTAgent: Generating and Evaluating Presentations Beyond Text-to-Slides* (PPTEval). Zheng, Guan, Kong et al., 2025. https://arxiv.org/abs/2501.03936
14. *DesignPref: Capturing Personal Preferences in Visual Design Generation*. Peng, Bigham, Wu, 2025. https://arxiv.org/abs/2511.20513
15. *UICrit: Enhancing Automated Design Evaluation with a UI Critique Dataset*. 2024 (UIST). https://arxiv.org/abs/2407.08850
16. *MLLM as a UI Judge: Benchmarking Multimodal LLMs for Predicting Human Perception of User Interfaces*. Luera, Rossi, Dernoncourt et al., 2025. https://arxiv.org/abs/2510.08783
17. *Agent-as-a-Judge: Evaluate Agents with Agents*. Zhuge, Zhao, Ashley et al. (Meta, KAUST), 2024. https://arxiv.org/abs/2410.10934
18. *AgentRewardBench: Evaluating Automatic Evaluations of Web Agent Trajectories*. Lù, Kazemnejad, Meade et al., 2025. https://arxiv.org/abs/2504.08942
19. *Who Validates the Validators? Aligning LLM-Assisted Evaluation of LLM Outputs with Human Preferences*. Shankar, Zamfirescu-Pereira, Hartmann, Parameswaran, Arawjo, 2024. https://arxiv.org/abs/2404.12272
20. *Using LLM-as-a-Judge For Evaluation: A Complete Guide*. Hamel Husain, 2024 (updated 2026-09-01). https://hamel.dev/blog/posts/llm-judge/
21. *Evaluating the Effectiveness of LLM-Evaluators (aka LLM-as-Judge)*. Eugene Yan, 2024. https://eugeneyan.com/writing/llm-evaluators/
22. *Demystifying evals for AI agents*. Grace, Hadfield, Olivares, De Jonghe (Anthropic), 2026. https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
23. *A Survey on LLM-as-a-Judge*. Gu, Jiang, Shi et al., 2024 (rev. 2025). https://arxiv.org/abs/2411.15594
