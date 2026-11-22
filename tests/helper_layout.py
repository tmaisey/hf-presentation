"""Layout-guard helpers: settle a step, then list its layout faults (used by S-030 tests).

The checker is generic (no per-slide knowledge) so it covers every slide the deck gains. It reports:

* ``off-slide``: visible text outside the slide (or, for the shared world, the viewport);
* ``clipped``: visible text cut by an ``overflow`` box (scrolling content, or text escaping its
  clipping ancestor);
* ``covers title``: a body, step list, diagram, narration tile, pop-over, overlay, world or any
  visible text overlapping a visible title's glyph lines;
* ``title under bar``: a title's text rising into the title bar.
"""

from __future__ import annotations

# Waits until every finite CSS animation/transition on the page has finished (delayed ones count as
# running), twice in a row. Infinite loops (radar, pulses) are ignored: they never settle.
SETTLE = """() => new Promise(res => {
  const busy = () => document.getAnimations().some(a => a.playState === 'running'
    && isFinite(a.effect && a.effect.getComputedTiming().endTime));
  let calm = 0;
  const tick = () => { calm = busy() ? 0 : calm + 1; if (calm >= 2) res(true); else setTimeout(tick, 80); };
  setTimeout(tick, 120); })"""

CHECK = r"""id => {
  const s = document.getElementById(id), vw = innerWidth, vh = innerHeight, bad = [];
  const sr = s.getBoundingClientRect(), view = {left: 0, top: 0, right: vw, bottom: vh};
  const name = e => (e.id ? '#' + e.id : (e.getAttribute('class') || e.tagName).split(' ')[0]) + ' "'
    + (e.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 36) + '"';
  const shown = e => {   // effective visibility: no hidden/none, product of ancestor opacities > 0.05
    const cs = getComputedStyle(e);
    if (cs.visibility === 'hidden' || cs.display === 'none') return false;
    let op = 1;
    for (let n = e; n && n.nodeType === 1; n = n.parentElement) {
      const c = getComputedStyle(n); if (c.display === 'none') return false; op *= +c.opacity; }
    const r = e.getBoundingClientRect();
    return op > 0.05 && r.width > 0 && r.height > 0;
  };
  const outside = (r, b) => r.left < b.left - 1 || r.right > b.right + 1 || r.top < b.top - 1 || r.bottom > b.bottom + 1;
  const hit = (a, b) => a.left < b.right - 1 && a.right > b.left + 1 && a.top < b.bottom - 1 && a.bottom > b.top + 1;
  const TEXT = '.title, .kicker, p, li, blockquote, figcaption, th, td, h3, text, .msg-agent';
  const inNote = e => !!e.closest('.note');
  const world = s.hasAttribute('data-world') ? document.querySelector('.world') : null;
  const scopes = [[s, sr]].concat(world ? [[world, view]] : []);
  const texts = [];
  scopes.forEach(([root, bounds]) => root.querySelectorAll(TEXT).forEach(e => {
    if (inNote(e) || !shown(e)) return;
    texts.push(e);
    const r = e.getBoundingClientRect();
    if (outside(r, bounds)) bad.push('off-slide: ' + name(e));
    // clipped: scrolled-away content, or text escaping a clipping ancestor inside its scope
    if (e instanceof HTMLElement && getComputedStyle(e).overflowX !== 'visible' && e.scrollWidth > e.clientWidth + 2)
      bad.push('clipped (x): ' + name(e));
    if (e instanceof HTMLElement && getComputedStyle(e).overflowY !== 'visible' && e.scrollHeight > e.clientHeight + 2)
      bad.push('clipped (y): ' + name(e));
    for (let a = e.parentElement; a && a !== root.parentElement && a !== s.parentElement; a = a.parentElement) {
      const c = getComputedStyle(a);
      if (c.overflowX === 'visible' && c.overflowY === 'visible') continue;
      if (outside(r, a.getBoundingClientRect())) { bad.push('clipped by ' + name(a).split(' ')[0] + ': ' + name(e)); break; }
    }
  }));
  // containers that clip and hold more than they show (e.g. a timeline taller than its row)
  s.querySelectorAll('.body, .steps, .narration, .narr-tile, .popover, .pop-panel, .overlay').forEach(e => {
    if (inNote(e) || !shown(e)) return;
    const c = getComputedStyle(e);
    if (c.overflowY !== 'visible' && e.scrollHeight > e.clientHeight + 2) bad.push('clipped (y): ' + name(e));
    if (c.overflowX !== 'visible' && e.scrollWidth > e.clientWidth + 2) bad.push('clipped (x): ' + name(e));
  });
  const bar = document.querySelector('.bar').getBoundingClientRect();
  const BLOCK = '.body, .steps, svg.diagram, .narration > *, .popover, .pop-panel, .overlay, .cluster, table, .prompts';
  const blockers = [...s.querySelectorAll(BLOCK)].filter(e => !inNote(e) && shown(e))
    .concat(texts.filter(e => !e.matches('.title, .kicker') && !e.closest('.title')))
    .concat(world && shown(world) ? [world] : []);
  s.querySelectorAll('.title').forEach(t => {
    if (!shown(t)) return;
    const range = document.createRange(); range.selectNodeContents(t);
    const lines = [...range.getClientRects()].filter(r => r.width > 0 && r.height > 0);
    if (!lines.length) return;
    if (Math.min(...lines.map(r => r.top)) < bar.bottom - 1) bad.push('title under bar: ' + name(t));
    if (lines.some(r => outside(r, sr))) bad.push('off-slide: ' + name(t));
    blockers.forEach(b => {
      if (b.contains(t)) return;
      const br = b.getBoundingClientRect();
      if (lines.some(l => hit(l, br))) bad.push('covers title: ' + name(b));
    });
  });
  return [...new Set(bad)];
}"""


def helper_settle(page) -> None:
    """Wait until the current step's transitions, tweens and delayed beats have finished.

    Args:
        page: A Playwright ``Page`` with the deck loaded.
    """
    page.evaluate(SETTLE)


def helper_layout_faults(page, slide_id: str) -> list[str]:
    """Step through one slide from step 0 to its last step and collect every layout fault.

    Args:
        page: A Playwright ``Page`` with the deck loaded at the viewport under test.
        slide_id: The slide's element id, e.g. ``"s-3"``.

    Returns:
        Fault strings ``"<slide>@<step>: <fault>"``; empty when the slide is clean at every step.
    """
    steps = dict(page.evaluate("() => window.deck.plan()"))[slide_id]
    faults: list[str] = []
    for k in range(steps + 1):
        page.evaluate("([id, k]) => window.deck.goto(id, k)", [slide_id, k])
        helper_settle(page)
        faults += [f"{slide_id}@{k}: {f}" for f in page.evaluate(CHECK, slide_id)]
    return faults
