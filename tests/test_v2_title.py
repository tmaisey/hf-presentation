"""Spec: S-034

v2 title slide (s-1): the approved title and subtitle (storyboard s-1, VOICE) over the ambient
background, with the byline "Tom Maisey, November 2026" and the sourced reader note on the subtitle.
Coverage: happy (title, subtitle and byline verbatim; ambient; note cites METR) · edge (title,
subtitle and bottom-left byline fit whole inside the slide, below the bar and apart from each other
at 1920×1080, 1280×720 and 1288×598) · negative (no kicker, no diagram, no build steps, the
replaced title and subtitle are gone).
"""

import re

import pytest

from helper_deck import open_deck, parse_slides, settle_animations, slides_source

pytestmark = pytest.mark.deck("v2")

SID = "s-1"
TITLE = "OpenAI breaching Hugging Face was a public example of AI misalignment"
SUB = "Flawed AI capability development methods led to autonomous cyber-attacks during routine testing"
OLD = ["OpenAI’s agent swarm breached Hugging Face", "What happened, why, and what it means for AI safety"]


def _section_src():
    m = re.search(r'<section[^>]*id="s-1".*?</section>', slides_source(), re.S)
    assert m, "s-1 missing"
    return m.group(0)


def _text(s):
    return " ".join(re.sub(r"<[^>]+>", "", s).split())


def test_title_slide_opens_the_deck_with_the_approved_copy():
    first = parse_slides()[0]
    assert first["attrs"]["id"] == SID and "data-ambient" in first["attrs"]
    assert _text(first["title"]) == TITLE
    src = _section_src()
    assert _text(re.search(r'<p id="s1-sub">(.*?)</p>', src, re.S).group(1)) == SUB
    assert 'class="kicker"' not in src, "no super-title (presenter, 22 Nov)"
    assert _text(re.search(r'<p class="byline">(.*?)</p>', src, re.S).group(1)) == "Tom Maisey, November 2026"


def test_reader_note_on_the_subtitle_cites_the_investigation():
    note = re.search(r'<aside class="note" data-for="#s1-sub">(.*?)</aside>', _section_src(), re.S)
    assert note and 'class="src" href="https://metr.org/' in note.group(1)


def test_replaced_copy_and_diagram_are_absent():
    src = _section_src()
    assert not any(o in src for o in OLD)
    assert "<svg" not in src and "data-show-at" not in src and "data-at" not in src


@pytest.mark.parametrize("vw,vh", [(1920, 1080), (1280, 720), (1288, 598)])
def test_title_and_subtitle_fit_below_the_bar(page, vw, vh):
    assert open_deck(page, vw, vh) == []
    page.evaluate("() => window.deck.goto('s-1', 0)")
    settle_animations(page, "#s-1, .bar")
    r = page.evaluate("""() => {
      const s = document.getElementById('s-1'), box = e => e.getBoundingClientRect();
      const u0 = s.querySelector('#s1-sub'), t = box(s.querySelector('.title')), u = box(u0), b = box(s.querySelector('.byline'));
      const bar = box(document.querySelector('.bar'));
      return { t: [t.top, t.bottom, t.left, t.right], u: [u.top, u.bottom, u.left, u.right], b: [b.top, b.bottom, b.left, b.right], by: (cs => [cs.fontStyle, cs.fontFamily, cs.filter, parseFloat(cs.fontSize), parseFloat(getComputedStyle(u0).fontSize)])(getComputedStyle(s.querySelector('.byline'))),
               bar: bar.bottom, vw: innerWidth, vh: innerHeight }; }""")
    (tt, tb, tl, tr), (ut, ub, ul, ur) = r["t"], r["u"]
    assert tt >= r["bar"], "title below the bar"
    assert tb <= ut, "subtitle below the title"
    assert ub <= r["vh"] and min(tl, ul) >= 0 and max(tr, ur) <= r["vw"]
    bt, bb, bl, br = r["b"]
    assert bt >= ub and bb <= r["vh"] and bl >= 0, "byline below the subtitle, on screen"
    assert bl < r["vw"] / 3 and bt > r["vh"] * .6, "byline sits bottom-left"
    style, family, filt, size, sub = r["by"]
    assert style == "italic" and "Newsreader" in family and filt in ("none", ""), "italic serif, soft but sharp"
    assert size < sub, "smallish: below the subtitle size"
