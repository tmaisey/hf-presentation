"""Spec: S-004, S-005

Insight overlays and agent-message clusters: shown only at their step, content softens
beneath, key message prominent, rack-focus exit.
Coverage: happy (shown at step, key sharp) · edge (exit leaves blur before vanishing) ·
negative (not shown before/after its step; non-key cards are not sharp).
"""

from helper_deck import goto_slide, open_deck

FIND = """sel => { const o = document.querySelector('section.slide ' + sel);
  return o && [o.closest('section').id, +o.dataset.at]; }"""


def _blur(page, el_js):
    return page.evaluate(
        f"() => {{ const f = getComputedStyle({el_js}).filter; const m = f.match(/blur\\(([\\d.]+)px\\)/);"
        " return m ? +m[1] : 0; }")


def test_insight_shows_only_at_its_step_over_softened_content(page):
    open_deck(page)
    sid, at = page.evaluate(FIND, ".overlay--insight")
    goto_slide(page, sid, at - 1)
    assert not page.evaluate(f"() => document.querySelector('#{sid} .overlay--insight').classList.contains('is-shown')")
    goto_slide(page, sid, at)
    assert page.evaluate(f"() => document.querySelector('#{sid} .overlay--insight').classList.contains('is-shown')")
    assert page.evaluate(f"() => document.getElementById('{sid}').classList.contains('is-overlaid')")


def test_insight_rack_focus_exit_blurs_before_vanishing(page):
    open_deck(page)
    sid, at = page.evaluate(FIND, ".overlay--insight")
    goto_slide(page, sid, at)
    page.evaluate("() => window.deck.prev()")
    page.wait_for_timeout(300)
    mid = _blur(page, f"document.querySelector('#{sid} .overlay--insight')")
    assert mid > 1, "overlay should be visibly defocusing mid-exit"


def test_message_cluster_key_rises_sharp_others_soften(page):
    open_deck(page)
    sid, at = page.evaluate(FIND, ".cluster")
    goto_slide(page, sid, at)
    page.wait_for_timeout(1500)
    key_blur = _blur(page, f"document.querySelector('#{sid} .cluster .overlay--msg[data-key]')")
    other_blur = _blur(page, f"document.querySelector('#{sid} .cluster .overlay--msg:not([data-key])')")
    assert key_blur == 0
    assert other_blur > 0
    z_key = page.evaluate(f"() => +getComputedStyle(document.querySelector('#{sid} .cluster [data-key]')).zIndex")
    z_other = page.evaluate(f"() => +getComputedStyle(document.querySelector('#{sid} .cluster .overlay--msg:not([data-key])')).zIndex")
    assert z_key > z_other


def test_message_cards_carry_agent_label_and_quote():
    from helper_deck import slides_source
    import re
    cards = re.findall(r'<article class="overlay overlay--msg[^"]*"[^>]*>(.*?)</article>', slides_source(), re.S)
    assert cards
    for c in cards:
        assert 'class="msg-agent"' in c and "<blockquote" in c


def test_cluster_not_shown_before_its_step(page):
    open_deck(page)
    sid, at = page.evaluate(FIND, ".cluster")
    goto_slide(page, sid, at - 1)
    assert not page.evaluate(f"() => document.querySelector('#{sid} .cluster').classList.contains('is-shown')")
