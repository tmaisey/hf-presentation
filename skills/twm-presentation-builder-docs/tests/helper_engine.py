"""Helpers for engine and design-layer tests: assemble fixture decks from the skeleton and wait on state.

The assembler here is a test stand-in (the real one is a later spec): it inlines the engine parts
into the skeleton's marked blocks and writes one self-contained HTML file. ``assemble_themed`` adds
the shipped components layer, a generated palette/style and embedded fonts; ``layout_faults`` is a
generic layout guard (overlap/overflow/off-canvas per step).
"""

from __future__ import annotations

import re
from pathlib import Path

from helper_skill import REPO, SKILL_DIR

ENGINE_DIR = SKILL_DIR / "assets" / "engine"
ENGINE_JS = ENGINE_DIR / "engine.js"
ARCH_CSS = ENGINE_DIR / "arch.css"
SKELETON = SKILL_DIR / "assets" / "templates" / "deck-skeleton.html"
ARCHITECTURE = SKILL_DIR / "architecture" / "ARCHITECTURE.md"
LAYER_ORDER = "@layer arch, components, palette, style, deck;"
BLOCKS = ("FONTS", "ARCH", "COMPONENTS", "PALETTE", "STYLE", "DECK", "DEFS", "MODULES", "ENGINE")
REVIEW_SIZES = ((1920, 1080), (1280, 720), (1288, 598))
# organisations and the source deck's incident-specific modules/names (word-bounded regexes)
BANNED = (r"hugging", r"openai", r"modal\b", r"metr\b", r"deloitte", r"anthropic", r"incident", r"swarm",
          r"world", r"narr-", r"narration", r"popover", r"mirror", r"day0", r"tl-day")

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


def assemble(out: Path, slides: str = FIXTURE_SLIDES, title: str = "Fixture Deck",
             subtitle: str = "Core engine", modules: str = "", css: str = FIXTURE_CSS,
             components: str = "", palette: str = "", style: str = "", fonts: str = "") -> Path:
    """Inline the engine parts and ``slides`` into the skeleton and write one HTML file.

    Args:
        out: Path of the HTML file to write.
        slides: Slide markup for the SLIDES block.
        title: Deck title (bar and ``<title>``).
        subtitle: Italic subtitle in the bar.
        modules: Optional module scripts for the MODULES block.
        css: Stand-in design CSS for the DECK block.
        components: CSS for the COMPONENTS block (empty = none).
        palette: CSS for the PALETTE block (empty = none).
        style: CSS for the STYLE block (empty = none).
        fonts: ``@font-face`` CSS for the FONTS block (empty = none).

    Returns:
        ``out``.
    """
    src = SKELETON.read_text(encoding="utf-8")
    src = src.replace("{{title}}", title).replace("{{subtitle}}", subtitle)
    src = fill(src, "ARCH", ARCH_CSS.read_text(encoding="utf-8"))
    for name, content in (("FONTS", fonts), ("COMPONENTS", components), ("PALETTE", palette), ("STYLE", style)):
        if content:
            src = fill(src, name, content)
    src = fill(src, "DECK", css)
    src = fill(src, "MODULES", modules)
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


# ---------- themed assembly (components + generated palette/style), for design-layer tests ----------

COMPONENTS_CSS = SKILL_DIR / "assets" / "components" / "components.css"
FONT_DIR = REPO / "assets" / "fonts"   # dev-side copy of the deck's fonts (test-only; the assembler owns embedding)
FONT_FACES = (("Newsreader", "normal", "200 800", "newsreader-latin.woff2"),
              ("Newsreader", "italic", "200 800", "newsreader-italic-latin.woff2"),
              ("Inter", "normal", "100 900", "inter-latin.woff2"))

# Generic slides exercising every core component: lead + byline (ambient), flow body with points and an
# Insight, split body with a step list beside a figure (tiles, key tile, coloured edges, label, tag,
# annotation cards), stat beside a quote, table + caption, terms, prompts beside an in-flow message
# card, and a closing page. Five chapters.
COMPONENT_SLIDES = """
<section class="slide slide--lead" id="c-1" data-chapter="Opening" data-ambient>
  <h2 class="title">A calm editorial layer makes <em>any</em> talk easier to follow</h2>
  <div class="body"><p id="c1-sub">One component set, styled only through semantic tokens, so palette and style can swap freely</p></div>
  <p class="byline">A. Presenter, November 2026</p>
  <aside class="note" data-for="#c1-sub"><h3>Why a layer</h3><p>Components read roles, never raw values.</p>
    <a class="src" href="https://example.org/layer">Example source</a></aside>
</section>

<section class="slide" id="c-2" data-chapter="Method">
  <p class="kicker">02 · Method</p>
  <h2 class="title">Each input reveals one idea, and the slide waits for the next</h2>
  <div class="body">
    <p id="c2-lede">Content settles in when its slide becomes current, then builds one step per input.</p>
    <ul class="points">
      <li id="c2-a" data-show-at="1">A point appears at its step and keeps its space before then</li>
      <li id="c2-b" data-show-at="2">Earlier points stay, so the argument accumulates on screen</li>
    </ul>
  </div>
  <aside class="overlay overlay--insight" id="c2-insight" data-at="3">
    <p>An Insight card frosts over the body for one step, then racks out of focus as the slide sharpens.</p>
  </aside>
  <aside class="note" data-for="#c2-lede"><h3>Settling in</h3><p>Entry is a rise and fade, staggered.</p>
    <a class="src" href="https://example.org/entry">Entry source</a></aside>
  <aside class="note" data-for="#c2-b"><h3>Accumulating points</h3><p>Nothing is replaced; the list grows.</p>
    <a class="src" href="https://example.org/points">Points source</a></aside>
</section>

<section class="slide" id="c-3" data-chapter="Method">
  <p class="kicker">02 · Method</p>
  <h2 class="title">Diagrams build beside a numbered step list</h2>
  <div class="body body--split">
    <div>
      <ol class="steps">
        <li id="c3-s1" data-show-at="1">A source tile feeds a checker</li>
        <li id="c3-s2" data-show-at="2">Verified results flow back as reward</li>
        <li id="c3-s3" data-show-at="3">The key tile marks what matters most</li>
      </ol>
    </div>
    <div class="fig">
      <svg class="diagram diagram--compact" viewBox="0 0 760 420" role="img" aria-label="Three tiles: a source, a checker and a key outcome">
        <g class="layer-edges">
          <path class="edge" id="c3-e1" data-from="#c3-a" data-to="#c3-b" marker-end="url(#arr)" data-show-at="1"/>
          <path class="edge edge--ok" id="c3-e2" data-from="#c3-b" data-to="#c3-c" marker-end="url(#arr-ok)" data-show-at="2"/>
          <path class="edge edge--loss" id="c3-e3" data-from="#c3-c" data-to="#c3-a" marker-end="url(#arr-loss)" data-show-at="3"/>
        </g>
        <g class="layer-nodes">
          <g class="tile" id="c3-a"><rect x="10" y="20" width="260" height="120"/><text class="tile-title">Source</text><text class="tile-sub">many tasks</text></g>
          <g class="tile" id="c3-b"><rect x="490" y="20" width="260" height="120"/><text class="tile-title">Checker</text></g>
        </g>
        <g class="layer-key">
          <g class="tile tile--key" id="c3-c" data-show-at="2"><rect x="250" y="280" width="260" height="120"/><text class="tile-title">Outcome</text></g>
        </g>
        <g class="layer-labels">
          <text class="label" x="380" y="60">FLOW</text>
          <text class="tag" x="660" y="220" data-show-at="2">VERIFIED</text>
          <text class="tag tag--loss" x="100" y="220" data-show-at="3">MISSED</text>
        </g>
      </svg>
      <div class="fig-notes">
        <p class="annot" id="c3-n1" data-show-at="2" data-hide-at="3"><strong class="annot-lead">Verified:</strong> only checked results are rewarded.</p>
        <p class="annot" id="c3-n2" data-show-at="3"><strong class="annot-lead annot-lead--loss">Missed:</strong> an unchecked shortcut is rewarded too.</p>
      </div>
    </div>
  </div>
  <aside class="note" data-for="#c3-b"><h3>The checker</h3><p>A note on a diagram tile.</p>
    <a class="src" href="https://example.org/checker">Checker source</a></aside>
</section>

<section class="slide" id="c-4" data-chapter="Evidence">
  <p class="kicker">03 · Evidence</p>
  <h2 class="title">One number carries the slide, the quote frames it</h2>
  <div class="body body--split">
    <p class="stat" id="c4-stat"><strong>1,200</strong>independent runs reviewed by hand</p>
    <div>
      <blockquote id="c4-quote" data-show-at="1">A sparse slide with one large figure reads faster than a dense table of the same facts</blockquote>
      <p class="cite" data-show-at="1">Example Review · <a href="https://example.org/review">Example report</a></p>
    </div>
  </div>
</section>

<section class="slide" id="c-5" data-chapter="Evidence">
  <p class="kicker">03 · Evidence</p>
  <h2 class="title">Controls map to the failures they would have caught</h2>
  <div class="body">
    <table>
      <thead><tr><th>Control</th><th>Failure it addresses</th></tr></thead>
      <tbody>
        <tr><td>Independent checker</td><td>Results were scored by the system being trained</td></tr>
        <tr data-show-at="1"><td>Scoped credentials</td><td>One shared credential opened every environment</td></tr>
        <tr data-show-at="2"><td>Alert ownership</td><td>An early alert was dismissed without review</td></tr>
      </tbody>
    </table>
    <p class="caption">Illustrative rows; the reader note carries the sources.</p>
  </div>
</section>

<section class="slide" id="c-6" data-chapter="Terms">
  <p class="kicker">04 · Terms</p>
  <h2 class="title">Three terms the rest of the talk relies on</h2>
  <div class="body">
    <dl class="terms">
      <div><dt>Reward</dt><dd>The signal a system is trained to increase</dd></div>
      <div data-show-at="1"><dt>Proxy</dt><dd>A measurable stand-in for what we actually want</dd></div>
      <div data-show-at="2"><dt>Shortcut</dt><dd>A way to raise the proxy without the real behaviour</dd></div>
    </dl>
  </div>
</section>

<section class="slide" id="c-7" data-chapter="Close" data-ambient>
  <p class="kicker">05 · Close</p>
  <h2 class="title">Questions for discussion</h2>
  <div class="body body--split body--flip">
    <ol class="prompts">
      <li class="prompt" id="c7-q1">Where would these risks show up in your own projects?</li>
      <li class="prompt" id="c7-q2">Which control would you add first, and who would own it?</li>
    </ol>
    <div class="msg-card" id="c7-msg">
      <p class="msg-agent">Agent · run log</p>
      <blockquote class="msg-text">The checker accepts any file with the right name, so the task is done.</blockquote>
      <p class="cite"><a href="https://example.org/log">Example log</a></p>
    </div>
  </div>
</section>

<section class="slide slide--lead slide--end" id="c-8" data-chapter="Close" data-ambient>
  <h2 class="title">Thank you</h2>
</section>
"""


def fonts_css() -> str:
    """Return ``@font-face`` rules embedding the dev-side woff2 files as base64 (test-only).

    Returns:
        CSS for the FONTS block.
    """
    import base64
    rules = []
    for family, style, weight, file in FONT_FACES:
        data = base64.b64encode((FONT_DIR / file).read_bytes()).decode("ascii")
        rules.append(f'@font-face {{ font-family: "{family}"; font-style: {style}; font-weight: {weight}; '
                     f'font-display: block; src: url(data:font/woff2;base64,{data}) format("woff2"); }}')
    return "\n".join(rules)


def components_css() -> str:
    """Return the shipped components CSS, or ``""`` before it exists (so tests fail on assertions).

    Returns:
        CSS text.
    """
    return COMPONENTS_CSS.read_text(encoding="utf-8") if COMPONENTS_CSS.exists() else ""


def theme_blocks(palette: str = "paper-green", style: str = "editorial") -> tuple[str, str]:
    """Generate the PALETTE and STYLE block contents with the shipped generator.

    Args:
        palette: Shipped palette name.
        style: Shipped style name.

    Returns:
        ``(palette_css, style_css)``.
    """
    from helper_tokens import load_script
    tok = load_script()
    theme = tok.load(palette, style)
    return tok.palette_css(theme), tok.style_css(theme)


def assemble_themed(out: Path, slides: str = COMPONENT_SLIDES, title: str = "Component Fixture",
                    subtitle: str = "Layout layer", components: str | None = None, deck_css: str = "",
                    palette: str = "paper-green", style: str = "editorial") -> Path:
    """Assemble a deck with the shipped components layer, a generated theme and embedded fonts.

    Args:
        out: Path of the HTML file to write.
        slides: Slide markup.
        title: Deck title.
        subtitle: Deck subtitle.
        components: Components CSS (default: the shipped ``components.css``).
        deck_css: Optional DECK-layer CSS (tests use it to plant faults).
        palette: Palette name.
        style: Style name.

    Returns:
        ``out``.
    """
    pal, sty = theme_blocks(palette, style)
    comp = components_css() if components is None else components
    return assemble(out, slides=slides, title=title, subtitle=subtitle, css=deck_css,
                    components=comp, palette=pal, style=sty, fonts=fonts_css())


# ---------- layout guard (generic port of the deck's S-030 idea) ----------

# Faults on the current slide at the current step: visible text off the slide, text clipped by an overflow
# box, a block or text covering a title's glyph lines, a title under the bar, a visible overlay or card under
# the always-visible Notes button, and the bar title meeting the agenda.
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
  const outside = (r, b) => r.left < b.left - 1 || r.right > b.right + 1 || r.top < b.top - 1 || r.bottom > b.bottom + 1;
  const hit = (a, b) => a.left < b.right - 1 && a.right > b.left + 1 && a.top < b.bottom - 1 && a.bottom > b.top + 1;
  const TEXT = '.title, .kicker, p, li, blockquote, dt, dd, th, td, h3, text, .msg-agent, .byline';
  const inNote = e => !!e.closest('.note');
  const texts = [];
  s.querySelectorAll(TEXT).forEach(e => {
    if (inNote(e) || !shown(e)) return;
    texts.push(e);
    const r = e.getBoundingClientRect();
    if (outside(r, sr)) bad.push('off-slide: ' + name(e));
    if (e instanceof HTMLElement && getComputedStyle(e).overflowX !== 'visible' && e.scrollWidth > e.clientWidth + 2)
      bad.push('clipped (x): ' + name(e));
    if (e instanceof HTMLElement && getComputedStyle(e).overflowY !== 'visible' && e.scrollHeight > e.clientHeight + 2)
      bad.push('clipped (y): ' + name(e));
    for (let a = e.parentElement; a && a !== s.parentElement; a = a.parentElement) {
      const c = getComputedStyle(a);
      if (c.overflowX === 'visible' && c.overflowY === 'visible') continue;
      if (outside(r, a.getBoundingClientRect())) { bad.push('clipped by ' + name(a).split(' ')[0] + ': ' + name(e)); break; }
    }
  });
  s.querySelectorAll('.body, .steps, .overlay, table, .fig-notes').forEach(e => {
    if (inNote(e) || !shown(e)) return;
    const c = getComputedStyle(e);
    if (c.overflowY !== 'visible' && e.scrollHeight > e.clientHeight + 2) bad.push('clipped (y): ' + name(e));
    if (c.overflowX !== 'visible' && e.scrollWidth > e.clientWidth + 2) bad.push('clipped (x): ' + name(e));
  });
  const bar = document.querySelector('.bar').getBoundingClientRect();
  const BLOCK = '.body, .steps, svg.diagram, .overlay, table, .prompts, .msg-card, .fig-notes';
  const blockers = [...s.querySelectorAll(BLOCK)].filter(e => !inNote(e) && shown(e))
    .concat(texts.filter(e => !e.matches('.title, .kicker') && !e.closest('.title')));
  s.querySelectorAll('.title').forEach(t => {
    if (!shown(t)) return;
    const range = document.createRange(); range.selectNodeContents(t);
    const lines = [...range.getClientRects()].filter(r => r.width > 0 && r.height > 0);
    if (!lines.length) return;
    if (Math.min(...lines.map(r => r.top)) < bar.bottom - 1) bad.push('title under bar: ' + name(t));
    if (lines.some(r => outside(r, sr))) bad.push('off-slide: ' + name(t));
    blockers.forEach(b => {
      if (b.contains(t)) return;
      const br = b.getBoundingClientRect();
      if (lines.some(l => hit(l, br))) bad.push('covers title: ' + name(b));
    });
  });
  const btn = document.querySelector('.notes-btn').getBoundingClientRect();
  s.querySelectorAll('.overlay, .msg-card, .fig-notes > *').forEach(e => {
    if (shown(e) && hit(e.getBoundingClientRect(), btn)) bad.push('under notes button: ' + name(e)); });
  const bt = document.querySelector('.bar-title').getBoundingClientRect();
  const compact = !!document.querySelector('.bar--compact');
  const nav = document.querySelector(compact ? '.nav-current' : '.agenda');
  if (nav && hit(bt, nav.getBoundingClientRect())) bad.push('bar title meets agenda');
  if (bt.right > innerWidth || bt.left < 0) bad.push('bar title off-screen');
  return [...new Set(bad)];
}"""


def layout_faults(page, slide_id: str, shoot=None) -> list[str]:
    """Step through one slide from step 0 to its last step and collect every layout fault.

    Args:
        page: Playwright page with a deck loaded at the viewport under test.
        slide_id: The slide's element id.
        shoot: Optional ``callable(step)`` run after each step settles (e.g. to save a screenshot).

    Returns:
        Fault strings ``"<slide>@<step>: <fault>"``; empty when the slide is clean at every step.
    """
    steps = dict(page.evaluate("deck.plan()"))[slide_id]
    faults: list[str] = []
    for k in range(steps + 1):
        page.evaluate("([id, k]) => deck.goto(id, k)", [slide_id, k])
        page.wait_for_function("([id, k]) => deck.state().slide === id && deck.state().step === k",
                               arg=[slide_id, k])
        settle(page)
        if shoot:
            shoot(k)
        faults += [f"{slide_id}@{k}: {f}" for f in page.evaluate(LAYOUT_CHECK, slide_id)]
    return faults
