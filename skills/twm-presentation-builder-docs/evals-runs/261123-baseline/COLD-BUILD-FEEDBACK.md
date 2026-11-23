# Cold-build feedback on the skill (261123)

Two fresh agents built decks from briefs using only the skill (`pitch-solar-coop`,
`data-review-bus-reliability`), with the presenter unavailable. Both finished: every spec
red → green → done, layout guard clean at all three review sizes, screenshots looked at. These are
the skill defects they reported, merged and de-duplicated; fixes are tracked as PB-027.

| # | Area | Defect | Reported by |
| --- | --- | --- | --- |
| 1 | tools | `layout_guard.guard()` can't run inside a pytest session that already holds a sync Playwright browser; the project template says "wrap" it without saying how (both ran the CLI as a subprocess with `--json`) | both |
| 2 | tools | `shoot.py --slides` behaviour on other slides' existing shots is undocumented (one build saw them deleted, the other kept): make it keep them and say so | both |
| 3 | assemble | No way to replace the SLIDES block after `new`; unclear whether the deck or a separate slides file is the source of truth | both |
| 4 | template | Project `AGENTS.md` index has rows for files the template never creates (`design/prototypes/PROTOTYPES.md`, `evals/runs/`, `docs/ADR.jsonl`) and hard-codes `deck/<name>.html`; conflicts with "docs are born on content" and with house rules | both |
| 5 | process | Install list omits the content docs (VOICE, STORYBOARD, DESIGN, research) the template indexes | data-review |
| 6 | content/voice | No definition of "visible words" for word caps (per slide or per step; kickers, cites, diagram labels?); a 30-word cap fights the voice profile's fuller titles and 1–2 sentence Insights | pitch |
| 7 | content | Title approval with no presenter: STORYBOARD says never self-approve, BRIEFS says play the presenter and approve; Definition of done is silent | both |
| 8 | voice | Byline rule assumes a named presenter; no team/unnamed form | both |
| 9 | layout | Closing layout can't hold discussion prompts (title runs under the bar at 1288×598) | data-review |
| 10 | layout | Timeline body documented only for scenes; works standalone but not stated | data-review |
| 11 | layout/diagram | No chart parts: bars from tiles inherit an 18 px radius (swatches become circles), `#lift` leaves faint rectangles behind bars, labels only middle-anchored, no guidance for keeping a two-word label together | data-review |
| 12 | layout/diagram | `text.label` has no width/anchoring guidance; a label spilled past the diagram edge and the layout guard missed it | pitch |
| 13 | layout | No way to centre a one-line tile among two-line siblings | pitch |
| 14 | architecture | `data-for` documents only `#id`; selector support unclear | pitch |
| 15 | research | Sources without URLs (logs, internal docs): RS-05 requires a link, nothing says how to cite an unlinked source | data-review |
| 16 | pptx | No route to the visual check (PX-06) without LibreOffice | data-review |
| 17 | misc | `${CLAUDE_SKILL_DIR}` shows the `.claude/skills` symlink path, not the real folder (harmless) | pitch |
