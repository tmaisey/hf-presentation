"""Spec: S-021

v2 slide s-4 (Early evaluation): the package mirror under load with a dated timeline beneath,
built in five steps from the first ExploitGym runs to the rebuild that wiped the board.
Coverage: happy (slide in storyboard order, shell copy, five steps, what each step reveals,
narration tiles at steps 2 and 5, cited notes on the dated events) · edge (board tile dissolves
exactly when the wipe tile appears; METR paraphrase shown in braces and labelled; tile text stays
inside its tile at 1280×720 and 1920×1080) · negative (no "deleted"/deliberate-deletion claim, no
wipe placed in training, no forbidden words, no console errors, no style/script in the slide).
"""

import re

import pytest

from helper_deck import goto_slide, open_deck, parse_slides, slides_source

pytestmark = pytest.mark.deck("v2")

SID = "s-4"
TITLE = "Early warning signals were handled as routine operational incidents"
ORDER = [f"s-{n}" for n in range(1, 11)]

# element id -> (first step visible, first step hidden or None)
DIAGRAM = {
    "s4-mirror": (0, None),
    "s4-agents": (1, None),
    "s4-board": (2, 5),
    "s4-zero": (2, None),
    "s4-alert": (3, None),
    "s4-crash": (4, None),
    "s4-rebuild": (5, None),
    "s4-wipe": (5, None),
}
TIMELINE = [("s4-zero", "26 JUN"), ("s4-alert", "27 JUN"), ("s4-crash", "4 JUL"), ("s4-rebuild", "5–6 JUL")]

PARAPHRASE = ("{Agents doing different tasks are abusing properties to make a bulletin board! "
              "They found [this api] and are trying to help one another}")


def _slide_html() -> str:
    m = re.search(r'<section class="slide" id="s-4".*?</section>', slides_source(), re.S)
    assert m, "s-4 slide missing"
    return m.group(0)


def _text(html: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def test_slide_sits_in_storyboard_order():
    ids = [s["attrs"]["id"] for s in parse_slides()]
    assert SID in ids
    present = [i for i in ORDER if i in ids]
    assert ids.index(SID) == present.index(SID) and [i for i in ids if i in ORDER] == present


def test_shell_has_chapter_kicker_and_storyboard_title():
    s = next(s for s in parse_slides() if s["attrs"]["id"] == SID)
    assert s["attrs"]["data-chapter"] == "Early evaluation"
    assert " ".join(s["title"].split()) == TITLE
    html = _slide_html()
    assert re.search(r'<p class="kicker">04 · Early evaluation</p>', html)
    assert len(re.findall(r'<div class="body[ "]', html)) == 1
    assert html.index('class="body') < html.index('class="narration"'), "narration follows the body"
    assert "<style" not in html and "<script" not in html and not re.search(r"\sstyle\s*=", html)


def test_slide_has_five_build_steps(page):
    open_deck(page)
    assert dict(page.evaluate("() => window.deck.plan()"))[SID] == 5


def test_each_step_reveals_its_diagram_state(page):
    """Mirror first, agents reach it, then one dated timeline event per step; board gives way to the wipe."""
    assert open_deck(page) == []
    for k in range(6):
        goto_slide(page, SID, k)
        shown = page.evaluate("""ids => Object.fromEntries(ids.map(id => {
          const e = document.getElementById(id); return [id, e ? +getComputedStyle(e).opacity : -1]; }))""",
                              list(DIAGRAM))
        for el, (on, off) in DIAGRAM.items():
            want = k >= on and (off is None or k < off)
            assert shown[el] >= 0, f"#{el} missing"
            assert (shown[el] > 0.9) == want, f"step {k}: #{el} opacity {shown[el]}"


def test_timeline_tiles_carry_their_dates_in_order():
    html = _slide_html()
    xs = []
    for tid, date in TIMELINE:
        tile = re.search(rf'<g class="tile[^"]*" id="{tid}"[^>]*>\s*<rect x="([\d.]+)"', html)
        assert tile, tid
        xs.append(float(tile.group(1)))
        assert re.search(rf'<text class="label"[^>]*>{date}</text>', html), date
    assert xs == sorted(xs), "timeline runs left to right"


def test_wipe_is_the_key_tile_and_says_unrecognised():
    html = _slide_html()
    wipe = re.search(r'<g class="tile tile--key" id="s4-wipe"[^>]*>(.*?)</g>', html, re.S)
    assert wipe, "wipe is a key tile"
    assert "wiped without being recognised" in _text(wipe.group(1)).lower()
    layer_key = re.search(r'<g class="layer-key">(.*?)</g>\s*<g class="layer-labels">', html, re.S)
    assert layer_key and 'id="s4-wipe"' in layer_key.group(1)


def test_narration_tiles_at_steps_two_and_five():
    html = _slide_html()
    narr = re.search(r'<div class="narration">(.*?)</div>', html, re.S)
    assert narr
    tiles = re.findall(r'<article class="narr-tile" data-at="(\d+)">\s*<p class="msg-agent">(.*?)</p>\s*'
                       r'<blockquote class="msg-text">(.*?)</blockquote>\s*</article>', narr.group(1), re.S)
    assert [int(a) for a, _, _ in tiles] == [2, 5]
    (_, lab2, q2), (_, lab5, q5) = tiles
    assert "ExploitGym run, 26 Jun" in lab2 and "paraphrased by METR" in lab2
    assert " ".join(q2.split()) == PARAPHRASE, "paraphrase verbatim, braces shown"
    assert lab5.strip() == "OpenAI"
    q5 = " ".join(q5.split())
    assert q5.startswith("The existence of the improvised message board") and "not apparent to leaders" in q5
    for q in (q2, q5):
        assert not re.search(r"^[\"“]|[\"”]$", q.strip()), "no quote marks: CSS adds them"


def test_notes_cite_each_dated_event_with_https_sources():
    html = _slide_html()
    notes = re.findall(r'<aside class="note" data-for="#([\w-]+)">(.*?)</aside>', html, re.S)
    assert len(notes) >= 4
    for target, body in notes:
        assert f'id="{target}"' in html, f"note target #{target} on this slide"
        assert DIAGRAM.get(target, (0, None))[1] is None, f"#{target} is hidden at the last step"
        assert re.search(r"<h3>[^<]+</h3>", body) and re.search(r'<a class="src" href="https://', body)
    alltext = _text(" ".join(b for _, b in notes))
    for date in ("26 June", "27 June", "4 July", "5–6 July"):
        assert date in alltext, date
    assert "no message board activity" in alltext, "METR's observation gap is disclosed"


def test_copy_never_claims_deliberate_deletion_or_a_training_wipe():
    text = _text(_slide_html()).lower()
    assert "suicide" not in text
    assert not re.search(r"\bdelet", text), "the board was wiped by a rebuild, not deleted"
    assert "deliberate" not in text or "not deliberate" in text
    assert not re.search(r"wiped (in|during) training", text)


@pytest.mark.parametrize("vw,vh", [(1920, 1080), (1280, 720)])
def test_tile_text_stays_inside_tiles_and_slide(page, vw, vh):
    assert open_deck(page, vw, vh) == []
    goto_slide(page, SID, 5)
    bad = page.evaluate("""() => {
      const s = document.getElementById('s-4'), sr = s.getBoundingClientRect(), out = [];
      s.querySelectorAll('.tile').forEach(t => {
        const r = t.querySelector('rect').getBoundingClientRect();
        t.querySelectorAll('text').forEach(x => { const b = x.getBoundingClientRect();
          if (b.left < r.left - 1 || b.right > r.right + 1 || b.top < r.top - 1 || b.bottom > r.bottom + 1)
            out.push(t.id + ': ' + x.textContent); });
      });
      s.querySelectorAll('.diagram text').forEach(x => { const b = x.getBoundingClientRect();
        if (b.width && (b.left < sr.left || b.right > sr.right || b.bottom > sr.bottom)) out.push('off-slide ' + x.textContent); });
      const t = s.querySelector('.title').getBoundingClientRect(), d = s.querySelector('.diagram').getBoundingClientRect();
      if (d.top < t.bottom - 1) out.push('diagram over title');
      return out; }""")
    assert bad == []
