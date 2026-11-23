"""Spec: S-017

Two decks, one suite: v2 is a new file on the shared architecture and v1 stays frozen.
Coverage: happy (--deck selects the file under test; v2 opens on the approved title slide; a jump
returns with the slide at rest) · edge (v2 shares v1's engine contract but is its own file; a jump
whose transitions outlast any fixed wait; the world's JS-tweened layout) · negative (v1 bytes never change).
"""

import hashlib
import os

import pytest

from helper_deck import DECK, DECK_FILES, goto_slide, open_deck, parse_slides

V1_SHA256 = "5fbe1007900382654573d8b8a669850ffaa7e89740f02146037411dece029466"  # v1 at S-016 close


def test_v1_deck_is_byte_unchanged():
    """v1 is frozen reference: any edit (even whitespace) is a regression."""
    assert hashlib.sha256(DECK_FILES["v1"].read_bytes()).hexdigest() == V1_SHA256


def test_suite_targets_the_selected_deck():
    assert DECK == DECK_FILES[os.environ["HF_DECK"]]


@pytest.mark.deck("v2")
def test_v2_is_its_own_file_on_the_shared_engine():
    v1, v2 = (DECK_FILES[k].read_text(encoding="utf-8") for k in ("v1", "v2"))
    assert v2 != v1
    assert "ADR: ADR-001" in v2 and "<!-- SLIDES:BEGIN -->" in v2
    engine = lambda s: s[s.index("<script>"):]  # noqa: E731
    assert "window.deck" in engine(v2)


@pytest.mark.deck("v2")
def test_v2_opens_on_the_approved_title_slide(page):
    first = parse_slides()[0]
    assert first["attrs"]["id"] == "s-1" and "data-ambient" in first["attrs"]
    assert first["title"].strip(), "approved title copy is S-034's (test_v2_title.py)"
    assert open_deck(page) == []


SLOW_STEPS = "[data-show-at], [data-hide-at] { transition-duration: 2.5s !important; transition-delay: 0s !important; }"
FINITE_BUSY = """sel => document.querySelector(sel).getAnimations({subtree: true})
  .filter(a => a.playState === 'running' && isFinite(a.effect.getComputedTiming().endTime)).length"""


@pytest.mark.deck("v2")
def test_jump_returns_at_rest_however_long_the_transitions_take(page):
    """A fixed wait flakes under parallel load; slowing the steps to 2.5 s makes that race certain."""
    open_deck(page)
    page.add_style_tag(content=SLOW_STEPS)
    goto_slide(page, "s-9", 1)
    assert page.evaluate("() => window.deck.state()")["step"] == 1
    assert page.evaluate(FINITE_BUSY, "#s-9") == 0, "transitions still running when the jump returned"
    assert page.evaluate("() => +getComputedStyle(document.getElementById('s9-t1')).opacity") == 1


WORLD_BOXES = """() => [...document.querySelectorAll('.world .cam, .world .mirror-group, #w-oai rect')]
  .map(e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height].map(Math.round).join(); })"""


@pytest.mark.deck("v2")
def test_jump_waits_for_the_worlds_layout_tween(page):
    """The world re-arranges by a JS tween (invisible to getAnimations): it must have stopped on return."""
    open_deck(page)
    goto_slide(page, "s-5", 0)
    goto_slide(page, "s-6", 0)
    # one in-page sample over 300 ms: a measurement of stillness, not a wait for a state
    before, after = page.evaluate(f"() => {{ const b = ({WORLD_BOXES})(); "
                                  f"return new Promise(r => setTimeout(() => r([b, ({WORLD_BOXES})()]), 300)); }}")
    assert before and after == before, "world still moving after the jump returned"
