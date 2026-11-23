"""Spec: PB-004, PB-007

The layout/components design layer: a LAYOUT part one hop from SKILL.md and a components CSS in
``@layer components`` that styles the core component API (ARCHITECTURE §5) through sys/comp tokens
only, so that a deck assembled with paper-green + editorial looks like the accepted deck-v2.

Coverage: happy (one layer, lint clean, routed and documented part; computed styles of bar, agenda,
type, slide grid, Insight, diagram kit, step list, notes UI, ambient and links match deck-v2 measured in
the same browser at 1920×1080; every fixture slide × step × review size free of overlap, clipping and
off-canvas text; compact agenda drops an opaque list) · edge (k-scaled diagram floors at deck-v2's own
--k, reduced motion lands without travel) · negative (lint catches colour literals, named/system
colours, ref reads, undefined and non-comp properties; the layout guard catches a planted collision).
"""

import re
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

import helper_components as hc
from helper_engine import (BANNED, COMPONENT_SLIDES, MODULE_SLIDES, REVIEW_SIZES, assemble_themed, components_css,
                           layout_faults, open_deck, settle, theme_blocks)
from helper_skill import SKILL_DIR
from helper_tokens import DECK_V2

LAYOUT_MD = SKILL_DIR / "design" / "LAYOUT.md"
SKILL_MD = SKILL_DIR / "SKILL.md"
ARTIFACTS = Path(__file__).parent / "artifacts" / "pb-004"
FIXTURE_IDS = re.findall(r'<section class="[^"]*" id="([\w-]+)"', COMPONENT_SLIDES)
TYPE = ("fontFamily", "fontSize", "fontWeight", "fontStyle", "lineHeight", "letterSpacing", "color",
        "textTransform")


# ---------- fixtures ----------

@pytest.fixture(scope="module")
def css():
    return components_css()


@pytest.fixture(scope="module")
def theme_css():
    return "\n".join(theme_blocks())


@pytest.fixture(scope="module")
def browser():
    """System Chrome, once per module (no conftest: other suites share this folder)."""
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        yield b
        b.close()


@pytest.fixture(scope="module")
def deck_file(tmp_path_factory):
    return assemble_themed(tmp_path_factory.mktemp("comp") / "components.html")


def _open(browser, path, width=1920, height=1080, **ctx):
    c = browser.new_context(viewport={"width": width, "height": height}, **ctx)
    pg = c.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    open_deck(pg, path)
    pg.wait_for_function("document.fonts.status === 'loaded'")
    return c, pg, errors


@pytest.fixture(scope="module")
def pages(browser, deck_file):
    """The fixture deck and deck-v2, side by side at 1920×1080 in the same browser."""
    cf, fixture, ef = _open(browser, deck_file)
    cv, v2, ev = _open(browser, DECK_V2)
    yield fixture, v2
    cf.close()
    cv.close()
    assert ef == [] and ev == [], f"page errors: {ef + ev}"


PROBE = """([sel, props, pseudo]) => { const e = document.querySelector(sel);
  if (!e) return null; const s = getComputedStyle(e, pseudo || null);
  return Object.fromEntries(props.map(p => [p, s[p]])); }"""


def _at(page, slide, step):
    page.evaluate("([s, k]) => deck.goto(s, k)", [slide, step])
    page.wait_for_function("([s, k]) => deck.state().slide === s && deck.state().step === k", arg=[slide, step])
    settle(page)


def _probe(page, slide, step, sel, props, pseudo=None):
    _at(page, slide, step)
    got = page.evaluate(PROBE, [sel, list(props), pseudo])
    assert got is not None, f"{sel} not found on {slide}"
    return _norm(got)


def _norm(d):
    """Font stacks compare without quotes (``"Georgia"`` and ``Georgia`` are the same family)."""
    return {k: (re.sub(r'["\']', "", v) if k == "fontFamily" else v) for k, v in d.items()}


# ---------- lint: tokens only ----------

def test_components_css_is_one_components_layer(css):
    body = hc.strip_comments(css).strip()
    assert body.startswith("@layer components {") and body.endswith("}")
    assert body.count("@layer") == 1


def test_components_css_holds_no_colour_literal(css):
    assert hc.colour_literals(css) == []


def test_components_css_reads_only_defined_sys_and_comp_tokens(css, theme_css):
    assert hc.lint(css, theme_css) == []
    assert any(v.startswith("--sys-color-") for v in hc.var_reads(css)), "colours come from palette roles"
    assert not [v for v in hc.var_reads(css) if v.startswith("--ref-")]


def test_components_css_names_no_organisation_or_incident(css):
    """Module class names (ARCHITECTURE §9: narration, ``narr-``, popover) are contract, not incident names."""
    text = css.lower()
    contract = {r"narr-", r"narration", r"popover"}
    assert [w for w in BANNED if w not in contract and re.search(rf"\b{w}", text)] == []


@pytest.mark.parametrize("snippet, fault", [
    (".x { color: #2b2a27; }", "colour literal"),
    (".x { background: rgb(1 2 3 / .5); }", "colour literal"),
    (".x { border-color: white; }", "colour literal"),
    (".x { outline: 2px solid Highlight; }", "colour literal"),
    (".x { color: var(--ref-color-charcoal-900); }", "reads a ref token"),
    (".x { color: var(--sys-color-nope); }", "reads an undefined sys token"),
    (".x { color: var(--comp-nope); }", "reads an undefined comp token"),
    (".x { --sys-color-ink: var(--sys-color-paper); }", "defines a non-comp property"),
    (".x { width: var(--bar); }", "reads a property outside the token tiers"),
])
def test_lint_rejects_literals_ref_reads_and_undefined_tokens(snippet, fault, theme_css):
    bad = "@layer components {\n" + snippet + "\n}"
    faults = hc.lint(bad, theme_css)
    assert faults and all(f.startswith(fault) for f in faults), faults


def test_lint_accepts_tokens_hue_free_keywords_and_def_urls(theme_css):
    """``transparent``/``currentColor`` carry no hue; ``url(#lift)`` and ``--k`` are contract, not colour."""
    ok = """@layer components { :root { --comp-fade: color-mix(in srgb, var(--sys-color-paper) 55%, transparent); }
      .x { fill: currentColor; filter: url(#lift); stroke-width: max(2px, calc(var(--k) * 2px));
           background: var(--comp-fade); grid-template: "kicker" auto "title" auto / 1fr; content: "Insight"; } }"""
    assert hc.lint(ok, theme_css) == []


# ---------- the LAYOUT part ----------

def test_layout_part_is_linked_once_from_skill_md_parts():
    skill = SKILL_MD.read_text(encoding="utf-8")
    parts = skill[skill.index("## Parts"):]
    assert parts.count("(design/LAYOUT.md)") == 1
    assert LAYOUT_MD.is_file()


def test_layout_part_documents_every_component_and_variant():
    doc = LAYOUT_MD.read_text(encoding="utf-8")
    for cls in (".bar", ".agenda", ".bar--compact", ".nav-current", ".progress", ".slide--lead", ".slide--end",
                ".kicker", ".title", ".body--split", ".body--flip", ".body--stack", ".body--layers", ".steps",
                ".points", ".overlay--insight", ".is-overlaid", ".tile", ".tile--key", ".edge", ".label",
                ".tag", "--k", ".callout", ".pin", ".ring", ".veil", ".notes-btn", ".notes-nav", ".orb",
                "a.src", ".cite", ".byline", ".msg-card", ".fig", ".annot", ".scene", ".scene-slot", ".is-soft",
                ".is-backdrop", ".narration", ".narr-tile", ".popover", ".pop-panel", ".body--tiles", ".text-tile",
                ".is-tight"):
        assert cls in doc, f"LAYOUT.md does not document {cls}"
    assert len(re.findall(r"(?im)^.*use when", doc)) >= 5, "each layout variant says when to use it"
    assert re.search(r"(?i)three-column scene", doc), "the scene layout is a documented variant"


def test_layout_part_lists_every_comp_token_and_every_sys_token_read(css):
    """The part is the component token reference: it may group sys reads with a trailing ``*``."""
    doc = LAYOUT_MD.read_text(encoding="utf-8")
    missing = [p for p in sorted(hc.defined_props(css)) if p.startswith("--comp-") and p not in doc]
    assert missing == [], f"comp tokens not documented: {missing}"
    rows = "\n".join(l for l in doc.splitlines() if l.startswith("|"))   # per-component rows only
    wild = [w for w in re.findall(r"(--sys-[\w-]*?)-?\*", rows) if w not in ("--sys-", "--sys-color")]
    unlisted = [v for v in sorted(hc.var_reads(css)) if v.startswith("--sys-")
                and v not in doc and not any(v.startswith(w) for w in wild)]
    assert unlisted == [], f"sys tokens read but not listed per component: {unlisted}"


# ---------- fidelity with deck-v2 at 1920×1080 ----------

# (what, fixture slide/step/selector, deck-v2 slide/step/selector, properties, pseudo)
PAIRS = [
    ("page", ("c-2", 0, "body"), ("s-2", 0, "body"), ("fontFamily", "fontSize", "lineHeight", "color", "backgroundColor"), None),
    ("slide padding", ("c-2", 0, "#c-2"), ("s-2", 0, "#s-2"),
     ("paddingTop", "paddingLeft", "paddingRight", "paddingBottom", "display"), None),
    ("lead title", ("c-1", 0, "#c-1 > .title"), ("s-1", 0, "#s-1 > .title"), TYPE + ("maxWidth",), None),
    ("title", ("c-2", 0, "#c-2 > .title"), ("s-2", 0, "#s-2 > .title"), TYPE + ("maxWidth", "marginTop", "marginBottom"), None),
    ("kicker", ("c-2", 0, "#c-2 > .kicker"), ("s-2", 0, "#s-2 > .kicker"), TYPE, None),
    ("body text", ("c-2", 0, "#c2-lede"), ("s-2", 0, "#s2-train"), TYPE + ("maxWidth",), None),
    ("byline", ("c-1", 0, "#c-1 .byline"), ("s-1", 0, "#s-1 .byline"), TYPE + ("left", "bottom"), None),
    ("bar", ("c-2", 0, ".bar"), ("s-2", 0, ".bar"), ("height", "backgroundColor", "backdropFilter", "paddingLeft"), None),
    ("bar title", ("c-2", 0, ".bar-title"), ("s-2", 0, ".bar-title"), ("fontFamily", "fontSize", "fontWeight", "color"), None),
    ("bar subtitle", ("c-2", 0, ".bar-title em"), ("s-2", 0, ".bar-title em"), ("color", "fontWeight", "fontStyle"), None),
    ("bar dot", ("c-2", 0, ".bar-title span"), ("s-2", 0, ".bar-title span"), ("color", "marginLeft"), None),
    ("agenda current", ("c-2", 0, ".agenda li.is-current button"), ("s-2", 0, ".agenda li.is-current button"),
     ("color", "backgroundColor", "boxShadow", "fontFamily", "fontSize", "fontWeight", "borderRadius", "paddingTop"), None),
    ("agenda other", ("c-2", 0, ".agenda li:not(.is-current) button"), ("s-2", 0, ".agenda li:not(.is-current) button"),
     ("color", "backgroundColor", "boxShadow"), None),
    ("progress", ("c-2", 0, ".progress"), ("s-2", 0, ".progress"), ("backgroundColor", "height"), None),
    ("Insight card", ("c-2", 3, "#c2-insight"), ("s-2", 5, "#s-2 .overlay--insight"),
     ("backgroundColor", "backdropFilter", "borderRadius", "boxShadow", "paddingTop", "paddingLeft", "width",
      "opacity", "filter", "transform", "marginBottom"), None),
    ("Insight text", ("c-2", 3, "#c2-insight p"), ("s-2", 5, "#s-2 .overlay--insight p"), TYPE, None),
    ("Insight label", ("c-2", 3, "#c2-insight"), ("s-2", 5, "#s-2 .overlay--insight"), TYPE + ("content",), "::before"),
    ("softened body", ("c-2", 3, "#c-2 > .body"), ("s-2", 5, "#s-2 > .body"), ("filter", "opacity"), None),
    ("tile", ("c-3", 3, "#c3-a rect"), ("s-2", 4, "#s2-model rect"), ("fill", "stroke", "filter", "rx"), None),
    ("key tile", ("c-3", 3, "#c3-c rect"), ("s-6", 4, "#w-hf-c1 rect"), ("fill", "stroke", "filter", "rx"), None),
    ("tile title", ("c-3", 3, "#c3-a .tile-title"), ("s-2", 4, "#s2-model .tile-title"),
     ("fontFamily", "fontWeight", "fill", "textAnchor", "dominantBaseline"), None),
    ("edge", ("c-3", 3, "#c3-e1"), ("s-2", 4, "#s-2 path.edge:not(.edge--ok):not(.edge--loss)"),
     ("stroke", "fill", "strokeLinecap", "strokeLinejoin"), None),
    ("edge ok", ("c-3", 3, "#c3-e2"), ("s-2", 4, "#s2-pass"), ("stroke",), None),
    ("edge loss", ("c-3", 3, "#c3-e3"), ("s-2", 4, "#s2-hack-in"), ("stroke",), None),
    ("arrowhead", ("c-3", 3, "#arr path"), ("s-2", 4, "#arr path"), ("fill",), None),
    ("arrowhead ok", ("c-3", 3, "#arr-ok path"), ("s-2", 4, "#arr-ok path"), ("fill",), None),
    ("lift shadow", ("c-3", 3, "#lift feDropShadow"), ("s-2", 4, "#lift feDropShadow"), ("floodColor",), None),
    ("key glow", ("c-3", 3, "#lift-key .glow"), ("s-2", 4, "#lift-key .glow"), ("floodColor",), None),
    ("step current", ("c-3", 2, "#c3-s2"), ("s-3", 3, "#s-3 .steps li.is-current:not(.sub)"), ("color",), None),
    ("step current disc", ("c-3", 2, "#c3-s2"), ("s-3", 3, "#s-3 .steps li.is-current:not(.sub)"),
     ("backgroundColor", "borderTopColor", "color", "borderRadius"), "::before"),
    ("step done disc", ("c-3", 2, "#c3-s1"), ("s-3", 3, "#s-3 .steps li.is-done:not(.sub)"),
     ("backgroundColor", "borderTopColor", "color"), "::before"),
    ("prompt", ("c-7", 0, "#c7-q1"), ("s-12", 0, "#s12-q1"), TYPE + ("paddingLeft",), None),
    ("prompt disc", ("c-7", 0, "#c7-q1"), ("s-12", 0, "#s12-q1"), ("backgroundColor", "color", "fontSize"), "::before"),
    ("orb far", ("c-1", 0, "#c-1 .orb--far"), ("s-1", 0, "#s-1 .orb.far"), ("filter", "opacity", "borderRadius"), None),
    ("orb mid", ("c-1", 0, "#c-1 .orb--mid"), ("s-1", 0, "#s-1 .orb.mid"), ("filter", "opacity"), None),
    ("orb near", ("c-1", 0, "#c-1 .orb--near"), ("s-1", 0, "#s-1 .orb.near"), ("filter", "opacity"), None),
    *[(f"orb tint {i}", ("c-1", 0, f"#c-1 .orb--{i}"), ("s-1", 0, f"#s-1 .orb--{i}"), ("backgroundImage",), None)
      for i in range(1, 6)],
    ("notes button", ("c-2", 0, ".notes-btn"), ("s-2", 0, ".notes-btn"),
     ("backgroundColor", "color", "borderTopColor", "fontSize", "borderRadius", "backdropFilter"), None),
    ("notes button mark", ("c-2", 0, ".notes-btn"), ("s-2", 0, ".notes-btn"),
     ("backgroundColor", "color", "content", "width"), "::before"),
]


@pytest.mark.parametrize("what, fix, ref, props, pseudo", PAIRS, ids=[p[0] for p in PAIRS])
def test_component_computes_like_deck_v2(pages, what, fix, ref, props, pseudo):
    fixture, v2 = pages
    want = _probe(v2, *ref, props, pseudo)
    got = _probe(fixture, *fix, props, pseudo)
    assert got == want, what


K_SCALED = [("tile title size", "#c3-a .tile-title", "#s2-model .tile-title", "fontSize"),
            ("edge width", "#c3-e1", "#s-2 path.edge:not(.edge--ok):not(.edge--loss)", "strokeWidth"),
            ("coloured edge width", "#c3-e2", "#s2-pass", "strokeWidth")]


@pytest.mark.parametrize("what, fsel, vsel, prop", K_SCALED, ids=[k[0] for k in K_SCALED])
def test_diagram_floors_scale_with_k_like_deck_v2(pages, what, fsel, vsel, prop):
    """Sizes depend on each diagram's --k, so the fixture is measured at deck-v2's own --k."""
    fixture, v2 = pages
    _at(v2, "s-2", 4)
    k, want = v2.evaluate("""([sel, p]) => { const e = document.querySelector(sel);
        return [getComputedStyle(e.closest('svg')).getPropertyValue('--k').trim(), getComputedStyle(e)[p]]; }""", [vsel, prop])
    _at(fixture, "c-3", 3)
    got = fixture.evaluate("""([sel, p, k]) => { const e = document.querySelector(sel), svg = e.closest('svg');
        const old = svg.style.getPropertyValue('--k'); svg.style.setProperty('--k', k);
        const v = getComputedStyle(e)[p]; svg.style.setProperty('--k', old); return v; }""", [fsel, prop, k])
    assert got == want, f"{what} at --k {k}"


NOTES = [("callout", ".callout", ("backgroundColor", "backdropFilter", "borderRadius", "boxShadow", "paddingTop",
                                  "paddingLeft", "opacity"), None),
         ("callout heading", ".callout h3", TYPE + ("marginBottom",), None),
         ("callout text", ".callout p:not(.cite)", ("fontFamily", "fontSize", "lineHeight", "color"), None),
         ("callout cite", ".callout .cite", ("fontFamily", "fontSize", "color", "borderTopColor", "paddingTop"), None),
         ("source link", ".callout a.src", ("textDecorationLine", "textDecorationThickness", "textUnderlineOffset",
                                            "color"), None),
         ("ring", ".ring", ("boxShadow", "borderRadius", "opacity"), None),
         ("veil", ".veil", ("backgroundColor", "backdropFilter", "opacity"), None),
         ("pin", ".pin:not(.is-current)", ("backgroundColor", "color", "width", "height", "boxShadow", "fontSize"), None),
         ("current pin", ".pin.is-current", ("backgroundColor", "color"), None),
         ("notes bar", ".notes-nav button", ("color", "fontSize", "fontFamily", "borderRadius"), None),
         ("notes position", ".notes-pos", ("color", "fontVariantNumeric"), None),
         ("notes button on", ".notes-btn", ("backgroundColor", "color", "borderTopColor"), None)]


@pytest.fixture
def notes_pages(pages):
    """Both decks in notes mode on a slide with two or more notes (so a non-current pin exists)."""
    fixture, v2 = pages
    for pg, slide in ((fixture, "c-2"), (v2, "s-2")):
        _at(pg, slide, 0)
        pg.keyboard.press("n")
        pg.wait_for_function("document.body.classList.contains('notes-focus')")
        settle(pg)
    yield fixture, v2
    for pg in (fixture, v2):
        pg.keyboard.press("Escape")
        pg.wait_for_function("!document.body.classList.contains('notes-on')")


@pytest.mark.parametrize("what, sel, props, pseudo", NOTES, ids=[n[0] for n in NOTES])
def test_notes_ui_computes_like_deck_v2(notes_pages, what, sel, props, pseudo):
    fixture, v2 = notes_pages
    got, want = (_norm(pg.evaluate(PROBE, [sel, list(props), pseudo])) for pg in (fixture, v2))
    assert got == want, what


def test_citation_links_underline_in_the_surrounding_colour(pages):
    fixture, v2 = pages
    js = """sel => { const a = document.querySelector(sel), s = getComputedStyle(a);
      return [s.textDecorationLine, s.textDecorationThickness, s.textUnderlineOffset, s.color === getComputedStyle(a.parentElement).color]; }"""
    _at(fixture, "c-4", 1)
    _at(v2, "s-12", 0)
    assert fixture.evaluate(js, "#c-4 .cite a") == v2.evaluate(js, "#s-12 .cite a")
    assert fixture.evaluate(js, "#c-4 .cite a")[3] is True, "never blue: the link takes its text's colour"


def test_waiting_steps_stay_visible_as_hollow_discs(pages):
    fixture, _ = pages
    _at(fixture, "c-3", 1)
    got = fixture.evaluate("""() => { const li = document.querySelector('#c3-s3'), b = getComputedStyle(li, '::before');
      return [+getComputedStyle(li).opacity, b.backgroundColor, b.borderTopStyle]; }""")
    assert got[0] == 1 and got[2] == "solid" and re.search(r"(rgba\(0, 0, 0, 0\)|transparent)", got[1]), got


# ---------- layout guard: every fixture slide × step × review size ----------

@pytest.mark.parametrize("size", REVIEW_SIZES, ids=[f"{w}x{h}" for w, h in REVIEW_SIZES])
def test_fixture_slides_have_no_overlap_clipping_or_offcanvas_text(browser, deck_file, size):
    w, h = size
    c, pg, errors = _open(browser, deck_file, w, h)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    faults = []
    for sid in FIXTURE_IDS:
        faults += layout_faults(pg, sid, shoot=lambda k, sid=sid: pg.screenshot(
            path=str(ARTIFACTS / f"fixture-{sid}-{k}-{w}x{h}.png")))
    c.close()
    assert errors == []
    assert faults == [], "\n".join(faults)


def test_layout_guard_catches_a_body_pushed_over_the_title(browser, tmp_path):
    """Negative control: the guard must see a real collision, or a green run proves nothing."""
    f = assemble_themed(tmp_path / "bad.html", deck_css="@layer deck { #c-2 > .body { translate: 0 -30vh; } }")
    c, pg, _ = _open(browser, f)
    faults = layout_faults(pg, "c-2")
    c.close()
    assert any("covers title" in x for x in faults), faults


# ---------- title bar: compact agenda ----------

def test_compact_agenda_drops_an_opaque_list_inside_the_viewport(browser, tmp_path):
    f = assemble_themed(tmp_path / "long.html", title="A Considerably Longer Deck Title For Crowding The Agenda Row",
                        subtitle="With a subtitle that keeps going and going")
    c, pg, errors = _open(browser, f, 1000, 598)
    assert pg.evaluate("document.querySelector('.bar').classList.contains('bar--compact')")
    pg.click(".nav-current")
    pg.wait_for_function("+getComputedStyle(document.querySelector('.agenda')).opacity === 1")
    settle(pg)
    got = pg.evaluate("""() => { const a = document.querySelector('.agenda'), r = a.getBoundingClientRect(),
        bar = document.querySelector('.nav-current').getBoundingClientRect(), s = getComputedStyle(a);
        const cur = getComputedStyle(document.querySelector('.agenda li.is-current button'));
        return { bg: s.backgroundColor, shadow: s.boxShadow, right: r.right, top: r.top, barBottom: bar.bottom,
                 bottom: r.bottom, vw: innerWidth, vh: innerHeight, current: cur.color,
                 label: getComputedStyle(document.querySelector('.nav-current')).color }; }""")
    c.close()
    assert errors == []
    assert re.fullmatch(r"rgb\(\d+, \d+, \d+\)", got["bg"]), f"opaque panel (no nested blur): {got['bg']}"
    assert got["shadow"] != "none" and got["top"] >= got["barBottom"] - 1
    assert got["right"] <= got["vw"] and got["bottom"] <= got["vh"]
    assert got["current"] == got["label"], "the current chapter keeps its accent-ink label in the list"


# ---------- motion ----------

def test_reduced_motion_reveals_without_travel(browser, deck_file):
    def transform_on_reveal(**ctx):
        c, pg, _ = _open(browser, deck_file, 1280, 720, **ctx)
        _at(pg, "c-2", 0)
        pg.evaluate("deck.goto('c-2', 1)")
        t = pg.evaluate("getComputedStyle(document.querySelector('#c2-a')).transform")
        c.close()
        return t
    assert transform_on_reveal(reduced_motion="reduce") == "none"
    assert transform_on_reveal() != "none", "control: with motion, a revealed part rises into place"


# ---------- optional modules: scene, narration tiles, pop-overs, tile row ----------

MODULE_IDS = re.findall(r'<section class="[^"]*" id="([\w-]+)"', MODULE_SLIDES)


@pytest.fixture(scope="module")
def module_file(tmp_path_factory):
    return assemble_themed(tmp_path_factory.mktemp("mod") / "modules.html", slides=MODULE_SLIDES,
                           title="Module Fixture", subtitle="Layout layer")


@pytest.fixture(scope="module")
def module_pages(browser, module_file):
    cf, fixture, ef = _open(browser, module_file)
    cv, v2, ev = _open(browser, DECK_V2)
    yield fixture, v2
    cf.close()
    cv.close()
    assert ef == [] and ev == [], f"page errors: {ef + ev}"


CARD = ("backgroundColor", "backdropFilter", "borderRadius", "boxShadow", "paddingTop", "paddingLeft")
MODULE_PAIRS = [
    ("scene grid", ("m-2", 0, "#m-2"), ("s-3", 0, "#s-3"), ("gridTemplateColumns", "columnGap", "paddingTop"), None),
    ("scene on", ("m-2", 1, ".scene"), ("s-3", 1, ".world"), ("opacity", "filter"), None),
    ("scene soft", ("m-3", 1, ".scene"), ("s-3", 2, ".world"), ("opacity", "filter"), None),
    ("scene backdrop", ("m-4", 3, ".scene"), ("s-8", 3, ".world"), ("opacity", "filter"), None),
    ("scene camera motion", ("m-2", 2, ".scene .cam"), ("s-3", 2, ".world .cam"),
     ("transitionDuration", "transitionTimingFunction"), None),
    ("scene step list", ("m-2", 2, "#m2-s2"), ("s-3", 3, "#s-3 .steps li.is-current:not(.sub)"),
     ("fontSize", "lineHeight", "paddingTop", "paddingLeft", "color"), None),
    ("narration tile", ("m-2", 1, "#n-1"), ("s-3", 4, "#s-3 .narr-tile.is-shown"),
     CARD + ("opacity", "filter", "transform"), None),
    ("narration quote", ("m-2", 1, "#n-1 .msg-text"), ("s-3", 4, "#s-3 .narr-tile.is-shown .msg-text"), TYPE, None),
    ("narration sender", ("m-2", 1, "#n-1 .msg-from"), ("s-3", 4, "#s-3 .narr-tile.is-shown .msg-agent"),
     TYPE + ("marginBottom",), None),
    ("pop-over", ("m-3", 1, "#m3-pop"), ("s-3", 2, "#s3-pop"),
     ("display", "columnGap", "opacity", "filter", "transform", "visibility", "marginBottom", "alignSelf"), None),
    ("pop-over tile", ("m-3", 1, "#m3-pop .pop-panel"), ("s-3", 2, "#s3-pop .pop-panel"),
     ("backgroundColor", "backdropFilter", "borderRadius", "boxShadow", "paddingTop", "paddingLeft", "display"), None),
    ("pop-over caption", ("m-3", 1, "#m3-pop-cap"), ("s-3", 2, "#s3-pop .pop-panel figcaption"), TYPE, None),
    ("tile row", ("m-4", 3, "#m-4 .body--tiles"), ("s-9", 3, "#s-9 .body--tiles"),
     ("columnGap", "alignSelf", "marginBottom"), None),
    ("text tile", ("m-4", 3, "#t-1"), ("s-9", 3, "#s9-t1"), CARD + ("opacity", "transform", "rowGap"), None),
    ("text tile heading", ("m-4", 3, "#t-1 h3"), ("s-9", 3, "#s9-t1 h3"), TYPE, None),
]


@pytest.mark.parametrize("what, fix, ref, props, pseudo", MODULE_PAIRS, ids=[p[0] for p in MODULE_PAIRS])
def test_module_component_computes_like_deck_v2(module_pages, what, fix, ref, props, pseudo):
    fixture, v2 = module_pages
    want = _probe(v2, *ref, props, pseudo)
    got = _probe(fixture, *fix, props, pseudo)
    assert got == want, what


def test_popover_tile_is_opaque_and_shadowed_not_frosted(module_pages):
    """Presenter, 23 Nov (PB-007): the pop-over tile is an opaque, shadowed tile as in deck-v2, not frosted."""
    fixture, _ = module_pages
    got = _probe(fixture, "m-3", 1, "#m3-pop .pop-panel", ("backgroundColor", "backdropFilter", "boxShadow"))
    assert re.fullmatch(r"rgb\(\d+, \d+, \d+\)", got["backgroundColor"]), f"alpha must be 1: {got['backgroundColor']}"
    assert got["backdropFilter"] == "none" and got["boxShadow"] != "none", got


@pytest.mark.parametrize("size", REVIEW_SIZES, ids=[f"{w}x{h}" for w, h in REVIEW_SIZES])
def test_module_slides_have_no_overlap_clipping_or_offcanvas_text(browser, module_file, size):
    w, h = size
    c, pg, errors = _open(browser, module_file, w, h)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    faults = []
    for sid in MODULE_IDS:
        faults += layout_faults(pg, sid, shoot=lambda k, sid=sid: pg.screenshot(
            path=str(ARTIFACTS / f"modules-{sid}-{k}-{w}x{h}.png")))
    c.close()
    assert errors == []
    assert faults == [], "\n".join(faults)
