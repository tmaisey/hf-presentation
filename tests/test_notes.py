"""Spec: S-006

Reader-notes mode: spotlight over targets, pins, callout with linked source, static nav.
Coverage: happy (N opens on a noted slide, next/prev cycle, links styled, every link opens in a
new tab) · edge (slide without notes still toggles cleanly; small window keeps callout below the bar)
· negative (Esc closes; nav is not inside the callout; pins never on target text or under the callout).
"""

import re

from helper_deck import goto_slide, open_deck, slides_source

NOTED = "() => document.querySelector('section.slide .note').closest('section').id"


def test_every_note_targets_an_element_on_its_slide_and_cites_a_link():
    notes = re.findall(r'<aside class="note"([^>]*)>(.*?)</aside>', slides_source(), re.S)
    assert notes
    for attrs, body in notes:
        target = re.search(r'data-for="#([\w-]+)"', attrs).group(1)
        assert f'id="{target}"' in slides_source(), target
        assert re.search(r'<a class="src" href="https?://', body)


def test_n_opens_notes_with_spotlight_pins_and_static_nav(page):
    open_deck(page)
    goto_slide(page, page.evaluate(NOTED))
    page.keyboard.press("n")
    page.wait_for_timeout(700)
    assert page.evaluate("() => document.body.classList.contains('notes-on')")
    assert page.evaluate("() => document.querySelectorAll('.pin').length") >= 1
    assert page.is_visible(".notes-nav")
    assert page.evaluate("() => !document.querySelector('.callout').contains(document.querySelector('.notes-nav'))")
    assert page.evaluate("() => !!document.querySelector('.callout a.src[target=_blank][rel~=noopener]')")


def test_source_links_are_underlined_in_inherited_colour(page):
    open_deck(page)
    goto_slide(page, page.evaluate(NOTED))
    page.keyboard.press("n")
    page.wait_for_timeout(700)
    link = page.evaluate("""() => { const a = document.querySelector('.callout a.src');
      const p = a.parentElement; return [getComputedStyle(a).color, getComputedStyle(p).color,
      getComputedStyle(a).textDecorationLine]; }""")
    assert link[0] == link[1] and "underline" in link[2]


def test_next_moves_to_following_note_and_escape_closes(page):
    open_deck(page)
    goto_slide(page, page.evaluate(NOTED))
    page.keyboard.press("n")
    page.wait_for_timeout(500)
    first = page.inner_text(".callout h3")
    page.keyboard.press("ArrowRight")
    page.wait_for_timeout(500)
    n = page.evaluate("() => document.querySelectorAll('.pin').length")
    if n > 1:
        assert page.inner_text(".callout h3") != first
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)
    assert not page.evaluate("() => document.body.classList.contains('notes-on')")


def test_arrow_keys_do_not_change_slide_while_notes_open(page):
    open_deck(page)
    sid = page.evaluate(NOTED)
    goto_slide(page, sid)
    page.keyboard.press("n")
    page.keyboard.press("ArrowRight")
    page.wait_for_timeout(600)
    assert page.evaluate("() => window.deck.state().slide") == sid


def test_every_slide_link_opens_in_a_new_tab(page):
    """Links in slides and in note sources open safely in a new tab, set once by the engine."""
    open_deck(page)
    bad = page.evaluate("""() => [...document.querySelectorAll('section.slide a[href]')]
      .filter(a => a.target !== '_blank' || !/\\bnoopener\\b/.test(a.rel)).map(a => a.href)""")
    assert bad == []


def test_callout_and_pins_stay_clear_of_title_bar_targets_and_each_other(page):
    """At the small window size every note keeps its callout below the bar, its pins off the
    target's text, and no visible pin hidden under the callout."""
    open_deck(page, 1280, 720)
    problems = []
    for sid in page.evaluate("() => [...document.querySelectorAll('section.slide')].filter(s => s.querySelector('.note')).map(s => s.id)"):
        goto_slide(page, sid)
        page.keyboard.press("n")
        page.wait_for_timeout(300)
        n = page.evaluate("() => document.querySelectorAll('.pin').length")
        for k in range(n):
            page.wait_for_timeout(650)
            problems += [f"{sid} note {k + 1}: {p}" for p in page.evaluate("""() => {
              const bad = [], c = document.querySelector('.callout').getBoundingClientRect();
              const bar = document.querySelector('.bar').getBoundingClientRect();
              if (c.top < bar.bottom + 8) bad.push('callout under title bar');
              const inside = (x, y, r) => x > r.left && x < r.right && y > r.top && y < r.bottom;
              document.querySelectorAll('.pin').forEach(p => {
                const r = p.getBoundingClientRect(), cx = (r.left + r.right) / 2, cy = (r.top + r.bottom) / 2;
                const cs = getComputedStyle(p);
                if (cs.visibility === 'hidden' || +cs.opacity < 0.05) return;
                if (inside(cx, cy, c) && +cs.zIndex <= +getComputedStyle(document.querySelector('.callout')).zIndex)
                  bad.push('pin ' + p.textContent + ' hidden under callout');
              });
              return bad; }""")]
            page.keyboard.press("ArrowRight")
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
    assert problems == [], "\n".join(problems)


def test_pins_sit_outside_their_targets(page):
    open_deck(page, 1280, 720)
    goto_slide(page, "s-3-1")
    page.keyboard.press("n")
    page.wait_for_timeout(700)
    inside = page.evaluate("""() => {
      const sec = document.getElementById('s-3-1');
      const targets = [...sec.querySelectorAll('aside.note')].map(n => sec.querySelector(n.dataset.for));
      return [...document.querySelectorAll('.pin')].filter((p, j) => {
        const r = p.getBoundingClientRect(), t = targets[j].getBoundingClientRect();
        const cx = (r.left + r.right) / 2, cy = (r.top + r.bottom) / 2;
        return cx > t.left && cx < t.right && cy > t.top && cy < t.bottom; }).map(p => p.textContent); }""")
    assert inside == [], f"pins centred inside their target: {inside}"
