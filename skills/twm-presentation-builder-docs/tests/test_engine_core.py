"""Spec: PB-002

The architecture contract and core engine: a skeleton with marked blocks, mechanics-only CSS in
``@layer arch`` and a define-once engine that drives any slides between the SLIDES markers, with an
ARCHITECTURE part that documents everything the engine reads and sets.

Coverage: happy (plan, keys/click/wheel stepping, snapping, show-at/hide-at, step list, Insight,
agenda, progress, notes, ambient, diagram kit, module hook) · edge (deck ends, notes at a target's
last revealed step, compact agenda, reduced motion, a different slide set) · negative (no remote
loads or risky JS, no incident/organisation names, no colour literals in arch, nothing undocumented).
"""

import re

import pytest
from playwright.sync_api import sync_playwright

from helper_engine import (ARCH_CSS, ARCHITECTURE, BLOCKS, ENGINE_JS, LAYER_ORDER, SKELETON,
                           RECORDER_MODULE, assemble, block, open_deck, opacity, settle, state)

NEXT = ("ArrowRight", "ArrowDown", "PageDown", " ")
# organisations and the source deck's incident-specific modules/names (word-bounded regexes)
BANNED = (r"hugging", r"openai", r"modal\b", r"metr\b", r"deloitte", r"anthropic", r"incident", r"swarm",
          r"world", r"narr-", r"narration", r"popover", r"mirror", r"day0", r"tl-day")


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
    return assemble(tmp_path_factory.mktemp("deck") / "fixture.html")


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


def press(page, key, times=1):
    for _ in range(times):
        page.keyboard.press(key)


def at(page, slide, step):
    page.wait_for_function("([s, k]) => deck.state().slide === s && deck.state().step === k", [slide, step])


# ---------- static contract ----------

def test_skeleton_declares_the_layer_order_and_each_block_once():
    src = SKELETON.read_text(encoding="utf-8")
    assert src.lstrip().lower().startswith("<!doctype html>")
    assert src.count(LAYER_ORDER) == 1
    for name in BLOCKS + ("SLIDES",):
        assert block(src, name), f"{name} block missing"
        assert src.count(f"{name}:BEGIN") == 1 and src.count(f"{name}:END") == 1
    assert block(src, "SLIDES").group(1).strip() == "", "the skeleton carries no slides"
    style = src.index("<style")
    assert style < src.index(LAYER_ORDER) < src.index("ARCH:BEGIN"), "layer order declared before any layer"


def test_assembled_deck_is_one_offline_endpoint_safe_file(deck_file):
    src = deck_file.read_text(encoding="utf-8")
    assert len(re.findall(r"<script\b", src)) == 1, "one script block: modules then engine"
    assert not re.search(r"<script[^>]*\bsrc=|<link\b|@import|<iframe|<form|<object|<embed", src, re.I)
    for bad in ("eval(", "atob(", "document.write", "new Function", "innerHTML", "outerHTML", "fetch(",
                "XMLHttpRequest", "import("):
        assert bad not in src, f"risky call {bad!r} in the assembled deck"
    without_links = re.sub(r'<a\b[^>]*\bhref="[^"]*"', "", src).replace("http://www.w3.org/2000/svg", "")
    assert not re.search(r"(?:https?:)?//[a-z0-9.-]+\.[a-z]{2,}", without_links, re.I), \
        "remote URLs appear only as citation link targets"


def test_assembled_deck_makes_no_network_request(browser, deck_file):
    c = browser.new_context()
    pg = c.new_page()
    remote = []
    pg.on("request", lambda r: remote.append(r.url) if not r.url.startswith(("file:", "data:", "about:")) else None)
    open_deck(pg, deck_file)
    settle(pg)
    c.close()
    assert remote == []


def test_core_carries_no_incident_or_organisation_names():
    for f in (ENGINE_JS, ARCH_CSS, SKELETON, ARCHITECTURE):
        text = f.read_text(encoding="utf-8").lower()
        if f is ARCHITECTURE:   # the doc may name the optional modules it reserves room for
            text = re.sub(r"<!-- modules:begin -->.*?<!-- modules:end -->", "", text, flags=re.S)
        hits = [w for w in BANNED if re.search(rf"\b{w}", text)]
        assert hits == [], f"{f.name}: {hits}"


def test_arch_css_is_one_arch_layer_without_colour_literals():
    css = ARCH_CSS.read_text(encoding="utf-8")
    body = re.sub(r"/\*.*?\*/", "", css, flags=re.S).strip()
    assert body.startswith("@layer arch {") and body.endswith("}")
    assert not re.search(r"#[0-9a-f]{3,8}\b|\b(?:rgb|rgba|hsl|hsla|oklch|lab)\(", body, re.I), \
        "palette is a later layer: arch uses system colours only"


def _engine_attributes():
    js = ENGINE_JS.read_text(encoding="utf-8")
    camel = re.findall(r"dataset\.([a-zA-Z]+)", js)
    attrs = {"data-" + re.sub(r"[A-Z]", lambda m: "-" + m.group(0).lower(), c) for c in camel}
    attrs |= set(re.findall(r"\b(data-[a-z-]+)", js))
    return attrs


def test_architecture_documents_every_attribute_the_engine_reads():
    doc = ARCHITECTURE.read_text(encoding="utf-8")
    attrs = _engine_attributes()
    assert {"data-chapter", "data-show-at", "data-hide-at", "data-at", "data-ambient", "data-for",
            "data-from", "data-to"} <= attrs
    assert [a for a in sorted(attrs) if f"`{a}" not in doc] == []


def test_architecture_documents_every_class_the_engine_sets():
    js = ENGINE_JS.read_text(encoding="utf-8")
    doc = ARCHITECTURE.read_text(encoding="utf-8")
    classes = set(re.findall(r"classList\.(?:toggle|add|remove)\('([\w-]+)'", js))
    for names in re.findall(r"\bel\('\w+', '([\w -]+)'", js):
        classes |= set(names.split())
    assert {"is-active", "is-visible", "is-shown", "is-overlaid", "notes-on", "bar--compact"} <= classes
    assert [c for c in sorted(classes) if not re.search(rf"\.{re.escape(c)}\b|`{re.escape(c)}`", doc)] == []


def test_architecture_states_layer_order_guarantees_and_api():
    doc = ARCHITECTURE.read_text(encoding="utf-8")
    assert LAYER_ORDER in doc
    for term in ("single file", "offline", "endpoint", "window.deck", "deckModules", "SLIDES:BEGIN",
                 "#lift", "#arr", "prefers-reduced-motion"):
        assert term.lower() in doc.lower(), term


# ---------- navigation ----------

def test_plan_counts_steps_from_show_at_and_at(page):
    assert page.evaluate("deck.plan()") == [["s-1", 0], ["s-2", 3], ["s-3", 2], ["s-4", 0]]


@pytest.mark.parametrize("key", NEXT)
def test_each_next_key_advances_one_step(page, key):
    press(page, key)
    at(page, "s-2", 0)
    press(page, key)
    at(page, "s-2", 1)


def test_steps_run_before_the_slide_is_left_and_back_lands_on_the_last_step(page):
    press(page, "ArrowRight", 4)
    at(page, "s-2", 3)
    press(page, "ArrowRight")
    at(page, "s-3", 0)
    press(page, "ArrowLeft")
    at(page, "s-2", 3)
    for key in ("ArrowUp", "PageUp"):
        press(page, key)
    at(page, "s-2", 1)


def test_home_and_end_jump_and_the_deck_ends_are_stops(page):
    press(page, "End")
    at(page, "s-4", 0)
    press(page, "ArrowRight")
    at(page, "s-4", 0)
    press(page, "Home")
    at(page, "s-1", 0)
    press(page, "ArrowLeft")
    at(page, "s-1", 0)


def test_click_on_the_slide_advances_one_step(page):
    page.mouse.click(640, 400)
    at(page, "s-2", 0)


def test_a_wheel_gesture_advances_exactly_one_step(page):
    page.evaluate("deck.goto('s-2', 0)")
    page.mouse.move(640, 400)
    for _ in range(6):   # one gesture = a burst of events
        page.mouse.wheel(0, 60)
    at(page, "s-2", 1)
    settle(page)
    assert state(page)["step"] == 1


def test_the_current_slide_snaps_to_fill_the_viewport(page):
    press(page, "ArrowRight")
    page.wait_for_function("Math.abs(document.querySelector('#s-2').getBoundingClientRect().top) < 1")
    settle(page)
    r = page.evaluate("(() => { const r = document.querySelector('#s-2').getBoundingClientRect();"
                      " return [r.top, r.height, innerHeight]; })()")
    assert abs(r[0]) < 1 and abs(r[1] - r[2]) < 1


# ---------- steps and overlays ----------

def test_show_at_reveals_from_its_step_and_hide_at_hides_from_its_step(page):
    seen = {}
    for k in range(4):
        page.evaluate("k => deck.goto('s-2', k)", k)
        settle(page)
        seen[k] = [round(opacity(page, f"#{i}")) for i in ("m-always", "m-first", "m-claim", "m-early")]
    assert seen == {0: [1, 0, 0, 1], 1: [1, 1, 0, 1], 2: [1, 1, 1, 0], 3: [1, 1, 1, 0]}


def test_show_at_works_on_svg_parts(page):
    page.evaluate("deck.goto('s-3', 0)")
    settle(page)
    assert round(opacity(page, "#d-b")) == 0 and round(opacity(page, "#d-edge")) == 0
    page.evaluate("deck.goto('s-3', 2)")
    settle(page)
    assert round(opacity(page, "#d-b")) == 1 and round(opacity(page, "#d-edge")) == 1


def test_step_list_marks_current_and_done(page):
    cls = "() => ['#d-step-1', '#d-step-2'].map(s => [...document.querySelector(s).classList].filter(c => c !== 'is-visible').sort())"
    page.evaluate("deck.goto('s-3', 1)")
    assert page.evaluate(cls) == [["is-current"], []]
    page.evaluate("deck.goto('s-3', 2)")
    assert page.evaluate(cls) == [["is-done"], ["is-current"]]


def test_overlay_shows_only_at_its_step_and_softens_the_slide(page):
    result = {}
    for k in (2, 3, 2):
        page.evaluate("k => deck.goto('s-2', k)", k)
        settle(page)
        result.setdefault(k, []).append((
            round(opacity(page, "#m-insight")),
            page.evaluate("document.querySelector('#s-2').classList.contains('is-overlaid')")))
    assert result == {2: [(0, False), (0, False)], 3: [(1, True)]}
    page.evaluate("deck.goto('s-3', 0)")
    settle(page)
    assert round(opacity(page, "#m-insight")) == 0, "an overlay never lingers past its slide"


# ---------- title bar ----------

def test_agenda_lists_distinct_chapters_in_order_and_marks_the_current_one(page):
    labels = page.evaluate("[...document.querySelectorAll('.agenda li')].map(li => li.textContent.trim())")
    assert labels == ["Opening", "Method", "Close"]
    current = "document.querySelector('.agenda [aria-current]').textContent.trim()"
    assert page.evaluate(current) == "Opening"
    page.evaluate("deck.goto('s-3', 1)")
    assert page.evaluate(current) == "Method"


def test_agenda_click_goes_to_the_chapter_start_and_the_title_goes_home(page):
    page.click(".agenda li:nth-child(3) button")
    at(page, "s-4", 0)
    page.click(".agenda li:nth-child(2) button")
    at(page, "s-2", 0)
    page.click(".bar-home")
    at(page, "s-1", 0)


def test_progress_grows_through_the_deck(page):
    w = "document.querySelector('.progress').style.width"
    first = page.evaluate(w)
    page.evaluate("deck.goto('s-3', 1)")
    mid = page.evaluate(w)
    page.evaluate("deck.goto('s-4', 0)")
    assert float(first.rstrip("%")) < float(mid.rstrip("%")) < float(page.evaluate(w).rstrip("%")) == 100


def test_agenda_goes_compact_only_when_the_row_would_crowd_the_title(browser, tmp_path):
    f = assemble(tmp_path / "long.html", title="A Considerably Longer Deck Title For Crowding",
                 subtitle="With a subtitle that keeps going")
    for width, compact in ((1920, False), (900, True)):
        c, pg, errors = _page(browser, f, viewport={"width": width, "height": 700})
        pg.wait_for_function("document.fonts.status === 'loaded'")
        got = pg.evaluate("document.querySelector('.bar').classList.contains('bar--compact')")
        label = pg.evaluate("getComputedStyle(document.querySelector('.nav-current')).display")
        c.close()
        assert errors == []
        assert got is compact and (label != "none") is compact, width


# ---------- reader notes ----------

def _notes(page):
    return page.evaluate("""(() => { const c = document.querySelector('.callout'), r = document.querySelector('.ring');
      const rr = r.getBoundingClientRect();
      return { on: document.body.classList.contains('notes-on'), heading: (c.querySelector('h3') || {}).textContent,
               link: (c.querySelector('a.src') || {}).href, ring: [rr.left, rr.top, rr.right, rr.bottom],
               pos: document.querySelector('.notes-pos').textContent, pins: document.querySelectorAll('.pin').length,
               state: deck.state() }; })()""")


def test_notes_mode_toggles_spotlights_the_target_and_restores_the_step(page):
    page.evaluate("deck.goto('s-2', 1)")
    press(page, "n")
    page.wait_for_function("document.body.classList.contains('notes-focus')")
    settle(page)
    n = _notes(page)
    assert n["on"] and n["heading"] == "Claim note" and n["link"] == "https://example.org/claim"
    assert n["pins"] == 2 and n["pos"] == "1 / 2"
    t = page.evaluate("(() => { const r = document.querySelector('#m-claim').getBoundingClientRect();"
                      " return [r.left, r.top, r.right, r.bottom]; })()")
    ring = n["ring"]
    assert ring[0] <= t[0] and ring[1] <= t[1] and ring[2] >= t[2] and ring[3] >= t[3], "window frames the target"
    assert round(opacity(page, "#m-insight")) == 0, "overlays are hidden in notes mode"
    press(page, "Escape")
    page.wait_for_function("!document.body.classList.contains('notes-on')")
    assert state(page)["step"] == 1 and page.evaluate("document.querySelectorAll('.pin').length") == 0


def test_a_note_shows_its_slide_at_the_last_step_its_target_is_revealed(page):
    page.evaluate("deck.goto('s-2', 0)")
    page.click(".notes-btn")
    page.wait_for_function("document.body.classList.contains('notes-focus')")
    assert _notes(page)["state"]["step"] == 3, "claim: revealed from 2, never hidden: last step"
    press(page, "ArrowRight")
    page.wait_for_function("document.querySelector('.callout h3').textContent === 'Early note'")
    settle(page)
    assert _notes(page)["state"]["step"] == 1, "early: hidden from step 2, so step 1"
    assert round(opacity(page, "#m-early")) == 1


def test_notes_keys_cycle_notes_and_page_keys_change_slide(page):
    page.evaluate("deck.goto('s-2', 0)")
    press(page, "n")
    page.wait_for_function("document.querySelector('.notes-pos').textContent === '1 / 2'")
    press(page, "ArrowRight", 2)
    page.wait_for_function("document.querySelector('.notes-pos').textContent === '1 / 2'")
    press(page, "PageDown")
    page.wait_for_function("deck.state().slide === 's-3'")
    page.wait_for_function("document.querySelector('.callout h3').textContent === 'Tile note'")
    press(page, "PageDown")
    page.wait_for_function("document.querySelector('.notes-pos').textContent === 'No notes on this slide'")
    page.click("[data-notes=close]")
    page.wait_for_function("!document.body.classList.contains('notes-on')")


# ---------- ambient, diagram kit, modules ----------

def test_ambient_layer_only_on_data_ambient_slides_and_it_drifts(page):
    counts = page.evaluate("[...document.querySelectorAll('section.slide')].map(s => s.querySelectorAll(':scope > .ambient .orb').length)")
    assert counts[0] > 0 and counts[1:] == [0, 0, 0]
    first = page.evaluate("document.querySelector('.ambient .orb').style.transform")
    page.wait_for_function("t => document.querySelector('.ambient .orb').style.transform !== t", arg=first)


def test_reduced_motion_lands_instantly_and_the_ambient_holds_still(browser, deck_file):
    jump = "(() => { deck.next(); return [document.querySelector('.deck').scrollTop, document.querySelector('#s-2').offsetTop]; })()"
    c, pg, errors = _page(browser, deck_file, reduced_motion="reduce")
    frames = pg.evaluate("""() => new Promise(res => { const seen = new Set(); let n = 0;
      const f = () => { seen.add(document.querySelector('.ambient .orb').style.transform);
        if (++n < 20) requestAnimationFrame(f); else res([...seen]); }; requestAnimationFrame(f); })""")
    top, target = pg.evaluate(jump)
    c.close()
    assert errors == [] and frames == [""], "no drift under reduced motion"
    assert top == target, "the slide change lands without a smooth scroll"
    c, pg, errors = _page(browser, deck_file)
    top, target = pg.evaluate(jump)
    c.close()
    assert top < target, "control: without reduced motion the deck scrolls smoothly"


def test_diagram_edges_are_drawn_gapped_between_tiles_and_tile_text_is_centred(page):
    d = page.evaluate("document.querySelector('#d-edge').getAttribute('d')")
    nums = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", d)]
    assert 300 < nums[0] < 330 and 570 < nums[-2] < 600, "starts after tile A, ends before tile B"
    xs = page.evaluate("[...document.querySelectorAll('#d-b text')].map(t => +t.getAttribute('x'))")
    ys = page.evaluate("[...document.querySelectorAll('#d-b text')].map(t => +t.getAttribute('y'))")
    assert xs == [730, 730] and ys[0] < 130 < ys[1], "lines centred as a block in the rect"


def test_registered_modules_get_init_and_a_render_per_step(browser, tmp_path):
    f = assemble(tmp_path / "mod.html", modules=RECORDER_MODULE)
    c, pg, errors = _page(browser, f)
    pg.keyboard.press("ArrowRight")
    pg.keyboard.press("ArrowRight")
    rec = pg.evaluate("window.__rec")
    c.close()
    assert errors == []
    assert rec["init"] == ["s-1", "s-2", "s-3", "s-4"]
    assert rec["renders"][-2:] == [["s-2", 0], ["s-2", 1]]


def test_the_engine_drives_any_slide_set(browser, tmp_path):
    slides = """
    <section class="slide" id="intro" data-chapter="Only"><h2 class="title">One</h2>
      <div class="body"><p data-show-at="1">later</p></div></section>
    <section class="slide" id="outro" data-chapter="Only"><h2 class="title">Two</h2><div class="body"></div></section>"""
    f = assemble(tmp_path / "any.html", slides=slides)
    c, pg, errors = _page(browser, f)
    plan = pg.evaluate("deck.plan()")
    pg.keyboard.press("ArrowRight")
    pg.keyboard.press("ArrowRight")
    pg.wait_for_function("deck.state().slide === 'outro'")
    agenda = pg.evaluate("document.querySelectorAll('.agenda li').length")
    c.close()
    assert errors == [] and plan == [["intro", 1], ["outro", 0]] and agenda == 1
