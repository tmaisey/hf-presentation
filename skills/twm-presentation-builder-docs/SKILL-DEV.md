# twm-presentation-builder — development index

Development docs and tests for the skill in `../twm-presentation-builder/` (which holds only what
ships). Work here follows root `AGENTS.md` (Workflow, Spec model, Test authoring) with `PB-0NN`
spec ids; tests (once written) live in `tests/` here and run with
`uv run pytest skills/twm-presentation-builder-docs/tests`, never in the deck's `tests/`.

| File | Description | When to use | When to update |
| --- | --- | --- | --- |
| `PRD.md` | Skill requirements: what/why, scope, separation of concerns, eval design, decisions, exclusions | Before scoping, specifying or changing any part of the skill | First, on any skill intent change (before spec/code). Not for feature state |
| `SPEC.jsonl` | Skill feature backlog + live state (`PB-0NN`, root Spec model) | Start of a skill build session to find done/next; before writing skill tests | On spec add/refine and every status flip, in the same commit as the work |
| `evals-runs/` | Dated eval runs of the skill itself (`yymmdd-<label>/`: manifest, evidence, verdicts, report), per `evals/EVAL.md` | To read past skill eval results or compare skill versions | Never edit a run; each run adds a new folder |
| `tests/` | pytest suite for the skill: `Spec: PB-0NN` markers, `helper_` modules, no conftest by default; outputs in git-ignored `tests/artifacts/`; PPTX schema validation reads `PB_OOXML_SCHEMAS` (skips without it) | Before changing the skill; to prove red/green for a `PB-` spec | When the run command or helper contract changes |
| `research/llm-judge.md` | LLM-as-judge methods: rubric anchoring, biases, judge count/aggregation, multimodal judging | Before designing rubrics, judge prompts or aggregation | When judge research is extended or overturned |
| `research/deck-rubrics.md` | Prior rubrics and benchmarks for slide/deck quality | Before choosing rubric dimensions or anchors | When new deck-eval prior art is found |
| `research/html-to-pptx.md` | Editable PPTX generation: python-pptx limits, converters, masters, themes, Morph | Before designing or changing the PPTX sub-skill | When converter research is extended |
| `research/skill-structure.md` | Skill authoring guidance: structure, progressive disclosure, scripts, skill evals | Before laying out `SKILL.md` and its parts | When skill guidance changes |
| `research/design-tokens.md` | Design-system layering: tokens, palette roles, type/effects vs components | Before defining the design layers and their contracts | When token/layering research is extended |
