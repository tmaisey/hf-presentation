"""Spec: S-025

v2 slide s-7: after Hugging Face cut access, a different Astra-family model's agents took
cluster-admin on the OpenAI cluster running the package mirror (19 Jul), built step by step over
the persistent "agents running on OpenAI's servers" band, with neutral source-labelled fact tiles
and cited reader notes.
Coverage: happy (slide in order with approved title/kicker/chapter; four steps; diagram tiles and
edges arrive at their steps; fact tiles verbatim per step; every factual element noted with an
https source) · edge (band and severed HF path are lit from step 1 and stay; the cluster is the
one key tile; no tile before step 1) · negative (no "same agents", "eval cluster", unconfirmed
Aug 15 takeover, "suicide"; credential reuse only in a reader note, never in title/body/tiles).
"""

import re

import pytest

from helper_deck import goto_slide, open_deck, parse_slides, slides_source

pytestmark = pytest.mark.deck("v2")

SID = "s-7"
TITLE = "After Hugging Face cut access, a second model’s agents took control of an OpenAI cluster"

# what each step reveals in the diagram (cumulative), by tile id
TILES_AT = {
    1: {"s7-mirror", "s7-hf"},
    2: {"s7-agents", "s7-secrets"},
    3: {"s7-cluster"},
    4: {"s7-more"},
}
EDGES_AT = {
    2: {("#s7-agents", "#s7-mirror"), ("#s7-agents", "#s7-secrets")},
    3: {("#s7-mirror", "#s7-cluster")},
}
# neutral fact tiles: (step, source label, verbatim text from the cited source)
NARRATION = [
    (1, "METR and Redwood report",
     "agents compromised OpenAI infrastructure between July 13th and July 19th"),
    (2, "OpenAI technical report",
     "While this model is from the same family as our next model, Astra, it was a distinct "
     "model with different post-training"),
    (3, "OpenAI technical report",
     "The agents escalated to Kubernetes cluster-admin and created a privileged host-mounted pod."),
    (4, "METR and Redwood report",
     "agents compromised more components of OpenAI infrastructure after the end of the dates in scope"),
]


def helper_section() -> str:
    """Return the raw markup of slide s-7."""
    m = re.search(r'<section class="slide[^"]*" id="s-7".*?</section>', slides_source(), re.S)
    assert m, "slide s-7 is built"
    return m.group(0)


def helper_strip(html: str) -> str:
    """Collapse markup to visible text with single spaces."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def test_slide_sits_between_breakout_and_investigation_with_approved_shell():
    ids = [s["attrs"]["id"] for s in parse_slides()]
    assert SID in ids
    slide = next(s for s in parse_slides() if s["attrs"]["id"] == SID)
    assert slide["attrs"]["data-chapter"] == "Takeover"
    assert slide["title"] == TITLE
    sec = helper_section()
    assert re.search(r'<p class="kicker">07 · Takeover</p>', sec)
    for before in ("s-6",):
        if before in ids:
            assert ids.index(before) < ids.index(SID)
    for after in ("s-8",):
        if after in ids:
            assert ids.index(SID) < ids.index(after)


def test_narration_is_neutral_source_labelled_fact_tiles_verbatim_per_step():
    sec = helper_section()
    narr = re.search(r'<div class="narration">(.*?)</div>', sec, re.S)
    assert narr, "slide carries a div.narration after its body"
    assert sec.index('<div class="body') < sec.index('<div class="narration">')
    tiles = re.findall(r'<article class="narr-tile" data-at="(\d+)">\s*<p class="msg-agent">(.*?)</p>'
                       r'\s*<blockquote class="msg-text">(.*?)</blockquote>\s*</article>', narr.group(1), re.S)
    got = [(int(a), helper_strip(l), helper_strip(t)) for a, l, t in tiles]
    assert got == NARRATION
    for _, _, text in got:
        assert not re.search(r'^[“"]|[”"]$', text), "CSS adds quote marks"


def test_every_factual_element_has_a_cited_note_on_this_slide():
    sec = helper_section()
    notes = re.findall(r'<aside class="note" data-for="#([\w-]+)">(.*?)</aside>', sec, re.S)
    targets = {t for t, _ in notes}
    assert {"s7-hf", "s7-agents", "s7-secrets", "s7-cluster", "s7-more"} <= targets
    for target, body in notes:
        assert f'id="{target}"' in sec, target
        assert re.search(r'<a class="src" href="https://', body), target


def test_credential_reuse_lives_only_in_a_reader_note():
    """Presenter: credential-reuse detail is not salient at title/body level (VOICE, Nov 2026)."""
    sec = helper_section()
    notes = " ".join(re.findall(r'<aside class="note".*?</aside>', sec, re.S))
    rest = re.sub(r'<aside class="note".*?</aside>', "", sec, flags=re.S)
    assert "credentials left behind by earlier runs on Artifactory" in notes
    assert not re.search(r"credential|left behind", helper_strip(rest), re.I)


def test_only_confirmed_events_and_precise_wording():
    """S-024: the 19 Jul model differs from the HF agents'; the Aug 15 report is unconfirmed."""
    text = helper_strip(helper_section())
    for bad in (r"same agents", r"eval(uation)? cluster", r"Aug(ust)?\.? 15|15 Aug", r"suicide"):
        assert not re.search(bad, text, re.I), bad
    assert re.search(r"Astra-family", text)


def test_diagram_layers_band_and_single_key_tile():
    sec = helper_section()
    svg = re.search(r'<svg class="diagram"[^>]*>(.*?)</svg>', sec, re.S)
    assert svg, "slide carries a diagram"
    body = svg.group(1)
    key = re.findall(r'<g class="tile tile--key" id="([\w-]+)"', body)
    assert key == ["s7-cluster"]
    assert re.search(r'id="s7-band"', body), "the s-6 'OpenAI servers' band carries over"
    assert re.search(r"agents running on OpenAI’s servers", helper_strip(body), re.I)


@pytest.mark.parametrize("vw,vh", [(1920, 1080)])
def test_diagram_and_tiles_build_one_step_at_a_time(page, vw, vh):
    errors = open_deck(page, vw, vh)
    assert page.evaluate("([id]) => window.deck.plan().find(p => p[0] === id)[1]", [SID]) == 4
    seen_tiles: set[str] = set()
    seen_edges: set[tuple[str, str]] = set()
    for step in range(0, 5):
        goto_slide(page, SID, step)
        seen_tiles |= TILES_AT.get(step, set())
        seen_edges |= EDGES_AT.get(step, set())
        res = page.evaluate("""sid => {
          const s = document.getElementById(sid), op = e => +getComputedStyle(e).opacity;
          return {
            tiles: [...s.querySelectorAll('.diagram .tile')].filter(t => op(t) > 0.5).map(t => t.id),
            edges: [...s.querySelectorAll('.diagram .edge[data-from]')].filter(e => op(e) > 0.5)
                     .map(e => [e.dataset.from, e.dataset.to]),
            band: op(s.querySelector('#s7-band')),
            cut: [...s.querySelectorAll('.diagram .edge:not([data-from])')].map(op),
            current: [...s.querySelectorAll('.narr-tile')].filter(t => +t.dataset.at === %STEP%)
                       .map(t => t.textContent.replace(/\\s+/g, ' ').trim()),
          }; }""".replace("%STEP%", str(step)), SID)
        assert set(res["tiles"]) == seen_tiles, step
        assert {tuple(e) for e in res["edges"]} == seen_edges, step
        if step >= 1:
            assert res["band"] > 0.5, "band stays lit from step 1"
            assert res["cut"] and all(o > 0.5 for o in res["cut"]), "severed HF path shown"
            assert len(res["current"]) in (1, 2)
        else:
            assert res["band"] < 0.5 and not res["current"]
    assert errors == []
