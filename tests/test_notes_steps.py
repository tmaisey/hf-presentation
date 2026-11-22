"""Spec: S-029

v2 notes mode shows each note's slide at a step where the note's target is actually visible, so
notes on content a later step hides or swaps out (s-10 tables, stepped titles) still spotlight it.
Coverage: happy (every note on every slide spotlights a visible target) · edge (targets hidden at
the slide's last step, e.g. s-10's comparison table) · negative (no visible pin points at content
that isn't on screen at the current step).
"""

import pytest

from helper_deck import goto_slide, open_deck, settle_animations

pytestmark = pytest.mark.deck("v2")

# element (on the slide or in the shared incident world) and every ancestor: rendered, not hidden, opacity > .5
TARGET_VISIBLE = """sel => {
  let e = document.querySelector('.slide ' + sel) || document.querySelector('.world ' + sel); if (!e) return false;
  const r = e.getBoundingClientRect(); if (!r.width || !r.height) return false;
  for (; e && !e.matches('section.slide'); e = e.parentElement) {
    const cs = getComputedStyle(e);
    if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity < 0.5) return false; }
  return true; }"""

NOTES_UI = ".callout, .pin, .ring, .veil"   # the notes layer, not the slide's own timed beats
# a condition wait's patience, not a sleep: a world part fades in late (.25 s delay + .8 s) and a loaded machine stretches it
VISIBLE_TIMEOUT = 10000
NOTED_SLIDES = "() => [...document.querySelectorAll('section.slide')].filter(s => s.querySelector('.note')).map(s => s.id)"


def helper_note_targets(page, sid):
    return page.evaluate(
        "id => [...document.querySelectorAll('#' + id + ' aside.note')].map(n => n.dataset.for)", sid)


def test_every_note_spotlights_a_visible_target(page):
    open_deck(page)
    hidden = []
    for sid in page.evaluate(NOTED_SLIDES):
        goto_slide(page, sid)
        page.keyboard.press("n")
        for k, sel in enumerate(helper_note_targets(page, sid)):
            if k:
                page.keyboard.press("ArrowRight")
            try:
                page.wait_for_function(TARGET_VISIBLE, arg=sel, timeout=VISIBLE_TIMEOUT, polling=100)
            except Exception:
                hidden.append(f"{sid} note {k + 1} → {sel}")
        page.keyboard.press("Escape")
        settle_animations(page, NOTES_UI)
    assert hidden == [], "notes spotlight content that isn't on screen:\n" + "\n".join(hidden)


def test_s10_table_notes_show_the_table_not_the_last_step(page):
    """s-10's last step shows only the prompts; a note on the comparison table must bring it back."""
    open_deck(page)
    goto_slide(page, "s-10")
    page.keyboard.press("n")
    targets = helper_note_targets(page, "s-10")
    first_table = next(k for k, sel in enumerate(targets)
                       if page.evaluate("s => !!document.querySelector('#s-10 ' + s).closest('table')", sel))
    for _ in range(first_table):
        page.keyboard.press("ArrowRight")
    page.wait_for_function(TARGET_VISIBLE, arg=targets[first_table], timeout=VISIBLE_TIMEOUT, polling=100)


def test_no_visible_pin_points_at_offscreen_content(page):
    open_deck(page)
    goto_slide(page, "s-10")
    page.keyboard.press("n")
    settle_animations(page)
    bad = page.evaluate("""() => {
      const pins = [...document.querySelectorAll('.pin')];
      const notes = [...document.querySelectorAll('#s-10 aside.note')];
      return pins.map((p, j) => [p, document.querySelector('#s-10 ' + notes[j].dataset.for)])
        .filter(([p, t]) => { const cs = getComputedStyle(p);
          if (cs.visibility === 'hidden' || +cs.opacity < 0.05) return false;
          for (let e = t; e && !e.matches('section.slide'); e = e.parentElement) {
            const c = getComputedStyle(e); if (c.visibility === 'hidden' || +c.opacity < 0.5) return true; }
          return false; }).map(([p]) => p.textContent); }""")
    assert bad == [], f"pins shown for hidden targets: {bad}"
