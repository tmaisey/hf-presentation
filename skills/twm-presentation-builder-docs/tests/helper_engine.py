"""Helpers for core-engine tests: assemble a fixture deck from the skeleton and wait on its state.

The assembler here is a test stand-in (the real one is a later spec): it inlines the engine parts
into the skeleton's marked blocks and writes one self-contained HTML file.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

from helper_skill import SKILL_DIR

ENGINE_DIR = SKILL_DIR / "assets" / "engine"
ENGINE_JS = ENGINE_DIR / "engine.js"
ARCH_CSS = ENGINE_DIR / "arch.css"
MODULES_DIR = ENGINE_DIR / "modules"
SKELETON = SKILL_DIR / "assets" / "templates" / "deck-skeleton.html"
ARCHITECTURE = SKILL_DIR / "architecture" / "ARCHITECTURE.md"
LAYER_ORDER = "@layer arch, components, palette, style, deck;"
BLOCKS = ("FONTS", "ARCH", "COMPONENTS", "PALETTE", "STYLE", "DECK", "DEFS", "MODULES", "ENGINE")
REVIEW_SIZES = ((1920, 1080), (1280, 720), (1288, 598))

# Test-only stand-in for the component/palette/style layers (later specs), so screenshots are legible.
# It sits in the deck layer and uses system colours only.
FIXTURE_CSS = """
@layer deck {
  body { font: 400 clamp(16px, 1.25vw, 24px)/1.5 system-ui, sans-serif; background: Canvas; color: CanvasText; }
  .bar { height: 64px; display: flex; align-items: center; gap: 24px; padding: 0 32px;
    background: color-mix(in srgb, Canvas 85%, transparent); border-bottom: 1px solid GrayText; }
  .bar-title { margin: 0; font-weight: 600; white-space: nowrap; }
  .bar-title span { margin: 0 .5em; color: GrayText; }
  .bar-home { color: inherit; text-decoration: none; }
  .nav { margin-left: auto; }
  .agenda { gap: 6px; }
  .agenda button, .nav-current { font: inherit; font-size: 15px; background: none; border: 0; padding: 8px 12px;
    border-radius: 999px; color: GrayText; cursor: pointer; }
  .agenda .is-current button, .nav-current { color: CanvasText; font-weight: 600; outline: 1px solid GrayText; }
  .bar--compact .agenda { background: Canvas; padding: 8px; border: 1px solid GrayText; border-radius: 12px; }
  .progress { height: 3px; background: Highlight; }
  .slide { display: grid; align-content: start; padding: calc(64px + 5vh) 7vw 7vh; }
  .slide--lead { align-content: center; }
  .kicker { margin: 0; font-size: .8em; letter-spacing: .14em; text-transform: uppercase; color: GrayText; }
  .title { margin: .4em 0 .6em; font-size: clamp(30px, 3vw, 60px); line-height: 1.06; }
  .body p { max-width: 46ch; }
  .points li, .steps li { margin: .4em 0; }
  .steps > li[data-show-at] { opacity: 1; }
  .steps li.is-done { color: GrayText; } .steps li.is-current { font-weight: 600; }
  [data-show-at], [data-hide-at] { transition: opacity .4s ease; }
  .overlay { position: relative; justify-self: end; max-width: 40vw; padding: 24px 32px; border-radius: 20px;
    background: Canvas; border: 1px solid GrayText; transition: opacity .5s ease; }
  .slide.is-overlaid > .body { opacity: .5; }
  .diagram { width: min(100%, 900px); height: auto; overflow: visible; }
  .tile rect { fill: Canvas; stroke: GrayText; stroke-width: 2; rx: 16px; }
  .tile text { text-anchor: middle; dominant-baseline: central; font-size: 26px; fill: CanvasText; }
  .edge { fill: none; stroke: GrayText; stroke-width: 2.5px; }
  #arr path { fill: GrayText; }
  .orb { background: radial-gradient(circle, Highlight, transparent 70%); opacity: .25; }
  .notes-btn { padding: 8px 14px; border-radius: 999px; border: 1px solid GrayText; background: Canvas; color: CanvasText; }
  .veil { background: color-mix(in srgb, Canvas 55%, transparent); backdrop-filter: blur(6px); }
  .ring { border-radius: 16px; box-shadow: 0 0 0 2px Highlight; }
  .callout { padding: 20px 24px; border-radius: 16px; background: Canvas; border: 1px solid GrayText; }
  .callout h3 { margin: 0 0 8px; }
  .pin { width: 28px; height: 28px; margin: -14px 0 0 -14px; border-radius: 50%; border: 0; background: CanvasText; color: Canvas; }
  .pin.is-current { background: Highlight; }
}
"""

# Four generic slides: a lead title (ambient), a stepped text slide with an Insight and notes, a
# diagram slide with a step list, and a closing slide. Three chapters.
FIXTURE_SLIDES = """
<section class="slide slide--lead" id="s-1" data-chapter="Opening" data-ambient>
  <p class="kicker">01 · Opening</p>
  <h2 class="title" id="s1-title">A <em>generic</em> fixture deck</h2>
  <div class="body"><p>Four slides that exercise the core engine.</p></div>
  <aside class="note" data-for="#s1-title"><h3>Lead note</h3><p>About the opening.</p>
    <a class="src" href="https://example.org/lead">Example source</a></aside>
</section>

<section class="slide" id="s-2" data-chapter="Method">
  <p class="kicker">02 · Method</p>
  <h2 class="title">Steps reveal content one input at a time</h2>
  <div class="body">
    <ul class="points">
      <li id="m-always">Always on screen</li>
      <li id="m-first" data-show-at="1">Shown from step 1</li>
      <li id="m-claim" data-show-at="2">Shown from step 2</li>
      <li id="m-early" data-hide-at="2">Hidden from step 2</li>
    </ul>
  </div>
  <aside class="overlay overlay--insight" id="m-insight" data-at="3"><p>Only at step 3.</p></aside>
  <aside class="note" data-for="#m-claim"><h3>Claim note</h3><p>Why step 2 matters.</p>
    <a class="src" href="https://example.org/claim">Claim source</a></aside>
  <aside class="note" data-for="#m-early"><h3>Early note</h3><p>Gone from step 2.</p>
    <a class="src" href="https://example.org/early">Early source</a></aside>
</section>

<section class="slide" id="s-3" data-chapter="Method">
  <p class="kicker">02 · Method</p>
  <h2 class="title">Diagrams build with the steps</h2>
  <div class="body">
    <ol class="steps">
      <li id="d-step-1" data-show-at="1">First, a tile</li>
      <li id="d-step-2" data-show-at="2">Then, a connection</li>
    </ol>
    <svg class="diagram" viewBox="0 0 900 260" role="img" aria-label="Two tiles joined by an edge">
      <g class="layer-edges"><path class="edge" id="d-edge" data-from="#d-a" data-to="#d-b" marker-end="url(#arr)" data-show-at="2"/></g>
      <g class="layer-nodes">
        <g class="tile" id="d-a"><rect x="40" y="70" width="260" height="120"/><text class="tile-title">Source</text></g>
        <g class="tile" id="d-b" data-show-at="1"><rect x="600" y="70" width="260" height="120"/><text class="tile-title">Target</text><text class="tile-sub">second line</text></g>
      </g>
    </svg>
  </div>
  <aside class="note" data-for="#d-b"><h3>Tile note</h3><p>A note on a diagram tile.</p>
    <a class="src" href="https://example.org/tile">Tile source</a></aside>
</section>

<section class="slide" id="s-4" data-chapter="Close">
  <p class="kicker">03 · Close</p>
  <h2 class="title">The end</h2>
  <div class="body"><p>No steps here.</p></div>
</section>
"""

# A module that records every render call, to prove the extension point.
RECORDER_MODULE = """
(window.deckModules = window.deckModules || []).push({
  name: 'recorder',
  init(api) { window.__rec = { init: api.slides.map(s => s.id), renders: [] }; },
  render(s, k, ctx) { if (ctx.current) window.__rec.renders.push([s.id, k]); },
});
"""

# Optional-module fixture: a plain lead, two live scene slides (short and long titles, cameras,
# narration tiles, a pop-over), a backdrop scene slide with a tile row, and a plain close. The scene's
# parts span slides via data-scene-at / data-scene-until; m-3's last step comes only from the scene.
MODULE_SLIDES = """
<div class="scene">
  <svg class="diagram" viewBox="-400 -200 800 400" role="img" aria-label="A shared scene of three tiles">
    <g class="cam">
      <g class="layer-edges">
        <path class="edge" id="p-ab" data-from="#p-a" data-to="#p-b" marker-end="url(#arr)" data-scene-at="m-2:1" data-scene-until="m-3:1"/>
        <path class="edge" id="p-ac" data-from="#p-a" data-to="#p-c" marker-end="url(#arr)" data-scene-at="m-3:3"/>
      </g>
      <g class="layer-nodes">
        <g class="tile" id="p-a" data-scene-at="m-2:0" data-scene-is="dim m-3:0 m-3:3"><rect x="-90" y="-50" width="180" height="100"/><text class="tile-title">Hub</text></g>
        <g class="tile" id="p-b" data-scene-at="m-2:1" data-scene-until="m-3:1"><rect x="-370" y="-170" width="180" height="100"/><text class="tile-title">Early</text></g>
        <g class="tile" id="p-c" data-scene-at="m-3:3"><rect x="190" y="70" width="180" height="100"/><text class="tile-title">Late</text></g>
      </g>
    </g>
  </svg>
</div>

<section class="slide slide--lead" id="m-1" data-chapter="Opening">
  <p class="kicker">01 · Opening</p>
  <h2 class="title">Optional modules</h2>
  <div class="body"><p>No scene here.</p></div>
</section>

<section class="slide" id="m-2" data-chapter="Scene" data-scene data-camera="0 0 1, 2: -120 0 1.6">
  <p class="kicker">02 · Scene</p>
  <h2 class="title" id="m2-title">A short title</h2>
  <div class="body">
    <ol class="steps">
      <li id="m2-s1" data-show-at="1">A second tile joins</li>
      <li id="m2-s2" data-show-at="2">The camera moves in</li>
      <li id="m2-s3" data-show-at="3">One more message</li>
    </ol>
  </div>
  <div class="scene-slot"></div>
  <div class="narration">
    <article class="narr-tile" id="n-1" data-at="1"><p class="msg-from">Speaker one</p><blockquote class="msg-text">The first message arrives with the first step.</blockquote></article>
    <article class="narr-tile" id="n-2a" data-at="2"><p class="msg-from">Speaker two</p><blockquote class="msg-text">A pair of messages shares the second step.</blockquote></article>
    <article class="narr-tile" id="n-2b" data-at="2"><p class="msg-from">Speaker three</p><blockquote class="msg-text">The second of the pair, placed apart from the first.</blockquote></article>
    <article class="narr-tile" id="n-3" data-at="3"><p class="msg-from">Speaker one</p><blockquote class="msg-text">A last message on its own.</blockquote></article>
  </div>
</section>

<section class="slide" id="m-3" data-chapter="Scene" data-scene data-camera="60 20 1.2">
  <p class="kicker">03 · Scene</p>
  <h2 class="title" id="m3-title">A much longer title that wraps over more than one line at every review size, so the scene must hold its place anyway</h2>
  <div class="body">
    <ol class="steps">
      <li id="m3-s1" data-show-at="1">A pop-over takes focus</li>
      <li id="m3-s2" data-show-at="2">It dissolves</li>
    </ol>
  </div>
  <div class="scene-slot"></div>
  <div class="popover" id="m3-pop" data-show-at="1" data-hide-at="2">
    <figure class="pop-panel"><figcaption id="m3-pop-cap">An illustration</figcaption>
      <p id="m3-pop-text">A panel over the scene, which softens while it has focus.</p></figure>
  </div>
  <div class="narration">
    <article class="narr-tile" id="n-m3" data-at="2"><p class="msg-from">Speaker two</p><blockquote class="msg-text">After the pop-over, a message.</blockquote></article>
  </div>
  <aside class="note" data-for="#p-b"><h3>Scene note</h3><p>A note on a scene part.</p>
    <a class="src" href="https://example.org/scene">Scene source</a></aside>
  <aside class="note" data-for="#m3-pop-cap"><h3>Pop-over caption</h3><p>On the pop-over.</p>
    <a class="src" href="https://example.org/pop">Pop source</a></aside>
  <aside class="note" data-for="#m3-pop-text"><h3>Pop-over text</h3><p>Also on the pop-over.</p>
    <a class="src" href="https://example.org/pop-text">Pop text source</a></aside>
</section>

<section class="slide" id="m-4" data-chapter="Backdrop" data-scene="backdrop">
  <p class="kicker">04 · Backdrop</p>
  <h2 class="title" id="m4-title">Three tiles over the blurred scene</h2>
  <div class="scene-slot"></div>
  <div class="body body--tiles">
    <article class="text-tile" id="t-1" data-show-at="1"><h3>First</h3><p>One idea per tile.</p></article>
    <article class="text-tile" id="t-2" data-show-at="2"><h3>Second</h3><p>Revealed with the steps.</p></article>
    <article class="text-tile" id="t-3" data-show-at="3"><h3>Third</h3><p>Over a backdrop.</p></article>
  </div>
</section>

<section class="slide" id="m-5" data-chapter="Close">
  <p class="kicker">05 · Close</p>
  <h2 class="title">The end</h2>
  <div class="body"><p>No scene again.</p></div>
</section>
"""

# Test-only stand-in for the module components' layout and look (later specs), system colours only.
MODULE_CSS = FIXTURE_CSS + """
@layer deck {
  .slide[data-scene] { grid-template: "kicker kicker kicker" auto "title title title" auto "body slot narr" minmax(0, 1fr)
      / minmax(0, 3fr) minmax(0, 4fr) minmax(0, 3fr); column-gap: 2.4vw; }
  .slide[data-scene] > .kicker { grid-area: kicker; } .slide[data-scene] > .title { grid-area: title; }
  .slide[data-scene] > .body { grid-area: body; align-self: center; }
  .slide[data-scene] > .scene-slot { grid-area: slot; min-height: 0; }
  .slide[data-scene] > .narration { grid-area: narr; min-height: 0; }
  .slide[data-scene] > .popover { grid-column: slot-start / narr-end; grid-row: 3; align-self: center; }
  .slide[data-scene] > .body--tiles { grid-column: body-start / narr-end; grid-row: 3; align-self: stretch; }
  .scene { transition: opacity .5s ease, filter .6s ease; }
  .scene .cam { transition: transform 1s ease; }
  .scene [data-scene-at] { transition: opacity .5s ease; }
  .scene .is-dim.is-visible { opacity: .6; }
  .narr-tile { padding: 12px 18px; border-radius: 16px; background: Canvas; border: 1px solid GrayText;
    font-size: .8em; transform: translateY(20px); transition: opacity .5s ease, filter .5s ease, transform .5s ease; }
  .narr-tile.is-shown { transform: none; }
  .narr-tile.was-shown { filter: blur(8px); transform: none; }
  .narr-tile p, .narr-tile blockquote { margin: 0; } .msg-from { font-weight: 600; font-size: .85em; color: GrayText; }
  .popover { padding: 24px 32px; border-radius: 20px; background: Canvas; border: 1px solid GrayText;
    box-shadow: 0 16px 48px color-mix(in srgb, CanvasText 25%, transparent); transition: opacity .6s ease, filter .6s ease; }
  .popover:not(.is-visible) { filter: blur(12px); }
  .pop-panel { margin: 0; } .pop-panel figcaption { font-weight: 600; }
  .body--tiles { gap: 24px; align-content: center; }
  .text-tile { padding: 20px 24px; border-radius: 20px; background: Canvas; border: 1px solid GrayText; transition: opacity .5s ease; }
  .text-tile h3 { margin: 0 0 .4em; } .text-tile p, .text-tile ul { margin: 0; }
  .body--tiles.is-tight { gap: 10px; } .body--tiles.is-tight .text-tile { padding: 8px 12px; }
}
"""


def block(text: str, name: str) -> re.Match | None:
    """Find a named insertion block (``/* NAME:BEGIN */…/* NAME:END */`` or the HTML-comment form).

    Args:
        text: Skeleton or deck source.
        name: Block name, e.g. ``ENGINE``.

    Returns:
        The match (group 1 = current contents), or ``None``.
    """
    pat = (rf"(?:/\*|<!--) {name}:BEGIN (?:\*/|-->)(.*?)(?:/\*|<!--) {name}:END (?:\*/|-->)")
    return re.search(pat, text, re.S)


def fill(text: str, name: str, content: str) -> str:
    """Replace a named block's contents, keeping its markers.

    Args:
        text: Source containing the block.
        name: Block name.
        content: New contents.

    Returns:
        The source with the block filled.

    Raises:
        AssertionError: When the block is missing.
    """
    m = block(text, name)
    assert m, f"skeleton lacks the {name} block"
    return text[:m.start(1)] + "\n" + content + "\n" + text[m.end(1):]


def module_triggers(js: Path) -> list[str]:
    """Read a module file's ``Triggers:`` header: the simple selectors that make a deck need it.

    Args:
        js: A module file, ``modules/<name>.js``.

    Returns:
        Selectors, each ``[data-attr]`` or ``.class``; empty when the header is missing.
    """
    m = re.search(r"Triggers:\s*([^\n*]+)", js.read_text(encoding="utf-8"))
    return m.group(1).split() if m else []


class _Markup(HTMLParser):
    """Collects every attribute name and class token in a markup fragment."""

    def __init__(self) -> None:
        super().__init__()
        self.attrs: set[str] = set()
        self.classes: set[str] = set()

    def handle_starttag(self, tag, attrs):  # noqa: D102
        for k, v in attrs:
            self.attrs.add(k)
            if k == "class" and v:
                self.classes.update(v.split())

    handle_startendtag = handle_starttag


def detect_modules(slides: str) -> list[str]:
    """Name the modules a deck needs: those whose triggers appear in its slide markup.

    The inclusion rule the real assembler (a later spec) adopts: a module ships in a deck only when
    one of its trigger attributes or classes appears in the SLIDES block.

    Args:
        slides: Slide markup (the SLIDES block).

    Returns:
        Module names (file stems), sorted.
    """
    mk = _Markup()
    mk.feed(slides)
    found = []
    for js in sorted(MODULES_DIR.glob("*.js")):
        for t in module_triggers(js):
            if (t.startswith("[") and t.strip("[]") in mk.attrs) or (t.startswith(".") and t[1:] in mk.classes):
                found.append(js.stem)
                break
    return found


def assemble(out: Path, slides: str = FIXTURE_SLIDES, title: str = "Fixture Deck",
             subtitle: str = "Core engine", modules: str = "", css: str = FIXTURE_CSS) -> Path:
    """Inline the engine parts, the modules the slides need and ``slides`` into the skeleton.

    Module JS goes in the MODULES block (before the engine); module CSS is appended to the ARCH
    block after ``arch.css``. A deck whose slides trigger no module carries no module code.

    Args:
        out: Path of the HTML file to write.
        slides: Slide markup for the SLIDES block.
        title: Deck title (bar and ``<title>``).
        subtitle: Italic subtitle in the bar.
        modules: Extra module scripts for the MODULES block (after the detected ones).
        css: Stand-in design CSS for the DECK block.

    Returns:
        ``out``.
    """
    names = detect_modules(slides)
    js = [(MODULES_DIR / f"{n}.js").read_text(encoding="utf-8") for n in names]
    arch = [ARCH_CSS.read_text(encoding="utf-8")]
    arch += [(MODULES_DIR / f"{n}.css").read_text(encoding="utf-8") for n in names
             if (MODULES_DIR / f"{n}.css").is_file()]
    src = SKELETON.read_text(encoding="utf-8")
    src = src.replace("{{title}}", title).replace("{{subtitle}}", subtitle)
    src = fill(src, "ARCH", "\n".join(arch))
    src = fill(src, "DECK", css)
    src = fill(src, "MODULES", "\n".join(js + ([modules] if modules else [])))
    src = fill(src, "ENGINE", ENGINE_JS.read_text(encoding="utf-8"))
    src = fill(src, "SLIDES", slides)
    out.write_text(src, encoding="utf-8")
    return out


_BUSY = """sel => (sel ? [...document.querySelectorAll(sel)].flatMap(e => e.getAnimations({subtree: true}))
    : document.getAnimations()).filter(a => (a.playState === 'running' || a.pending)
    && isFinite(a.effect && a.effect.getComputedTiming().endTime))"""


def settle(page, quiet: int = 150, timeout: int = 15000) -> None:
    """Wait until no finite animation/transition runs and scrolling has stopped (never a fixed sleep).

    Args:
        page: Playwright page with a deck loaded.
        quiet: How long the page must stay calm, in ms.
        timeout: Give up after this many ms.
    """
    calm = page.evaluate(
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
    assert calm, f"page still animating after {timeout} ms"


def open_deck(page, path: Path) -> None:
    """Load a deck file and wait for the engine to be ready.

    Args:
        page: Playwright page.
        path: Deck HTML file.
    """
    page.goto(path.as_uri())
    page.wait_for_function("window.deck && window.deck.ready === true")


def state(page) -> dict:
    """Return ``window.deck.state()``.

    Args:
        page: Playwright page with a deck loaded.

    Returns:
        The engine state mapping (slide, index, step, steps).
    """
    return page.evaluate("deck.state()")


def opacity(page, sel: str) -> float:
    """Computed opacity of the first element matching ``sel``.

    Args:
        page: Playwright page.
        sel: CSS selector.

    Returns:
        The element's computed opacity.
    """
    return page.evaluate("s => +getComputedStyle(document.querySelector(s)).opacity", sel)
