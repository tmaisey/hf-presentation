"""Spec: PB-003

The optional engine modules: a persistent scene with a camera, narration tiles, pop-overs and a tile
row, each one file under ``assets/engine/modules/`` that registers on ``window.deckModules`` through
the documented hooks, ships only in decks whose slides use it, and is documented in ARCHITECTURE.

Coverage: happy (scene persists and holds its place, parts by slide:step, state classes, camera per
slide and step, backdrop blur; 1–2 narration tiles per step that soften then hide; pop-over focus
softens the scene and dissolves; tile row over the blurred backdrop; notes on scene and pop-over
parts) · edge (scene raises a slide's step count, backdrop inherits the camera, tiles clear of the
title in a column that runs beside it, tile row tightens only when it overflows, three review sizes)
· negative (a deck without module markup carries no module code, no incident names, no colour
literals in module CSS, nothing undocumented, no risky calls).
"""

import re

import pytest
from playwright.sync_api import sync_playwright

from helper_engine import (ARCHITECTURE, FIXTURE_CSS, FIXTURE_SLIDES, MODULE_CSS, MODULE_SLIDES,
                           MODULES_DIR, REVIEW_SIZES, assemble, detect_modules, module_triggers,
                           open_deck, opacity, settle, state)

MODULES = ("narration", "popover", "scene", "tile-row")
HOOKS = ("init", "place", "render", "overlaid", "settle", "instant", "noteTarget", "noteRange", "noteFrame")
BANNED = (r"hugging", r"openai", r"modal\b", r"metr\b", r"deloitte", r"anthropic", r"incident", r"swarm",
          r"world", r"mirror", r"exploit", r"agent", r"day0", r"tl-day")
RISKY = ("eval(", "atob(", "document.write", "new Function", "innerHTML", "outerHTML", "fetch(",
         "XMLHttpRequest", "import(")


# ---------- fixtures ----------

@pytest.fixture(scope="module")
def browser():
    """System Chrome, once per module (no conftest: other suites share this folder)."""
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        yield b
        b.close()


@pytest.fixture(scope="module")
def deck_file(tmp_path_factory):
    return assemble(tmp_path_factory.mktemp("mods") / "modules.html", slides=MODULE_SLIDES,
                    subtitle="Modules", css=MODULE_CSS)


def _page(browser, deck_file, **ctx):
    c = browser.new_context(viewport=ctx.pop("viewport", {"width": 1280, "height": 720}), **ctx)
    pg = c.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    open_deck(pg, deck_file)
    return c, pg, errors


@pytest.fixture
def page(browser, deck_file):
    c, pg, errors = _page(browser, deck_file)
    yield pg
    c.close()
    assert errors == [], f"engine raised: {errors}"


def go(page, slide, step):
    page.evaluate("([s, k]) => deck.goto(s, k)", [slide, step])
    settle(page)


def _js(name):
    return (MODULES_DIR / f"{name}.js").read_text(encoding="utf-8")


def _css(name):
    f = MODULES_DIR / f"{name}.css"
    return f.read_text(encoding="utf-8") if f.is_file() else ""


def _module_doc(name):
    """The module's subsection of ARCHITECTURE (inside the modules markers)."""
    doc = ARCHITECTURE.read_text(encoding="utf-8")
    m = re.search(r"<!-- modules:begin -->(.*?)<!-- modules:end -->", doc, re.S)
    assert m, "ARCHITECTURE keeps its module section between the modules markers"
    part = re.search(rf"^### [^\n]*`modules/{re.escape(name)}\.js`.*?(?=^### |\Z)", m.group(1), re.S | re.M)
    assert part, f"no ARCHITECTURE subsection for modules/{name}.js"
    return part.group(0)


SCENE = "document.querySelector('.scene')"


def _rect(page, sel):
    return page.evaluate("s => { const r = document.querySelector(s).getBoundingClientRect();"
                         " return [r.left, r.top, r.width, r.height]; }", sel)


def _camera(page):
    m = page.evaluate("getComputedStyle(document.querySelector('.scene .cam')).transform")
    if m == "none":
        return [0.0, 0.0, 1.0]
    a, _b, _c, _d, e, f = (float(v) for v in re.findall(r"-?[\d.]+(?:e-?\d+)?", m)[:6])
    return [round(e, 1), round(f, 1), round(a, 2)]


def _blurred(page, sel=".scene"):
    return "blur" in page.evaluate("s => getComputedStyle(document.querySelector(s)).filter", sel)


def _cls(page, sel, c):
    return page.evaluate("([s, c]) => document.querySelector(s).classList.contains(c)", [sel, c])


# ---------- static contract ----------

def test_each_module_is_one_file_that_registers_with_its_name_and_triggers():
    for name in MODULES:
        js = _js(name)
        assert re.search(r"\(window\.deckModules = window\.deckModules \|\| \[\]\)\.push\(", js), name
        assert re.search(rf"name: '{name}'", js), name
        assert module_triggers(MODULES_DIR / f"{name}.js"), f"{name}: Triggers header missing"
        defined = set(re.findall(rf"^\s+({'|'.join(HOOKS)})\([^)]*\)\s*\{{", js, re.M))
        assert defined, f"{name} uses no documented hook"


def test_module_css_is_mechanics_only_in_the_arch_layer():
    for name in MODULES:
        css = re.sub(r"/\*.*?\*/", "", _css(name), flags=re.S).strip()
        if not css:
            continue
        assert css.startswith("@layer arch {") and css.endswith("}"), name
        assert not re.search(r"#[0-9a-f]{3,8}\b|\b(?:rgb|rgba|hsl|hsla|oklch|lab)\(", css, re.I), \
            f"{name}: system colours only"


def test_modules_carry_no_incident_or_organisation_names():
    for name in MODULES:
        for text in (_js(name), _css(name), _module_doc(name)):
            hits = [w for w in BANNED if re.search(rf"\b{w}", text.lower())]
            assert hits == [], f"{name}: {hits}"


def test_architecture_documents_each_module_triggers_attributes_classes_and_hooks():
    for name in MODULES:
        js, doc = _js(name), _module_doc(name)
        for t in module_triggers(MODULES_DIR / f"{name}.js"):
            assert t.strip("[]") in doc, f"{name}: trigger {t} undocumented"
        attrs = {"data-" + re.sub(r"[A-Z]", lambda m: "-" + m.group(0).lower(), c)
                 for c in re.findall(r"dataset\.([a-zA-Z]+)", js)} | set(re.findall(r"\b(data-[a-z-]+)", js))
        assert [a for a in sorted(attrs) if f"`{a}" not in doc] == [], name
        classes = set(re.findall(r"classList\.(?:toggle|add|remove)\('([\w-]+)'", js))
        for names in re.findall(r"\bel\('\w+', '([\w -]+)'", js):
            classes |= set(names.split())
        assert [c for c in sorted(classes) if not re.search(rf"\.{re.escape(c)}\b|`{re.escape(c)}`", doc)] == [], name
        hooks = set(re.findall(rf"^\s+({'|'.join(HOOKS)})\([^)]*\)\s*\{{", js, re.M))
        assert [h for h in sorted(hooks) if f"`{h}`" not in doc] == [], name


def test_architecture_states_the_inclusion_rule():
    doc = ARCHITECTURE.read_text(encoding="utf-8")
    for term in ("Triggers:", "modules/<name>.js", "modules/<name>.css"):
        assert term in doc, term


def test_a_deck_without_module_markup_carries_no_module_code(tmp_path):
    """The core fixture uses no module attribute or class, so its file holds no module JS or CSS."""
    assert detect_modules(FIXTURE_SLIDES) == []
    src = assemble(tmp_path / "plain.html").read_text(encoding="utf-8")
    assert "(window.deckModules = window.deckModules || []).push(" not in src, "no module registers"
    for name in MODULES:
        assert _js(name).strip() not in src, name
        if _css(name).strip():
            assert _css(name).strip() not in src, name


def test_a_deck_carries_only_the_modules_its_slides_use(tmp_path):
    slides = """<section class="slide" id="a" data-chapter="A"><h2 class="title">One</h2>
      <div class="narration"><article class="narr-tile" data-at="1"><p>Hello</p></article></div></section>"""
    assert detect_modules(slides) == ["narration"]
    src = assemble(tmp_path / "one.html", slides=slides).read_text(encoding="utf-8")
    assert _js("narration").strip() in src
    for name in ("popover", "scene", "tile-row"):
        assert _js(name).strip() not in src, name
    assert detect_modules(MODULE_SLIDES) == list(MODULES)


def test_assembled_module_deck_stays_one_endpoint_safe_script(deck_file):
    src = deck_file.read_text(encoding="utf-8")
    assert len(re.findall(r"<script\b", src)) == 1
    for bad in RISKY:
        assert bad not in src, bad


# ---------- scene ----------

def test_scene_parts_raise_a_slides_step_count(page):
    assert page.evaluate("deck.plan()") == [["m-1", 0], ["m-2", 3], ["m-3", 3], ["m-4", 3], ["m-5", 0]]


def test_scene_shows_only_on_scene_slides(page):
    on = {}
    for sid in ("m-1", "m-2", "m-3", "m-4", "m-5"):
        go(page, sid, 0)
        on[sid] = (page.evaluate(f"{SCENE}.classList.contains('is-on')"), round(opacity(page, ".scene")))
    assert on == {"m-1": (False, 0), "m-2": (True, 1), "m-3": (True, 1), "m-4": (True, 1), "m-5": (False, 0)}


def test_scene_parts_appear_at_their_point_and_persist_until_their_end(page):
    parts = ("#p-a", "#p-b", "#p-ab", "#p-c")
    seen = {}
    for sid, k in (("m-2", 0), ("m-2", 1), ("m-3", 0), ("m-3", 1), ("m-3", 3), ("m-4", 0)):
        go(page, sid, k)
        seen[(sid, k)] = [round(opacity(page, p)) for p in parts]
    assert seen == {("m-2", 0): [1, 0, 0, 0], ("m-2", 1): [1, 1, 1, 0], ("m-3", 0): [1, 1, 1, 0],
                    ("m-3", 1): [1, 0, 0, 0], ("m-3", 3): [1, 0, 0, 1], ("m-4", 0): [1, 0, 0, 1]}


def test_scene_state_classes_hold_for_their_range(page):
    got = []
    for sid, k in (("m-2", 3), ("m-3", 0), ("m-3", 2), ("m-3", 3)):
        page.evaluate("([s, k]) => deck.goto(s, k)", [sid, k])
        got.append(_cls(page, "#p-a", "is-dim"))
    assert got == [False, True, True, False]


def test_scene_is_one_element_carried_across_consecutive_scene_slides(page):
    go(page, "m-2", 3)
    page.evaluate(f"window.__scene = {SCENE}")
    page.keyboard.press("ArrowRight")
    page.wait_for_function("deck.state().slide === 'm-3'")
    settle(page)
    assert page.evaluate(f"window.__scene === {SCENE} && {SCENE}.classList.contains('is-on')")
    assert round(opacity(page, "#p-a")) == 1, "parts from the previous slide stay on screen"


@pytest.mark.parametrize("size", REVIEW_SIZES, ids=lambda s: f"{s[0]}x{s[1]}")
def test_scene_holds_one_place_whatever_the_title_length(browser, deck_file, size):
    c, pg, errors = _page(browser, deck_file, viewport={"width": size[0], "height": size[1]})
    rects, text_h = {}, {}
    for sid in ("m-2", "m-3", "m-4"):
        go(pg, sid, 0)
        rects[sid] = [round(v) for v in _rect(pg, ".scene")]
        text_h[sid] = pg.evaluate("s => { const r = document.createRange(); r.selectNodeContents(document.querySelector(s));"
                                  " return r.getBoundingClientRect().height; }", f"#{sid[0]}{sid[2]}-title")
    c.close()
    assert errors == []
    assert text_h["m-3"] > text_h["m-2"] * 1.5, "control: the titles really differ in length"
    assert rects["m-2"][2] > 100 and rects["m-2"][3] > 100, "the scene fills its slot"
    assert rects["m-2"] == rects["m-3"] == rects["m-4"]


def test_camera_follows_each_slide_and_step(page):
    cams = {}
    for sid, k in (("m-2", 0), ("m-2", 1), ("m-2", 2), ("m-2", 3), ("m-3", 0)):
        go(page, sid, k)
        cams[(sid, k)] = _camera(page)
    assert cams == {("m-2", 0): [0, 0, 1], ("m-2", 1): [0, 0, 1], ("m-2", 2): [-120, 0, 1.6],
                    ("m-2", 3): [-120, 0, 1.6], ("m-3", 0): [60, 20, 1.2]}


def test_camera_moves_between_states_rather_than_jumping(page):
    go(page, "m-2", 1)
    page.keyboard.press("ArrowRight")
    page.wait_for_function("deck.state().step === 2")
    scales = page.evaluate("""() => new Promise(res => { const seen = [], t0 = performance.now();
      const f = () => { const m = getComputedStyle(document.querySelector('.scene .cam')).transform;
        const a = m === 'none' ? 1 : parseFloat(m.slice(7)); seen.push(a);
        if (Math.abs(a - 1.6) < 1e-3 || performance.now() - t0 > 4000) res(seen); else requestAnimationFrame(f); };
      requestAnimationFrame(f); })""")
    assert abs(scales[-1] - 1.6) < 1e-3, "the camera lands on the step's state"
    assert any(1.01 < a < 1.59 for a in scales), "camera tweens (style layer motion), not a cut"


def test_backdrop_slide_blurs_the_scene_and_keeps_the_last_camera(page):
    go(page, "m-3", 3)
    assert not _blurred(page)
    cam = _camera(page)
    go(page, "m-4", 0)
    assert _cls(page, ".scene", "is-backdrop") and _blurred(page)
    assert _camera(page) == cam, "a backdrop without its own camera keeps the last live slide's"
    go(page, "m-2", 0)
    assert not _cls(page, ".scene", "is-backdrop") and not _blurred(page)


def test_a_note_can_target_a_scene_part_and_uses_its_scene_range(page):
    go(page, "m-3", 3)
    page.keyboard.press("n")
    page.wait_for_function("document.body.classList.contains('notes-focus')")
    settle(page)
    assert page.evaluate("document.querySelector('.callout h3').textContent") == "Scene note"
    assert state(page)["step"] == 0, "#p-b leaves at m-3:1, so its note shows step 0"
    t = _rect(page, "#p-b")
    ring = _rect(page, ".ring")
    assert ring[0] <= t[0] and ring[1] <= t[1] and ring[0] + ring[2] >= t[0] + t[2] and ring[1] + ring[3] >= t[1] + t[3]


# ---------- narration tiles ----------

def _shown_tiles(page):
    return page.evaluate("[...document.querySelectorAll('section.is-active .narr-tile.is-shown')].map(t => t.id)")


def test_narration_shows_one_or_two_tiles_per_step(page):
    got = {}
    for k in range(4):
        go(page, "m-2", k)
        got[k] = _shown_tiles(page)
        col = _rect(page, "#m-2 .narration")
        for t in got[k]:
            r = _rect(page, f"#{t}")
            assert col[0] - 0.5 <= r[0] and r[0] + r[2] <= col[0] + col[2] + 0.5 and r[2] < col[2], \
                f"{t}: placed within its column, narrower than it"
    assert got == {0: [], 1: ["n-1"], 2: ["n-2a", "n-2b"], 3: ["n-3"]}


def test_earlier_tiles_soften_then_disappear(page):
    go(page, "m-2", 1)
    page.keyboard.press("ArrowRight")
    page.wait_for_function("deck.state().step === 2")
    soft = page.evaluate("""(() => { const t = document.querySelector('#n-1');
      return [t.classList.contains('is-shown'), t.classList.contains('was-shown'), getComputedStyle(t).visibility]; })()""")
    assert soft == [False, True, "visible"], "the outgoing tile is still drawn while it softens"
    page.wait_for_function("getComputedStyle(document.querySelector('#n-1')).visibility === 'hidden'")
    assert opacity(page, "#n-1") == 0


def test_a_pair_is_staggered_not_a_rigid_column(page):
    go(page, "m-2", 2)
    a, b = _rect(page, "#n-2a"), _rect(page, "#n-2b")
    assert abs(a[0] - b[0]) > 4 or abs(a[2] - b[2]) > 4


def _overlaps(a, b, tol=0.5):
    return a[0] < b[2] - tol and b[0] < a[2] - tol and a[1] < b[3] - tol and b[1] < a[3] - tol


GEOM = """(() => { const s = document.querySelector('section.slide.is-active');
  const R = e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; };
  const vis = e => +getComputedStyle(e).opacity > .05;
  return { tiles: [...s.querySelectorAll('.narr-tile.is-shown')].map(R),
           fixed: [...s.querySelectorAll(':scope > .title, :scope > .kicker')].filter(vis).map(R)
             .concat([R(document.querySelector('.bar')), R(document.querySelector('.notes-btn'))]),
           vw: innerWidth, vh: innerHeight }; })()"""


def _check_tiles(pg, label):
    g = pg.evaluate(GEOM)
    for i, t in enumerate(g["tiles"]):
        assert t[0] >= -0.5 and t[1] >= -0.5 and t[2] <= g["vw"] + 0.5 and t[3] <= g["vh"] + 0.5, f"{label}: off-canvas"
        assert not any(_overlaps(t, f) for f in g["fixed"]), f"{label}: tile over the title or chrome"
        assert not any(_overlaps(t, u) for u in g["tiles"][i + 1:]), f"{label}: tiles overlap"
    return len(g["tiles"])


@pytest.mark.parametrize("size", REVIEW_SIZES, ids=lambda s: f"{s[0]}x{s[1]}")
def test_tiles_never_overlap_the_title_or_each_other(browser, deck_file, size):
    c, pg, errors = _page(browser, deck_file, viewport={"width": size[0], "height": size[1]})
    shown = 0
    for sid, steps in (("m-2", 3), ("m-3", 3)):
        for k in range(steps + 1):
            go(pg, sid, k)
            shown += _check_tiles(pg, f"{sid}:{k}")
    c.close()
    assert errors == [] and shown == 5


# a narration column that runs the full slide height beside (and under) a full-width title
BESIDE = """
<section class="slide" id="b-1" data-chapter="Beside">
  <p class="kicker">Beside</p>
  <h2 class="title">A full-width title that the narration column runs underneath on the right-hand side</h2>
  <div class="body"><p data-show-at="1">Body</p></div>
  <div class="narration">
    <article class="narr-tile" id="bn-1" data-at="0"><p>The first tile, at step zero.</p></article>
    <article class="narr-tile" id="bn-2" data-at="1"><p>One of a pair of tiles.</p></article>
    <article class="narr-tile" id="bn-3" data-at="1"><p>The other tile of the pair, a little longer than the first.</p></article>
  </div>
</section>"""
BESIDE_CSS = MODULE_CSS + """
@layer deck { .slide > .narration { position: absolute; right: 3vw; top: 0; bottom: 0; width: 30vw; } }"""


@pytest.mark.parametrize("size", REVIEW_SIZES, ids=lambda s: f"{s[0]}x{s[1]}")
def test_tiles_keep_clear_of_a_title_their_column_runs_beside(browser, tmp_path, size):
    f = assemble(tmp_path / "beside.html", slides=BESIDE, css=BESIDE_CSS)
    c, pg, errors = _page(browser, f, viewport={"width": size[0], "height": size[1]})
    shown = 0
    for k in (0, 1):
        go(pg, "b-1", k)
        shown += _check_tiles(pg, f"b-1:{k}")
    c.close()
    assert errors == [] and shown == 3


def test_narration_never_softens_the_slide(page):
    go(page, "m-2", 2)
    assert not _cls(page, "#m-2", "is-overlaid") and not _blurred(page)


# ---------- pop-overs ----------

def test_popover_focus_softens_the_scene_then_dissolves_on_its_exit_step(page):
    seen = {}
    for k in (0, 1, 2):
        go(page, "m-3", k)
        seen[k] = (round(opacity(page, "#m3-pop")), _cls(page, "#m-3", "is-overlaid"), _blurred(page))
    assert seen == {0: (0, False, False), 1: (1, True, True), 2: (0, False, False)}


def test_popover_sits_over_the_scene(page):
    go(page, "m-3", 1)
    p, s = _rect(page, "#m3-pop"), _rect(page, ".scene")
    assert _cls(page, ".scene", "is-on") and s[2] > 100
    assert p[0] < s[0] + s[2] and s[0] < p[0] + p[2], "drawn over the scene's area"
    hit = page.evaluate("(() => { const r = document.querySelector('#m3-pop').getBoundingClientRect();"
                        " return document.elementFromPoint(r.left + r.width / 2, r.top + 20).closest('.popover') !== null; })()")
    assert hit


def test_pins_behind_a_focused_popover_are_clipped_by_its_frame(page):
    go(page, "m-3", 3)
    page.keyboard.press("n")
    page.wait_for_function("document.body.classList.contains('notes-focus')")
    page.keyboard.press("ArrowRight")
    page.wait_for_function("document.querySelector('.callout h3').textContent === 'Pop-over caption'")
    settle(page)
    assert state(page)["step"] == 1
    clip = page.evaluate("document.querySelectorAll('.pin')[2].style.clipPath")
    assert clip.startswith("polygon"), "the other pop-over pin is cut where the pop-over covers it"


# ---------- tile row ----------

def test_tile_row_reveals_its_tiles_over_the_blurred_backdrop(page):
    got = []
    for k in range(4):
        go(page, "m-4", k)
        got.append([round(opacity(page, f"#t-{i}")) for i in (1, 2, 3)])
    assert got == [[0, 0, 0], [1, 0, 0], [1, 1, 0], [1, 1, 1]]
    assert _blurred(page)
    s = _rect(page, ".scene")
    t = _rect(page, "#t-2")
    assert _overlaps([t[0], t[1], t[0] + t[2], t[1] + t[3]], [s[0], s[1], s[0] + s[2], s[1] + s[3]]), \
        "the middle tile sits over the scene"
    for i in (1, 2, 3):
        hit = page.evaluate("s => { const r = document.querySelector(s).getBoundingClientRect();"
                            " return document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2).closest('.text-tile').id; }",
                            f"#t-{i}")
        assert hit == f"t-{i}", "tiles are drawn above the scene"
    widths = [round(_rect(page, f"#t-{i}")[2]) for i in (1, 2, 3)]
    assert max(widths) - min(widths) <= 1, "a row of equal tiles"


DENSE = """
<section class="slide" id="r-1" data-chapter="Row">
  <h2 class="title">A dense row</h2>
  <div class="body body--tiles">""" + "".join(
    f'<article class="text-tile" id="r-t{i}"><h3>Tile {i}</h3><ul>' + "<li>a line</li>" * 20 + "</ul></article>"
    for i in (1, 2, 3)) + """</div>
</section>"""
DENSE_CSS = MODULE_CSS + """
@layer deck { .slide:has(> .body--tiles) { grid-template-rows: auto minmax(0, 1fr); }
  .slide > .body--tiles { align-self: stretch; } .text-tile li { font-size: 18px; line-height: 24px; } }"""


def test_tile_row_tightens_only_when_its_tiles_overflow(browser, tmp_path):
    f = assemble(tmp_path / "dense.html", slides=DENSE, css=DENSE_CSS)
    tight = "document.querySelector('.body--tiles').classList.contains('is-tight')"
    c, pg, errors = _page(browser, f, viewport={"width": 1288, "height": 598})
    pg.wait_for_function("document.fonts.status === 'loaded'")
    small = pg.evaluate(tight)
    pg.set_viewport_size({"width": 1920, "height": 1080})
    pg.wait_for_function(f"!{tight}")
    c.close()
    assert errors == [] and small is True
