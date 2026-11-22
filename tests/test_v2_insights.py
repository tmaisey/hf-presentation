"""Spec: S-027

v2 closing slides. s-9 Insights reuses s-8's tile row over the frozen, blurred incident world: three
text tiles built one per step (how misalignment happened from training to evaluation; why it is hard
to design out and unsolved; opaque firings discourage transparency, both sides stated). s-10
Takeaways, in phases with a title each: three pace tiles in the same tile row (capability still
accelerating; industry calls for pacing and disclosure; public concern rising, safety secondary),
controls with practical considerations for AI projects, then three discussion prompts.
Coverage: happy (slides close the deck in order with approved titles/kickers; s-9 and s-10 build one
tile per step with sourced facts, verbatim quotes and links; s-10 swaps tiles → controls → prompts) ·
edge (s-9 world frozen in s-8's place and state; tiles read left to right in one row at every review
size; s-10's Coxon quote sits in tile 1 and leaves with the tiles; s-10 tiles keep every approved
figure as bullets, moved detail lives in the tile's notes; notes target elements on their slide;
each control's incident failure lives in its note) · negative (s-9 has no loop diagram,
narration or separate Insight; s-10 has no Insight step or comparison table; no slide-scoped tile
CSS; no causal claim on the firings or on the sentiment shift; quotes verbatim from research;
Hubinger not repeated on s-10; no weakly sourced Anthropic pause; no "suicide", "same agents" or
firm-specific advice).
"""

import re

import pytest

from helper_deck import ROOT, deck_source, goto_slide, open_deck, parse_slides, settle, slides_source

pytestmark = pytest.mark.deck("v2")

S9_TITLE = ("Misalignment grew from ordinary training choices, and the obvious fixes risk making it "
            "harder to see")
S10_TITLES = {  # visible title per step: tiles (✓ 22 Nov) → controls (✓ 22 Nov) → discussion (v1 6.1 ◇)
    "tiles": "Capability keeps accelerating as industry calls for restraint and public concern grows",
    "controls": "Practical controls keep AI agents within the bounds their tasks need",
    "discussion": "Detection, training and independent oversight remain open questions after this incident",
}
SIZES = [(1920, 1080), (1280, 720), (1288, 598)]
TILES = ["s9-t1", "s9-t2", "s9-t3"]   # row order = build step 1, 2, 3
FACTS = {   # per tile: what its visible text must state
    "s9-t1": ["impossible", "training", "rewarded", "shared credential", "alert", "reasoning monitor",
              "evaluation", "unprompted by humans", "1,200", "4 hours"],
    "s9-t2": ["reward", "penalising", "reasoning", "hid", "crude", "plan to solve alignment"],
    "s9-t3": ["OpenAI says", "were not about raising safety concerns", "dispute", "METR", "whatever the reason",
              "public explanation", "transparency"],
}
QUOTES = {  # verbatim, and each must appear in the research notes
    "s9-t1": "Persistence is valuable, but can amplify misalignment",
    "s9-t2": "we do not yet have a plan to solve alignment for superintelligence",
    "s9-t3": "are chilling the open culture OpenAI has prized",
}
LINKS = {
    "s9-t1": ["cdn.openai.com", "blog.redwoodresearch.org"],
    "s9-t2": ["time.com", "arxiv.org/abs/2503.11926"],   # Sleeper Agents, alignment faking: #s9-research note
    "s9-t3": ["fortune.com", "sfstandard.com"],
}
COXON = "One, it’s obvious that things are speeding up, and two, they’re not under control."
S10_TILES = ["s10-t1", "s10-t2", "s10-t3"]   # row order = build step 1, 2, 3
S10_COPY = {   # STORYBOARD s-10 (22 Nov): heading (verbatim), approved sentences as bullets, quote
    "s10-t1": ("Capability, compute and spending are still accelerating",
               ["The length of task AI agents can complete has grown about 10× every two years, faster since 2024",
                "Training compute grows about 5× a year, and 2026 data-centre spending is around $700B",
                "METR could not reliably measure GPT-5.6 Sol: 11 to over 270 hours"],
               COXON),
    "s10-t2": ("Incidents prompted industry calls for pacing and disclosure",
               ["OpenAI paused its largest runs twice",
                "Anthropic’s CEO called for pacing the frontier, endorsed by OpenAI’s CEO",
                "Over 1,300 lab staff signed a pacing letter",
                "Hugging Face called for ‘radical transparency’"],
               "Our misalignment disclosure practices need to expand for this new phase of model capabilities."),
    "s10-t3": ("AI concern is rising, though safety remains secondary",
               ["Most Americans are concerned about AI, and 73% worry future AI could threaten human survival",
                "But politics and markets focus elsewhere: polls and midterms weighed jobs, power bills and data centres",
                "AI-led market drops were about spending and growth, not safety"],
               None),
}
S10_MOVED = {   # approved detail that did not fit 1288×598 as a bullet: it lives in the tile's notes instead
    "s10-t2": ["reinforcement learning runs", "senators", "Attorney General"],
}
S10_LINKS = {   # hosts each tile's cite line links (research notes: capability_pace.md, public_sentiment.md)
    "s10-t1": ["metr.org", "time.com"],   # Epoch AI: #s10-compute note
    "s10-t2": ["thestar.com.my", "darioamodei.com", "pacingthefrontier.com"],   # PBS/AP: #s10-calls note
    "s10-t3": ["techpolicy.press", "nbcnews.com", "boston.com"],   # NBC's own exit-poll page (56%)
}
CONTROLS = [   # control · practical consideration (approved, verbatim)
    ("Least agency and autonomy", "While it’s tempting to use the most powerful tools for every use case, "
     "give agent systems only the capabilities they need for the task."),
    ("Per-agent authentication and authorisation", "Give each agent its own credentials, scoped to its task, "
     "so you can trace and revoke access one agent at a time."),
    ("Sandbox isolation", "Keep agents’ environments apart, including shared storage, so one environment "
     "can’t become a channel to others."),
    ("Deterministic controls and monitoring", "In higher-risk use cases, build in kill-switches and rule-based "
     "escalation to a human, so a warning always reaches someone who can stop the agent."),
    ("Network access only when justified", "Block internet and outside access by default, and open only the "
     "routes a task needs."),
]
CONTROL_FAILURES = [   # per control row, in order: what its note must say failed in the incident
    "reasoning budgets", "shared credential", "writable mirror", "27 June", "internet"]
TILE_TEXT = """id => { const t = document.getElementById(id);
  return { text: t.innerText, quotes: [...t.querySelectorAll('blockquote')].map(q => q.textContent.trim()),
           links: [...t.querySelectorAll('a[href]')].map(a => a.href), head: (t.querySelector('h3') || {}).textContent }; }"""


def helper_norm(s: str) -> str:
    """Fold typographic apostrophes/quotes and whitespace so deck, docs and research text compare."""
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("\u2011", "-")   # a non-breaking hyphen is still a hyphen
    s = s.replace("&nbsp;", " ").replace("\u00a0", " ")   # so is a non-breaking space
    return re.sub(r"\s+", " ", s).strip()


def helper_section(sid: str) -> str:
    m = re.search(rf'<section class="[^"]*" id="{sid}".*?</section>', slides_source(), re.S)
    assert m, f"slide {sid} missing"
    return m.group(0)


def helper_storyboard(prefix: str) -> str:
    text = (ROOT / "docs" / "STORYBOARD.md").read_text(encoding="utf-8")
    return helper_norm(text.split(f"## {prefix}")[1].split("\n## ")[0])


def helper_research() -> str:
    return helper_norm(" ".join(p.read_text(encoding="utf-8") for p in (ROOT / "docs" / "research").rglob("*.md")))


def helper_flat(html: str) -> str:
    return helper_norm(re.sub(r"<[^>]+>", " ", html))


# ---------- static: shell, order, copy ----------

def test_insights_and_takeaways_close_the_deck_in_order():
    slides = parse_slides()
    assert [s["attrs"]["id"] for s in slides[-2:]] == ["s-9", "s-10"]
    s9, s10 = slides[-2], slides[-1]
    assert s9["attrs"]["data-chapter"] == "Insights" and s10["attrs"]["data-chapter"] == "Takeaways"
    assert '<p class="kicker">09 · Insights</p>' in helper_section("s-9")
    assert '<p class="kicker">10 · Takeaways</p>' in helper_section("s-10")


def test_titles_are_the_approved_storyboard_titles():
    s9 = parse_slides()[-2]
    assert s9["title"] == S9_TITLE
    assert helper_norm(S9_TITLE) in helper_storyboard("s-9 · Insights")
    assert helper_norm(S9_TITLE) in helper_norm((ROOT / "docs" / "VOICE.md").read_text(encoding="utf-8"))
    titles = re.findall(r'<h2 class="title"[^>]*>(.*?)</h2>', helper_section("s-10"), re.S)
    assert titles == list(S10_TITLES.values())
    for phase in ("tiles", "controls"):
        assert helper_norm(S10_TITLES[phase]) in helper_storyboard("s-10 · Pace"), phase


S9_HEADINGS = ["Reinforced training behaviours re-emerged in evaluation",   # presenter, 22 Nov (round 2)
               "Penalising misaligned reasoning in training rewards concealing it",
               "Opaque staff firings discourage transparency"]


def test_s9_tile_headings_are_the_approved_findings():
    """VOICE: one specific finding per heading; the presenter rejected two-clause, metaphor-led drafts."""
    sec = helper_section("s-9")
    got = [helper_norm(re.sub(r"<[^>]+>", "", re.search(r"<h3>(.*?)</h3>", sec[sec.index(f'id="{t}"'):], re.S).group(1)))
           for t in TILES]
    assert got == S9_HEADINGS
    voice = helper_norm((ROOT / "docs" / "VOICE.md").read_text(encoding="utf-8"))
    assert all(helper_norm(h) in voice for h in S9_HEADINGS), "approved headings are recorded in VOICE"


def test_s9_is_a_backdrop_world_slide_with_one_tile_row_of_three_tiles():
    s9 = parse_slides()[-2]
    assert s9["attrs"].get("data-world") == "backdrop", "s-9 keeps the incident world as a backdrop, like s-8"
    sec = helper_section("s-9")
    assert '<div class="world-slot"></div>' in sec
    assert re.findall(r'<div class="body[^"]*"', sec) == ['<div class="body body--tiles"']
    tiles = re.findall(r'<article class="text-tile" id="([\w-]+)" data-show-at="(\d+)">', sec)
    assert tiles == [(t, str(n)) for n, t in enumerate(TILES, start=1)], tiles


def test_s9_drops_the_loop_diagram_narration_and_separate_insight():
    """The tiles are the insights (storyboard): no SVG loop, no narration column, no Insight overlay."""
    sec = helper_section("s-9")
    assert "<svg" not in sec
    assert 'class="narration"' not in sec and "narr-tile" not in sec
    assert "overlay--insight" not in sec


def test_s9_reuses_the_tile_row_component_without_slide_scoped_css():
    css = re.search(r"<style>(.*?)</style>", deck_source(), re.S).group(1)
    assert not re.search(r"#s-9\b|#s9-|\.s9-", css), "the shared tile row must not be styled per slide"


def test_s9_quotes_are_verbatim_from_research_and_carry_no_typed_quote_marks():
    sec, research = helper_section("s-9"), helper_research()
    for q in re.findall(r"<blockquote[^>]*>(.*?)</blockquote>", sec, re.S):
        assert not re.search(r'^["“”]|["“”]$', q.strip()), f"CSS adds quote marks: {q}"
        assert helper_norm(q) in research, f"quote not found verbatim in docs/research: {q[:50]}"
    assert "{" not in sec and "}" not in sec and not re.search(r"\sstyle\s*=", sec)


def helper_s10_tile(tid: str) -> str:
    sec = helper_section("s-10")
    m = re.search(rf'<article class="text-tile" id="{tid}".*?</article>', sec, re.S)
    assert m, f"{tid} missing"
    return m.group(0)


def test_s10_tiles_phase_reuses_the_tile_row_one_tile_per_step():
    sec = helper_section("s-10")
    row = re.search(r'<div class="body body--tiles"[^>]*>(.*?)</div>\s*<div', sec, re.S)
    assert row, "s-10's tiles phase is the shared tile row (div.body.body--tiles)"
    tiles = re.findall(r'<article class="text-tile" id="([\w-]+)" data-show-at="(\d+)">', row.group(1))
    assert tiles == [(t, str(n)) for n, t in enumerate(S10_TILES, start=1)], tiles


def test_s10_tiles_carry_the_approved_copy_as_bullets():
    """Presenter, 22 Nov: the approved sentences become bullets; heading and quote stay verbatim."""
    story = helper_storyboard("s-10 · Pace")
    for tid, (head, bullets, quote) in S10_COPY.items():
        tile = helper_s10_tile(tid)
        assert helper_flat(re.search(r"<h3>(.*?)</h3>", tile, re.S).group(1)) == helper_norm(head), tid
        assert helper_norm(head) in story, f"{tid}: heading is the storyboard's"
        got = [helper_flat(li) for li in re.findall(r"<li[^>]*>(.*?)</li>", tile, re.S)]
        assert got == [helper_norm(b) for b in bullets], tid
        quotes = [helper_flat(q) for q in re.findall(r"<blockquote[^>]*>(.*?)</blockquote>", tile, re.S)]
        assert quotes == ([helper_norm(quote)] if quote else []), tid
        if quote:
            assert helper_norm(quote) in story, f"{tid}: quote is the storyboard's"


S10_FIGURES = {   # every approved figure and claim of the storyboard sentences, per tile
    "s10-t1": ["10×", "every two years", "faster since 2024", "5× a year", "$700B", "GPT-5.6 Sol", "11", "270"],
    "s10-t2": ["paused", "twice", "disclosure practices", "pacing the frontier", "OpenAI’s CEO", "1,300",
               "radical transparency"],   # disclosure: OpenAI's own words, in the quote
    "s10-t3": ["Most Americans", "73%", "human survival", "jobs, power bills and data centres", "spending and growth",
               "not safety"],
}


def test_s10_bullets_keep_every_approved_figure_and_notes_hold_what_moved():
    """Convert, don't cut (VOICE tile bullets): a fact is on the tile, or in that tile's notes."""
    sec = helper_section("s-10")
    notes = dict(re.findall(r'<aside class="note" data-for="#([\w-]+)">(.*?)</aside>', sec, re.S))
    for tid, figures in S10_FIGURES.items():
        tile = helper_s10_tile(tid)
        flat = helper_flat(tile)
        for fig in figures:
            assert helper_norm(fig) in flat, f"{tid} must keep {fig!r}"
        ids = set(re.findall(r'id="([\w-]+)"', tile))
        tile_notes = helper_flat(" ".join(body for target, body in notes.items() if target in ids))
        for moved in S10_MOVED.get(tid, []):
            assert helper_norm(moved) in tile_notes, f"{tid}: {moved!r} moved off the tile but is not in its notes"


def test_s10_tile_quotes_are_verbatim_from_research_and_carry_no_typed_quote_marks():
    sec, research = helper_section("s-10"), helper_research()
    for q in re.findall(r"<blockquote[^>]*>(.*?)</blockquote>", sec, re.S):
        assert not re.search(r'^["“”]|["“”]$', q.strip()), f"CSS adds quote marks: {q}"
        assert helper_norm(q) in research, f"quote not found verbatim in docs/research: {q[:50]}"
    assert "{" not in sec and "}" not in sec and not re.search(r"\sstyle\s*=", sec)


def test_s10_tiles_cite_their_sources_with_links():
    for tid, hosts in S10_LINKS.items():
        cite = re.search(r'<p class="cite"[^>]*>(.*?)</p>', helper_s10_tile(tid), re.S)
        assert cite, f"{tid} has a cite line"
        hrefs = re.findall(r'<a href="([^"]+)"', cite.group(1))
        assert all(h.startswith("https://") for h in hrefs)
        for host in hosts:
            assert any(host in h for h in hrefs), f"{tid} must link {host}"
    assert "Coxon" in helper_flat(re.search(r'<p class="cite".*?</p>', helper_s10_tile("s10-t1"), re.S).group(0))


def test_s10_reuses_the_tile_row_without_slide_scoped_css():
    css = re.search(r"<style>(.*?)</style>", deck_source(), re.S).group(1)
    assert not re.search(r"#s-10\b|#s10-|\.s10-", css), "the shared tile row must not be styled per slide"


def test_s10_has_no_comparison_table_or_separate_insight_step():
    """The tiles replace the comparison table, and the Insight (METR on GPT-5.6 Sol) folds into tile 1."""
    sec = helper_section("s-10")
    assert 'class="compare"' not in sec
    assert "overlay--insight" not in sec
    assert 'class="narration"' not in sec


def test_s10_omits_the_weakly_sourced_anthropic_pause():
    """Only a weak source reports an Anthropic pause (capability_pace.md): omitted unless confirmed."""
    flat = helper_flat(helper_section("s-10")).lower()
    assert not re.search(r"anthropic (also |reportedly )?(paused|halted)", flat)


def test_s10_never_claims_the_incident_caused_the_sentiment_shift():
    """Most of the measured shift predates the incident (public_sentiment.md): the notes say so."""
    flat = helper_flat(helper_section("s-10")).lower()
    for claim in (r"(incident|breach|hack|attack)\w* (caused|drove|triggered|sparked|led to) (the |a )?"
                  r"(shift|rise|concern|sentiment|drop|sell-?off)", r"because of the (incident|breach|hack)",
                  r"after the (incident|breach|hack),? (concern|sentiment|support) (rose|jumped|grew)"):
        assert not re.search(claim, flat), claim
    notes = helper_flat(" ".join(re.findall(r'<aside class="note".*?</aside>', helper_section("s-10"), re.S)))
    assert "before the incident" in notes.lower(), "the sentiment note says the shift mostly predates it"
    assert "alleg" in notes.lower(), "the AG suit is reported as allegations"
    assert "did not ask about the incident" in notes.lower()


def test_s10_hubinger_moved_to_s9():
    assert "plan to solve alignment" not in helper_section("s-10"), "Hubinger's quote moved to s-9 tile 2"


def test_s10_controls_give_practical_considerations_verbatim():
    sec = helper_section("s-10")
    table = re.search(r"<table.*?</table>", sec, re.S).group(0)
    assert [helper_flat(h) for h in re.findall(r"<th[^>]*>(.*?)</th>", table, re.S)] == \
        ["Control", "Practical considerations for AI projects"]
    rows = re.findall(r"<tr[^>]*>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>", table, re.S)
    assert [(helper_flat(c), helper_flat(p)) for c, p in rows] == [(helper_norm(c), helper_norm(p)) for c, p in CONTROLS]
    story = helper_storyboard("s-10 · Pace")
    assert all(helper_norm(p) in story for _, p in CONTROLS)
    assert "where it failed" not in helper_flat(table).lower()


def test_s10_each_control_notes_where_it_failed_in_the_incident():
    sec = helper_section("s-10")
    table = re.search(r"<table.*?</table>", sec, re.S).group(0)
    ids = re.findall(r'<tr[^>]*>\s*<td id="(s10-[\w-]+)"', table)
    assert len(ids) == len(CONTROLS), "each control row is a note target"
    notes = dict(re.findall(r'<aside class="note" data-for="#([\w-]+)">(.*?)</aside>', sec, re.S))
    for rid, evidence in zip(ids, CONTROL_FAILURES):
        assert rid in notes, f"control #{rid} has no note"
        assert evidence in helper_flat(notes[rid]), f"#{rid} note must say {evidence!r}"


def test_s10_has_three_discussion_prompts_one_per_step():
    sec = helper_section("s-10")
    prompts = re.findall(r'<li class="prompt" id="(s10-\w+)" data-show-at="(\d)">(.*?)</li>', sec, re.S)
    assert [(i, at) for i, at, _ in prompts] == [("s10-detect", "5"), ("s10-train", "6"),
                                                ("s10-investigate", "7")]
    assert all(p.rstrip().endswith("?") for *_, p in prompts)


def test_notes_target_elements_on_their_slide_and_cite_https_sources():
    for sid, minimum in (("s-9", 6), ("s-10", 15)):
        sec = helper_section(sid)
        notes = re.findall(r'<aside class="note" data-for="#([\w-]+)">(.*?)</aside>', sec, re.S)
        assert len(notes) >= minimum, sid
        for target, body in notes:
            assert f'id="{target}"' in sec, f"{sid}: note targets #{target}, not on this slide"
            assert "<h3>" in body and re.search(r'<a class="src" href="https://', body), target
    s9_targets = {t for t, _ in re.findall(r'<aside class="note" data-for="#([\w-]+)">(.*?)</aside>',
                                           helper_section("s-9"), re.S)}
    assert s9_targets >= set(TILES), "every s-9 tile has a note"
    s10 = helper_section("s-10")
    s10_targets = re.findall(r'<aside class="note" data-for="#([\w-]+)">', s10)
    research = dict(re.findall(r'<aside class="note" data-for="#([\w-]+)">(.*?)</aside>', helper_section("s-9"), re.S))
    for paper in ("arxiv.org/abs/2401.05566", "arxiv.org/abs/2412.14093"):
        assert paper in research["s9-research"], f"tile 2's research note links {paper}"
    assert "epoch.ai" in s10 and "pbs.org" in s10, "links dropped from s-10 cites live in its notes"
    for tid in S10_TILES:
        tile = helper_s10_tile(tid)
        assert any(f'id="{t}"' in tile for t in s10_targets), f"{tid} has a note on it or inside it"


def test_s9_notes_carry_the_caveats_and_our_inferences_labelled():
    notes = " ".join(re.findall(r'<aside class="note".*?</aside>', helper_section("s-9"), re.S))
    for must in ("within one second", "the gap between the experimental tampering we saw and tampering that "
                 "successfully erased evidence of itself is large", "our inference", "misjudged",
                 "alignment reward models", "mishandled sensitive information"):
        assert helper_norm(must) in helper_flat(notes), must


def test_forbidden_and_inaccurate_wording_is_absent():
    text = (helper_section("s-9") + helper_section("s-10")).lower()
    assert "suicide" not in text
    assert "same agents" not in text, "19 Jul OpenAI-cluster takeover was a different Astra-family model"
    for firm in ("deloitte", "our firm", "our clients"):
        assert firm not in text


# ---------- browser: what is on screen at each step ----------

def test_step_counts_and_clean_load(page):
    errors = open_deck(page)
    plan = dict(page.evaluate("window.deck.plan()"))
    assert plan["s-9"] == 3 and plan["s-10"] == 7
    goto_slide(page, "s-9", 3)
    goto_slide(page, "s-10", 7)
    assert errors == []


def test_s9_each_step_adds_one_tile_and_keeps_the_earlier_ones(page):
    open_deck(page)
    for step in range(4):
        goto_slide(page, "s-9", step)
        shown = page.evaluate("ids => ids.map(id => +getComputedStyle(document.getElementById(id)).opacity > .9)", TILES)
        assert shown == [n <= step for n in range(1, 4)], f"step {step}: {shown}"


def test_s9_tiles_state_their_sourced_facts_with_verbatim_quotes_and_links(page):
    open_deck(page)
    goto_slide(page, "s-9", 3)
    for tid in TILES:
        t = page.evaluate(TILE_TEXT, tid)
        assert t["head"] and len(t["head"]) < 80, f"{tid}: a short heading"
        text = helper_norm(t["text"]).lower()
        for fact in FACTS[tid]:
            assert helper_norm(fact).lower() in text, f"{tid} must state {fact!r}"
        assert any(QUOTES[tid] in helper_norm(q) for q in t["quotes"]), f"{tid} must quote {QUOTES[tid]!r}"
        for host in LINKS[tid]:
            assert any(host in h for h in t["links"]), f"{tid} must link {host}"
        assert all(h.startswith("https://") for h in t["links"])


def test_s9_firings_tile_states_both_sides_and_claims_the_effect_not_the_motive(page):
    open_deck(page)
    goto_slide(page, "s-9", 3)
    text = helper_norm(page.evaluate(TILE_TEXT, "s9-t3")["text"]).lower()
    assert "openai says" in text and "staff dispute" in text, "both sides are given"
    for claim in (r"fired (for|because|over|after) (their|the) (work|investigation|role)", r"retaliat",
                  r"because (of )?(they|their) (worked|work|talked)", r"punish", r"in order to"):
        assert not re.search(claim, text), f"causal claim on the firings: {claim}"


def test_s9_world_holds_s8s_frozen_state_and_place(page):
    open_deck(page)
    snap = """() => { const w = document.querySelector('.world'), r = w.getBoundingClientRect(), s = getComputedStyle(w);
      return { parts: [...w.querySelectorAll('[data-world-at], [data-world-is]')].map(e => e.getAttribute('class')),
               cam: w.querySelector('.cam').style.transform, box: [r.left, r.top, r.width, r.height].map(Math.round),
               backdrop: w.classList.contains('is-backdrop'), vis: s.visibility }; }"""
    goto_slide(page, "s-8", 3)
    page.wait_for_timeout(900)
    end = page.evaluate(snap)
    assert end["backdrop"] and end["vis"] == "visible"
    for step in range(4):
        goto_slide(page, "s-9", step)
        assert page.evaluate(snap) == end, f"step {step}: s-9 must hold s-8's frozen, blurred world"


@pytest.mark.parametrize("size", SIZES)
def test_s9_tiles_read_left_to_right_in_one_row_at_a_readable_size(page, size):
    """The layout guard covers clipping and overlap with the title; this checks the row reads as one."""
    open_deck(page, *size)
    goto_slide(page, "s-9", 3)
    settle(page, "#s9-t3")
    res = page.evaluate("""ids => { const nb = document.querySelector('.notes-btn').getBoundingClientRect();
      return { vw: innerWidth, notes: [nb.left, nb.top, nb.right, nb.bottom], tiles: ids.map(id => { const t = document.getElementById(id),
        b = t.getBoundingClientRect(); return { box: [b.left, b.top, b.right, b.bottom],
        body: parseFloat(getComputedStyle(t.querySelector('li')).fontSize) }; }) }; }""", TILES)
    tiles = res["tiles"]
    for a, b in zip(tiles, tiles[1:]):
        assert a["box"][2] <= b["box"][0] + 1 and abs(a["box"][1] - b["box"][1]) <= 2, "one row, left to right"
    nl, nt, nr, nb = res["notes"]
    for tid, t in zip(TILES, tiles):
        l, top, r, bot = t["box"]
        assert r - l >= 0.22 * res["vw"], f"{tid} too narrow to read"
        assert t["body"] >= 16, f"{tid}: body type too small"
        assert not (l < nr and r > nl and top < nb and bot > nt), f"{tid} covers the Notes button"


@pytest.mark.parametrize("size", SIZES)
def test_s9_headings_wrap_on_whole_words(page, size):
    """Presenter, 22 Nov: 're-' / 'emerged' split across lines (line count: the shared tile-row test)."""
    open_deck(page, *size)
    goto_slide(page, "s-9", 3)
    settle(page, "#s9-t3")
    res = page.evaluate("""ids => ids.map(id => { const h = document.querySelector('#' + id + ' h3'),
        lh = parseFloat(getComputedStyle(h).lineHeight), w = document.createTreeWalker(h, NodeFilter.SHOW_TEXT), split = [];
      for (let node; (node = w.nextNode());) for (const m of node.textContent.matchAll(/\\S+/g)) {
        if (!/[-\u2010\u2011]/.test(m[0])) continue;
        const r = document.createRange(); r.setStart(node, m.index); r.setEnd(node, m.index + m[0].length);
        if (new Set([...r.getClientRects()].map(b => Math.round(b.top))).size > 1) split.push(m[0]); }
      return { id, split }; })""", TILES)
    for r in res:
        assert not r["split"], f"{r['id']} breaks inside {r['split']}"


VISIBLE = """sid => { const s = document.getElementById(sid);
  const on = e => { for (; e && e !== s; e = e.parentElement) if (+getComputedStyle(e).opacity <= 0.5) return false; return true; };
  return {
    titles: [...s.querySelectorAll('h2.title')].filter(on).map(e => e.textContent.trim()),
    tiles: [...s.querySelectorAll('.text-tile')].filter(on).map(e => e.id),
    quote: [...s.querySelectorAll('.body blockquote')].filter(on).map(e => e.textContent.trim()),
    controls: [...s.querySelectorAll('table')].some(on),
    prompts: [...s.querySelectorAll('li.prompt')].filter(on).map(e => e.id),
    insight: [...s.querySelectorAll('.overlay--insight')].some(e => e.classList.contains('is-shown')),
  }; }"""


def test_s10_swaps_tiles_controls_prompts_with_a_title_per_phase(page):
    open_deck(page)
    for k in range(8):
        goto_slide(page, "s-10", k)
        v = page.evaluate(VISIBLE, "s-10")
        phase = "tiles" if k <= 3 else "controls" if k == 4 else "discussion"
        assert v["titles"] == [S10_TITLES[phase]], k
        assert v["tiles"] == (S10_TILES[:k] if k <= 3 else []), k
        assert (helper_norm(COXON) in [helper_norm(q) for q in v["quote"]]) == (1 <= k <= 3), k
        assert not v["insight"], k
        assert v["controls"] == (k == 4), k
        assert v["prompts"] == ["s10-detect", "s10-train", "s10-investigate"][:max(0, k - 4)], k


@pytest.mark.parametrize("size", SIZES)
def test_s10_tiles_read_left_to_right_in_one_row_as_on_s9(page, size):
    """Same row and type as s-9: one row, readable width, body type no smaller than s-9's."""
    open_deck(page, *size)
    goto_slide(page, "s-9", 3)
    settle(page, "#s9-t3")
    s9_body = page.evaluate("() => parseFloat(getComputedStyle(document.querySelector('#s9-t1 li')).fontSize)")
    goto_slide(page, "s-10", 3)
    settle(page, "#s10-t3")
    res = page.evaluate("""ids => { const nb = document.querySelector('.notes-btn').getBoundingClientRect();
      return { vw: innerWidth, notes: [nb.left, nb.top, nb.right, nb.bottom], tiles: ids.map(id => { const t = document.getElementById(id),
        b = t.getBoundingClientRect(); return { box: [b.left, b.top, b.right, b.bottom],
        body: parseFloat(getComputedStyle(t.querySelector('li')).fontSize) }; }) }; }""", S10_TILES)
    tiles = res["tiles"]
    for a, b in zip(tiles, tiles[1:]):
        assert a["box"][2] <= b["box"][0] + 1 and abs(a["box"][1] - b["box"][1]) <= 2, "one row, left to right"
    nl, nt, nr, nb = res["notes"]
    for tid, t in zip(S10_TILES, tiles):
        l, top, r, bot = t["box"]
        assert r - l >= 0.22 * res["vw"], f"{tid} too narrow to read"
        assert t["body"] >= s9_body, f"{tid}: body type smaller than s-9's"
        assert not (l < nr and r > nl and top < nb and bot > nt), f"{tid} covers the Notes button"
