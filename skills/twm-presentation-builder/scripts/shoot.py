# /// script
# requires-python = ">=3.12"
# dependencies = ["playwright>=1.49"]
# ///
"""Shoot: screenshot every slide × step × review size of any assembled deck, for the look and eval evidence.

Opens the deck in the system Chrome (Playwright ``channel="chrome"``), steps each slide through
``window.deck`` and waits until animations and scrolling have settled before each shot (a condition,
never a fixed sleep; ``--settle`` adds an explicit extra wait only for timed beats a settle can't see).

Usage (from the skill folder)::

    uv run scripts/shoot.py deck.html [out_dir] [--sizes 1920x1080,1280x720,1288x598] [--slides s-1,s-3]
        [--settle ms] [--notes]

Writes ``<out_dir>/<slide>-<step>-<w>x<h>.png`` (the eval's evidence naming), with ``--notes`` also
``<slide>-n<i>-<w>x<h>.png`` per reader note ``i`` (1-based) in notes mode, and ``<out_dir>/shots.json``::

    {"tool": "shoot", "version": 1, "deck": str, "sizes": ["1920x1080", ...], "settle_ms": int,
     "notes": bool, "slides": [{"id": str, "steps": int}],
     "shots": [{"file": str, "slide": str, "step": int | null, "size": "WxH", "mode": "step" | "notes",
                "note"?: int}]}

Default ``out_dir``: ``shots/`` beside the deck. A full re-run removes the PNGs the previous
``shots.json`` listed (and nothing else), so the folder never mixes two runs. A ``--slides`` run
replaces only those slides' shots: it keeps (and re-indexes) other slides' shots from earlier runs,
and drops shots of slides no longer in the deck; re-shoot everything after a change that touches
shared parts. Exit codes: 0 ok, 2 unusable input.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layout_guard as lg  # noqa: E402  (sibling script: shared browser helpers)

INDEX = "shots.json"


def _drop_previous(out: Path, plan: list[tuple[str, int]], chosen: list[str] | None) -> list[dict]:
    """Delete the files a previous run's index listed, except other slides' shots on a ``--slides`` run.

    Args:
        out: Output folder.
        plan: The whole deck's ``deck.plan()`` pairs.
        chosen: Slide ids this run shoots (``None`` = all: every previous file goes).

    Returns:
        The previous index entries kept (shots of slides still in the deck that this run does not
        re-shoot), so the new index lists them too.
    """
    old = out / INDEX
    if not old.is_file():
        return []
    try:
        entries = [e for e in json.loads(old.read_text(encoding="utf-8")).get("shots", []) if isinstance(e, dict)]
    except (ValueError, AttributeError):
        return []
    in_deck = {s for s, _ in plan}
    keep = [e for e in entries if chosen is not None and e.get("slide") in in_deck - set(chosen)
            and (out / str(e.get("file", ""))).is_file()]
    kept = {e["file"] for e in keep}
    for e in entries:
        name = str(e.get("file", ""))
        if name and name not in kept and Path(name).name == name and name.endswith(".png"):
            (out / name).unlink(missing_ok=True)
    return keep


def _notes_shots(page, sid: str, size: str, out: Path) -> list[dict]:
    """Shoot one slide in notes mode, one image per reader note; return the index entries."""
    n = page.evaluate("id => document.getElementById(id).querySelectorAll('aside.note').length", sid)
    if not n:
        return []
    lg.goto_step(page, sid, 0)
    page.keyboard.press("n")
    page.wait_for_function("document.body.classList.contains('notes-on')")
    shots = []
    for i in range(1, n + 1):
        if i > 1:
            page.keyboard.press("ArrowRight")
        page.wait_for_function("t => { const p = document.querySelector('.notes-pos'); return !p || p.textContent.trim() === t; }",
                               arg=f"{i} / {n}")
        if not lg.settle(page):
            raise lg.ToolError(f"{sid} note {i}: page still animating after 15 s")
        name = f"{sid}-n{i}-{size}.png"
        page.screenshot(path=str(out / name))
        shots.append({"file": name, "slide": sid, "step": None, "size": size, "mode": "notes", "note": i})
    page.keyboard.press("Escape")
    page.wait_for_function("!document.body.classList.contains('notes-on')")
    lg.settle(page)
    return shots


def shoot(deck: Path, out: Path | None = None, sizes=lg.REVIEW_SIZES, slides: list[str] | None = None,
          settle_ms: int = 0, notes: bool = False) -> dict:
    """Screenshot every chosen slide at every step and size; write and return the index.

    Runs Chrome in a worker thread, so it also works while the caller holds its own sync Playwright
    session (a deck test suite's browser fixture). Arguments, return value and errors: ``_shoot``.
    """
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(_shoot, deck, out, sizes, slides, settle_ms, notes).result()


def _shoot(deck: Path, out: Path | None = None, sizes=lg.REVIEW_SIZES, slides: list[str] | None = None,
           settle_ms: int = 0, notes: bool = False) -> dict:
    """Screenshot every chosen slide at every step and size; write and return the index.

    Args:
        deck: Assembled deck HTML file.
        out: Output folder (default: ``shots/`` beside the deck); created if missing.
        sizes: Viewport sizes ``(w, h)``.
        slides: Slide ids to shoot (default: all, in deck order).
        settle_ms: Extra wait per step after settling, for timed beats.
        notes: Also shoot each reader note in notes mode.

    Returns:
        The index written to ``<out>/shots.json``.

    Raises:
        ToolError: When the deck is missing or not an assembled deck, or a slide is unknown; nothing
            is written in that case.
    """
    from playwright.sync_api import sync_playwright

    deck = Path(deck)
    if not deck.is_file():
        raise lg.ToolError(f"{deck}: no such file")
    out = Path(out) if out else deck.parent / "shots"
    shots, chosen, kept, order = [], None, [], []
    with sync_playwright() as p:
        browser = lg.launch(p)
        try:
            for size in sizes:
                sid_ = lg.size_id(size)
                ctx = browser.new_context(viewport={"width": size[0], "height": size[1]})
                page = ctx.new_page()
                full = lg.open_deck(page, deck)
                plan = lg.pick_slides(full, slides)
                if chosen is None:
                    chosen, order = plan, full
                    out.mkdir(parents=True, exist_ok=True)
                    kept = _drop_previous(out, full, slides)
                for sid, steps in plan:
                    for k in range(steps + 1):
                        lg.goto_step(page, sid, k, settle_ms)
                        name = f"{sid}-{k}-{sid_}.png"
                        page.screenshot(path=str(out / name))
                        shots.append({"file": name, "slide": sid, "step": k, "size": sid_, "mode": "step"})
                    if notes:
                        shots += _notes_shots(page, sid, sid_, out)
                ctx.close()
        finally:
            browser.close()
    rank = {s: i for i, (s, _) in enumerate(order)}
    shots = sorted(kept, key=lambda e: rank.get(e.get("slide"), 0)) + shots
    shots.sort(key=lambda e: rank.get(e["slide"], 0))  # stable: deck order, each slide's shots as taken
    steps = dict(order)
    shot_ids = sorted({e["slide"] for e in shots}, key=lambda s: rank.get(s, 0))
    size_ids = [lg.size_id(s) for s in sizes]
    size_ids += [z for z in dict.fromkeys(e["size"] for e in kept) if z not in size_ids]
    index = {"tool": "shoot", "version": 1, "deck": str(deck), "sizes": size_ids,
             "settle_ms": settle_ms, "notes": notes,
             "slides": [{"id": s, "steps": steps[s]} for s in shot_ids], "shots": shots}
    (out / INDEX).write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    return index


def main(argv: list[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv: Arguments (defaults to ``sys.argv[1:]``).

    Returns:
        Exit code: 0 ok, 2 unusable input.
    """
    ap = argparse.ArgumentParser(
        description="Screenshot every slide x step x review size of a deck into <slide>-<step>-<w>x<h>.png "
                    "plus shots.json (system Chrome via Playwright).")
    ap.add_argument("deck", type=Path, help="assembled deck HTML file")
    ap.add_argument("out", nargs="?", type=Path, help="output folder (default: shots/ beside the deck)")
    ap.add_argument("--sizes", default=",".join(lg.size_id(s) for s in lg.REVIEW_SIZES),
                    help="comma-separated WxH viewports (default: %(default)s)")
    ap.add_argument("--slides", help="comma-separated slide ids to shoot (default: all)")
    ap.add_argument("--settle", type=int, default=0, metavar="MS",
                    help="extra ms per step after animations settle, only for timed beats (default: 0)")
    ap.add_argument("--notes", action="store_true", help="also shoot each reader note in notes mode")
    args = ap.parse_args(argv)
    try:
        index = shoot(args.deck, args.out, lg.parse_sizes(args.sizes),
                      args.slides.split(",") if args.slides else None, args.settle, args.notes)
    except lg.ToolError as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 2
    out = args.out or args.deck.parent / "shots"
    print(f"wrote {len(index['shots'])} screenshots and {INDEX} to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
