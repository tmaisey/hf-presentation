# /// script
# requires-python = ">=3.12"
# dependencies = ["playwright>=1.49"]
# ///
"""Extract per-slide text evidence for text (``T``) judges: kicker, title, what each step shows, notes, sources.

Opens the assembled deck in the system Chrome (Playwright), steps every slide through
``window.deck`` (the same helpers as ``scripts/shoot.py``, waiting on a settle condition) and, at
each step, reads the text a viewer can see: text nodes inside the slide, and inside shared layers
such as a scene, that are rendered, not transparent and on screen. Reader notes (``aside.note``)
and their links are read from the markup. So a build step that adds, removes or swaps words shows
up exactly as presented, including text the engine moves into the slide (scene parts).

Per step, each visible block (an HTML block element, or an SVG group or drawing) is one line,
tagged with its region (``tag#id.class``) and whether it is new at that step.

Usage (from the skill folder)::

    uv run evals/extract.py deck.html <out_dir> [--size 1920x1080]

Writes ``<out_dir>/<slide>.txt`` (the judge-facing text) and ``<out_dir>/text.json``::

    {"tool": "extract", "version": 1, "deck": str, "size": "WxH",
     "slides": [{"id", "chapter", "steps": last_step, "kicker": str | null, "title": str,
                 "states": [{"step": k, "lines": [{"region": str, "text": str, "new": bool}]}],
                 "notes": [{"for": str | null, "heading": str, "text": str,
                            "sources": [{"text": str, "href": str}]}],
                 "sources": [{"text": str, "href": str}]}]}

Text is whitespace-normalised. Exit codes: 0 ok, 2 unusable input (missing file, not a deck).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _guard():
    name = "layout_guard"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / "layout_guard.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


lg = _guard()

#: Visible text of one slide at its current step: [{region, parts: [[text, is_svg]]}] in DOM order.
_VISIBLE = r"""(sid) => {
  const sec = document.getElementById(sid);
  const roots = [sec, ...document.querySelectorAll('main > :not(section)')];
  const vw = innerWidth, vh = innerHeight;
  const blocks = new Map();
  const blockOf = el => {
    if (el instanceof SVGElement) return el.closest('g[id], g[class]') || el.closest('svg') || el;
    for (let b = el; b && b !== document.body; b = b.parentElement) {
      const d = getComputedStyle(b).display;
      if (!d.startsWith('inline') && d !== 'contents') return b;
    }
    return el;
  };
  const region = b => {
    // the first authored class; engine state classes (is-visible, is-current…) change per step
    const cls = (b.getAttribute('class') || '').trim().split(/\s+/).filter(c => c && !/^(is|was|has)-/.test(c))[0];
    return b.tagName.toLowerCase() + (b.id ? '#' + b.id : '') + (cls ? '.' + cls : '');
  };
  for (const root of roots) {
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode(); n; n = w.nextNode()) {
      if (!n.nodeValue.trim()) continue;
      const el = n.parentElement;
      if (!el || el.closest('aside.note, script, style, title, desc, template, noscript')) continue;
      const head = el.closest('.title, .kicker');
      if (head && head.parentElement === sec) continue;
      if (!el.checkVisibility({opacityProperty: true, visibilityProperty: true})) continue;
      const range = document.createRange();
      range.selectNodeContents(n);
      const r = range.getBoundingClientRect();
      if (r.width <= 0 || r.height <= 0 || r.right <= 0 || r.bottom <= 0 || r.left >= vw || r.top >= vh) continue;
      const b = blockOf(el);
      if (!blocks.has(b)) blocks.set(b, {region: region(b), parts: []});
      blocks.get(b).parts.push([n.nodeValue, el instanceof SVGElement]);
    }
  }
  return [...blocks.values()];
}"""

#: Static facts of every slide: id, chapter, kicker, title, notes and links.
_STATIC = r"""() => [...document.querySelectorAll('main section.slide')].map(s => {
  const q = sel => s.querySelector(':scope > ' + sel);
  const link = a => ({text: a.textContent, href: a.getAttribute('href')});
  const notes = [...s.querySelectorAll('aside.note')].map(n => {
    const c = n.cloneNode(true);
    c.querySelectorAll('h3').forEach(h => h.remove());
    return {for: n.dataset.for || null, heading: (n.querySelector('h3') || {}).textContent || '',
            text: c.textContent, sources: [...n.querySelectorAll('a[href]')].map(link)};
  });
  return {id: s.id, chapter: s.dataset.chapter || '', kicker: q('.kicker') ? q('.kicker').textContent : null,
          title: q('.title') ? q('.title').textContent : '', notes,
          links: [...s.querySelectorAll('a[href]')].map(link)};
})"""


def _norm(s: str | None) -> str:
    return " ".join((s or "").split())


def _join(parts: list) -> str:
    """Join a block's text nodes: HTML runs as written, SVG text elements as separate words."""
    out = ""
    for text, svg in parts:
        out += (" " if svg and out else "") + text
    return _norm(out)


def _render(sl: dict) -> str:
    """The judge-facing text file for one slide."""
    last = sl["steps"]
    lines = [f"# {sl['id']} · {sl['chapter']}".rstrip(" ·"), "",
             f"Steps 0–{last} ({last + 1} state{'s' if last else ''}). Each line is one visible block, "
             "[region] first; '+' marks a line new at that step.", ""]
    if sl["kicker"] is not None:
        lines.append(f"Kicker: {sl['kicker']}")
    lines += [f"Title: {sl['title']}", ""]
    for st in sl["states"]:
        lines.append(f"## Step {st['step']}")
        lines += [f"{'+' if ln['new'] else ' '} [{ln['region']}] {ln['text']}" for ln in st["lines"]]
        lines.append("")
    lines.append("## Reader notes")
    if not sl["notes"]:
        lines.append("(none)")
    for i, n in enumerate(sl["notes"], 1):
        lines.append(f"### Note {i} (for {n['for'] or 'the slide'}): {n['heading']}".rstrip(": "))
        lines.append(n["text"])
        lines += [f"- source: {s['text']} <{s['href']}>" for s in n["sources"]]
    lines += ["", "## Sources (every link on the slide and in its notes)"]
    lines += [f"- {s['text']} <{s['href']}>" for s in sl["sources"]] or ["(none)"]
    return "\n".join(lines) + "\n"


def extract(deck: Path, out: Path | None = None, size=(1920, 1080), browser=None) -> dict:
    """Read every slide's text at every step and write the text files.

    Args:
        deck: Assembled deck HTML file.
        out: Output folder (created); None returns the index without writing.
        size: Viewport ``(w, h)`` the deck is read at (layout can hide text at some sizes).
        browser: Optional launched Playwright browser to reuse.

    Returns:
        The index (also written to ``<out>/text.json``).

    Raises:
        ToolError: When the deck is missing or not an assembled deck.
    """
    deck = Path(deck)
    if not deck.is_file():
        raise lg.ToolError(f"{deck}: no such file")

    def read(b):
        ctx = b.new_context(viewport={"width": size[0], "height": size[1]})
        try:
            page = ctx.new_page()
            plan = lg.open_deck(page, deck)
            static = {s["id"]: s for s in page.evaluate(_STATIC)}
            slides = []
            for sid, last in plan:
                st = static[sid]
                states, prev = [], None
                for k in range(last + 1):
                    lg.goto_step(page, sid, k)
                    lines = [{"region": b_["region"], "text": _join(b_["parts"])}
                             for b_ in page.evaluate(_VISIBLE, sid)]
                    lines = [ln for ln in lines if ln["text"]]
                    seen = {(ln["region"], ln["text"]) for ln in prev} if prev is not None else set()
                    for ln in lines:
                        ln["new"] = (ln["region"], ln["text"]) not in seen
                    states.append({"step": k, "lines": lines})
                    prev = lines
                notes = [{"for": n["for"], "heading": _norm(n["heading"]), "text": _norm(n["text"]),
                          "sources": [{"text": _norm(s["text"]), "href": s["href"]} for s in n["sources"]]}
                         for n in st["notes"]]
                sources, hrefs = [], set()
                for s in st["links"]:
                    if s["href"] not in hrefs:
                        hrefs.add(s["href"])
                        sources.append({"text": _norm(s["text"]), "href": s["href"]})
                slides.append({"id": sid, "chapter": st["chapter"], "steps": last,
                               "kicker": _norm(st["kicker"]) if st["kicker"] is not None else None,
                               "title": _norm(st["title"]), "states": states, "notes": notes,
                               "sources": sources})
            return slides
        finally:
            ctx.close()

    if browser is not None:
        slides = read(browser)
    else:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            b = lg.launch(p)
            try:
                slides = read(b)
            finally:
                b.close()
    index = {"tool": "extract", "version": 1, "deck": str(deck), "size": lg.size_id(size), "slides": slides}
    if out is not None:
        out = Path(out)
        out.mkdir(parents=True, exist_ok=True)
        for sl in slides:
            (out / f"{sl['id']}.txt").write_text(_render(sl), encoding="utf-8")
        (out / "text.json").write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return index


def main(argv: list[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv: Arguments (defaults to ``sys.argv[1:]``).

    Returns:
        Exit code: 0 ok, 2 unusable input.
    """
    ap = argparse.ArgumentParser(description="Per-slide, per-step text extracts of a deck for text judges.")
    ap.add_argument("deck", type=Path, help="assembled deck HTML file")
    ap.add_argument("out", type=Path, help="output folder (e.g. <run>/evidence/text)")
    ap.add_argument("--size", default="1920x1080", help="viewport WxH to read at (default: %(default)s)")
    args = ap.parse_args(argv)
    try:
        index = extract(args.deck, args.out, lg.parse_sizes(args.size)[0])
    except lg.ToolError as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 2
    print(f"wrote {len(index['slides'])} slide text file(s) and text.json to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
