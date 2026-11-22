"""Screenshot one slide of the v2 deck at every step, at the agreed review sizes.

Usage:
    uv run python tools/shoot.py s-3 [OUT_DIR] [--sizes 1920x1080,1280x720,1288x598] [--settle 2600]

Writes ``<OUT_DIR>/<slide>-<WxH>-<step>.png`` (default OUT_DIR: tests/artifacts/shots) so the
assembled deck can be looked at step by step (AGENTS.md *Definition of done*, item 4). Uses the
system Chrome, like the test suite.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DECK = ROOT / "deck" / "deck-v2.html"


def shoot(slide: str, out: Path, sizes: list[tuple[int, int]], settle_ms: int = 2600) -> list[Path]:
    """Capture every step of one slide at each viewport size.

    Args:
        slide: Slide element id, e.g. ``"s-3"``.
        out: Directory to write PNGs into (created if missing).
        sizes: Viewport sizes as ``(width, height)`` pairs.
        settle_ms: Wait after each step so transitions and tweens finish.

    Returns:
        The paths written, in capture order.
    """
    out.mkdir(parents=True, exist_ok=True)
    written = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        for w, h in sizes:
            page = browser.new_page(viewport={"width": w, "height": h})
            page.goto(DECK.as_uri())
            page.wait_for_function("window.deck && window.deck.ready")
            steps = dict(page.evaluate("window.deck.plan()"))[slide]
            for k in range(steps + 1):
                page.evaluate("([id, k]) => window.deck.goto(id, k)", [slide, k])
                page.wait_for_timeout(settle_ms)
                path = out / f"{slide}-{w}x{h}-{k}.png"
                page.screenshot(path=str(path))
                written.append(path)
            page.close()
        browser.close()
    return written


def main() -> None:
    """Parse arguments and capture the slide."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("slide")
    ap.add_argument("out", nargs="?", default=str(ROOT / "tests" / "artifacts" / "shots"))
    ap.add_argument("--sizes", default="1920x1080,1280x720,1288x598")
    ap.add_argument("--settle", type=int, default=2600, help="ms to wait after each step (timed beats need longer)")
    a = ap.parse_args()
    sizes = [tuple(int(v) for v in s.split("x")) for s in a.sizes.split(",")]
    for path in shoot(a.slide, Path(a.out), sizes, a.settle):
        print(path)


if __name__ == "__main__":
    main()
