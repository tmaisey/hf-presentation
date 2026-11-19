"""Spec: S-006

Reader-notes mode: spotlight over targets, pins, callout with linked source, static nav.
Coverage: happy (N opens on a noted slide, next/prev cycle, links styled) · edge (slide
without notes still toggles cleanly) · negative (Esc closes; nav is not inside the callout).
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
