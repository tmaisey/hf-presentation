"""Shared helpers for deck tests: file access, parsing and browser control."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECK = ROOT / "deck" / "deck.html"
ARTIFACTS = ROOT / "tests" / "artifacts"


def deck_source() -> str:
    """Return the deck's raw HTML source.

    Returns:
        The full text of deck/deck.html.
    """
    return DECK.read_text(encoding="utf-8")


def slides_source() -> str:
    """Return only the slide-content region of the deck.

    The region sits between the ``<!-- SLIDES:BEGIN -->`` and ``<!-- SLIDES:END -->``
    markers, so engine/component code is excluded from per-slide checks.

    Returns:
        The HTML between the markers.
    """
    src = deck_source()
    m = re.search(r"<!-- SLIDES:BEGIN -->(.*)<!-- SLIDES:END -->", src, re.S)
    assert m, "deck must mark its slide region with SLIDES:BEGIN/END comments"
    return m.group(1)


class SectionParser(HTMLParser):
    """Collect each ``section.slide`` with its attributes and inner markup tags.

    Attributes:
        slides: One dict per slide with ``attrs``, ``tags`` (list of (tag, attrs)),
            ``title`` text and ``title_em`` count.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.slides: list[dict] = []
        self._depth = 0
        self._in_title = False
        self._section_depth = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "section" and "slide" in (a.get("class") or "").split():
            self.slides.append({"attrs": a, "tags": [], "title": "", "title_em": 0})
            self._section_depth = 1
            return
        if not self.slides or self._section_depth == 0:
            return
        if tag == "section":
            self._section_depth += 1
        self.slides[-1]["tags"].append((tag, a))
        if tag == "h2" and "title" in (a.get("class") or "").split():
            self._in_title = True
        elif tag == "em" and self._in_title:
            self.slides[-1]["title_em"] += 1

    def handle_endtag(self, tag):
        if self._section_depth and tag == "section":
            self._section_depth -= 1
        if tag == "h2":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title and self.slides:
            self.slides[-1]["title"] += data


def parse_slides() -> list[dict]:
    """Parse all slides from the deck.

    Returns:
        A list of slide dicts as produced by :class:`SectionParser`.
    """
    p = SectionParser()
    p.feed(slides_source())
    return p.slides


def open_deck(page, width: int = 1920, height: int = 1080, reduced_motion: bool = False):
    """Load the deck in a Playwright page and wait for the engine.

    Args:
        page: A Playwright ``Page``.
        width: Viewport width in CSS px.
        height: Viewport height in CSS px.
        reduced_motion: Emulate ``prefers-reduced-motion: reduce``.

    Returns:
        A list collecting console error messages raised while the page runs.
    """
    errors: list[str] = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.set_viewport_size({"width": width, "height": height})
    if reduced_motion:
        page.emulate_media(reduced_motion="reduce")
    page.goto(DECK.as_uri())
    page.wait_for_function("window.deck && window.deck.ready === true", timeout=5000)
    return errors


def state(page) -> dict:
    """Return the engine's current position.

    Args:
        page: A Playwright ``Page`` with the deck loaded.

    Returns:
        ``{"slide": id, "index": int, "step": int, "steps": int}``.
    """
    return page.evaluate("window.deck.state()")


def goto_slide(page, slide_id: str, step: int = 0) -> None:
    """Jump straight to a slide and step, then let transitions settle.

    Args:
        page: A Playwright ``Page`` with the deck loaded.
        slide_id: The slide's element id, e.g. ``"s-3-1"``.
        step: Step within the slide.
    """
    page.evaluate("([id, s]) => window.deck.goto(id, s)", [slide_id, step])
    page.wait_for_timeout(1200)
