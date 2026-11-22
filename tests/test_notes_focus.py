"""Spec: S-029

v2 notes mode lands every note fully drawn and keeps the focus frame clear: moving to a note sets
its slide to the target's step with every transition, animation and timed sequence already at its
end state; a focused pop-over is drawn in front of other notes' pins, and round any other target
no other pin sits on the current focus frame (spotlight window + ring). The callout never covers its
own target, the title bar or the static Prev/Next bar, and stays on screen (scrolling inside itself
only as a last resort); the spotlight window never shows a neighbouring line of text as a sliver.
Coverage: happy (every note on every slide, at 1920×1080, 1280×720 and short-wide 1288×598) · edge
(opening notes mid-slide, world targets, pop-over targets, tall callouts on short screens, tightly
stacked timeline sub-items) · negative (no animation still running on arrival; leaving notes mode
restores normal motion; no callout over target or bar; no partial line in the window).
"""

import pytest

from helper_deck import goto_slide, open_deck, settle_animations

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

# a focused pop-over is drawn in front of other pins (no pin paints over it: hit-test a grid of the overlap);
# round any other focused target, no shown non-current pin's box touches the focus frame (the ring)
PIN_CLASH = """() => {
  """ + FOCUSED + """
  const pop = t && t.closest('.popover'), bad = [];
  const f = (pop || document.querySelector('.ring')).getBoundingClientRect();
  document.querySelectorAll('.pin:not(.is-current)').forEach(p => {
    if (getComputedStyle(p).visibility === 'hidden') return;
    const r = p.getBoundingClientRect();
    const l = Math.max(r.left, f.left), rt = Math.min(r.right, f.right), tp = Math.max(r.top, f.top), bt = Math.min(r.bottom, f.bottom);
    if (rt <= l || bt <= tp) return;
    if (!pop) { bad.push(label + ': pin ' + p.textContent + ' sits on the focus frame'); return; }
    for (let i = 0; i <= 4; i++) for (let j = 0; j <= 4; j++) {
      const e = document.elementFromPoint(l + (rt - l) * (i + .5) / 5.0001, tp + (bt - tp) * (j + .5) / 5.0001);
      if (e === p) { bad.push(label + ': pin ' + p.textContent + ' is drawn over the pop-over'); return; }
    }
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


NOTES_UI = ".callout, .pin, .ring, .veil"   # the notes layer, not the slide's own timed beats
SIZES = [(1920, 1080), (1280, 720), (1288, 598)]

# the callout keeps clear of its own target, the title bar and the static Prev/Next bar, inside the viewport
CALLOUT_CLEAR = """() => {
  """ + FOCUSED + """
  if (!t) return [label + ': no focused target'];
  const bad = [], c = document.querySelector('.callout').getBoundingClientRect();
  const hit = (a, b) => a.left < b.right - 1 && a.right > b.left + 1 && a.top < b.bottom - 1 && a.bottom > b.top + 1;
  if (hit(c, t.getBoundingClientRect())) bad.push(label + ': callout covers its target');
  if (hit(c, document.querySelector('.notes-nav').getBoundingClientRect())) bad.push(label + ': callout covers the Prev/Next bar');
  if (c.top < document.querySelector('.bar').getBoundingClientRect().bottom) bad.push(label + ': callout under the title bar');
  if (c.left < 0 || c.right > innerWidth || c.bottom > innerHeight) bad.push(label + ': callout off screen');
  const box = document.querySelector('.callout');
  if (box.scrollHeight > box.clientHeight + 1 && getComputedStyle(box).overflowY !== 'auto')
    bad.push(label + ': callout text clipped without scrolling');
  return bad; }"""

# every visible line of slide text outside the target lies wholly inside or wholly outside the spotlight window
SLIVERS = """() => {
  """ + FOCUSED + """
  if (!t) return [label + ': no focused target'];
  const w = document.querySelector('.ring').getBoundingClientRect(), tr = t.getBoundingClientRect(), bad = [];
  const shown = e => { for (; e && e !== s.parentElement; e = e.parentElement) { const cs = getComputedStyle(e);
    if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity < 0.05) return false; } return true; };
  const walk = document.createTreeWalker(s, NodeFilter.SHOW_TEXT);
  for (let n; (n = walk.nextNode());) {
    if (!n.textContent.trim() || t.contains(n) || n.parentElement.closest('aside.note, .bokeh') || !shown(n.parentElement)) continue;
    const range = document.createRange(); range.selectNodeContents(n);
    for (const r of range.getClientRects()) {
      if (!r.width || !r.height) continue;
      // overlaps the target itself (2px slack: a stacked neighbour's line box meets the target at a subpixel edge)
      if (r.left < tr.right - 2 && r.right > tr.left + 2 && r.top < tr.bottom - 2 && r.bottom > tr.top + 2) continue;
      const l = Math.max(r.left, w.left), rt = Math.min(r.right, w.right), tp = Math.max(r.top, w.top), bt = Math.min(r.bottom, w.bottom);
      if (rt - l <= 1 || bt - tp <= 1) continue;                                   // wholly outside
      if (r.left >= w.left - 1 && r.right <= w.right + 1 && r.top >= w.top - 1 && r.bottom <= w.bottom + 1) continue;   // wholly inside
      bad.push(label + ': "' + n.textContent.trim().slice(0, 30) + '" shows as a sliver in the window');
    }
  }
  return bad; }"""


def helper_each_note(page, probe):
    """Visit every note on every noted slide, settled, and collect the probe's findings."""
    bad = []
    for sid in page.evaluate(NOTED_SLIDES):
        goto_slide(page, sid)
        for k in range(helper_note_count(page, sid)):
            page.keyboard.press("n" if k == 0 else "ArrowRight")
            settle_animations(page, NOTES_UI, still=".callout, .ring")
            bad += page.evaluate(probe)
        page.keyboard.press("Escape")
    return bad


@pytest.mark.parametrize("size", SIZES, ids=[f"{w}x{h}" for w, h in SIZES])
def test_callout_never_covers_its_target_or_the_bars(page, size):
    """s-5's pop-over and s-8's tiles leave no room above or below at 1288×598: the callout must go beside,
    narrow, or scroll inside itself, never over the target or the static Prev/Next bar."""
    open_deck(page, *size)
    bad = helper_each_note(page, CALLOUT_CLEAR)
    assert bad == [], "callouts collide:\n" + "\n".join(bad)


@pytest.mark.parametrize("size", SIZES, ids=[f"{w}x{h}" for w, h in SIZES])
def test_spotlight_window_shows_no_slivers_of_neighbouring_text(page, size):
    """s-6's timeline sub-items sit a line apart: padding the window by a fixed amount cut its neighbours."""
    open_deck(page, *size)
    bad = helper_each_note(page, SLIVERS)
    assert bad == [], "partial lines in the spotlight window:\n" + "\n".join(bad)
