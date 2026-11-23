"""Spec: PB-007

Editorial theme from the HF deck: the skill's defaults (paper-green palette, editorial style, components
layer, engine and modules) rebuild a representative subset of the accepted deck-v2 (title, concepts
diagram + Insight, two scene slides with pop-overs and narration, a tile row over the backdrop, the end)
under the skill's authoring contract, as the worked example's gold reference in ``examples/hf-incident``
(``slides.html`` + the assembled ``deck.html``), and the result looks like deck-v2 at the review sizes,
with the pop-over tile opaque and shadowed (presenter, 23 Nov).

Coverage: happy (the example deck is exactly the assembler's output for its slides, passes the endpoint
check and renders offline without errors; slide ids, steps and copy are deck-v2's; computed styles of the
key parts match deck-v2's same slide in the same browser; key boxes sit where deck-v2 puts them; mean pixel
difference per slide and step at 1920×1080 stays under its bound; layout guard clean on every slide × step ×
review size) · edge (the short-wide window; the scene's place and scale; deck-v2's timeline hides entries
ahead of their step) · negative (the pop-over tile is never frosted; the image metric rejects a different
slide; slides carry no styling or scripts and nothing points out of the skill).
"""

from __future__ import annotations

import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest
from PIL import Image, ImageChops, ImageStat
from playwright.sync_api import sync_playwright

from helper_engine import ASSEMBLE, REVIEW_SIZES, block, layout_faults, open_deck, settle
from helper_skill import SKILL_DIR
from helper_tokens import DECK_V2

EXAMPLE = SKILL_DIR / "examples" / "hf-incident"
SLIDES = EXAMPLE / "slides.html"
DECK = EXAMPLE / "deck.html"
TITLE, SUBTITLE = "The Hugging Face Attack", "Misaligned Agents"
PORTED = ["s-1", "s-2", "s-4", "s-5", "s-9", "s-12"]
ARTIFACTS = Path(__file__).parent / "artifacts" / "pb-007"
BAR_CROP = 66   # the bar (64 px) and its progress hairline: agenda and progress differ by design (6 of 12 slides)
# ambient orbs are seeded by a slide's place among the ambient slides (s-12 is 2nd here, 3rd in deck-v2) and drift
# with time; their look is PB-004's parity test, so both decks hide them for the image comparison
HIDE_AMBIENT = "document.querySelectorAll('.ambient, .orb').forEach(a => a.style.visibility = 'hidden')"
TYPE = ("fontFamily", "fontSize", "fontWeight", "fontStyle", "lineHeight", "letterSpacing", "color", "textTransform")
CARD = ("backgroundColor", "backdropFilter", "borderRadius", "boxShadow", "paddingTop", "paddingLeft")

# Mean absolute per-channel difference (0–255) over the slide area below the bar (ambient hidden), per slide,
# at 1920×1080. A missing pop-over card or Insight costs ~8–15 and an unstyled scene ~20, a different slide
# > 8 (the negative control). Bounds are the measured maximum plus headroom. The scene slides carry deck-v2's
# world as static markup without its engine-only beats (radar sweeps, pulses, flying notes, day tags, skull
# marks: ARCHITECTURE §9 leaves them out) and the narration module places tiles by its own seeded layout, so
# their bound is looser; the backdrop is that scene blurred at 42%.
# measured (23 Nov): s-1, s-2, s-12 0.00 · s-4 ≤ 2.73 · s-5 ≤ 3.16 · s-9 ≤ 0.85
BOUNDS = {"s-1": 0.5, "s-2": 0.5, "s-4": 3.5, "s-5": 4.0, "s-9": 1.5, "s-12": 0.5}
DIFFERENT = 8.0


# ---------- fixtures ----------

@pytest.fixture(scope="module")
def browser():
    """System Chrome, once per module (no conftest: other suites share this folder)."""
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        yield b
        b.close()


def _open(browser, path, width=1920, height=1080):
    c = browser.new_context(viewport={"width": width, "height": height})
    pg = c.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and errors.append(m.text))
    open_deck(pg, path)
    pg.wait_for_function("document.fonts.status === 'loaded'")
    return c, pg, errors


@pytest.fixture(scope="module")
def pages(browser):
    """The example deck and deck-v2 side by side at 1920×1080 in the same browser."""
    assert DECK.is_file(), "examples/hf-incident/deck.html missing"
    ce, ex, ee = _open(browser, DECK)
    cv, v2, ev = _open(browser, DECK_V2)
    yield ex, v2
    ce.close()
    cv.close()
    assert ee == [] and ev == [], f"page errors: {ee + ev}"


def _at(page, slide, step):
    page.evaluate("([s, k]) => deck.goto(s, k)", [slide, step])
    page.wait_for_function("([s, k]) => deck.state().slide === s && deck.state().step === k", arg=[slide, step])
    settle(page)


PROBE = """([sel, props, pseudo]) => { const e = document.querySelector(sel);
  if (!e) return null; const s = getComputedStyle(e, pseudo || null);
  return Object.fromEntries(props.map(p => [p, s[p]])); }"""


def _probe(page, slide, step, sel, props, pseudo=None):
    _at(page, slide, step)
    got = page.evaluate(PROBE, [sel, list(props), pseudo])
    assert got is not None, f"{sel} not found on {slide}"
    return {k: (re.sub(r'["\']', "", v) if k == "fontFamily" else v) for k, v in got.items()}


# ---------- the example: assembled, safe, self-contained ----------

def test_example_deck_is_the_assemblers_output_for_its_slides(tmp_path):
    """The committed deck is regenerated, never hand-edited: same bytes as ``assemble.py new`` today."""
    out = tmp_path / "deck.html"
    r = subprocess.run([sys.executable, str(ASSEMBLE), "new", str(out), "--title", TITLE, "--subtitle", SUBTITLE,
                        "--slides", str(SLIDES)], capture_output=True, text=True, cwd=SKILL_DIR)
    assert r.returncode == 0, r.stderr
    assert DECK.is_file() and out.read_bytes() == DECK.read_bytes(), "rebuild examples/hf-incident/deck.html"


def test_example_deck_passes_the_endpoint_check():
    r = subprocess.run([sys.executable, str(ASSEMBLE), "check", str(DECK)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_example_slides_carry_no_styling_and_stay_inside_the_skill():
    src = SLIDES.read_text(encoding="utf-8")
    assert not re.search(r"<style|<script|\sstyle\s*=", src, re.I)
    assert not re.search(r"#[0-9a-f]{3,8}\b(?![-\w])|rgba?\(|hsla?\(", src.replace("url(#", "url("), re.I)
    for f in (SLIDES, DECK):
        text = f.read_text(encoding="utf-8")
        assert not re.search(r"(?<![\w.])\.\./|/Users/|/home/|~/", text), f.name
    assert block(DECK.read_text(encoding="utf-8"), "SLIDES").group(1).strip() == src.strip()


def test_example_renders_offline_without_errors(browser):
    ctx = browser.new_context(viewport={"width": 1280, "height": 720})
    page = ctx.new_page()
    requests, errors = [], []
    page.route("**/*", lambda r: r.continue_() if r.request.url.startswith(("file:", "data:")) else
               (requests.append(r.request.url), r.abort()))
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: m.type == "error" and errors.append(m.text))
    open_deck(page, DECK)
    for sid, last in page.evaluate("deck.plan()"):
        _at(page, sid, last)
    ctx.close()
    assert requests == [] and errors == []


# ---------- faithful port: ids, steps, verbatim copy ----------

class _Text(HTMLParser):
    """Visible copy of a section: text nodes, whitespace-normalised (notes included: they are copy too)."""

    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        if data.strip():
            self.parts.append(" ".join(data.split()))


def _section(src: str, sid: str) -> str:
    m = re.search(rf'<section class="[^"]*" id="{sid}"[^>]*>.*?</section>', src, re.S)
    assert m, sid
    return m.group(0)


def _copy(html: str) -> list[str]:
    p = _Text()
    p.feed(html)
    return p.parts


def test_ported_slides_are_deck_v2s_subset_in_order(pages):
    ex, v2 = pages
    plan, ref = ex.evaluate("deck.plan()"), dict(v2.evaluate("deck.plan()"))
    assert [s for s, _ in plan] == PORTED
    assert {s: n for s, n in plan} == {s: ref[s] for s in PORTED}, "same steps per slide as deck-v2"


@pytest.mark.parametrize("sid", PORTED)
def test_copy_is_verbatim_from_deck_v2(sid):
    """Sourced, approved copy: every text run (incl. notes, pop-over art labels) as in deck-v2."""
    ours = _copy(_section(SLIDES.read_text(encoding="utf-8"), sid))
    theirs = _copy(_section(DECK_V2.read_text(encoding="utf-8"), sid))
    assert ours == theirs


# ---------- computed styles match deck-v2's same slide ----------

# (what, slide, step, example selector, deck-v2 selector (None = same), properties, pseudo)
PAIRS = [
    ("lead title", "s-1", 0, "#s-1 > .title", None, TYPE + ("maxWidth",), None),
    ("lead body", "s-1", 0, "#s1-sub", None, TYPE + ("maxWidth",), None),
    ("byline", "s-1", 0, "#s-1 .byline", None, TYPE + ("left", "bottom"), None),
    ("kicker", "s-2", 0, "#s-2 > .kicker", None, TYPE, None),
    ("title", "s-2", 0, "#s-2 > .title", None, TYPE + ("maxWidth", "marginTop", "marginBottom"), None),
    ("body text", "s-2", 0, "#s2-train", None, TYPE + ("maxWidth",), None),
    ("annotation", "s-2", 2, "#s2-why", None, CARD + ("fontSize", "color"), None),
    ("annotation lead", "s-2", 2, "#s2-why .annot-lead", None, ("fontWeight", "color"), None),
    ("Insight card", "s-2", 5, "#s-2 .overlay--insight", None, CARD + ("width", "opacity", "filter", "transform"), None),
    ("Insight text", "s-2", 5, "#s-2 .overlay--insight p", None, TYPE, None),
    ("softened body", "s-2", 5, "#s-2 > .body", None, ("filter", "opacity"), None),
    ("tile", "s-2", 4, "#s2-model rect", None, ("fill", "stroke", "filter", "rx"), None),
    ("tile title", "s-2", 4, "#s2-model .tile-title", None, ("fontFamily", "fontWeight", "fontSize", "fill"), None),
    ("edge", "s-2", 4, "#s-2 path.edge:not(.edge--ok):not(.edge--loss)", None, ("stroke", "strokeWidth", "strokeLinecap"), None),
    ("edge ok", "s-2", 4, "#s2-pass", None, ("stroke", "strokeWidth"), None),
    ("edge loss", "s-2", 4, "#s2-hack-in", None, ("stroke", "strokeWidth"), None),
    ("badge disc", "s-2", 4, "#s2-tick circle", None, ("fill", "stroke", "strokeWidth"), None),
    ("badge mark", "s-2", 4, "#s2-tick path", None, ("fill", "stroke", "strokeWidth", "strokeLinecap"), None),
    ("scene grid", "s-4", 0, "#s-4", None, ("gridTemplateColumns", "columnGap", "paddingTop"), None),
    ("timeline entry", "s-4", 3, "#s4-t2", None, ("fontSize", "lineHeight", "paddingTop", "paddingLeft", "color", "opacity"), None),
    ("timeline date", "s-4", 3, "#s4-t2 strong", None, ("fontWeight", "color", "fontSize"), None),
    ("timeline disc", "s-4", 3, "#s4-t2", None, ("backgroundColor", "color", "width", "top"), "::before"),
    ("timeline sub-entry", "s-4", 2, "#s4-t1b", None, ("fontSize", "paddingTop", "paddingBottom", "color", "opacity"), None),
    ("timeline sub dash", "s-4", 2, "#s4-t1b", None, ("backgroundColor", "width", "height", "borderRadius", "left", "top"), "::before"),
    ("timeline ahead of its step", "s-4", 0, "#s4-t2", None, ("opacity",), None),
    ("scene on", "s-4", 0, ".scene", ".world", ("opacity", "filter"), None),
    ("scene soft", "s-4", 1, ".scene", ".world", ("opacity", "filter"), None),
    ("scene backdrop", "s-9", 0, ".scene", ".world", ("opacity", "filter"), None),
    ("domain", "s-4", 0, "#w-oai rect", None, ("fill", "stroke"), None),
    ("domain label", "s-4", 0, "#w-oai .domain-label", None, ("fontFamily", "fontWeight", "fontSize", "letterSpacing", "fill"), None),
    ("domain out", "s-4", 0, "#w-net rect", None, ("fill",), None),
    ("dimmed part", "s-4", 0, "#w-net", None, ("opacity",), None),
    ("scene tile", "s-4", 0, "#w-mirror rect", None, ("fill", "filter", "rx"), None),
    ("scene tile title", "s-4", 0, "#w-mirror .tile-title", None, ("fontFamily", "fontWeight", "fontSize", "fill"), None),
    ("node dot", "s-4", 0, "#w-eval circle", None, ("fill", "stroke", "strokeWidth"), None),
    ("link", "s-4", 0, "#w-eval-links line", None, ("stroke", "strokeWidth", "opacity"), None),
    ("bold link", "s-4", 3, "#w-admin line", None, ("stroke", "strokeWidth", "opacity", "strokeLinecap"), None),
    ("ring", "s-4", 3, "#w-admin-ring circle", None, ("fill", "stroke", "strokeWidth"), None),
    ("loss badge", "s-4", 3, "#w-lock circle", None, ("fill",), None),
    ("loss badge mark", "s-4", 3, "#w-lock path", None, ("fill", "stroke", "strokeWidth"), None),
    ("glyph", "s-4", 5, "#w-flood path", None, ("fill", "stroke", "strokeWidth", "filter"), None),
    ("lit link", "s-5", 2, "#w-swarm-links line", None, ("stroke", "strokeWidth", "opacity"), None),
    ("folder glyph", "s-5", 2, "#w-folders path", None, ("fill", "stroke"), None),
    ("ink dot", "s-5", 5, "#w-coords circle", None, ("fill", "stroke", "strokeWidth"), None),
    ("ink link", "s-5", 5, "#w-coord-links line", None, ("stroke", "strokeWidth", "opacity"), None),
    ("loss dot", "s-5", 7, "#w-sacrificed circle", None, ("fill", "stroke", "opacity"), None),
    # deck-v2's engine shrinks its key to fit a fourth entry the subset never shows, so size and gap are not compared
    ("scene key", "s-5", 7, ".scene-key", ".world-key", ("color", "display", "alignItems", "marginTop", "whiteSpace"), None),
    # width and place are the narration module's seeded layout (generalised from deck-v2's), not the look
    ("narration tile", "s-4", 3, "#s-4 .narr-tile.is-shown", None, CARD + ("opacity", "filter", "transform"), None),
    ("narration sender", "s-4", 3, "#s-4 .narr-tile.is-shown .msg-agent", None, TYPE + ("marginBottom",), None),
    ("narration quote", "s-4", 3, "#s-4 .narr-tile.is-shown .msg-text", None, TYPE, None),
    ("fact tile, no quote marks", "s-4", 5, "#s-4 .narr-tile--fact .msg-text", None, ("content",), "::before"),
    ("pop-over", "s-4", 1, "#s4-pop", None, ("display", "columnGap", "opacity", "filter", "transform", "visibility", "alignSelf"), None),
    ("pop-over tile", "s-4", 2, "#s4-pop-flag", None, CARD + ("opacity",), None),
    ("pop-over tag", "s-4", 2, "#s4-pop-flag .pop-tag", None, TYPE + ("display", "marginBottom"), None),
    ("pop-over caption", "s-4", 2, "#s4-pop-flag figcaption", None, TYPE, None),
    ("pop-over note", "s-4", 2, "#s4-pop-flag > p", None, TYPE, None),
    ("art", "s-4", 2, "#s4-pop-flag .art", "#s4-pop-flag .pop-art", ("maxHeight", "display"), None),
    ("art frame", "s-4", 2, "#s4-pop-flag .art-frame", "#s4-pop-flag .pa-box", ("fill", "stroke", "strokeWidth"), None),
    ("art box", "s-4", 2, "#s4-pop-flag .art-box", "#s4-pop-flag .pa-lib", ("fill", "stroke", "strokeWidth"), None),
    ("art text", "s-4", 2, "#s4-pop-flag .art-text", "#s4-pop-flag .pa-lib-text", ("fontFamily", "fontSize", "fontWeight", "fill", "textAnchor"), None),
    ("art actor", "s-4", 2, "#s4-pop-flag .art-actor", "#s4-pop-flag .pa-agent", ("fill", "stroke", "strokeWidth"), None),
    ("art path", "s-4", 2, "#s4-pop-flag .art-path", "#s4-pop-flag .pa-arrow", ("fill", "stroke", "strokeWidth", "strokeLinecap"), None),
    ("art pill", "s-4", 2, "#s4-pop-flag .art-pill rect", "#s4-pop-flag .pa-reward rect", ("fill",), None),
    ("art pill text", "s-4", 2, "#s4-pop-flag .art-pill text", "#s4-pop-flag .pa-reward text", ("fontFamily", "fontSize", "fontWeight", "fill"), None),
    ("art mark", "s-4", 2, "#s4-pop-flag .art-mark", "#s4-pop-flag .pa-tick", ("fill", "stroke", "strokeWidth"), None),
    ("art flag", "s-4", 2, "#s4-pop-flag .art-flag path", "#s4-pop-flag .pa-flag path", ("fill", "stroke"), None),
    ("art sealed flag", "s-4", 2, "#s4-pop-nosol .art-flag--sealed path", "#s4-pop-nosol .pa-flag--sealed path", ("fill", "stroke"), None),
    ("art wall", "s-4", 2, "#s4-pop-nosol .art-wall", "#s4-pop-nosol .pa-wall", ("stroke", "strokeWidth"), None),
    ("wide pop-over tile", "s-5", 4, "#s5-pop-programme", None, CARD, None),
    ("art card", "s-5", 4, "#s5-pop-programme .art-card rect", "#s5-pop-programme .pa-ws rect", ("fill", "stroke", "strokeWidth"), None),
    ("art title", "s-5", 4, "#s5-pop-programme .art-title", "#s5-pop-programme .pa-ws-title", ("fontSize", "fontWeight", "fill"), None),
    ("art sub", "s-5", 4, "#s5-pop-programme .art-sub", "#s5-pop-programme .pa-ws-sub", ("fontSize", "fontWeight", "fill"), None),
    ("art lead", "s-5", 4, "#s5-pop-programme .art-lead", "#s5-pop-programme .pa-ws-lead", ("fontSize", "fontWeight", "fill"), None),
    ("art ink actor", "s-5", 4, "#s5-pop-programme .art-actor--ink", "#s5-pop-programme .pa-coord", ("fill",), None),
    ("art soft path", "s-5", 4, "#s5-pop-programme .art-path--soft", "#s5-pop-programme .pa-branch", ("stroke", "strokeWidth"), None),
    ("art doc", "s-5", 3, "#s5-pop-poison .art-doc", "#s5-pop-poison .pa-doc", ("fill", "stroke", "strokeWidth"), None),
    ("art bubble", "s-5", 3, "#s5-pop-poison .art-bubble rect", "#s5-pop-poison .pa-imagined rect", ("fill", "stroke", "strokeWidth"), None),
    ("art cross", "s-5", 3, "#s5-pop-poison .art-cross", "#s5-pop-poison .pa-cross", ("stroke", "strokeWidth"), None),
    ("tile row", "s-9", 3, "#s-9 .body--tiles", None, ("columnGap", "alignSelf", "marginBottom"), None),
    ("text tile", "s-9", 3, "#s9-t1", None, CARD + ("opacity", "transform", "rowGap"), None),
    ("text tile heading", "s-9", 3, "#s9-t1 h3", None, TYPE, None),
    ("text tile point", "s-9", 3, "#s9-t1 .points li", None, TYPE, None),
    ("text tile quote", "s-9", 3, "#s9-q1", None, TYPE, None),
    ("closing title", "s-12", 0, "#s-12 > .title", None, TYPE, None),
]


@pytest.mark.parametrize("what, sid, k, sel, ref, props, pseudo", PAIRS, ids=[p[0] for p in PAIRS])
def test_part_computes_like_deck_v2(pages, what, sid, k, sel, ref, props, pseudo):
    ex, v2 = pages
    want = _probe(v2, sid, k, ref or sel, props, pseudo)
    got = _probe(ex, sid, k, sel, props, pseudo)
    assert got == want, what


def test_popover_tile_is_opaque_and_shadowed(pages):
    """Presenter, 23 Nov: an opaque tile with a shadow, never a frosted (translucent, blurred) one."""
    ex, _ = pages
    got = _probe(ex, "s-4", 2, "#s4-pop-flag", ("backgroundColor", "backdropFilter", "boxShadow"))
    assert re.fullmatch(r"rgb\(\d+, \d+, \d+\)", got["backgroundColor"]), f"alpha must be 1: {got['backgroundColor']}"
    assert got["backdropFilter"] == "none" and got["boxShadow"] != "none", got


# ---------- key boxes sit where deck-v2 puts them ----------

# (slide, step, selector): same id in both decks; boxes compared in CSS px at 1920×1080
BOXES = [
    ("s-1", 0, "#s-1 > .title"), ("s-1", 0, "#s1-sub"), ("s-1", 0, "#s-1 .byline"),
    ("s-2", 0, "#s-2 > .title"), ("s-2", 0, "#s2-train"), ("s-2", 4, "#s2-model rect"), ("s-2", 4, "#s2-scorer rect"),
    ("s-2", 4, "#s2-hack"), ("s-2", 5, "#s-2 .overlay--insight"),
    ("s-4", 0, "#s-4 > .title"), ("s-4", 3, "#s4-t2"), ("s-4", 0, "#w-mirror rect"), ("s-4", 0, "#w-oai rect"),
    ("s-4", 2, "#s4-pop-flag"), ("s-4", 2, "#s4-pop-nosol"), ("s-4", 7, "#s4-insight"),
    ("s-5", 6, "#w-scorer rect"), ("s-5", 4, "#s5-pop-programme"), ("s-5", 8, "#s5-t3"),
    ("s-9", 3, "#s9-t1"), ("s-9", 3, "#s9-t3"), ("s-12", 0, "#s-12 > .title"),
]
TOLERANCE = 3   # px: sub-pixel layout and font hinting, never a moved block


@pytest.mark.parametrize("sid, k, sel", BOXES, ids=[f"{b[0]}@{b[1]} {b[2]}" for b in BOXES])
def test_box_sits_where_deck_v2_puts_it(pages, sid, k, sel):
    js = "s => { const r = document.querySelector(s).getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }"
    ex, v2 = pages
    _at(v2, sid, k)
    want = v2.evaluate(js, sel)
    _at(ex, sid, k)
    got = ex.evaluate(js, sel)
    assert all(abs(a - b) <= TOLERANCE for a, b in zip(got, want)), f"{sel}: {got} vs {want}"


# ---------- image comparison at 1920×1080 ----------

def _shots(browser, path, tag, w=1920, h=1080, slides=PORTED) -> dict[tuple[str, int], Path]:
    """Screenshot every step of the given slides into the artifacts folder."""
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    c, pg, errors = _open(browser, path, w, h)
    plan = dict(pg.evaluate("deck.plan()"))
    pg.evaluate(HIDE_AMBIENT)
    out = {}
    for sid in slides:
        for k in range(plan[sid] + 1):
            _at(pg, sid, k)
            f = ARTIFACTS / f"{sid}-{k}-{w}x{h}-{tag}.png"
            pg.screenshot(path=str(f))
            out[(sid, k)] = f
    c.close()
    assert errors == [], errors
    return out


@pytest.fixture(scope="module")
def shots(browser):
    return _shots(browser, DECK, "skill"), _shots(browser, DECK_V2, "v2")


def mean_diff(a: Path, b: Path, top: int = BAR_CROP) -> float:
    """Mean absolute per-channel difference (0–255) of two screenshots below the bar.

    Args:
        a: One PNG.
        b: The other, same size.
        top: Rows to skip (the bar).

    Returns:
        The mean over pixels and RGB channels.
    """
    ia, ib = (Image.open(p).convert("RGB") for p in (a, b))
    assert ia.size == ib.size
    box = (0, top, ia.width, ia.height)
    return sum(ImageStat.Stat(ImageChops.difference(ia.crop(box), ib.crop(box))).mean) / 3


@pytest.mark.parametrize("sid", PORTED)
def test_each_step_looks_like_deck_v2(shots, sid):
    ours, theirs = shots
    diffs = {k: round(mean_diff(ours[(s, k)], theirs[(s, k)]), 2) for s, k in ours if s == sid}
    print(f"{sid} mean diff per step: {diffs}")
    assert max(diffs.values()) <= BOUNDS[sid], diffs


def test_image_metric_rejects_a_different_slide(shots):
    """Negative control: the metric must separate slides, or a pass under the bounds proves nothing."""
    ours, theirs = shots
    assert mean_diff(ours[("s-2", 0)], theirs[("s-9", 3)]) > DIFFERENT
    assert mean_diff(ours[("s-4", 2)], theirs[("s-5", 6)]) > DIFFERENT


# ---------- layout guard: every slide × step × review size ----------

@pytest.mark.parametrize("size", REVIEW_SIZES, ids=[f"{w}x{h}" for w, h in REVIEW_SIZES])
def test_example_has_no_overlap_clipping_or_offcanvas_text(browser, size):
    w, h = size
    c, pg, errors = _open(browser, DECK, w, h)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    faults = []
    for sid in PORTED:
        faults += layout_faults(pg, sid, shoot=lambda k, sid=sid: pg.screenshot(
            path=str(ARTIFACTS / f"{sid}-{k}-{w}x{h}-skill.png")))
    c.close()
    assert errors == []
    assert faults == [], "\n".join(faults)
