"""Spec: S-004, S-005

Insight overlays and agent-message clusters: shown only at their step, content softens
beneath, hovered message prominent, rack-focus exit.
Coverage: happy (shown at step, every card sharp, hover pops one forward, single-card cluster) ·
edge (exit leaves blur before vanishing; Insight waits for a cluster's exit) · negative (not shown
before/after its step; hover softens siblings; notes button never covers an overlay).
"""

import pytest

from helper_deck import goto_slide, open_deck

V1_ONLY = pytest.mark.deck("v1")  # clusters are v1 legacy (S-005); v2 uses narration tiles

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


MULTI = """() => { const c = [...document.querySelectorAll('section.slide .cluster')]
  .find(x => x.querySelectorAll('.overlay--msg').length > 1);
  return c && [c.closest('section').id, +c.dataset.at]; }"""

CARDS = """id => [...document.querySelectorAll('#' + id + ' .cluster .overlay--msg')].map(c => {
  const cs = getComputedStyle(c), m = cs.filter.match(/blur\\(([\\d.]+)px\\)/);
  return { blur: m ? +m[1] : 0, opacity: +cs.opacity, z: +cs.zIndex }; })"""


@V1_ONLY
def test_cluster_cards_all_sharp_until_hover_pops_one_forward(page):
    """Presenter-directed (DESIGN §5): no auto-highlight; hover/focus brings one card forward."""
    open_deck(page)
    sid, at = page.evaluate(MULTI)
    page.mouse.move(5, 300)
    goto_slide(page, sid, at)
    page.wait_for_timeout(1000)
    cards = page.evaluate(CARDS, sid)
    assert all(c["blur"] == 0 and c["opacity"] > 0.95 for c in cards), cards
    page.hover(f"#{sid} .cluster .overlay--msg >> nth=1")
    page.wait_for_timeout(900)
    cards = page.evaluate(CARDS, sid)
    hovered, others = cards[1], cards[:1] + cards[2:]
    assert hovered["blur"] == 0
    assert all(o["blur"] > 0 for o in others), cards
    assert all(hovered["z"] > o["z"] for o in others), cards
    page.mouse.move(5, 300)
    page.wait_for_timeout(900)
    cards = page.evaluate(CARDS, sid)
    assert all(c["blur"] == 0 for c in cards), cards


@V1_ONLY
def test_single_card_cluster_shows_one_sharp_centred_message(page):
    open_deck(page)
    found = page.evaluate("""() => { const c = [...document.querySelectorAll('section.slide .cluster')]
      .find(x => x.querySelectorAll('.overlay--msg').length === 1);
      return c && [c.closest('section').id, +c.dataset.at]; }""")
    assert found, "a single agent message must use a one-card cluster"
    sid, at = found
    goto_slide(page, sid, at)
    page.wait_for_timeout(800)
    card = page.evaluate(CARDS, sid)[0]
    assert card["blur"] == 0 and card["opacity"] > 0.95
    off = page.evaluate(f"""() => {{ const c = document.querySelector('#{sid} .cluster .overlay--msg').getBoundingClientRect();
      const s = document.getElementById('{sid}').getBoundingClientRect();
      return Math.abs((c.left + c.right) / 2 - (s.left + s.right) / 2) / s.width; }}""")
    assert off < 0.05, "single card sits centred"


@V1_ONLY
def test_insight_entry_waits_for_a_cluster_exit(page):
    """Cluster → Insight on consecutive steps must not smear both half-blurred at once."""
    open_deck(page)
    found = page.evaluate("""() => { for (const c of document.querySelectorAll('section.slide .cluster')) {
      const i = c.closest('section').querySelector('.overlay--insight[data-at="' + (+c.dataset.at + 1) + '"]');
      if (i) return [c.closest('section').id, +c.dataset.at]; } return null; }""")
    sid, at = found
    goto_slide(page, sid, at)
    page.evaluate("() => window.deck.next()")
    page.wait_for_timeout(200)
    op = page.evaluate(f"() => +getComputedStyle(document.querySelector('#{sid} .overlay--insight')).opacity")
    assert op < 0.15, f"insight already {op:.2f} opaque while the cluster is still leaving"


def test_notes_button_never_overlaps_a_shown_overlay(page):
    open_deck(page, 1280, 720)
    for sid, at in page.evaluate("""() => [...document.querySelectorAll('section.slide .overlay--insight')]
        .map(o => [o.closest('section').id, +o.dataset.at])"""):
        goto_slide(page, sid, at)
        hit = page.evaluate(f"""() => {{ const b = document.querySelector('.notes-btn');
          if (+getComputedStyle(b).opacity < 0.05) return false;
          const r = b.getBoundingClientRect(), o = document.querySelector('#{sid} .overlay--insight').getBoundingClientRect();
          return !(r.right < o.left || r.left > o.right || r.bottom < o.top || r.top > o.bottom); }}""")
        assert not hit, f"{sid}: notes button over the Insight"


@V1_ONLY
def test_message_cards_carry_agent_label_and_quote():
    from helper_deck import slides_source
    import re
    cards = re.findall(r'<article class="overlay overlay--msg[^"]*"[^>]*>(.*?)</article>', slides_source(), re.S)
    assert cards
    for c in cards:
        assert 'class="msg-agent"' in c and "<blockquote" in c


@V1_ONLY
def test_cluster_not_shown_before_its_step(page):
    open_deck(page)
    sid, at = page.evaluate(FIND, ".cluster")
    goto_slide(page, sid, at - 1)
    assert not page.evaluate(f"() => document.querySelector('#{sid} .cluster').classList.contains('is-shown')")
