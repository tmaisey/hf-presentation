"""Spec: S-016

Full visual pass: every slide at every step, at presenter (1920×1080) and small-window
(1280×720) sizes. Screenshots land in tests/artifacts/ for independent review.
Coverage: happy (every state renders error-free; quotes below/right of core content) · edge
(small viewport still fits; waiting step items readable; stacked quotes separated) · negative (no
clipped or off-screen text, no overlay over a title, title clear of the bar, hidden rows paint nothing).
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


def _rgb(css: str) -> tuple[float, float, float]:
    """Parse a computed ``rgb()``/``rgba()`` colour into channels."""
    import re

    return tuple(float(v) for v in re.findall(r"[\d.]+", css)[:3])


def _luminance(rgb) -> float:
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def test_hidden_table_rows_paint_nothing(page):
    """Rows waiting for their step must not leave empty ruled lines on screen."""
    import io

    from PIL import Image

    open_deck(page, 1280, 720)
    for sid in page.evaluate("() => [...document.querySelectorAll('section.slide')].filter(s => s.querySelector('tr[data-show-at]')).map(s => s.id)"):
        goto_slide(page, sid, 0)
        boxes = page.evaluate(f"""() => [...document.querySelectorAll('#{sid} tr[data-show-at]')]
          .filter(r => !r.classList.contains('is-visible')).map(r => {{ const b = r.getBoundingClientRect();
          return [b.left, b.top - 4, b.width, b.height + 8]; }})""")
        assert boxes, sid
        paper = _rgb(page.evaluate("() => getComputedStyle(document.body).backgroundColor"))
        for x, y, w, h in boxes:
            img = Image.open(io.BytesIO(page.screenshot(clip={"x": x, "y": y, "width": w, "height": h}))).convert("RGB")
            worst = max(max(abs(a - b) for a, b in zip(px, paper)) for px in img.getdata())
            assert worst < 10, f"{sid}: hidden row paints (max channel diff {worst})"


BODY_QUOTES = """id => {
  const s = document.getElementById(id), bad = [];
  const shown = e => { const cs = getComputedStyle(e); return +cs.opacity > 0.05 && e.getClientRects().length; };
  s.querySelectorAll('.body blockquote:not(.msg-text)').forEach(q => {
    const block = q.parentElement.matches('.body') ? q : q.parentElement;
    if (!shown(block)) return;
    const qr = block.getBoundingClientRect();
    const core = [...s.querySelectorAll('.body ul, .body ol, .body dl, .body table, .body svg.diagram, .body .msg-card, .body .stat')]
      .filter(c => !block.contains(c) && !c.contains(block) && shown(c));
    core.forEach(c => {
      const r = c.getBoundingClientRect();
      if (!(qr.top >= r.bottom - 2 || qr.left >= r.right - 2))
        bad.push('quote "' + q.textContent.slice(0, 30) + '" is above/left of ' + c.tagName);
    });
  });
  return bad; }"""


@pytest.mark.parametrize("vw,vh", VIEWPORTS)
def test_body_quotes_sit_below_or_right_of_core_content(page, vw, vh):
    """Presenter rule: italic body quotes support the slide, so they never lead it."""
    open_deck(page, vw, vh)
    problems = []
    for sid, steps in page.evaluate("() => window.deck.plan()"):
        goto_slide(page, sid, steps)
        problems += [f"{sid}: {b}" for b in page.evaluate(BODY_QUOTES, sid)]
    assert problems == [], "\n".join(problems)


def test_waiting_step_items_keep_readable_contrast(page):
    """Not-yet-current step list items are body text, so they keep ≥ 4.5:1 on paper."""
    open_deck(page, 1280, 720)
    sid = page.evaluate("() => document.querySelector('section.slide .steps').closest('section').id")
    goto_slide(page, sid, 1)
    paper = _luminance(_rgb(page.evaluate("() => getComputedStyle(document.body).backgroundColor")))
    for css in page.evaluate(f"""() => [...document.querySelectorAll('#{sid} .steps > li')]
        .filter(l => !l.classList.contains('is-current') && !l.classList.contains('is-done'))
        .map(l => getComputedStyle(l).color)"""):
        ratio = (paper + 0.05) / (_luminance(_rgb(css)) + 0.05)
        assert ratio >= 4.5, f"{css}: {ratio:.2f}:1"


def test_stacked_quote_blocks_are_visibly_separated(page):
    open_deck(page, 1280, 720)
    gaps = []
    for sid, steps in page.evaluate("() => window.deck.plan()"):
        goto_slide(page, sid, steps)
        gaps += page.evaluate(f"""() => {{ const out = [];
          const blocks = [...document.querySelectorAll('#{sid} .body div, #{sid} .body .msg-card')]
            .filter(d => d.querySelector(':scope > blockquote'));
          for (let i = 1; i < blocks.length; i++) {{
            const a = blocks[i - 1].getBoundingClientRect(), b = blocks[i].getBoundingClientRect();
            if (b.top >= a.bottom - 1 && Math.abs(a.left - b.left) < 40) out.push(['{sid}', b.top - a.bottom]);
          }} return out; }}""")
    tight = [g for g in gaps if g[1] < 16]
    assert gaps and not tight, tight
