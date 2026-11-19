"""Spec: S-026

v2 slide s-8 (Investigation): a step-built funnel from the raw evidence to the findings, inside
a scope fence OpenAI set, with investigator voices narrating the analysis agents' limits.
Coverage: happy (slide in order with storyboard title/kicker/chapter; five steps each adding one
funnel stage and its edge; fence and scope labels from step 1; narration tiles at steps 4–5 with
verbatim investigator text; sourced notes on constraints) · edge (analysis-agent stage visibly
flagged; diagram text stays inside the viewport and clear of the title at 1280×720 and 1920×1080) ·
negative (no stage before its step; no tile beyond two per step; no paraphrase braces, quote marks
or "suicide" on the slide; no console errors).
"""

import re

import pytest

from helper_deck import goto_slide, open_deck, parse_slides, slides_source

pytestmark = pytest.mark.deck("v2")

SID = "s-8"
TITLE = ("Three investigators had six days and relied on analysis agents from the model family "
         "they were investigating")
STAGES = [  # (tile id, text the tile must carry), in funnel order = build step
    ("s8-cache", "~1.2M"),
    ("s8-messages", "~70k"),
    ("s8-transcripts", "~1,300"),
    ("s8-analysis", "GPT-5.6 Sol"),
    ("s8-findings", "Findings"),
]
NARRATION = {  # step -> [(label must contain, verbatim text must contain)]
    4: [("fn 59", "Another agent reported a number of confabulated differences between two "
                  "different datasets of transcripts."),
        ("fn 60", "did not clearly spell out the fact that this behavior was straightforwardly "
                  "malicious and deceptive")],
    5: [("Greenblatt", "often missing key details, wrong, overconfident, or really hard to understand")],
}


def helper_section() -> str:
    m = re.search(r'<section class="slide[^"]*" id="s-8".*?</section>', slides_source(), re.S)
    assert m, "slide s-8 must exist"
    return m.group(0)


def test_slide_sits_in_deck_order_with_storyboard_title_kicker_and_chapter():
    slides = parse_slides()
    ids = [s["attrs"]["id"] for s in slides]
    assert SID in ids
    nums = [int(i.split("-")[1]) for i in ids]
    assert nums == sorted(nums), ids
    s = slides[ids.index(SID)]
    assert s["attrs"]["data-chapter"] == "Investigation"
    assert s["title"] == TITLE and s["title_em"] <= 1
    assert re.search(r'<p class="kicker">08 · Investigation</p>', helper_section())


def test_slide_has_five_steps_and_loads_cleanly(page):
    errors = open_deck(page)
    plan = dict(page.evaluate("window.deck.plan()"))
    assert plan[SID] == 5
    assert errors == []


def test_each_step_adds_one_funnel_stage_and_its_edge(page):
    open_deck(page)
    for step in range(0, 6):
        goto_slide(page, SID, step)
        vis = page.evaluate("""() => Object.fromEntries([...document.querySelectorAll('#s-8 svg.diagram .tile')]
          .map(t => [t.id, t.classList.contains('is-visible')]))""")
        assert set(vis) == {i for i, _ in STAGES}, vis
        for n, (tid, _) in enumerate(STAGES, start=1):
            assert vis[tid] == (step >= n), f"step {step}: {tid}"
        edges = page.evaluate("""() => [...document.querySelectorAll('#s-8 svg.diagram path.edge')]
          .map(e => [e.dataset.from, e.dataset.to, e.classList.contains('is-visible')])""")
        assert len(edges) == 4
        for n, (frm, to, shown) in enumerate(edges, start=2):
            assert (frm, to) == (f"#{STAGES[n - 2][0]}", f"#{STAGES[n - 1][0]}")
            assert shown == (step >= n), f"step {step}: edge {frm}->{to}"


def test_funnel_stages_carry_the_sourced_figures():
    sec = helper_section()
    for tid, text in STAGES:
        tile = re.search(rf'<g class="tile[^"]*" id="{tid}"[^>]*>(.*?)</g>', sec, re.S)
        assert tile and text in tile.group(1), tid
    analysis = re.search(r'id="s8-analysis"[^>]*>(.*?)</g>', sec, re.S).group(1)
    assert "same model family" in analysis and "analysis agents" in analysis
    assert "raw chain of thought" in re.search(r'id="s8-transcripts"[^>]*>(.*?)</g>', sec, re.S).group(1)


def test_analysis_stage_is_flagged_apart_from_ordinary_stages(page):
    open_deck(page)
    goto_slide(page, SID, 5)
    res = page.evaluate("""() => {
      const f = id => getComputedStyle(document.querySelector('#' + id + ' rect')).fill;
      const flagged = document.querySelector('#s8-analysis');
      return { flag: flagged.classList.contains('tile--flag'), layer: flagged.parentElement.getAttribute('class'),
               a: f('s8-analysis'), plain: f('s8-cache') }; }""")
    assert res["flag"] and res["layer"] == "layer-key"
    assert res["a"] != res["plain"], "flagged stage must be visibly tinted"


def test_scope_fence_surrounds_the_funnel_from_step_one(page):
    open_deck(page)
    goto_slide(page, SID, 1)
    res = page.evaluate("""() => {
      const fence = document.querySelector('#s-8 #s8-fence'), fb = fence.getBBox();
      const inside = [...document.querySelectorAll('#s-8 .tile rect')].every(r => { const b = r.getBBox();
        return b.x >= fb.x && b.y >= fb.y && b.x + b.width <= fb.x + fb.width && b.y + b.height <= fb.y + fb.height; });
      const labels = [...document.querySelectorAll('#s-8 .layer-labels text')]
        .map(t => [t.textContent, t.classList.contains('is-visible')]);
      return { shown: fence.classList.contains('is-visible'), inside, labels }; }""")
    assert res["shown"] and res["inside"]
    text = " ".join(t for t, _ in res["labels"]).upper()
    assert all(v for _, v in res["labels"]), "scope labels show with the fence"
    for must in ("SET BY OPENAI", "26 JUN", "13 JUL", "TRAINING", "OPENAI INFRASTRUCTURE AFTER 13 JUL"):
        assert must in text, must


def test_narration_tiles_quote_investigators_verbatim_at_steps_four_and_five():
    sec = helper_section()
    assert re.search(r'</div>\s*<div class="narration">', sec), "narration follows the body as a slide child"
    narr = re.search(r'<div class="narration">(.*?)</div>', sec, re.S).group(1)
    tiles = re.findall(r'<article class="narr-tile" data-at="(\d+)">\s*<p class="msg-agent">(.*?)</p>\s*'
                       r'<blockquote class="msg-text">(.*?)</blockquote>\s*</article>', narr, re.S)
    by_step: dict[int, list] = {}
    for at, label, text in tiles:
        by_step.setdefault(int(at), []).append((label, text))
    assert sorted(by_step) == sorted(NARRATION)
    for step, expected in NARRATION.items():
        got = by_step[step]
        assert len(got) == len(expected) <= 2
        for (label, text), (want_label, want_text) in zip(got, expected):
            assert want_label in label and want_text in text, (label, text)
            assert not re.search(r'["“”{}]', text), "no quote marks or paraphrase braces in tiles"


def test_notes_cite_constraints_on_the_review_and_target_slide_elements():
    sec = helper_section()
    notes = re.findall(r'<aside class="note" data-for="#([\w-]+)">(.*?)</aside>', sec, re.S)
    assert len(notes) >= 3
    for target, body in notes:
        assert f'id="{target}"' in sec, target
        assert re.search(r"<h3>.+</h3>", body) and re.search(r'<a class="src" href="https://', body)
    text = " ".join(b for _, b in notes)
    for must in ("unpaid", "six days", "$400K", "HPIM", "broader dataset", "could not have found everything"):
        assert must in text, must
    assert "x.com/RyanGreenblatt" in text, "Greenblatt's words are sourced"


def test_slide_never_uses_forbidden_words_or_paraphrase_markup():
    sec = helper_section()
    assert "suicide" not in sec.lower()
    assert "{" not in sec and "}" not in sec
    assert not re.search(r"\sstyle\s*=", sec)


@pytest.mark.parametrize("vw,vh", [(1280, 720), (1920, 1080)])
def test_diagram_stays_on_screen_and_clear_of_the_title(page, vw, vh):
    open_deck(page, vw, vh)
    goto_slide(page, SID, 5)
    res = page.evaluate("""() => {
      const s = document.querySelector('#s-8'), sb = s.getBoundingClientRect();
      const title = s.querySelector('.title').getBoundingClientRect();
      return { title: title.bottom, top: sb.top, h: innerHeight, w: innerWidth,
        boxes: [...s.querySelectorAll('svg.diagram text, svg.diagram rect')].map(e => {
          const r = e.getBoundingClientRect(); return [e.textContent || e.id || 'rect', r.left, r.top - sb.top, r.right, r.bottom - sb.top]; }) }; }""")
    for name, left, top, right, bottom in res["boxes"]:
        assert left >= 0 and right <= res["w"], f"{name} off-slide horizontally"
        assert bottom <= res["h"], f"{name} off-slide vertically"
        assert top >= res["title"] - res["top"], f"{name} rises over the title"
