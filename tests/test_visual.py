"""Spec: S-016

Full visual pass: every slide at every step, at presenter (1920×1080) and small-window
(1280×720) sizes. Screenshots land in tests/artifacts/ for independent review.
Coverage: happy (every state renders error-free) · edge (small viewport still fits) ·
negative (no clipped or off-screen text, no overlay over a title, title clear of the bar).
"""

import pytest

from helper_deck import ARTIFACTS, goto_slide, open_deck

VIEWPORTS = [(1920, 1080), (1280, 720)]

CHECK = """id => {
  const s = document.getElementById(id), vw = innerWidth, vh = innerHeight, bad = [];
  const sr = s.getBoundingClientRect();
  const off = r => r.left < sr.left - 1 || r.right > sr.right + 1 || r.top < sr.top - 1 || r.bottom > sr.bottom + 1;
  const visible = e => { const cs = getComputedStyle(e); return cs.visibility !== 'hidden' && +cs.opacity > 0.05 && e.getClientRects().length; };
  s.querySelectorAll('.title, .kicker, p, li, blockquote, .msg-agent, th, td, .tile-title, .tile-sub').forEach(e => {
    if (!visible(e)) return;
    const r = e.getBoundingClientRect();
    if (r.width === 0) return;
    if (off(r)) bad.push('off-slide: ' + (e.className || e.tagName) + ' ' + e.textContent.slice(0, 40));
    if (e.scrollWidth > e.clientWidth + 2 && getComputedStyle(e).overflowX !== 'visible')
      bad.push('clipped: ' + e.textContent.slice(0, 40));
  });
  const title = s.querySelector('.title').getBoundingClientRect();
  const bar = document.querySelector('.bar').getBoundingClientRect();
  if (title.top < bar.bottom) bad.push('title under bar');
  s.querySelectorAll('.overlay--insight.is-shown, .cluster.is-shown .overlay--msg').forEach(o => {
    const r = o.getBoundingClientRect();
    const hit = !(r.right < title.left || r.left > title.right || r.bottom < title.top || r.top > title.bottom);
    if (hit) bad.push('overlay covers title');
    if (off(r)) bad.push('overlay off-slide');
  });
  return bad;
}"""


@pytest.mark.parametrize("vw,vh", VIEWPORTS)
def test_every_slide_and_step_renders_cleanly(page, vw, vh):
    errors = open_deck(page, vw, vh)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    plan = page.evaluate("() => window.deck.plan()")
    problems = []
    for sid, steps in plan:
        for k in range(steps + 1):
            goto_slide(page, sid, k)
            page.screenshot(path=str(ARTIFACTS / f"{vw}x{vh}-{sid}-step{k}.png"))
            problems += [f"{sid}@{k}: {b}" for b in page.evaluate(CHECK, sid)]
    assert errors == []
    assert problems == [], "\n".join(problems)
