"""Spec: S-027

v2 closing slides: s-9 Insights (readable reasoning made the incident discoverable; penalising it
risks concealment; a more capable system closes the gap) and s-10 Takeaways (capability pace,
honest about pauses and pledges → proportionate controls mapped to incident failures → three
discussion prompts).
Coverage: happy (slides close the deck in order with storyboard titles/kickers; s-9 builds its
loop tile by tile with evidence and narration, then the approved Insight; s-10 swaps pace →
Insight → controls → prompts with a title per phase) · edge (narration verbatim and never on an
Insight step; earlier phases leave the screen when the next arrives; every note targets an element
on its slide with an https source) · negative (no "suicide", no curly quote marks inside tiles,
no claim that the same agents took the OpenAI cluster, no firm-specific advice).
"""

import re
from html.parser import HTMLParser

import pytest

from helper_deck import ROOT, goto_slide, open_deck, parse_slides, slides_source

pytestmark = pytest.mark.deck("v2")

S9_TITLE = "Investigators could reconstruct the agents’ intent because their reasoning stayed readable"
S10_TITLES = {  # visible title per step: pace (✓) → controls (v1 5.5) → discussion (v1 6.1 ◇)
    "pace": "Capability, compute and spending are still accelerating despite pauses and pledges",
    "controls": ("Each failure in this incident maps to a control that everyday AI systems can "
                 "apply in proportion to risk"),
    "discussion": "Detection, training and independent oversight remain open questions after this incident",
}
S9_INSIGHT = ("The agents’ reasoning stayed readable, which is what let investigators reconstruct "
              "their intent. Penalising that reasoning in training risks teaching models to hide it.")
S10_INSIGHT = ("METR could not reliably measure GPT-5.6 Sol: its time-horizon estimate ranged from "
               "11 to over 270 hours depending on how cheating was scored.")
S9_NARR = {
    1: ["Could strategically manipulate trajectory evidence? Our thoughts aren’t necessarily logged? "
        "Yes transcript.",
        "The models are highly explicit in their CoT about these deception attempts"],
    4: ["the gap between the experimental tampering we saw and tampering that successfully erased "
        "evidence of itself is large"],
}
S10_NARR = {
    1: ["One, it’s obvious that things are speeding up, and two, they’re not under control.",
        "we do not yet have a plan to solve alignment for superintelligence."],
}
CONTROLS = ["Least agency and autonomy", "Per-agent authentication and authorisation",
            "Sandbox isolation", "Deterministic controls", "Network access only when justified"]


def _norm(s: str) -> str:
    """Fold typographic apostrophes/quotes and whitespace so deck and storyboard text compare."""
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", s).strip()


def _section(sid: str) -> str:
    m = re.search(rf'<section class="[^"]*" id="{sid}".*?</section>', slides_source(), re.S)
    assert m, f"slide {sid} missing"
    return m.group(0)


class _Text(HTMLParser):
    """Collect text of elements matching a tag + class, with their data-at attribute."""

    def __init__(self, tag, cls):
        super().__init__(convert_charrefs=True)
        self.tag, self.cls, self.out, self._cur = tag, cls, [], None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == self.tag and self.cls in (a.get("class") or "").split():
            self._cur = [a, ""]

    def handle_endtag(self, tag):
        if tag == self.tag and self._cur:
            self.out.append(tuple(self._cur))
            self._cur = None

    def handle_data(self, data):
        if self._cur:
            self._cur[1] += data


def _texts(html: str, tag: str, cls: str) -> list:
    p = _Text(tag, cls)
    p.feed(html)
    return p.out


def _tiles_by_step(sid: str) -> dict:
    """Map step → list of normalised narration quotes, from article.narr-tile[data-at]."""
    out = {}
    for tile in re.findall(r'<article class="narr-tile" data-at="(\d+)">(.*?)</article>', _section(sid), re.S):
        quote = _texts(tile[1], "blockquote", "msg-text")
        label = _texts(tile[1], "p", "msg-agent")
        assert len(quote) == 1 and len(label) == 1 and label[0][1].strip(), "tile = label + one quote"
        out.setdefault(int(tile[0]), []).append(_norm(quote[0][1]))
    return out


def _storyboard(heading: str) -> str:
    text = (ROOT / "docs" / "STORYBOARD.md").read_text(encoding="utf-8")
    return _norm(text.split(f"## {heading}")[1].split("\n## ")[0])


# ---------- static: shell, order, copy ----------

def test_insights_and_takeaways_close_the_deck_in_order():
    slides = parse_slides()
    assert [s["attrs"]["id"] for s in slides[-2:]] == ["s-9", "s-10"]
    s9, s10 = slides[-2], slides[-1]
    assert s9["attrs"]["data-chapter"] == "Insights" and s10["attrs"]["data-chapter"] == "Takeaways"
    assert '<p class="kicker">09 · Insights</p>' in _section("s-9")
    assert '<p class="kicker">10 · Takeaways</p>' in _section("s-10")


def test_titles_are_the_storyboard_titles():
    assert [t for _, t in _texts(_section("s-9"), "h2", "title")] == [S9_TITLE]
    titles = [t for _, t in _texts(_section("s-10"), "h2", "title")]
    assert titles == list(S10_TITLES.values())
    assert _norm(S10_TITLES["pace"]) in _storyboard("s-10 · Pace, takeaway, discussion")
    assert _norm(S9_TITLE) in _storyboard("s-9 · Insights: discoverable this time")


def test_narration_is_verbatim_from_the_storyboard_and_steps_match():
    for sid, want, head in (("s-9", S9_NARR, "s-9 · Insights: discoverable this time"),
                            ("s-10", S10_NARR, "s-10 · Pace, takeaway, discussion")):
        got = _tiles_by_step(sid)
        assert got == {k: [_norm(q) for q in v] for k, v in want.items()}, sid
        board = _storyboard(head)
        for qs in want.values():
            for q in qs:
                assert _norm(q) in board, f"{sid} quote not in storyboard: {q[:40]}"


def test_narration_tiles_carry_no_quote_marks_and_sit_after_the_body():
    for sid in ("s-9", "s-10"):
        sec = _section(sid)
        for _, q in _texts(sec, "blockquote", "msg-text"):
            assert not re.match(r'\s*["“]', q) and not re.search(r'["”]\s*$', q), q
        assert sec.index('<div class="narration">') > sec.index('<div class="body'), "narration follows the body"


def test_insights_are_the_approved_text_on_their_own_step():
    for sid, text, at in (("s-9", S9_INSIGHT, 5), ("s-10", S10_INSIGHT, 2)):
        ins = re.findall(r'<aside class="overlay overlay--insight" data-at="(\d+)">\s*<p>(.*?)</p>',
                         _section(sid), re.S)
        assert ins == [(str(at), text)], sid
        assert at not in _tiles_by_step(sid), f"{sid}: Insight shares its step with narration"
    assert _norm(S10_INSIGHT) in _storyboard("s-10 · Pace, takeaway, discussion")


def test_s9_diagram_layers_tiles_and_evidence():
    sec = _section("s-9")
    svg = re.search(r'<svg class="diagram".*?</svg>', sec, re.S).group(0)
    order = re.findall(r'<g class="(layer-[a-z]+)"', svg)
    assert order == ["layer-edges", "layer-nodes", "layer-key", "layer-labels"]
    tiles = dict(re.findall(r'<g class="tile[^"]*" id="(s9-[a-z]+)" data-show-at="(\d)"', svg))
    assert tiles == {"s9-read": "1", "s9-penalise": "2", "s9-hide": "3", "s9-capable": "4",
                     "s9-baker": "3", "s9-sleeper": "3", "s9-faking": "3"}
    assert re.search(r'<g class="tile tile--key" id="s9-hide"', svg), "cheat invisibly is the key tile"
    edges = re.findall(r'<path class="edge" data-from="#(s9-\w+)" data-to="#(s9-\w+)"[^>]*data-show-at="(\d)"', svg)
    assert edges == [("s9-read", "s9-penalise", "2"), ("s9-penalise", "s9-hide", "3"),
                     ("s9-hide", "s9-capable", "4")]
    flat = _norm(re.sub(r"<[^>]+>", " ", svg))
    for words in ("Readable reasoning", "no visible cheating", "cheat invisibly",
                  "more capable system", "78% under RL"):
        assert _norm(words).lower() in flat.lower(), words
    for href in ("arxiv.org/abs/2503.11926", "arxiv.org/abs/2401.05566", "arxiv.org/abs/2412.14093"):
        assert href in sec


def test_s10_compare_is_honest_about_both_sides():
    sec = _section("s-10")
    table = re.search(r'<table class="compare".*?</table>', sec, re.S).group(0)
    heads = re.findall(r"<th[^>]*>(.*?)</th>", table)
    assert len(heads) == 2 and "accelerating" in heads[0].lower() and "pause" in heads[1].lower()
    flat = _norm(re.sub(r"<[^>]+>", " ", table))
    for fact in ("~10×", "~5× a year", "$700B", "Nov 2026",                       # still rising
                 "paused its largest", "We Must Pace the Frontier", "letter", "slow, plateau"):  # pauses
        assert _norm(fact) in flat, fact
    assert "rising steeply" not in sec, "presenter rejected 'rising steeply' for 'accelerating'"


def test_s10_controls_pair_each_control_with_its_incident_failure():
    sec = _section("s-10")
    table = re.search(r'<table(?! class="compare").*?</table>', sec, re.S).group(0)
    rows = re.findall(r"<tr[^>]*>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>", table, re.S)
    assert [c for c, _ in rows] == CONTROLS
    failures = " ".join(f for _, f in rows)
    for evidence in ("shared credential", "mirror", "27 June", "internet"):
        assert evidence in failures, evidence
    assert "in proportion to" in _norm(re.sub(r"<[^>]+>", " ", sec)).lower()


def test_s10_has_three_discussion_prompts_one_per_step():
    sec = _section("s-10")
    prompts = re.findall(r'<li class="prompt" id="(s10-\w+)" data-show-at="(\d)">(.*?)</li>', sec, re.S)
    assert [(i, at) for i, at, _ in prompts] == [("s10-detect", "4"), ("s10-train", "5"),
                                                ("s10-investigate", "6")]
    assert all(p.rstrip().endswith("?") for *_, p in prompts)
    assert re.search(r'<ol class="prompts">', sec)


def test_notes_target_elements_on_their_slide_and_cite_https_sources():
    for sid, minimum in (("s-9", 7), ("s-10", 15)):
        sec = _section(sid)
        notes = re.findall(r'<aside class="note" data-for="#([\w-]+)">(.*?)</aside>', sec, re.S)
        assert len(notes) >= minimum, sid
        for target, body in notes:
            assert f'id="{target}"' in sec, f"{sid}: note targets #{target}, not on this slide"
            assert "<h3>" in body and re.search(r'<a class="src" href="https://', body), target


def test_forbidden_and_inaccurate_wording_is_absent():
    text = (_section("s-9") + _section("s-10")).lower()
    assert "suicide" not in text
    assert "same agents" not in text, "19 Jul OpenAI-cluster takeover was a different Astra-family model"
    for firm in ("deloitte", "our firm", "our clients"):
        assert firm not in text


# ---------- browser: what is on screen at each step ----------

VISIBLE = """sid => { const s = document.getElementById(sid);
  const on = e => +getComputedStyle(e).opacity > 0.5;
  const ids = sel => [...s.querySelectorAll(sel)].filter(on).map(e => e.id || e.className.baseVal || e.className);
  return {
    titles: [...s.querySelectorAll('h2.title')].filter(on).map(e => e.textContent.trim()),
    tiles: [...s.querySelectorAll('g.tile[id]')].filter(e => e.classList.contains('is-visible')).map(e => e.id),
    edges: [...s.querySelectorAll('path.edge')].filter(e => e.classList.contains('is-visible')).length,
    compare: [...s.querySelectorAll('table.compare')].some(on),
    controls: [...s.querySelectorAll('table:not(.compare)')].some(on),
    prompts: [...s.querySelectorAll('li.prompt')].filter(on).map(e => e.id),
    insight: [...s.querySelectorAll('.overlay--insight')].some(e => e.classList.contains('is-shown')),
  }; }"""


def test_step_counts(page):
    assert open_deck(page) == []
    plan = dict(page.evaluate("window.deck.plan()"))
    assert plan["s-9"] == 5 and plan["s-10"] == 6


def test_s9_builds_the_loop_step_by_step(page):
    open_deck(page)
    want = {0: [], 1: ["s9-read"], 2: ["s9-read", "s9-penalise"],
            3: ["s9-read", "s9-penalise", "s9-baker", "s9-sleeper", "s9-faking", "s9-hide"],
            4: ["s9-read", "s9-penalise", "s9-baker", "s9-sleeper", "s9-faking", "s9-hide", "s9-capable"]}
    for k in range(6):
        goto_slide(page, "s-9", k)
        v = page.evaluate(VISIBLE, "s-9")
        assert sorted(v["tiles"]) == sorted(want.get(k, want[4])), k
        assert v["edges"] == max(0, min(k, 4) - 1), k
        assert v["insight"] == (k == 5), k
        assert v["titles"] == [S9_TITLE]


def test_s10_swaps_pace_insight_controls_prompts_with_a_title_per_phase(page):
    open_deck(page)
    for k in range(7):
        goto_slide(page, "s-10", k)
        v = page.evaluate(VISIBLE, "s-10")
        phase = "pace" if k <= 2 else "controls" if k == 3 else "discussion"
        assert v["titles"] == [S10_TITLES[phase]], k
        assert v["compare"] == (1 <= k <= 2), k
        assert v["insight"] == (k == 2), k
        assert v["controls"] == (k == 3), k
        assert v["prompts"] == ["s10-detect", "s10-train", "s10-investigate"][:max(0, k - 3)], k
