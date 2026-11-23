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
        [--settle ms] [--notes] [--contact [WxH]] [--contact-grid 3x4]

Writes ``<out_dir>/<slide>-<step>-<w>x<h>.png`` (the eval's evidence naming), with ``--notes`` also
``<slide>-n<i>-<w>x<h>.png`` per reader note ``i`` (1-based) in notes mode, with ``--contact`` also
contact sheets ``contact-<w>x<h>-<n>.png`` (every step shot of one size, default the first, tiled in
deck order with a ``<slide> · step <k>`` label under each, ``--contact-grid`` columns × rows per
sheet, default 3x4) so a deck-scope judge sees every state in a few images, and
``<out_dir>/shots.json``::

    {"tool": "shoot", "version": 1, "deck": str, "sizes": ["1920x1080", ...], "settle_ms": int,
     "notes": bool, "slides": [{"id": str, "steps": int}],
     "shots": [{"file": str, "slide": str, "step": int | null, "size": "WxH",
                "mode": "step" | "notes" | "contact", "note"?: int,
                "tiles"?: [{"file", "slide", "step", "label"}]}]}

Default ``out_dir``: ``shots/`` beside the deck. A re-run removes the PNGs the previous ``shots.json``
listed (and nothing else), so the folder never mixes two runs. Exit codes: 0 ok, 2 unusable input.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layout_guard as lg  # noqa: E402  (sibling script: shared browser helpers)

INDEX = "shots.json"
CONTACT_GRID = (3, 4)   # columns × rows of tiles per contact sheet
CONTACT_TILE_W = 640    # px width of one tile on a sheet
_CONTACT_PAGE = """<!doctype html><meta charset="utf-8"><style>
body {{ margin: 0; padding: 16px; background: #fff; color: #111; font: 600 18px/1.2 system-ui, sans-serif; }}
.g {{ display: grid; grid-template-columns: repeat({cols}, {w}px); gap: 18px 16px; }}
figure {{ margin: 0; }} img {{ display: block; width: {w}px; height: {h}px; outline: 1px solid #888; }}
figcaption {{ padding-top: 5px; }}
</style><div class="g">{tiles}</div>"""


def _drop_previous(out: Path) -> None:
    """Delete the files a previous run's index listed (plain names inside ``out`` only)."""
    old = out / INDEX
    if not old.is_file():
        return
    try:
        listed = [e.get("file", "") for e in json.loads(old.read_text(encoding="utf-8")).get("shots", [])]
    except (ValueError, AttributeError):
        return
    for name in listed:
        if name and Path(name).name == name and name.endswith(".png"):
            (out / name).unlink(missing_ok=True)


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


def contact_sheets(browser, out: Path, shots: list[dict], size: str, grid=CONTACT_GRID) -> list[dict]:
    """Tile one size's step shots, in order, into labelled contact sheets.

    Args:
        browser: A launched Playwright browser (the sheet is laid out and shot in a page).
        out: Folder holding the shots; sheets are written there.
        shots: Index entries; only ``mode == "step"`` shots of ``size`` are tiled.
        size: ``WxH`` of the shots to tile.
        grid: ``(columns, rows)`` of tiles per sheet.

    Returns:
        One index entry per sheet (``mode: "contact"``, its ``tiles`` with labels).
    """
    cols, rows = grid
    w, h = (int(x) for x in size.split("x"))
    tw = CONTACT_TILE_W
    th = round(tw * h / w)
    steps = [s for s in shots if s["mode"] == "step" and s["size"] == size]
    per = cols * rows
    entries = []
    ctx = browser.new_context(viewport={"width": cols * tw + (cols - 1) * 16 + 32, "height": 400})
    page = ctx.new_page()
    scratch = out / ".contact.html"
    try:
        for n, i in enumerate(range(0, len(steps), per), 1):
            chunk = steps[i:i + per]
            tiles = [{"file": s["file"], "slide": s["slide"], "step": s["step"],
                      "label": f"{s['slide']} · step {s['step']}"} for s in chunk]
            figs = "".join(f'<figure><img src="{html.escape(t["file"])}" alt=""><figcaption>{html.escape(t["label"])}'
                           "</figcaption></figure>" for t in tiles)
            scratch.write_text(_CONTACT_PAGE.format(cols=cols, w=tw, h=th, tiles=figs), encoding="utf-8")
            page.goto(scratch.resolve().as_uri())
            page.wait_for_function("[...document.images].every(i => i.complete && i.naturalWidth > 0)")
            name = f"contact-{size}-{n}.png"
            page.screenshot(path=str(out / name), full_page=True)
            entries.append({"file": name, "slide": None, "step": None, "size": size, "mode": "contact",
                            "tiles": tiles})
    finally:
        scratch.unlink(missing_ok=True)
        ctx.close()
    return entries


def shoot(deck: Path, out: Path | None = None, sizes=lg.REVIEW_SIZES, slides: list[str] | None = None,
          settle_ms: int = 0, notes: bool = False, contact: str | None = None,
          contact_grid=CONTACT_GRID) -> dict:
    """Screenshot every chosen slide at every step and size; write and return the index.

    Args:
        deck: Assembled deck HTML file.
        out: Output folder (default: ``shots/`` beside the deck); created if missing.
        sizes: Viewport sizes ``(w, h)``.
        slides: Slide ids to shoot (default: all, in deck order).
        settle_ms: Extra wait per step after settling, for timed beats.
        notes: Also shoot each reader note in notes mode.
        contact: ``WxH`` (one of ``sizes``) to tile into contact sheets; ``""`` for the first size;
            None for no sheets.
        contact_grid: ``(columns, rows)`` of tiles per contact sheet.

    Returns:
        The index written to ``<out>/shots.json``.

    Raises:
        ToolError: When the deck is missing or not an assembled deck, a slide is unknown or the
            contact size is not shot; nothing is written in that case.
    """
    from playwright.sync_api import sync_playwright

    deck = Path(deck)
    if not deck.is_file():
        raise lg.ToolError(f"{deck}: no such file")
    if contact is not None:
        contact = contact or lg.size_id(sizes[0])
        if contact not in [lg.size_id(s) for s in sizes]:
            raise lg.ToolError(f"--contact {contact} is not one of the shot sizes")
        if min(contact_grid) < 1:
            raise lg.ToolError("--contact-grid needs at least 1x1")
    out = Path(out) if out else deck.parent / "shots"
    shots, chosen = [], None
    with sync_playwright() as p:
        browser = lg.launch(p)
        try:
            for size in sizes:
                sid_ = lg.size_id(size)
                ctx = browser.new_context(viewport={"width": size[0], "height": size[1]})
                page = ctx.new_page()
                plan = lg.pick_slides(lg.open_deck(page, deck), slides)
                if chosen is None:
                    chosen = plan
                    out.mkdir(parents=True, exist_ok=True)
                    _drop_previous(out)
                for sid, steps in plan:
                    for k in range(steps + 1):
                        lg.goto_step(page, sid, k, settle_ms)
                        name = f"{sid}-{k}-{sid_}.png"
                        page.screenshot(path=str(out / name))
                        shots.append({"file": name, "slide": sid, "step": k, "size": sid_, "mode": "step"})
                    if notes:
                        shots += _notes_shots(page, sid, sid_, out)
                ctx.close()
            if contact is not None:
                shots += contact_sheets(browser, out, shots, contact, contact_grid)
        finally:
            browser.close()
    index = {"tool": "shoot", "version": 1, "deck": str(deck), "sizes": [lg.size_id(s) for s in sizes],
             "settle_ms": settle_ms, "notes": notes,
             "slides": [{"id": s, "steps": k} for s, k in (chosen or [])], "shots": shots}
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
    ap.add_argument("--contact", nargs="?", const="", metavar="WxH",
                    help="also tile every step shot of one size (default: the first) into labelled contact sheets")
    ap.add_argument("--contact-grid", default="3x4", metavar="CxR",
                    help="columns x rows of tiles per contact sheet (default: %(default)s)")
    args = ap.parse_args(argv)
    try:
        grid = tuple(int(x) for x in args.contact_grid.lower().split("x"))
        if len(grid) != 2:
            raise ValueError
    except ValueError:
        print(f"ERROR --contact-grid {args.contact_grid!r}: expected CxR, e.g. 3x4", file=sys.stderr)
        return 2
    try:
        index = shoot(args.deck, args.out, lg.parse_sizes(args.sizes),
                      args.slides.split(",") if args.slides else None, args.settle, args.notes,
                      args.contact, grid)
    except lg.ToolError as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 2
    out = args.out or args.deck.parent / "shots"
    print(f"wrote {len(index['shots'])} screenshots and {INDEX} to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
