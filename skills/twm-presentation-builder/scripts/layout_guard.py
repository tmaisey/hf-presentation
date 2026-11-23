# /// script
# requires-python = ">=3.12"
# dependencies = ["playwright>=1.49"]
# ///
"""Layout guard: check every slide × step × review size of any assembled deck for layout faults.

Opens the deck in the system Chrome (Playwright ``channel="chrome"``), steps each slide from 0 to its
last step through ``window.deck`` (``plan()``, ``goto()``, ``state()``), waits until animations and
scrolling have settled (a condition, never a fixed sleep) and checks the current slide:

- ``overlap``: a block or text covering a title's glyph lines, a title under the bar, the bar title
  meeting the agenda;
- ``overflow``: text clipped by its own or an ancestor's overflow box;
- ``off-canvas``: visible text outside the slide (scene text outside the viewport), the bar title
  off-screen;
- ``occlusion``: a visible overlay or card under the always-visible Notes button.

Usage (from the skill folder)::

    uv run scripts/layout_guard.py deck.html [--sizes 1920x1080,1280x720,1288x598] [--slides s-1,s-3] [--json]

Exit codes: 0 clean, 1 faults (one ``FAIL <slide>@<step> <WxH> <kind>: <check>: <target>`` line each),
2 the deck, a size or a slide could not be used. ``--json`` prints the report instead (same exit codes)::

    {"tool": "layout_guard", "version": 1, "deck": str, "sizes": ["1920x1080", ...], "states": int,
     "ok": bool, "faults": [{"slide": str, "step": int, "size": "WxH", "kind": str, "check": str,
     "target": str}]}

The browser helpers here (``open_deck``, ``settle``, ``goto_step``, ``parse_sizes``) are shared with
``scripts/shoot.py``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REVIEW_SIZES = ((1920, 1080), (1280, 720), (1288, 598))
KINDS = ("overlap", "overflow", "off-canvas", "occlusion")


class ToolError(Exception):
    """A deck, size or slide the tool cannot use (CLI exit 2)."""


# ---------- shared browser helpers ----------

def parse_sizes(text: str) -> list[tuple[int, int]]:
    """Parse ``"1920x1080,1280x720"`` into ``[(1920, 1080), (1280, 720)]``.

    Args:
        text: Comma-separated ``WxH`` sizes.

    Returns:
        Viewport sizes.

    Raises:
        ToolError: On a malformed or zero size.
    """
    sizes = []
    for part in text.split(","):
        m = re.fullmatch(r"\s*(\d+)x(\d+)\s*", part)
        if not m or not int(m[1]) or not int(m[2]):
            raise ToolError(f"bad size {part!r}: use WxH, e.g. 1280x720")
        sizes.append((int(m[1]), int(m[2])))
    return sizes


def size_id(size: tuple[int, int]) -> str:
    """Return ``"WxH"`` for a size."""
    return f"{size[0]}x{size[1]}"


_BUSY = """sel => (sel ? [...document.querySelectorAll(sel)].flatMap(e => e.getAnimations({subtree: true}))
    : document.getAnimations()).filter(a => (a.playState === 'running' || a.pending)
    && isFinite(a.effect && a.effect.getComputedTiming().endTime))"""


def settle(page, quiet: int = 150, timeout: int = 15000) -> bool:
    """Wait until no finite animation/transition runs and the deck has stopped scrolling.

    Looping (infinite) animations such as ambient motion are ignored. Never a fixed sleep.

    Args:
        page: Playwright page with a deck loaded.
        quiet: How long the page must stay calm, in ms.
        timeout: Give up after this many ms.

    Returns:
        ``True`` when calm, ``False`` on timeout.
    """
    return page.evaluate(
        f"""([quiet, timeout]) => new Promise(res => {{ const t0 = performance.now(); let since = null, last = null;
          const deck = document.querySelector('.deck');
          const tick = () => {{ const now = performance.now(), sig = deck ? deck.scrollTop : 0;
            if (({_BUSY})(null).length || sig !== last) since = null;
            else if (since === null) since = now;
            else if (now - since >= quiet) return res(true);
            last = sig;
            if (now - t0 > timeout) return res(false);
            setTimeout(tick, 30); }};
          requestAnimationFrame(tick); }})""", [quiet, timeout])


def open_deck(page, deck: Path, timeout: int = 15000) -> list[tuple[str, int]]:
    """Load a deck, wait for its engine and fonts, and return its plan.

    Args:
        page: Playwright page (viewport already set).
        deck: Deck HTML file.
        timeout: ms to wait for ``window.deck.ready``.

    Returns:
        ``[(slide_id, last_step), …]`` from ``deck.plan()``.

    Raises:
        ToolError: When the page has no ready ``window.deck``.
    """
    page.goto(Path(deck).resolve().as_uri())
    try:
        page.wait_for_function("window.deck && window.deck.ready === true", timeout=timeout)
    except Exception as e:  # Playwright TimeoutError
        raise ToolError(f"{deck}: no ready window.deck (is it an assembled deck?)") from e
    page.wait_for_function("!document.fonts || document.fonts.status === 'loaded'")
    return [(s, int(k)) for s, k in page.evaluate("deck.plan()")]


def goto_step(page, slide_id: str, step: int, extra_ms: int = 0) -> None:
    """Show one slide at one step and wait until it has settled.

    Args:
        page: Playwright page with a deck loaded.
        slide_id: Slide element id.
        step: Step number (0 = on entry).
        extra_ms: Optional extra wait after settling, for timed beats a settle can't see; the page
            is settled again afterwards.

    Raises:
        ToolError: When the page never settles.
    """
    page.evaluate("([id, k]) => deck.goto(id, k)", [slide_id, step])
    page.wait_for_function("([id, k]) => deck.state().slide === id && deck.state().step === k",
                           arg=[slide_id, step])
    if not settle(page):
        raise ToolError(f"{slide_id}@{step}: page still animating after 15 s")
    if extra_ms:
        page.wait_for_timeout(extra_ms)
        if not settle(page):
            raise ToolError(f"{slide_id}@{step}: page still animating after 15 s")


def launch(playwright):
    """Launch the system Chrome headless, as the skill's tests do.

    Args:
        playwright: A started ``sync_playwright()`` object.

    Returns:
        The browser.

    Raises:
        ToolError: When no Chrome is installed.
    """
    try:
        return playwright.chromium.launch(channel="chrome")
    except Exception as e:
        raise ToolError(f"cannot launch Chrome via Playwright (install Google Chrome): {e}") from e


def pick_slides(plan: list[tuple[str, int]], slides: list[str] | None) -> list[tuple[str, int]]:
    """Filter a plan to the named slides, in deck order.

    Args:
        plan: ``deck.plan()`` pairs.
        slides: Slide ids to keep (``None`` = all).

    Returns:
        The kept pairs.

    Raises:
        ToolError: When a named slide is not in the deck.
    """
    if not slides:
        return plan
    unknown = sorted(set(slides) - {s for s, _ in plan})
    if unknown:
        raise ToolError(f"no such slide: {', '.join(unknown)}")
    return [p for p in plan if p[0] in slides]


# ---------- the check ----------

# Faults on the current slide at the current step (and the scene, when the slide shows it). Chrome
# (.bar, .bar-title, .notes-btn) is optional so any deck can be checked.
LAYOUT_CHECK = r"""id => {
  const s = document.getElementById(id), bad = [], sr = s.getBoundingClientRect();
  const name = e => (e.id ? '#' + e.id : (e.getAttribute('class') || e.tagName).split(' ')[0]) + ' "'
    + (e.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 36) + '"';
  const shown = e => {
    const cs = getComputedStyle(e);
    if (cs.visibility === 'hidden' || cs.display === 'none') return false;
    let op = 1;
    for (let n = e; n && n.nodeType === 1; n = n.parentElement) {
      const c = getComputedStyle(n); if (c.display === 'none') return false; op *= +c.opacity; }
    const r = e.getBoundingClientRect();
    return op > 0.05 && r.width > 0 && r.height > 0;
  };
  const rect = sel => { const e = document.querySelector(sel); return e ? e.getBoundingClientRect() : null; };
  const outside = (r, b) => r.left < b.left - 1 || r.right > b.right + 1 || r.top < b.top - 1 || r.bottom > b.bottom + 1;
  const hit = (a, b) => a.left < b.right - 1 && a.right > b.left + 1 && a.top < b.bottom - 1 && a.bottom > b.top + 1;
  const TEXT = '.title, .kicker, p, li, blockquote, dt, dd, th, td, h3, text, figcaption, .msg-agent, .byline';
  const inNote = e => !!e.closest('.note');
  const view = {left: 0, top: 0, right: innerWidth, bottom: innerHeight};
  const scene = s.hasAttribute('data-scene') ? document.querySelector('.scene') : null;
  const scopes = [[s, sr]].concat(scene ? [[scene, view]] : []);
  const texts = [];
  scopes.forEach(([root, bounds]) => root.querySelectorAll(TEXT).forEach(e => {
    if (inNote(e) || !shown(e)) return;
    texts.push(e);
    const r = e.getBoundingClientRect();
    if (outside(r, bounds)) bad.push('off-slide: ' + name(e));
    if (e instanceof HTMLElement && getComputedStyle(e).overflowX !== 'visible' && e.scrollWidth > e.clientWidth + 2)
      bad.push('clipped (x): ' + name(e));
    if (e instanceof HTMLElement && getComputedStyle(e).overflowY !== 'visible' && e.scrollHeight > e.clientHeight + 2)
      bad.push('clipped (y): ' + name(e));
    for (let a = e.parentElement; a && a !== root.parentElement; a = a.parentElement) {
      const c = getComputedStyle(a);
      if (c.overflowX === 'visible' && c.overflowY === 'visible') continue;
      if (outside(r, a.getBoundingClientRect())) { bad.push('clipped by ' + name(a).split(' ')[0] + ': ' + name(e)); break; }
    }
  }));
  s.querySelectorAll('.body, .steps, .overlay, table, .fig-notes, .narration, .narr-tile, .popover, .pop-panel, .text-tile').forEach(e => {
    if (inNote(e) || !shown(e)) return;
    const c = getComputedStyle(e);
    if (c.overflowY !== 'visible' && e.scrollHeight > e.clientHeight + 2) bad.push('clipped (y): ' + name(e));
    if (c.overflowX !== 'visible' && e.scrollWidth > e.clientWidth + 2) bad.push('clipped (x): ' + name(e));
  });
  const bar = rect('.bar');
  const BLOCK = '.body, .steps, svg.diagram, .overlay, table, .prompts, .msg-card, .fig-notes, .narration > *, .popover, .pop-panel, .text-tile';
  const blockers = [...s.querySelectorAll(BLOCK)].filter(e => !inNote(e) && shown(e))
    .concat(texts.filter(e => !e.matches('.title, .kicker') && !e.closest('.title')))
    .concat(scene && shown(scene) ? [scene.querySelector('svg') || scene] : []);
  s.querySelectorAll('.title').forEach(t => {
    if (!shown(t)) return;
    const range = document.createRange(); range.selectNodeContents(t);
    const lines = [...range.getClientRects()].filter(r => r.width > 0 && r.height > 0);
    if (!lines.length) return;
    if (bar && Math.min(...lines.map(r => r.top)) < bar.bottom - 1) bad.push('title under bar: ' + name(t));
    if (lines.some(r => outside(r, sr))) bad.push('off-slide: ' + name(t));
    blockers.forEach(b => {
      if (b.contains(t)) return;
      const br = b.getBoundingClientRect();
      if (lines.some(l => hit(l, br))) bad.push('covers title: ' + name(b));
    });
  });
  const btn = rect('.notes-btn');
  if (btn) s.querySelectorAll('.overlay, .msg-card, .fig-notes > *, .narr-tile, .pop-panel, .text-tile').forEach(e => {
    if (shown(e) && hit(e.getBoundingClientRect(), btn)) bad.push('under notes button: ' + name(e)); });
  const bt = rect('.bar-title');
  if (bt) {
    const nav = rect(document.querySelector('.bar--compact') ? '.nav-current' : '.agenda');
    if (nav && hit(bt, nav)) bad.push('bar title meets agenda');
    if (bt.right > innerWidth || bt.left < 0) bad.push('bar title off-screen');
  }
  return [...new Set(bad)];
}"""


def slide_faults(page, slide_id: str, shoot=None, extra_ms: int = 0) -> list[str]:
    """Step through one slide from step 0 to its last step and collect every layout fault.

    Args:
        page: Playwright page with a deck loaded at the viewport under test.
        slide_id: The slide's element id.
        shoot: Optional ``callable(step)`` run after each step settles (e.g. to save a screenshot).
        extra_ms: Extra wait per step for timed beats (see ``goto_step``).

    Returns:
        Fault strings ``"<slide>@<step>: <check>: <target>"``; empty when clean at every step.
    """
    steps = dict(page.evaluate("deck.plan()"))[slide_id]
    faults: list[str] = []
    for k in range(steps + 1):
        goto_step(page, slide_id, k, extra_ms)
        if shoot:
            shoot(k)
        faults += [f"{slide_id}@{k}: {f}" for f in page.evaluate(LAYOUT_CHECK, slide_id)]
    return faults


def classify(fault: str) -> tuple[str, str, str]:
    """Split one check result into ``(kind, check, target)``.

    Args:
        fault: A ``LAYOUT_CHECK`` string, e.g. ``'covers title: .body "…"'``.

    Returns:
        ``kind`` (one of ``KINDS``), the check label and the element it names (may be empty).
    """
    check, _, target = fault.partition(": ")
    if check.startswith("clipped"):
        kind = "overflow"
    elif check in ("off-slide", "bar title off-screen"):
        kind = "off-canvas"
    elif check == "under notes button":
        kind = "occlusion"
    else:
        kind = "overlap"
    return kind, check, target


def guard(deck: Path, sizes=REVIEW_SIZES, slides: list[str] | None = None) -> dict:
    """Check every slide × step × size of a deck.

    Args:
        deck: Assembled deck HTML file.
        sizes: Viewport sizes ``(w, h)``.
        slides: Slide ids to check (default: all, in deck order).

    Returns:
        The report (schema in the module docstring); ``ok`` is ``True`` when there are no faults.

    Raises:
        ToolError: When the deck is missing or not an assembled deck, or a slide is unknown.
    """
    from playwright.sync_api import sync_playwright

    deck = Path(deck)
    if not deck.is_file():
        raise ToolError(f"{deck}: no such file")
    faults, states = [], 0
    with sync_playwright() as p:
        browser = launch(p)
        try:
            for size in sizes:
                ctx = browser.new_context(viewport={"width": size[0], "height": size[1]})
                page = ctx.new_page()
                for sid, steps in pick_slides(open_deck(page, deck), slides):
                    states += steps + 1
                    for f in slide_faults(page, sid):
                        head, _, rest = f.partition(": ")
                        kind, check, target = classify(rest)
                        sl, _, k = head.rpartition("@")
                        faults.append({"slide": sl, "step": int(k), "size": size_id(size), "kind": kind,
                                       "check": check, "target": target})
                ctx.close()
        finally:
            browser.close()
    return {"tool": "layout_guard", "version": 1, "deck": str(deck), "sizes": [size_id(s) for s in sizes],
            "states": states, "ok": not faults, "faults": faults}


def main(argv: list[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv: Arguments (defaults to ``sys.argv[1:]``).

    Returns:
        Exit code: 0 clean, 1 faults, 2 unusable input.
    """
    ap = argparse.ArgumentParser(
        description="Check every slide x step x review size of a deck for overlap, overflow, "
                    "off-canvas and occlusion faults (system Chrome via Playwright).")
    ap.add_argument("deck", type=Path, help="assembled deck HTML file")
    ap.add_argument("--sizes", default=",".join(size_id(s) for s in REVIEW_SIZES),
                    help="comma-separated WxH viewports (default: %(default)s)")
    ap.add_argument("--slides", help="comma-separated slide ids to check (default: all)")
    ap.add_argument("--json", action="store_true", help="print the JSON report instead of FAIL lines")
    args = ap.parse_args(argv)
    try:
        report = guard(args.deck, parse_sizes(args.sizes), args.slides.split(",") if args.slides else None)
    except ToolError as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for f in report["faults"]:
            print(f"FAIL {f['slide']}@{f['step']} {f['size']} {f['kind']}: {f['check']}"
                  + (f": {f['target']}" if f["target"] else ""))
        verdict = "layout-clean" if report["ok"] else f"{len(report['faults'])} fault(s)"
        print(f"{report['deck']}: {verdict} over {report['states']} slide-step states "
              f"at {', '.join(report['sizes'])}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
