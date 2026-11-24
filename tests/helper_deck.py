"""Shared helpers for deck tests: file access, parsing and browser control."""

from __future__ import annotations

import os
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECK_FILES = {"v1": ROOT / "deck" / "deck.html", "v2": ROOT / "deck" / "deck-v2.html"}
DECK_NAME = os.environ.get("HF_DECK", "v2")  # set by conftest from --deck
DECK = DECK_FILES[DECK_NAME]
ARTIFACTS = ROOT / "tests" / "artifacts" / DECK_NAME


def deck_source() -> str:
    """Return the raw HTML source of the deck under test.

    Returns:
        The full text of the selected deck file.
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


# parts the world's layout tween moves by requestAnimationFrame (invisible to getAnimations)
WORLD_TWEENED = ".world .cam, .world .mirror-group, #w-oai rect"


def goto_slide(page, slide_id: str, step: int = 0) -> None:
    """Jump straight to a slide and step, and return once the page is at rest.

    Waits for the engine to report the slide and step, then for every finite CSS/Web animation and
    transition (including those still in their delay) and the world's JS layout tween to finish, however
    long they take: a fixed wait races them under parallel load. A beat started later by a ``setTimeout``
    (e.g. the coordinator grouping, 1.3 s after its step) is not waited for: wait on its end state in the test.

    Args:
        page: A Playwright ``Page`` with the deck loaded.
        slide_id: The slide's element id, e.g. ``"s-3-1"``.
        step: Step within the slide.
    """
    page.evaluate("([id, s]) => window.deck.goto(id, s)", [slide_id, step])
    # a step past the slide's last lands on its last (callers use e.g. 9 for "the end state")
    page.wait_for_function("([id, s]) => { const st = window.deck.state(); "
                           "return st.slide === id && st.step === Math.min(s, st.steps); }", arg=[slide_id, step])
    settle_animations(page, still=WORLD_TWEENED)


def settle(page, selector: str, timeout: int = 5000) -> None:
    """Wait until an element has stopped moving (its box is unchanged across 150 ms).

    Fixed sleeps race CSS transitions when tests run in parallel on a loaded machine;
    this waits for the end state the assertion is about instead.

    Args:
        page: A Playwright ``Page`` with the deck loaded.
        selector: CSS selector of the element to watch.
        timeout: Give up after this many ms (Playwright raises TimeoutError).
    """
    # wait_for_function treats a returned promise as truthy, so the old version never waited: loop in-page
    ok = page.evaluate(
        """([sel, timeout]) => new Promise(res => {
          const box = () => { const e = document.querySelector(sel); if (!e) return '';
            const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height].map(Math.round).join(); };
          const t0 = performance.now();
          const tick = () => { const a = box(); setTimeout(() => {
            if (a !== '' && a === box()) return res(true);
            if (performance.now() - t0 > timeout) return res(false);
            tick(); }, 150); };
          tick(); })""", [selector, timeout])
    assert ok, f"{selector} kept moving for {timeout} ms"


# Busy = a finite animation or transition (CSS or Web Animations) is running, pending, or waiting out its
# delay, on the selector's elements and their subtrees (whole document when no selector). Infinite loops
# (radar, pulses, fireflies) never finish, so they are ignored.
_BUSY = """sel => (sel ? [...document.querySelectorAll(sel)].flatMap(e => e.getAnimations({subtree: true}))
    : document.getAnimations()).filter(a => (a.playState === 'running' || a.pending)
    && isFinite(a.effect && a.effect.getComputedTiming().endTime))"""


def settle_animations(page, selector: str | None = None, timeout: int = 15000, quiet: int = 120,
                      still: str | None = None) -> None:
    """Wait until every finite animation/transition has finished, instead of sleeping a fixed time.

    Fixed sleeps race CSS transitions when tests run in parallel on a loaded machine; this waits for the
    end state the assertion is about. The page must stay calm for ``quiet`` ms, checked from the next
    rendered frame, so a transition started by the next style change (e.g. a delayed handover) is caught
    too. JS-driven tweens (``requestAnimationFrame``) are invisible to ``getAnimations``: name the
    elements they move in ``still`` and their boxes must also hold still for ``quiet`` ms. A
    ``setTimeout`` beat that starts later than ``quiet`` needs its own ``wait_for_function`` condition.

    Args:
        page: A Playwright ``Page`` with the deck loaded.
        selector: CSS selector whose elements (and subtrees) must be calm; ``None`` = the whole document.
        timeout: Give up after this many ms (raises AssertionError).
        quiet: How long the page must stay calm.
        still: CSS selector of elements whose bounding boxes must stop changing (JS tweens).
    """
    # page.evaluate awaits the promise; wait_for_function would not (it takes a returned promise as truthy)
    calm = page.evaluate(
        f"""([sel, quiet, timeout, still]) => new Promise(res => {{ const t0 = performance.now();
          let since = null, last = null;
          const boxes = () => still ? [...document.querySelectorAll(still)].map(e => {{
            const r = e.getBoundingClientRect(); return [r.left, r.top, r.width, r.height].map(v => v.toFixed(1)); }}).join() : '';
          const tick = () => {{ const now = performance.now(), sig = boxes();
            if (({_BUSY})(sel).length || sig !== last) since = null;
            else if (since === null) since = now;
            else if (now - since >= quiet) return res(true);
            last = sig;
            if (now - t0 > timeout) return res(false);
            setTimeout(tick, 30); }};
          requestAnimationFrame(tick); }})""",
        [selector, quiet, timeout, still])
    assert calm, f"animations on {selector or 'the page'} still running after {timeout} ms"


def sample_at(page, ms: int, probe: str, arg=None, selector: str | None = None):
    """Evaluate ``probe`` with the running animations seeked to ``ms`` after they started.

    For assertions about a mid-animation state ("at 150 ms the newcomer is still hidden"): rather than
    sleeping ``ms`` of wall-clock time (which overshoots on a loaded machine), every finite running
    animation is paused, set to ``currentTime = ms``, probed, then resumed. Call it straight after the
    trigger, with earlier animations settled, so every animation it seeks started at that trigger.

    Args:
        page: A Playwright ``Page`` with the deck loaded.
        ms: Animation time to sample at, in ms since each animation started (delays included).
        probe: A JS function source, called as ``probe(arg)`` while the animations are held at ``ms``.
        arg: Argument passed to ``probe``.
        selector: Limit the seek to this selector's animations; ``None`` = the whole document.

    Returns:
        Whatever ``probe`` returns.
    """
    return page.evaluate(
        f"""([sel, ms, probe, arg]) => {{ const anims = ({_BUSY})(sel);
          anims.forEach(a => {{ a.pause(); a.currentTime = ms; }});
          try {{ return new Function('return (' + probe + ')')()(arg); }}
          finally {{ anims.forEach(a => a.play()); }} }}""",
        [selector, ms, probe, arg])
