# Skill structure: best practice for `twm-presentation-builder`

Researched 22 Nov 2026 from Anthropic's official docs, the agentskills.io spec, the
`anthropics/skills` repo, and local copies of `skill-creator`, `pptx`, `docx`, `frontend-design`
and `plugin-dev`. Sources are numbered in §4.

## 1. TL;DR for our design

```
skills/twm-presentation-builder/
├── SKILL.md              # frontmatter + router: phases, one line per part saying when to read it; aim ≤250 lines, hard cap 500 [1][2][3]
├── LICENSE.txt           # referenced from the `license` field, as every anthropics/skills skill does [4]
├── process/PROCESS.md    # PRD → one-question interview → research → prototype → spec → TDD → screenshot gate; checklist to copy [2]
├── content/STORYBOARD.md # storyboard method + template (chapters, timings, core message)
├── research/RESEARCH.md  # sourcing method, research-note template, citation rules
├── voice/
│   ├── VOICE.md          # how a voice profile is applied (contract), not the profile itself
│   └── profiles/twm.md   # presenter's personal profile: rules + approved/rejected examples
├── design/
│   ├── LAYOUT.md         # layout/components contract (header, nav, title, diagram kit, pop-overs, tiles)
│   ├── palettes/<name>.md# one file per palette: colour roles + application; pick one [2][5]
│   └── styles/<name>.md  # one file per style/material: fonts, bokeh, frost, depth, motion; pick one
├── architecture/ENGINE.md# engine API + data-attribute authoring contract (Low-freedom: exact attributes) [2]
├── assets/               # files copied into output, never loaded into context [1][3]
│   ├── engine/           # deck.js, deck.css, tokens.css (palette/style slots)
│   ├── fonts/            # woff2 for embedding
│   └── templates/        # deck-skeleton.html, PRD/SPEC/storyboard templates
├── scripts/              # run, don't read: shoot.py, embed_fonts.py, layout_guard.py [2]
├── pptx/
│   ├── PPTX.md           # HTML → editable-PPTX part; self-contained so it can be promoted to its own skill
│   └── scripts/          # html_to_pptx.py + validators
├── eval/
│   ├── EVAL.md           # scope prompt (briefs, concerns, output/process), run protocol, aggregation
│   ├── rubrics/*.md      # runner-agnostic anchored rubrics, one per concern
│   ├── briefs/           # bundled test briefs (+ evals.json if we adopt skill-creator's format) [6][7]
│   └── agents/           # judge role prompts (judge-output.md, judge-process.md), skill-creator style [6]
└── examples/hf-incident/ # worked-example excerpts + screenshots from the real deck, cited by parts
```

Key rules (each with refs):

- **Frontmatter:** `name` = folder name, ≤64 chars, lowercase/digits/hyphens, no `claude`/`anthropic`
  [3][2]; `description` ≤1,024 chars (spec) and listed truncated at 1,536 in Claude Code [3][1];
  third person, "what + when", front-load the key use case, a little "pushy" [2][6]. Add
  `compatibility` (≤500 chars) for uv, Python, Playwright/Chromium [3]. Claude Code ignores
  `license`/`compatibility`/`metadata`; other runtimes read them [1].
- **One hop from `SKILL.md`:** every part is linked directly from `SKILL.md` with "read when…";
  no part-to-part chains, because Claude partially reads files it reaches through nested links [2][3].
  This is *stricter* than our repo's "two hops max" rule: inside the skill, use one.
- **Long parts get a contents list** (platform docs: >100 lines; skill-creator: >300) [2][6].
- **Most important instructions go at the top of `SKILL.md`:** after compaction Claude Code
  re-attaches only the first ~5,000 tokens of an invoked skill [1].
- **Scripts are run, not read:** say "Run `…`" vs "See `…`" explicitly; reference them as
  `${CLAUDE_SKILL_DIR}/scripts/…` so paths work at personal, project or plugin scope [1][2].
- **Rules that must hold every time** (e.g. the screenshot gate) belong in a hook, not prose:
  skill text isn't re-read on later turns [1].
- **Judges:** a standalone skill can't register `.claude/agents/` definitions; ship judge prompts as
  `eval/agents/*.md` and have the orchestrator spawn a general-purpose subagent that reads them
  (skill-creator's pattern) [6][8]. Promote them to real plugin agents only if we package as a plugin [9].
- **Self-contained:** no paths out of the skill folder; plugin installs copy only the plugin dir
  and reject `..` paths [10][9]. This matches PRD workstream 8.

## 2. Findings

**Loading model.** Three levels: metadata (~100 tokens) always in context; the `SKILL.md` body
when triggered (<5,000 tokens / <500 lines recommended); bundled files only when read or run [3][2].
Unread files cost nothing, so large references and worked examples can be bundled freely [2].
Scripts cost only their output [2].

**Frontmatter in Claude Code.** Beyond the spec's `name`, `description`, `license`, `compatibility`,
`metadata` and `allowed-tools` [3], Claude Code adds `when_to_use`, `argument-hint`, `arguments`,
`disable-model-invocation`, `user-invocable`, `disallowed-tools`, `model`, `effort`,
`context: fork` + `agent` + `background`, `hooks`, `paths` and `shell`; unknown keys are silently
ignored [1]. Caution: skill-creator's `quick_validate.py` rejects anything outside
`{name, description, license, allowed-tools, metadata, compatibility}` [6], so Claude Code-only keys
stop us using it to validate or package the skill. `allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/… *)`
pre-approves our own scripts [1].

**Description writing.** The description is the only trigger signal and competes with 100+ others
[2]. Write it in third person (it is injected into the system prompt), naming concrete triggers
[2]. Claude tends to *under*-trigger, so lean "pushy" [6]. Claude only consults skills for tasks it
can't do trivially, so trigger tests should use substantive prompts [6]. Near-miss negatives
matter most: for us, "make me a .pptx" (should go to Anthropic's `pptx` skill) and "build a React
dashboard" [6][4]. Note that Anthropic's `pptx` and `docx` descriptions now explicitly defer to "a
separate slides skill if this session offers one" when no file format is named [4], so a clear
"HTML slide deck / talk / presentation" description should win those prompts.

**Instructions vs scripts (degrees of freedom).** Use high freedom (prose heuristics) where many
approaches are valid, and low freedom (exact script, no flags) where operations are fragile [2].
For us: storyboard, voice and design choices are high freedom. The engine's data-attribute contract,
font embedding, the layout guard and screenshots are low freedom. Scripts should "solve, don't
punt" (handle errors themselves, no magic constants) and print verbose, fixable errors [2]. Use
plan-validate-execute loops for risky batch work [2], which fits PPTX conversion (emit a mapping,
validate, then write).

**Variants as interchangeable files.** The domain-organisation pattern (one reference file per
variant, Claude reads only the relevant one) [2][6] fits our interchangeable concerns.
`theme-factory` does exactly this for palettes and fonts: a `themes/` folder of ten `.md` files plus
a showcase PDF, and the user is shown the showcase and picks one before anything is applied [5].
Copy that for `design/palettes/` and `design/styles/`, ideally with a rendered swatch per variant
in `examples/`.

**How Anthropic lays out comparable skills** [4][11]:
- `pptx`: `SKILL.md` (273 lines) with a task→approach table and a script table, plus `scripts/`
  (`thumbnail.py`, `slide_text.py`, `add_slide.py`, `clean.py`, `apply_theme.js`, `office/`
  validators and XSDs). No `references/` folder: depth lives in scripts.
- `docx`: same shape, with `scripts/templates/`.
- `frontend-design`: a single 71-line `SKILL.md`, all high-freedom guidance.
- `web-artifacts-builder`: `SKILL.md` + `scripts/init-artifact.sh`, `bundle-artifact.sh`
  and a tarball of components. That is "scripts produce a single HTML file", the closest analogue
  to our engine.
- `skill-creator`: `SKILL.md` (485 lines) + `agents/` (grader, comparator, analyzer role
  prompts) + `references/schemas.md` + `scripts/` + `eval-viewer/` + `assets/`.
- The repo's `.claude-plugin/marketplace.json` groups separate skills into plugins (for example
  `document-skills` = xlsx, docx, pptx, pdf) using `"source": "./", "strict": false, "skills": [...]` [11].

**Sub-skill packaging (PPTX).** Claude Code discovers `<name>/SKILL.md` exactly one level under a
skills root. A plugin's `skills` path is "a directory of `<name>/SKILL.md` folders or one folder
holding `SKILL.md` directly" [9][1]. A `SKILL.md` nested inside our skill folder would therefore
*not* register as its own skill: it would just be a referenced part. The choice:
- *Part* (`pptx/PPTX.md`, linked from `SKILL.md`): it triggers only via the parent, shares the
  engine contract, and keeps one install. It suits a converter that only understands our engine's
  markup.
- *Sibling skill* (`skills/twm-deck-to-pptx/SKILL.md`): it triggers on its own ("turn this deck into
  PowerPoint"), but competes with Anthropic's `pptx` skill for triggering and duplicates contract
  knowledge. Anthropic's own precedent is separate skills bundled in one plugin [11].
- Recommendation: a part now, written self-contained (own scripts, no links back into other
  parts) so it can be promoted to a sibling skill when we package a plugin.

**Agent definitions.** Subagents load from managed settings, `--agents`, `.claude/agents/`,
`~/.claude/agents/` or a plugin's `agents/`, in that priority order. No skill-level location exists [8].
Agent frontmatter supports `model`, `tools`, `disallowedTools`, `skills` (which preloads full skill
content), `effort`, `maxTurns` and others. Plugin agents ignore `hooks`, `mcpServers` and
`permissionMode` [8], which is harmless for a read-only judge. Skill-creator sidesteps the gap: its
`agents/*.md` are plain role prompts ("read `agents/grader.md`") given to a spawned subagent [6]. For
a *pinned* judge without a plugin, the orchestrator can pass a `model` override when spawning, and
the judge prompt file fixes role, tools and rubric. A skill can also run itself in a subagent via
`context: fork` + `agent:` [1], but that runs the whole skill isolated, which isn't what an eval
judge needs.

**Evals: two official tools, incompatible formats.**
- *skill-creator* (in-conversation iteration) [6][7][12]: `evals/evals.json` in the skill folder
  (`id`, `prompt`, `expected_output`, `files`, `expectations`). Results go in a sibling
  `<skill>-workspace/iteration-N/eval-<name>/{with_skill,without_skill|old_skill}/outputs/`. With-skill
  and baseline runs are spawned in the same turn. Timing comes from task notifications. A grader
  subagent writes `grading.json` (`text`/`passed`/`evidence`). `aggregate_benchmark.py` computes
  mean±stddev and the delta. An analyst pass flags non-discriminating or flaky assertions, and the
  HTML viewer collects human feedback into `feedback.json`. It also offers blind A/B comparison and a
  trigger-description optimiser (60/40 train/test split, 3 runs per query, using `claude -p`). It
  explicitly says subjective qualities like visual design suit human review more than assertions [6][7].
- *`claude plugin eval`* (CLI, CI-gradable, v2.1.269+) [13]: plugin-only, though a skills-directory
  plugin counts. Each case is `evals/<case>/prompt.md` + `graders/*.md`, with grader types `regex`,
  `tool_used`, `tool_order`, `file_exists`, `llm` and `baseline`, and no custom-code graders. It runs
  with-plugin and no-plugin arms in isolated sandboxes. An `llm` judge is **shown PNG/JPEG/WebP
  outputs as images** but refuses PPTX/PDF, which must be rendered first. The Artifact tool is off
  during runs. "Neither tool reads the other's case files" [13].
- For us, rubric-scored multimodal judging of screenshots and process evidence from git/SPEC fits
  neither runner exactly. Keep our rubric format runner-agnostic (PRD), and borrow skill-creator's
  workspace layout, field names and analyst checks so its viewer can be reused. Keep the workspace
  out of the shipped folder, in `-docs/` or gitignored.

**Plugin packaging (if it moves).** `.claude-plugin/plugin.json` needs only `name`, which must not
start with `claude-`/`anthropic-` [9]. Defaults: `skills/<name>/SKILL.md`, `agents/*.md`,
`hooks/hooks.json`, plus `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PLUGIN_DATA}` (use the latter for
installed deps and caches, since the root changes per version) [9][10]. Components are namespaced
(`plugin:skill`, `plugin:agent`) [9]. Marketplace installs copy only the plugin dir [10]. A
skills-directory plugin (a folder with `.claude-plugin/plugin.json` under `.claude/skills/`) loads
in place, which offers a low-friction path to real judge agents and hooks without a marketplace [10].
`claude plugin validate` checks frontmatter and paths [1][9].

**Discovery in this repo.** `skills/` at the repo root is *not* a Claude Code skill location [1].
To dogfood, symlink it into `.claude/skills/`, load it with `--plugin-dir`, or package it as a
plugin.

**Authoring style tension.** skill-creator advises explaining *why* over all-caps MUST/NEVER,
calling those a "yellow flag" [6]. The platform guide accepts "MUST" when observation shows a rule
being skipped [2]. Our repo docs use binding MUST/NEVER with a *why*. For shipped skill text, prefer
reasons and keep MUST for gates (screenshot look, layout guard).

## 3. Open questions

1. Name: keep `twm-presentation-builder` (valid), or switch to the gerund style Anthropic suggests,
   e.g. `building-presentations` [2]? Folder and `name` must match [3].
2. PPTX: a part now (recommended), or a sibling skill from day one so it can trigger alone?
3. Eval format: adopt skill-creator's `evals/evals.json` for the test briefs (reuses its viewer and
   benchmark), our own `eval/briefs/` format, or both? Naming the folder `evals/` would collide with
   `claude plugin eval`'s default if we become a plugin [13].
4. Should the eval be a separate `disable-model-invocation: true` entry point, so a costly run only
   starts when asked [1]?
5. Enforce the screenshot gate with a skill-scoped `hooks` entry [1], or keep it as process prose?
6. Do we want Claude Code-only frontmatter (`allowed-tools` with `${CLAUDE_SKILL_DIR}`, `hooks`) at
   the cost of failing skill-creator's validator and portability to claude.ai/API [6][1]?
7. Python deps for scripts: uv inline script metadata (PEP 723) vs a bundled `pyproject.toml`.
   Untested here; the API runtime has no network for installs [2].

## 4. Sources

1. Anthropic, *Extend Claude with skills* (Claude Code docs), 2026. https://code.claude.com/docs/en/skills
2. Anthropic, *Skill authoring best practices*, 2026. https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
3. Agent Skills, *Specification*, 2026. https://agentskills.io/specification
4. anthropics/skills, `skills/pptx`, `skills/docx`, `skills/frontend-design`, `skills/web-artifacts-builder` (repo tree + SKILL.md), 2026. https://github.com/anthropics/skills ; local synced copies `~/.claude/skills/synced/*/pptx/`, `docx/`
5. anthropics/skills, `skills/theme-factory/SKILL.md`, 2026. https://github.com/anthropics/skills/tree/main/skills/theme-factory
6. Anthropic, `skill-creator` SKILL.md, `agents/grader.md`, `references/schemas.md`, `scripts/quick_validate.py`, 2026. Local: `~/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator/skills/skill-creator/`; https://github.com/anthropics/skills/tree/main/skills/skill-creator
7. Agent Skills, *Evaluating skill output quality*, 2026. https://agentskills.io/skill-creation/evaluating-skills
8. Anthropic, *Create custom subagents* (Claude Code docs), 2026. https://code.claude.com/docs/en/sub-agents
9. Anthropic, *Plugin manifest reference*, 2026. https://code.claude.com/docs/en/plugins-reference
10. Anthropic, *Plugin loading reference*, 2026. https://code.claude.com/docs/en/plugins/loading.md
11. anthropics/skills, `.claude-plugin/marketplace.json`, 2026. https://github.com/anthropics/skills/blob/main/.claude-plugin/marketplace.json
12. Anthropic, `plugin-dev` plugin (`skills/plugin-structure`, `agents/skill-reviewer.md`), 2026. Local: `~/.claude/plugins/marketplaces/claude-plugins-official/plugins/plugin-dev/`
13. Anthropic, *Test plugins with evals* (`claude plugin eval`), 2026. https://code.claude.com/docs/en/plugin-evals.md
