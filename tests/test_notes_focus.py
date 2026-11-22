"""Spec: S-029

v2 notes mode lands every note fully drawn and keeps the focus frame clear: moving to a note sets
its slide to the target's step with every transition, animation and timed sequence already at its
end state, and no other note's pin sits on the current focus frame (spotlight window + ring).
Coverage: happy (every note on every slide, at a large and a short-wide viewport) · edge (opening
notes mid-slide, world targets, pop-over targets) · negative (no animation still running on arrival;
leaving notes mode restores normal motion).
"""

import pytest

from helper_deck import goto_slide, open_deck

pytestmark = pytest.mark.deck("v2")

NOTED_SLIDES = "() => [...document.querySelectorAll('section.slide')].filter(s => s.querySelector('.note')).map(s => s.id)"

# the focused note's target: the current pin's number indexes the slide's notes that have a target
FOCUSED = """const s = document.querySelector('section.slide.is-active'), world = document.querySelector('.world');
  const find = sel => s.querySelector(sel) || (world && world.querySelector(sel));
  const cur = document.querySelector('.pin.is-current');
  const noted = [...s.querySelectorAll('aside.note')].filter(n => find(n.dataset.for));
  const t = cur && find(noted[+cur.textContent - 1].dataset.for);
  const label = s.id + ' note ' + (cur ? cur.textContent : '?') + ' (' + (cur ? noted[+cur.textContent - 1].dataset.for : '') + ')';"""

# press a key, then (in the same task, no waiting) report anything not yet at its end state
ARRIVE = """key => {
  dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true }));
  """ + FOCUSED + """
  if (!t) return [label + ': no focused target'];
  const bad = [];
  const inScope = e => e && (t.contains(e) || e.contains(t) || (world && world.contains(e)));
  document.getAnimations().forEach(a => {
    const e = a.effect && a.effect.target;
    if (!inScope(e) || e.closest('.bokeh') || !['running', 'pending', 'paused'].includes(a.playState)) return;
    const what = a.animationName || a.transitionProperty || 'script animation';
    bad.push(label + ': ' + what + ' still running on ' + e.tagName.toLowerCase() + '.' + (e.getAttribute('class') || '') + (e.id ? '#' + e.id : ''));
  });
  for (let e = t; e && !e.matches('section.slide, .world'); e = e.parentElement) {
    const cs = getComputedStyle(e);
    if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity < 0.5)
      bad.push(label + ': target not drawn on arrival (' + e.tagName.toLowerCase() + ' opacity ' + cs.opacity + ')');
  }
  return bad; }"""

# every shown non-current pin's box against the current focus frame (the ring around the spotlight window)
PIN_CLASH = """() => {
  """ + FOCUSED + """
  const f = document.querySelector('.ring').getBoundingClientRect(), bad = [];
  document.querySelectorAll('.pin:not(.is-current)').forEach(p => {
    if (getComputedStyle(p).visibility === 'hidden') return;
    const r = p.getBoundingClientRect();
    if (r.right > f.left && r.left < f.right && r.bottom > f.top && r.top < f.bottom)
      bad.push(label + ': pin ' + p.textContent + ' sits on the focus frame');
  });
  return bad; }"""


def helper_note_count(page, sid):
    return page.evaluate("id => document.querySelectorAll('#' + id + ' aside.note').length", sid)


def test_every_note_arrives_fully_drawn(page):
    """No waiting after the key press: the target and the world must already be at their end state."""
    open_deck(page)
    bad = []
    for sid in page.evaluate(NOTED_SLIDES):
        goto_slide(page, sid)
        for k in range(helper_note_count(page, sid)):
            bad += page.evaluate(ARRIVE, "n" if k == 0 else "ArrowRight")
        page.keyboard.press("Escape")
    assert bad == [], "notes land before their target is drawn:\n" + "\n".join(bad)


def test_stepping_back_through_notes_also_arrives_fully_drawn(page):
    """Going back can move the slide to an earlier step (e.g. s-5's pop-over, s-10's swapped panels)."""
    open_deck(page)
    bad = []
    for sid in page.evaluate(NOTED_SLIDES):
        goto_slide(page, sid)
        bad += page.evaluate(ARRIVE, "n")
        for _ in range(helper_note_count(page, sid) - 1):
            bad += page.evaluate(ARRIVE, "ArrowLeft")
        page.keyboard.press("Escape")
    assert bad == [], "notes land before their target is drawn:\n" + "\n".join(bad)


@pytest.mark.parametrize("size", [(1920, 1080), (1288, 598)], ids=["1920x1080", "1288x598"])
def test_other_pins_keep_off_the_focus_frame(page, size):
    open_deck(page, *size)
    bad = []
    for sid in page.evaluate(NOTED_SLIDES):
        goto_slide(page, sid)
        for k in range(helper_note_count(page, sid)):
            page.keyboard.press("n" if k == 0 else "ArrowRight")
            page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
            bad += page.evaluate(PIN_CLASH)
        page.keyboard.press("Escape")
    assert bad == [], "pins collide with the current focus frame:\n" + "\n".join(bad)


def test_leaving_notes_restores_normal_motion(page):
    """Instant build states are a notes-mode-only rule: presenting after closing notes animates again."""
    open_deck(page)
    goto_slide(page, "s-4")
    page.keyboard.press("n")
    page.keyboard.press("Escape")
    goto_slide(page, "s-3")
    moving = page.evaluate("""() => { window.deck.next();
      return document.getAnimations().filter(a => a.playState === 'running' && !a.effect.target.closest('.bokeh')).length; }""")
    assert moving > 0, "stepping after notes mode should animate, not jump"
