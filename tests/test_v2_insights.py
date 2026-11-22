"""Spec: S-027

v2 closing slides. s-9 Insights reuses s-8's tile row over the frozen, blurred incident world: three
text tiles built one per step (how misalignment happened from training to evaluation; why it is hard
to design out and unsolved; opaque firings discourage transparency, both sides stated). s-10
Takeaways: capability pace honest about pauses and pledges, its Insight, proportionate controls
mapped to incident failures, then three discussion prompts, with a title per phase.
Coverage: happy (slides close the deck in order with approved titles/kickers; s-9 builds one tile per
step with sourced facts, verbatim quotes and links; s-10 swaps pace → Insight → controls → prompts) ·
edge (s-9 world frozen in s-8's place and state; tiles read left to right in one row at every review
size; s-10's insider quote sits in the pace panel and leaves with it; notes target elements on their
slide) · negative (s-9 has no loop diagram, narration or separate Insight; no slide-scoped tile CSS;
no causal claim on the firings; quotes verbatim from research; Hubinger not repeated on s-10; no
weakly sourced Anthropic pause; no "suicide", "same agents" or firm-specific advice).
"""

import re

import pytest

from helper_deck import ROOT, deck_source, goto_slide, open_deck, parse_slides, settle, slides_source

pytestmark = pytest.mark.deck("v2")

S9_TITLE = ("Misalignment grew from ordinary training choices, and the obvious fixes risk making it "
            "harder to see")
S10_TITLES = {  # visible title per step: pace (✓) → controls (v1 5.5) → discussion (v1 6.1 ◇)
    "pace": "Capability, compute and spending are still accelerating despite pauses and pledges",
    "controls": ("Each failure in this incident maps to a control that everyday AI systems can "
                 "apply in proportion to risk"),
    "discussion": "Detection, training and independent oversight remain open questions after this incident",
}
S10_INSIGHT = ("METR could not reliably measure GPT-5.6 Sol: its time-horizon estimate ranged from "
               "11 to over 270 hours depending on how cheating was scored.")
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
    "s9-t2": ["time.com", "arxiv.org/abs/2503.11926", "arxiv.org/abs/2401.05566", "arxiv.org/abs/2412.14093"],
    "s9-t3": ["fortune.com", "sfstandard.com"],
}
COXON = "One, it’s obvious that things are speeding up, and two, they’re not under control."
CONTROLS = ["Least agency and autonomy", "Per-agent authentication and authorisation",
            "Sandbox isolation", "Deterministic controls", "Network access only when justified"]
TILE_TEXT = """id => { const t = document.getElementById(id);
  return { text: t.innerText, quotes: [...t.querySelectorAll('blockquote')].map(q => q.textContent.trim()),
           links: [...t.querySelectorAll('a[href]')].map(a => a.href), head: (t.querySelector('h3') || {}).textContent }; }"""


def helper_norm(s: str) -> str:
    """Fold typographic apostrophes/quotes and whitespace so deck, docs and research text compare."""
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("\u2011", "-")   # a non-breaking hyphen is still a hyphen
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
    assert helper_norm(S10_TITLES["pace"]) in helper_storyboard("s-10 · Pace")


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


def test_s10_compare_is_honest_about_both_sides():
    sec = helper_section("s-10")
    table = re.search(r'<table class="compare".*?</table>', sec, re.S).group(0)
    heads = re.findall(r"<th[^>]*>(.*?)</th>", table)
    assert len(heads) == 2 and "accelerating" in heads[0].lower() and "pause" in heads[1].lower()
    flat = helper_flat(table)
    for fact in ("~10×", "~5× a year", "$700B", "Nov 2026",                          # still rising
                 "paused its largest", "We Must Pace the Frontier", "Over 1,100", "letter", "(Jul)",
                 "slow, plateau"):                                                    # pauses, pledges
        assert helper_norm(fact) in flat, fact
    assert "rising steeply" not in sec, "presenter rejected 'rising steeply' for 'accelerating'"


def test_s10_omits_the_weakly_sourced_anthropic_pause():
    """Only a weak source reports an Anthropic pause (capability_pace.md): omitted unless confirmed."""
    flat = helper_flat(helper_section("s-10")).lower()
    assert not re.search(r"anthropic (also |reportedly )?(paused|halted)", flat)


def test_s10_insider_quote_sits_in_the_pace_panel_and_hubinger_moved_to_s9():
    sec = helper_section("s-10")
    assert 'class="narration"' not in sec, "s-10's one quote lives in the body, so the body keeps the full width"
    body = re.search(r'<div class="body.*?(?=<aside)', sec, re.S).group(0)
    quote = re.search(r"<blockquote[^>]*>(.*?)</blockquote>\s*<p class=\"cite\">(.*?)</p>", body, re.S)
    assert quote and helper_norm(quote.group(1)) == helper_norm(COXON) and "Coxon" in quote.group(2)
    assert helper_norm(COXON) in helper_research()
    assert "plan to solve alignment" not in sec, "Hubinger's quote moved to s-9 tile 2"


def test_s10_controls_pair_each_control_with_its_incident_failure():
    sec = helper_section("s-10")
    table = re.search(r'<table(?! class="compare").*?</table>', sec, re.S).group(0)
    rows = re.findall(r"<tr[^>]*>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>", table, re.S)
    assert [c for c, _ in rows] == CONTROLS
    failures = " ".join(f for _, f in rows)
    for evidence in ("shared credential", "mirror", "27 June", "internet"):
        assert evidence in failures, evidence
    assert "in proportion to" in helper_flat(sec).lower()


def test_s10_has_three_discussion_prompts_one_per_step():
    sec = helper_section("s-10")
    prompts = re.findall(r'<li class="prompt" id="(s10-\w+)" data-show-at="(\d)">(.*?)</li>', sec, re.S)
    assert [(i, at) for i, at, _ in prompts] == [("s10-detect", "4"), ("s10-train", "5"),
                                                ("s10-investigate", "6")]
    assert all(p.rstrip().endswith("?") for *_, p in prompts)


def test_s10_insight_is_the_storyboard_text_on_its_own_step():
    ins = re.findall(r'<aside class="overlay overlay--insight" data-at="(\d+)">\s*<p>(.*?)</p>',
                     helper_section("s-10"), re.S)
    assert ins == [("2", S10_INSIGHT)]
    assert helper_norm(S10_INSIGHT) in helper_storyboard("s-10 · Pace")


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
    assert plan["s-9"] == 3 and plan["s-10"] == 6
    goto_slide(page, "s-9", 3)
    goto_slide(page, "s-10", 6)
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
        body: parseFloat(getComputedStyle(t.querySelector('p')).fontSize) }; }) }; }""", TILES)
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
def test_s9_headings_wrap_on_whole_words_within_two_lines(page, size):
    """Presenter, 22 Nov: 're-' / 'emerged' split across lines; every heading fits two lines."""
    open_deck(page, *size)
    goto_slide(page, "s-9", 3)
    settle(page, "#s9-t3")
    res = page.evaluate("""ids => ids.map(id => { const h = document.querySelector('#' + id + ' h3'),
        lh = parseFloat(getComputedStyle(h).lineHeight), w = document.createTreeWalker(h, NodeFilter.SHOW_TEXT), split = [];
      for (let node; (node = w.nextNode());) for (const m of node.textContent.matchAll(/\\S+/g)) {
        if (!/[-\u2010\u2011]/.test(m[0])) continue;
        const r = document.createRange(); r.setStart(node, m.index); r.setEnd(node, m.index + m[0].length);
        if (new Set([...r.getClientRects()].map(b => Math.round(b.top))).size > 1) split.push(m[0]); }
      return { id, lines: Math.round(h.getBoundingClientRect().height / lh), split }; })""", TILES)
    for r in res:
        assert r["lines"] <= 2, f"{r['id']} heading takes {r['lines']} lines"
        assert not r["split"], f"{r['id']} breaks inside {r['split']}"


VISIBLE = """sid => { const s = document.getElementById(sid);
  const on = e => { for (; e && e !== s; e = e.parentElement) if (+getComputedStyle(e).opacity <= 0.5) return false; return true; };
  return {
    titles: [...s.querySelectorAll('h2.title')].filter(on).map(e => e.textContent.trim()),
    compare: [...s.querySelectorAll('table.compare')].some(on),
    quote: [...s.querySelectorAll('.body blockquote')].filter(on).map(e => e.textContent.trim()),
    controls: [...s.querySelectorAll('table:not(.compare)')].some(on),
    prompts: [...s.querySelectorAll('li.prompt')].filter(on).map(e => e.id),
    insight: [...s.querySelectorAll('.overlay--insight')].some(e => e.classList.contains('is-shown')),
  }; }"""


def test_s10_swaps_pace_insight_controls_prompts_with_a_title_per_phase(page):
    open_deck(page)
    for k in range(7):
        goto_slide(page, "s-10", k)
        v = page.evaluate(VISIBLE, "s-10")
        phase = "pace" if k <= 2 else "controls" if k == 3 else "discussion"
        assert v["titles"] == [S10_TITLES[phase]], k
        assert v["compare"] == (1 <= k <= 2), k
        assert [helper_norm(q) for q in v["quote"]] == ([helper_norm(COXON)] if 1 <= k <= 2 else []), k
        assert v["insight"] == (k == 2), k
        assert v["controls"] == (k == 3), k
        assert v["prompts"] == ["s10-detect", "s10-train", "s10-investigate"][:max(0, k - 3)], k
