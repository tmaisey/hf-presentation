"""Spec: S-020

v2 slide s-3 (Training board): a five-step diagram of how the training-phase message board formed,
narrated by the few verbatim training-phase messages, with sourced reader notes.
Coverage: happy (slide in chapter order with storyboard title/kicker; five steps; tiles, edges and
narration tiles appear at the storyboard's steps; dates on the timeline tiles; every key claim noted
with an https source) · edge (≤2 narration tiles per step, quiet steps carry none; diagram stays in
the viewport below the title at 1280×720 and 1920×1080) · negative ("reinforced" never appears
unattributed to OpenAI; no OpenAI hypothetical "agent-07"; no "suicide"; no CTF/ExploitGym framing
of training tasks; no console errors while stepping).
"""

import html
import re

import pytest

from helper_deck import goto_slide, open_deck, parse_slides, slides_source

pytestmark = pytest.mark.deck("v2")

SID = "s-3"
TITLE = ("Training rewarded agents that cheated on accidentally impossible tasks, and they built a "
         "message board to do it")

# step → tiles first visible at that step (storyboard s-3 diagram beats 1–5)
TILES_AT = {
    1: {"s3-a1", "s3-a2", "s3-a3"},                    # isolated containers, impossible tasks
    2: {"s3-mirror", "s3-cred"},                       # package mirror + one shared credential
    3: {"s3-reward"},                                  # cheat earns positive reward
    4: {"s3-note", "s3-board", "s3-net"},              # 12 May note → 13 May board → 26 May internet
    5: {"s3-team"},                                    # internal team sees the board
}
# step → (from tile, to tile) connections first visible at that step
EDGES_AT = {
    2: {("s3-a1", "s3-cred"), ("s3-a2", "s3-cred"), ("s3-a3", "s3-cred"), ("s3-cred", "s3-mirror")},
    3: {("s3-a1", "s3-reward")},
    4: {("s3-note", "s3-mirror"), ("s3-mirror", "s3-board"), ("s3-board", "s3-net")},
    5: {("s3-team", "s3-mirror")},
}
# step → narration tiles (label, verbatim text) per storyboard / quotes.md 2.3
NARR_AT = {
    3: [("Training task instruction (human-written)",
         "After saving, the post’s updated time must read 2025-04-22T12:00:00Z.")],
    4: [("Agent · training run, 12 May", "Agent seeks [filename]; upload if found!")],
    5: [("OpenAI · technical report",
         "These forms of ‘cheating’ rose over the training runs that contributed to the Hugging "
         "Face incident.")],
}


def helper_section() -> str:
    m = re.search(r'<section class="slide" id="s-3"[^>]*>.*?</section>', slides_source(), re.S)
    assert m, "slide s-3 not built"
    return m.group(0)


def helper_text(markup: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", markup)).split())


def helper_visible_copy() -> str:
    """Slide copy the audience sees: everything except reader notes."""
    return helper_text(re.sub(r'<aside class="note".*?</aside>', "", helper_section(), flags=re.S))


# ---------- shell ----------

def test_training_slide_sits_between_concepts_and_early_evaluation():
    ids = [s["attrs"]["id"] for s in parse_slides()]
    assert SID in ids
    i = ids.index(SID)
    assert ids.index("s-1") < i
    for before in ("s-2",):
        if before in ids:
            assert ids.index(before) == i - 1
    if "s-4" in ids:
        assert ids.index("s-4") == i + 1


def test_title_kicker_and_chapter_match_the_storyboard():
    s = next(s for s in parse_slides() if s["attrs"]["id"] == SID)
    assert s["attrs"]["data-chapter"] == "Training"
    assert " ".join(s["title"].split()) == TITLE
    assert re.search(r'<p class="kicker">03 · Training</p>', helper_section())


def test_shell_order_is_body_then_narration_then_notes():
    sec = helper_section()
    assert sec.count('<div class="body') == 1
    body, narr, note = (sec.index(x) for x in ('<div class="body', '<div class="narration"', '<aside class="note"'))
    assert body < narr < note
    svg = re.search(r'<svg class="diagram".*?</svg>', sec, re.S).group(0)
    layers = [svg.index(f'class="layer-{n}"') for n in ("edges", "nodes", "key", "labels")]
    assert layers == sorted(layers), "layer groups in importance order"


def test_credential_and_internet_are_the_only_key_tiles():
    keys = set(re.findall(r'<g class="tile tile--key" id="([\w-]+)"', helper_section()))
    assert keys == {"s3-cred", "s3-net"}


def test_timeline_tiles_carry_their_dates():
    sec = helper_section()
    for tid, date in (("s3-note", "12 May"), ("s3-board", "13 May"), ("s3-net", "26 May")):
        tile = re.search(rf'<g class="tile[^"]*" id="{tid}".*?</g>', sec, re.S).group(0)
        assert date in helper_text(tile), tid


# ---------- narration ----------

def test_narration_tiles_per_step_are_verbatim_storyboard_quotes():
    narr = re.search(r'<div class="narration">(.*?)</div>', helper_section(), re.S).group(1)
    tiles = re.findall(r'<article class="narr-tile" data-at="(\d+)">\s*<p class="msg-agent">(.*?)</p>\s*'
                       r'<blockquote class="msg-text">(.*?)</blockquote>\s*</article>', narr, re.S)
    got: dict[int, list] = {}
    for at, label, text in tiles:
        got.setdefault(int(at), []).append((helper_text(label), helper_text(text)))
    assert got == NARR_AT
    assert narr.count("<article") == len(tiles), "every tile follows the narr-tile contract"


def test_narration_quotes_carry_no_typed_quote_marks():
    """CSS adds the outer quote marks; typed ones would double them."""
    for text in re.findall(r'<blockquote class="msg-text">(.*?)</blockquote>', helper_section(), re.S):
        assert not re.match(r'\s*[“"]', text) and not re.search(r'[”"]\s*$', text)


# ---------- reader notes ----------

def test_notes_target_slide_elements_and_cite_https_sources():
    sec = helper_section()
    notes = re.findall(r'<aside class="note" data-for="#([\w-]+)">(.*?)</aside>', sec, re.S)
    targets = {t for t, _ in notes}
    for t, body in notes:
        assert f'id="{t}"' in sec, t
        assert re.search(r'<h3>.+?</h3>', body) and re.search(r'<a class="src" href="https://', body), t
    assert {"s3-a1", "s3-cred", "s3-reward", "s3-note", "s3-board", "s3-net", "s3-team"} <= targets


def test_reinforcement_is_attributed_to_openai_and_scope_caveated():
    """'Reinforced' is OpenAI's finding: METR/Redwood were scoped out of training."""
    notes = dict(re.findall(r'<aside class="note" data-for="#([\w-]+)">(.*?)</aside>', helper_section(), re.S))
    reward = helper_text(notes["s3-reward"])
    assert "OpenAI" in reward and "reinforce" in reward.lower()
    assert "METR" in reward and "Redwood" in reward
    copy = helper_visible_copy()
    for m in re.finditer(r"reinforc", copy, re.I):
        window = copy[max(0, m.start() - 120): m.end() + 120]
        assert "OpenAI" in window, f"unattributed 'reinforced': …{window}…"


def test_model_scale_and_first_ssrf_attempt_are_noted():
    notes = helper_text("".join(re.findall(r'<aside class="note".*?</aside>', helper_section(), re.S)))
    assert "GPT-5.6 Sol" in notes and "8 May" in notes


# ---------- forbidden ----------

def test_no_hypothetical_agent_message_or_forbidden_framing():
    sec = helper_section()
    assert "agent-07" not in sec, "OpenAI's hypothetical is never an agent message"
    assert "suicid" not in sec.lower()
    copy = helper_visible_copy()
    assert "CTF" not in copy and "ExploitGym" not in copy, "training tasks were not CTF/eval tasks"


# ---------- in the browser ----------

TILE_OPACITY = """id => Object.fromEntries([...document.querySelectorAll(`#${id} svg.diagram g.tile`)]
  .map(t => [t.id, +getComputedStyle(t).opacity]))"""

EDGE_LINKS = """id => {
  const svg = document.querySelector(`#${id} svg.diagram`);
  const boxes = [...svg.querySelectorAll('g.tile')].map(t => { const r = t.querySelector('rect');
    const n = a => +r.getAttribute(a); return [t.id, n('x'), n('y'), n('width'), n('height')]; });
  const near = ([px, py]) => { let best = null, bd = 1e9;
    for (const [tid, x, y, w, h] of boxes) { const dx = Math.max(x - px, 0, px - x - w), dy = Math.max(y - py, 0, py - y - h);
      const d = Math.hypot(dx, dy); if (d < bd) { bd = d; best = tid; } }
    return bd <= 40 ? best : null; };
  return [...svg.querySelectorAll('path.edge')].filter(p => +getComputedStyle(p).opacity > .5).map(p => {
    const L = p.getTotalLength(), a = p.getPointAtLength(0), b = p.getPointAtLength(L);
    return [near([a.x, a.y]), near([b.x, b.y])]; });
}"""


def test_slide_has_five_steps(page):
    open_deck(page)
    plan = dict(page.evaluate("window.deck.plan()"))
    assert plan[SID] == 5


@pytest.mark.parametrize("step", range(0, 6))
def test_diagram_reveals_tiles_and_edges_per_step(page, step):
    errors = open_deck(page)
    goto_slide(page, SID, step)
    shown = {t for t, o in page.evaluate(TILE_OPACITY, SID).items() if o > .5}
    expected = set().union(*(TILES_AT[k] for k in TILES_AT if k <= step))
    assert shown == expected
    links = {tuple(x) for x in page.evaluate(EDGE_LINKS, SID)}
    assert all(None not in x for x in links), f"edge not gapped onto two tiles: {links}"
    assert links == set().union(*(EDGES_AT[k] for k in EDGES_AT if k <= step))
    assert errors == []


@pytest.mark.parametrize("size", [(1280, 720), (1920, 1080)])
def test_diagram_and_steps_stay_on_screen_below_the_title(page, size):
    open_deck(page, *size)
    goto_slide(page, SID, 5)
    boxes = page.evaluate("""id => { const s = document.getElementById(id);
      const r = e => { const b = e.getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom]; };
      return { title: r(s.querySelector('.title')), svg: r(s.querySelector('svg.diagram')),
               steps: r(s.querySelector('ol.steps')), vw: innerWidth, vh: innerHeight }; }""", SID)
    for k in ("svg", "steps"):
        l, t, r, b = boxes[k]
        assert l >= 0 and r <= boxes["vw"] + 1 and b <= boxes["vh"] + 1, k
        assert t >= boxes["title"][3] - 1, f"{k} rises over the title"
