"""Fetch the deck's web fonts and inline them into deck/deck.html.

The deck must render offline from a single file (S-009, ADR-001), so fonts are embedded
as ``data:font/woff2;base64,...`` URLs inside ``@font-face`` blocks. The raw woff2 files
live in ``assets/fonts/`` so the embed is reproducible without network access.

Usage::

    uv run python tools/embed_fonts.py fetch   # download latin woff2 files (network)
    uv run python tools/embed_fonts.py embed   # rewrite the block between the markers

The deck's ``<style>`` carries ``/* FONTS:BEGIN */`` and ``/* FONTS:END */``; ``embed``
replaces everything between them and leaves the rest of the file untouched.
"""

from __future__ import annotations

import argparse
import base64
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = ROOT / "assets" / "fonts"
DECK = ROOT / "deck" / "deck.html"
BEGIN, END = "/* FONTS:BEGIN */", "/* FONTS:END */"

# Variable fonts, latin subset only. Newsreader keeps its opsz + wght axes.
CSS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Newsreader:ital,opsz,wght@0,6..72,200..800;1,6..72,200..800"
    "&family=Inter:wght@100..900&display=swap"
)
# Google serves woff2 only to browsers it recognises, so a browser User-Agent is required.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class Face:
    """One embedded font face.

    Attributes:
        family: CSS font-family name.
        style: CSS font-style (``normal`` or ``italic``).
        weight: CSS font-weight range of the variable font.
        file: File name under ``assets/fonts/``.
    """

    family: str
    style: str
    weight: str
    file: str


FACES = [
    Face("Newsreader", "normal", "200 800", "newsreader-latin.woff2"),
    Face("Newsreader", "italic", "200 800", "newsreader-italic-latin.woff2"),
    Face("Inter", "normal", "100 900", "inter-latin.woff2"),
]


def _get(url: str) -> bytes:
    """Download a URL with a browser User-Agent.

    Args:
        url: Absolute https URL.

    Returns:
        The response body.
    """
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 (fixed https hosts)
        return resp.read()


def fetch() -> None:
    """Download the latin woff2 file for each face into ``assets/fonts/``.

    Raises:
        SystemExit: If the CSS no longer lists a latin block for a face.
    """
    css = _get(CSS_URL).decode("utf-8")
    blocks = re.findall(r"/\* latin \*/\s*@font-face\s*\{(.*?)\}", css, re.S)
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    for face in FACES:
        match = next(
            (b for b in blocks
             if f"font-family: '{face.family}'" in b and f"font-style: {face.style}" in b),
            None,
        )
        if match is None:
            raise SystemExit(f"no latin block for {face}")
        url = re.search(r"url\((https://[^)]+\.woff2)\)", match).group(1)
        data = _get(url)
        (FONT_DIR / face.file).write_bytes(data)
        print(f"{face.file}: {len(data):,} bytes")


def font_face_css(face: Face) -> str:
    """Render one ``@font-face`` block with the font inlined as base64.

    Args:
        face: The face to render; its file must exist under ``assets/fonts/``.

    Returns:
        The CSS block, indented to sit inside the deck's ``<style>``.
    """
    b64 = base64.b64encode((FONT_DIR / face.file).read_bytes()).decode("ascii")
    return (
        f"  @font-face {{ font-family: \"{face.family}\"; font-style: {face.style}; "
        f"font-weight: {face.weight}; font-display: block;\n"
        f"    src: url(data:font/woff2;base64,{b64}) format(\"woff2\"); }}\n"
    )


def embed(deck: Path = DECK) -> None:
    """Replace the deck's font block with freshly inlined ``@font-face`` rules.

    Args:
        deck: Path to the deck HTML file.

    Raises:
        SystemExit: If the marker comments are missing.
    """
    src = deck.read_text(encoding="utf-8")
    start, stop = src.find(BEGIN), src.find(END)
    if start < 0 or stop < start:
        raise SystemExit(f"{deck} lacks {BEGIN} … {END} markers")
    block = "".join(font_face_css(f) for f in FACES)
    out = src[: start + len(BEGIN)] + "\n" + block + "  " + src[stop:]
    deck.write_text(out, encoding="utf-8")
    print(f"embedded {len(FACES)} faces into {deck.relative_to(ROOT)}")


def main(argv: list[str] | None = None) -> None:
    """Command-line entry point.

    Args:
        argv: Arguments (defaults to ``sys.argv[1:]``).
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["fetch", "embed"])
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    fetch() if args.command == "fetch" else embed()


if __name__ == "__main__":
    main()
