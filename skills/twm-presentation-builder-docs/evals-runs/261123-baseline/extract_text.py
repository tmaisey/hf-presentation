# /// script
# requires-python = ">=3.12"
# dependencies = ["beautifulsoup4>=4.12", "lxml>=5"]
# ///
"""Extract per-slide text evidence (title, body copy, overlays, reader notes, sources) for T judges.

EVAL.md §2 asks for per-slide text extracts but the skill ships no extractor, so this run carries
its own. Static parse of the deck markup between the slides of ``<main>``; build steps are marked
where an element carries ``data-step`` (the step it enters on).

Usage::

    uv run extract_text.py <deck.html> <out_dir>

Writes ``<out_dir>/<slide>.txt`` per slide.
"""

from __future__ import annotations

import sys
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag


def _text(node: Tag) -> str:
    """Return a node's text with collapsed whitespace."""
    return " ".join(node.get_text(" ", strip=True).split())


def _lines(node: Tag, depth: int = 0) -> list[str]:
    """Walk a slide's visible markup and emit one line per block-level text element.

    Args:
        node: Element to walk (reader notes are skipped; they are listed separately).
        depth: Recursion depth, for indentation.

    Returns:
        Text lines, prefixed with the element's class and its entry step when it has one.
    """
    out: list[str] = []
    for child in node.children:
        if isinstance(child, NavigableString) or not isinstance(child, Tag):
            continue
        if child.name in ("aside", "script", "style", "defs", "template"):
            continue
        block = child.name in ("p", "h1", "h2", "h3", "li", "blockquote", "text", "figcaption",
                               "td", "th", "dt", "dd", "span") and not child.find(
            ["p", "li", "blockquote", "h2", "h3", "text"])
        step = child.get("data-step")
        tag = f"[{child.name}{'.' + '.'.join(child.get('class', [])) if child.get('class') else ''}"
        tag += f" step={step}]" if step is not None else "]"
        if block:
            t = _text(child)
            if t:
                out.append("  " * depth + f"{tag} {t}")
        else:
            sub = _lines(child, depth + 1)
            if sub:
                if step is not None or child.get("class"):
                    out.append("  " * depth + tag)
                out.extend(sub)
    return out


def extract(deck: Path, out: Path) -> list[str]:
    """Write one text file per slide of ``deck`` into ``out``; return the slide ids."""
    soup = BeautifulSoup(deck.read_text(encoding="utf-8"), "lxml")
    out.mkdir(parents=True, exist_ok=True)
    ids = []
    for sec in soup.select("main section.slide"):
        sid = sec.get("id")
        ids.append(sid)
        lines = [f"# slide {sid} · chapter: {sec.get('data-chapter', '')}", "", "## Visible markup"]
        lines += _lines(sec)
        lines += ["", "## Reader notes"]
        for i, note in enumerate(sec.select("aside.note"), 1):
            lines.append(f"### note {i} (for {note.get('data-for', '?')})")
            for a in note.select("a[href]"):
                a.replace_with(f"{_text(a)} <{a['href']}>")
            lines.append(_text(note))
        if not sec.select("aside.note"):
            lines.append("(none)")
        (out / f"{sid}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ids


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    print(" ".join(extract(Path(sys.argv[1]), Path(sys.argv[2]))))
