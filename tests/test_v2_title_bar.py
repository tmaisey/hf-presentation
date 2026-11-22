"""Spec: S-031

v2 title bar: Title-Case title with an italic subtitle; an agenda that labels every chapter
(current in green, no dot markers) with a hover lift that softens the rest; and a compact form
that collapses to the current chapter and drops down a vertical list when the row won't fit.
Coverage: happy (title text, all labels at 1920, hover lift, compact list opens and navigates)
· edge (1288×598 and 1280×720 keep the full row; keyboard focus opens the compact list)
· negative (no dot markers; title and nav never overlap; compact list closed until asked for,
closes on outside click; slide content never shows through the open list).
"""

import pytest

from helper_deck import goto_slide, open_deck, settle_animations, state

pytestmark = pytest.mark.deck("v2")

CHAPTERS = "() => [...document.querySelectorAll('section.slide')].map(s => s.dataset.chapter)" \
           ".filter((c, i, a) => a.indexOf(c) === i)"
VISIBLE_LABELS = """() => [...document.querySelectorAll('.agenda li')].filter(li => {
  const b = li.querySelector('button'), r = b.getBoundingClientRect(), cs = getComputedStyle(b);
  return r.width > 0 && r.height > 0 && getComputedStyle(li.closest('ol')).visibility !== 'hidden'
    && r.right <= innerWidth && r.bottom <= innerHeight;
}).map(li => li.innerText.trim())"""
GAP = """() => {
  const t = document.querySelector('.bar-title').getBoundingClientRect();
  const navEls = [...document.querySelectorAll('.bar button')].filter(b => {
    const r = b.getBoundingClientRect();
    return r.width > 0 && r.top < t.bottom && getComputedStyle(b.closest('ol, nav, header')).visibility !== 'hidden';
  });
  return Math.min(...navEls.map(b => b.getBoundingClientRect().left)) - t.right;
}"""
ACCENT_INK = "rgb(75, 110, 16)"


def _current_slide_of_chapter(page, k):
    return page.evaluate(f"""() => {{ const ch = ({CHAPTERS})()[{k}];
      return [...document.querySelectorAll('section.slide')].find(s => s.dataset.chapter === ch).id; }}""")


def test_bar_title_reads_hugging_face_attack_with_italic_subtitle(page):
    open_deck(page)
    text = page.evaluate("() => document.querySelector('.bar-title').innerText.replace(/\\s+/g, ' ').trim()")
    assert " · ".join(p.strip() for p in text.split("·")) == "The Hugging Face Attack · Misaligned Agents"
    sub = page.evaluate("""() => [...document.querySelectorAll('.bar-title *')]
      .filter(e => e.innerText.trim() === 'Misaligned Agents').map(e => getComputedStyle(e).fontStyle)""")
    assert sub == ["italic"]
    assert page.title() == "The Hugging Face Attack · Misaligned Agents"


@pytest.mark.parametrize("w,h", [(1920, 1080), (1288, 598), (1280, 720)])
def test_full_agenda_labels_every_chapter_clear_of_title(page, w, h):
    open_deck(page, w, h)
    settle_animations(page, ".bar")
    assert page.evaluate(VISIBLE_LABELS) == page.evaluate(CHAPTERS)
    assert page.evaluate(GAP) >= 24


def test_current_chapter_label_is_green_and_others_are_not(page):
    open_deck(page)
    goto_slide(page, _current_slide_of_chapter(page, 2), 0)
    colours = page.evaluate("() => [...document.querySelectorAll('.agenda li button')].map(b => getComputedStyle(b).color)")
    assert colours[2] == ACCENT_INK
    assert all(c != ACCENT_INK for i, c in enumerate(colours) if i != 2)


def test_agenda_has_no_dot_markers(page):
    """v1's dots are gone: no chapter item draws a marker beside its label."""
    open_deck(page)
    markers = page.evaluate("""() => [...document.querySelectorAll('.agenda li, .agenda li button')]
      .flatMap(e => ['::before', '::after'].map(p => getComputedStyle(e, p)))
      .filter(cs => cs.content !== 'none' && cs.content !== 'normal'
                    && parseFloat(cs.width) > 0 && parseFloat(cs.height) > 0).length""")
    assert markers == 0


def test_hover_lifts_one_chapter_and_softens_the_rest_readably(page):
    open_deck(page)
    page.hover(".agenda li:nth-child(5) button")
    settle_animations(page, ".bar")
    looks = page.evaluate("""() => [...document.querySelectorAll('.agenda li button')].map(b => {
      const cs = getComputedStyle(b);
      return {scale: new DOMMatrix(cs.transform).a, op: +cs.opacity, blur: cs.filter.includes('blur')}; })""")
    hovered, others = looks[4], looks[:4] + looks[5:]
    assert hovered["scale"] > 1 and not hovered["blur"]
    assert all(o["blur"] and 0.6 <= o["op"] < 1 for o in others)


@pytest.mark.parametrize("w,h", [(1100, 700), (900, 600)])
def test_narrow_bar_shows_only_current_chapter_clear_of_title(page, w, h):
    open_deck(page, w, h)
    goto_slide(page, _current_slide_of_chapter(page, 2), 0)
    current = page.evaluate(CHAPTERS)[2]
    assert page.evaluate(VISIBLE_LABELS) == []
    shown = page.evaluate("""() => [...document.querySelectorAll('.bar button')].filter(b => {
      const r = b.getBoundingClientRect(); return r.width > 0 && r.top < 64
        && getComputedStyle(b.closest('ol, nav, header')).visibility !== 'hidden'; })
      .map(b => ({text: b.innerText.trim(), color: getComputedStyle(b).color}))""")
    assert shown == [{"text": current, "color": ACCENT_INK}]
    assert page.evaluate(GAP) >= 24


def test_compact_hover_drops_vertical_list_that_navigates(page):
    open_deck(page, 1100, 700)
    chapters = page.evaluate(CHAPTERS)
    page.hover(f".bar button:has-text('{chapters[0]}')")
    settle_animations(page, ".bar")
    assert page.evaluate(VISIBLE_LABELS) == chapters
    tops = page.evaluate("() => [...document.querySelectorAll('.agenda li')].map(li => li.getBoundingClientRect().top)")
    assert tops == sorted(tops) and len(set(round(t) for t in tops)) == len(tops)
    colours = page.evaluate("() => [...document.querySelectorAll('.agenda li button')].map(b => getComputedStyle(b).color)")
    assert colours[0] == ACCENT_INK
    page.click(f".agenda li:nth-child(6) button")
    settle_animations(page, ".bar")
    target = _current_slide_of_chapter(page, 5)
    assert state(page)["slide"] == target


def test_compact_list_opens_on_keyboard_focus(page):
    open_deck(page, 1100, 700)
    page.keyboard.press("Tab")
    for _ in range(4):
        if page.evaluate("() => document.activeElement.closest('.bar') !== null"):
            break
        page.keyboard.press("Tab")
    settle_animations(page, ".bar")
    assert page.evaluate(VISIBLE_LABELS) == page.evaluate(CHAPTERS)


def test_compact_list_stays_closed_until_asked_and_closes_on_outside_click(page):
    open_deck(page, 1100, 700)
    page.mouse.move(500, 400)
    settle_animations(page, ".bar")
    assert page.evaluate(VISIBLE_LABELS) == []
    chapters = page.evaluate(CHAPTERS)
    page.click(f".bar button:has-text('{chapters[0]}')")
    page.mouse.move(1090, 690)
    settle_animations(page, ".bar")
    assert page.evaluate(VISIBLE_LABELS) == chapters
    page.mouse.click(500, 650)
    settle_animations(page, ".bar")
    assert page.evaluate(VISIBLE_LABELS) == []


def test_open_compact_list_hides_slide_content_beneath(page):
    """The list overlaps slide content (e.g. narration tiles); a translucent panel let their text
    bleed through, because the frosted bar stops a nested backdrop blur from applying."""
    open_deck(page, 1100, 700)
    page.click(".nav-current")
    settle_animations(page, ".bar")
    alpha = page.evaluate("""() => { const c = getComputedStyle(document.querySelector('.agenda')).backgroundColor;
      const m = c.match(/[\\d.]+/g).map(Number); return m.length > 3 ? m[3] : 1; }""")
    assert alpha == 1
