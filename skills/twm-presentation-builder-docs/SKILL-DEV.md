# twm-presentation-builder — development index

Development docs and tests for the skill in `../twm-presentation-builder/` (which holds only what
ships). Intent and decisions so far: root `docs/PRD.md` *Decisions* (workstream 8), until this
folder gets its own PRD.

| File | Description | When to use | When to update |
| --- | --- | --- | --- |
| `research/llm-judge.md` | LLM-as-judge methods: rubric anchoring, biases, judge count/aggregation, multimodal judging | Before designing rubrics, judge prompts or aggregation | When judge research is extended or overturned |
| `research/deck-rubrics.md` | Prior rubrics and benchmarks for slide/deck quality | Before choosing rubric dimensions or anchors | When new deck-eval prior art is found |
| `research/html-to-pptx.md` | Editable PPTX generation: python-pptx limits, converters, masters, themes, Morph | Before designing or changing the PPTX sub-skill | When converter research is extended |
| `research/skill-structure.md` | Skill authoring guidance: structure, progressive disclosure, scripts, skill evals | Before laying out `SKILL.md` and its parts | When skill guidance changes |
| `research/design-tokens.md` | Design-system layering: tokens, palette roles, type/effects vs components | Before defining the design layers and their contracts | When token/layering research is extended |
