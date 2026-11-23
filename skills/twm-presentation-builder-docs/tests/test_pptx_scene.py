"""Spec: PB-023

PPTX scene extraction: `pptx/scripts/scene.py` opens an assembled deck in Chrome and writes one
scene per deck: every slide's final-state layout (roles, geometry, text runs, palette roles, style
effect bands, SVG primitives in slide coordinates, z-order, notes) plus a step timeline in the
PB-022 effect vocabulary, with what has no native equivalent flagged `unsupported`.

Decks: the core component fixture and the module fixture (scene, narration, pop-over, tile row),
both assembled with `scripts/assemble.py new`, plus a small shapes deck (transformed groups,
relative and arc paths) for geometry.

Coverage: happy (schema-valid, slide order and size, every visible component captured with its
role, boxes match the render, text runs match DOM text, palette roles, effect bands, absolute and
transformed paths, enter/exit/fill deltas at their steps, notes, deterministic, CLI) · edge
(hidden-at-final elements measured where visible, camera-scaled tiles, arcs and relative paths,
step-list markers) · negative (validator rejects broken scenes, camera moves flagged
unsupported/morph, no per-part motion under a camera move, non-skill deck and missing marker
refused with a clear error).
"""

from __future__ import annotations

import copy
import json
import re

import pytest
from playwright.sync_api import sync_playwright

import helper_engine as he
import helper_pptx as hp

scene_mod = hp.load_script("scene")
anim = hp.load_script("animations")
asm = he.load_assemble()

W, H = 1920, 1080

SHAPES_SLIDES = """
<section class="slide" id="g-1" data-chapter="Shapes">
  <p class="kicker">01 · Shapes</p>
  <h2 class="title">Transformed groups and free paths</h2>
  <div class="body">
    <svg class="diagram" viewBox="0 0 800 400" role="img" aria-label="Shapes under transforms">
      <g transform="translate(40 30) scale(1.5)">
        <g class="layer-nodes">
          <g class="tile" id="g-tile"><rect x="10" y="10" width="160" height="80"/><text class="tile-title">Scaled</text></g>
        </g>
        <path id="g-free" class="shape" d="m 260 20 h 60 v 40 a 20 20 0 0 1 -20 20 q -30 0 -40 -30 s 10 -20 0 -30 z"/>
      </g>
      <g class="layer-labels"><text class="label" id="g-label" x="400" y="360">PLAIN</text></g>
    </svg>
  </div>
</section>
"""

ROLE_OF = {  # independent map from the architecture's component API to the scene's role names
    ".kicker": "kicker", "h2.title": "title", ".byline": "byline", "ol.steps > li": "step-item",
    "ul.points > li": "point", ".overlay--insight": "insight", "g.tile:not(.tile--key)": "tile",
    "g.tile--key": "key-tile", "path.edge": "edge", "text.label": "label", "text.tag": "tag",
    ".narr-tile": "narration-tile", ".popover": "popover", ".text-tile": "tile-card",
    ".msg-card": "message-card", "p.annot": "annotation", "svg.diagram": "diagram", "blockquote": None,
    ".ambient .orb": "orb", "td": "cell", "th": "cell", "dt": "term-title", "dd": "term-text",
}

VISIBLE_IDS = r"""([slide, sels]) => {
  const s = document.getElementById(slide);
  const roots = [s].concat(s.hasAttribute('data-scene') ? [document.querySelector('.scene')] : []);
  const shown = e => { let op = 1;
    for (let n = e; n && n.nodeType === 1; n = n.parentElement) { const c = getComputedStyle(n);
      if (c.display === 'none') return false; op *= +c.opacity; }
    const r = e.getBoundingClientRect();
    return getComputedStyle(e).visibility !== 'hidden' && op > 0.01 && (r.width > 0 || r.height > 0); };
  const out = {};
  for (const sel of sels) out[sel] = roots.flatMap(r => [...r.querySelectorAll(sel)])
    .filter(e => !e.closest('.note') && shown(e)).map(e => e.id || null);
  return out;
}"""


# ---------- fixtures ----------

@pytest.fixture(scope="module")
def browser():
    """System Chrome, once per module (no conftest: other suites share this folder)."""
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        yield b
        b.close()


@pytest.fixture(scope="module")
def decks(tmp_path_factory):
    d = tmp_path_factory.mktemp("scene")
    return {
        "core": asm.new(d / "core.html", "Core Fixture", "Scene", slides=he.COMPONENT_SLIDES),
        "mods": asm.new(d / "mods.html", "Module Fixture", "Scene", slides=he.MODULE_SLIDES),
        "shapes": asm.new(d / "shapes.html", "Shapes Fixture", "Scene", slides=SHAPES_SLIDES),
    }


@pytest.fixture(scope="module")
def scenes(browser, decks):
    return {k: scene_mod.extract(v, browser=browser) for k, v in decks.items()}


def _open(browser, deck):
    ctx = browser.new_context(viewport={"width": W, "height": H}, reduced_motion="reduce")
    pg = ctx.new_page()
    he.open_deck(pg, deck)
    return ctx, pg


@pytest.fixture(scope="module")
def pages(browser, decks):
    opened = {k: _open(browser, v) for k, v in decks.items()}
    yield {k: pg for k, (_, pg) in opened.items()}
    for ctx, _ in opened.values():
        ctx.close()


def go(page, slide, step):
    page.evaluate("([s, k]) => deck.goto(s, k)", [slide, step])
    page.wait_for_function("([s, k]) => deck.state().slide === s && deck.state().step === k", arg=[slide, step])
    he.settle(page)


def slide(doc, sid):
    return next(s for s in doc["slides"] if s["id"] == sid)


def el(doc, sid, eid):
    found = [e for e in slide(doc, sid)["elements"] if e["id"] == eid]
    assert found, f"{eid} not captured on {sid}"
    return found[0]


def deltas(doc, sid, step, eid=None):
    t = next(t for t in slide(doc, sid)["timeline"] if t["step"] == step)
    return [d for d in t["deltas"] if eid is None or d["el"] == eid]


def screen_box(page, sel):
    return page.evaluate("s => { const r = document.querySelector(s).getBoundingClientRect();"
                         " return {x: r.left, y: r.top, w: r.width, h: r.height}; }", sel)


def near(a, b, tol=1.0):
    return all(abs(a[k] - b[k]) <= tol for k in ("x", "y", "w", "h"))


# ---------- schema and structure ----------

def test_every_scene_validates_against_the_shipped_schema(scenes):
    schema = json.loads(scene_mod.SCHEMA_PATH.read_text(encoding="utf-8"))
    for name, doc in scenes.items():
        assert scene_mod.validate(doc, schema) == [], name


def test_validator_rejects_a_broken_scene(scenes):
    """Guards the validator itself: a no-op validator would make the schema test meaningless."""
    schema = json.loads(scene_mod.SCHEMA_PATH.read_text(encoding="utf-8"))
    bad = copy.deepcopy(scenes["core"])
    del bad["slides"][0]["elements"][0]["box"]
    bad["slides"][1]["elements"][0]["role"] = "not-a-role"
    bad["slides"][1]["timeline"][1]["deltas"][0]["effect"] = "spin"
    bad["size"]["width"] = "wide"
    errors = scene_mod.validate(bad, schema)
    joined = "\n".join(errors)
    assert len(errors) >= 4, joined
    for needle in ("box", "not-a-role", "spin", "wide"):
        assert needle in joined, f"no error mentions {needle!r}:\n{joined}"


def test_slides_follow_the_deck_plan_at_the_slide_size(scenes, pages):
    for name in ("core", "mods"):
        plan = pages[name].evaluate("deck.plan()")
        doc = scenes[name]
        assert [[s["id"], s["steps"]] for s in doc["slides"]] == plan
        assert doc["size"] == {"width": W, "height": H, "unit": "px", "emu_per_px": 9525}
        for s in doc["slides"]:
            assert [t["step"] for t in s["timeline"]] == list(range(s["steps"] + 1))


def test_every_visible_component_is_captured_with_its_role(scenes, pages):
    for name in ("core", "mods"):
        doc, page = scenes[name], pages[name]
        assert len(doc["slides"]) >= 5, name
        for s in doc["slides"]:
            go(page, s["id"], s["steps"])
            seen = page.evaluate(VISIBLE_IDS, [s["id"], list(ROLE_OF)])
            by_id = {e["id"]: e for e in s["elements"]}
            for sel, ids in seen.items():
                role = ROLE_OF[sel]
                for eid in ids:
                    if eid:
                        assert eid in by_id, f"{s['id']}: visible {sel} #{eid} missing"
                        if role:
                            assert by_id[eid]["role"] == role, f"{s['id']} #{eid}"
                if role:
                    got = [e for e in s["elements"] if e["role"] == role and s["steps"] in e["visible_steps"]]
                    assert len(got) >= len(ids), f"{s['id']}: {len(ids)} visible {sel}, {len(got)} {role}"


def test_every_element_has_a_role_a_stable_id_and_a_z_order(scenes):
    for doc in scenes.values():
        assert doc["slides"] and all(s["elements"] for s in doc["slides"])
        for s in doc["slides"]:
            ids = [e["id"] for e in s["elements"]]
            assert len(ids) == len(set(ids)), s["id"]
            assert [e["z"] for e in s["elements"]] == list(range(len(ids)))
            for e in s["elements"]:
                assert e["role"] and e["visible_steps"]
                assert e["parent"] is None or e["parent"] in ids


def test_geometry_lies_within_the_slide(scenes):
    for doc in scenes.values():
        assert doc["slides"] and all(s["elements"] for s in doc["slides"])
        for s in doc["slides"]:
            for e in s["elements"]:
                if e["role"] == "orb":  # ambient orbs bleed off the slide by design
                    continue
                b = e["box"]
                assert b["w"] >= 0 and b["h"] >= 0
                assert b["x"] >= -1 and b["y"] >= -1 and b["x"] + b["w"] <= W + 1 and b["y"] + b["h"] <= H + 1, \
                    f"{s['id']} {e['id']} {b}"


def test_boxes_match_the_render_at_their_measured_step(scenes, pages):
    for name, sid, eid in (("core", "c-2", "c2-b"), ("core", "c-2", "c2-insight"), ("core", "c-3", "c3-c"),
                           ("mods", "m-2", "n-2b"), ("mods", "m-3", "m3-pop"), ("mods", "m-4", "t-2")):
        e = el(scenes[name], sid, eid)
        go(pages[name], sid, e["measured_at"])
        assert near(e["box"], screen_box(pages[name], f"#{eid}")), (eid, e["box"])


def test_an_element_hidden_at_the_final_step_is_measured_where_it_is_visible(scenes):
    e = el(scenes["core"], "c-3", "c3-n1")  # data-show-at=2 data-hide-at=3, last step 3
    assert e["visible_steps"] == [2] and e["measured_at"] == 2
    assert e["box"]["w"] > 0 and e["box"]["h"] > 0


# ---------- text ----------

DOM_TEXT = r"""id => (document.getElementById(id).textContent || '').replace(/\s+/g, ' ').trim()"""


def test_text_runs_match_the_dom_text(scenes, pages):
    for name in ("core", "mods"):
        doc, page = scenes[name], pages[name]
        checked = 0
        for s in doc["slides"]:
            parents = {e["parent"] for e in s["elements"] if not e["pseudo"]}
            for e in s["elements"]:
                if not e["text"] or e["pseudo"] or e["id"] in parents or "/" in e["id"]:
                    continue
                joined = "".join(r["text"] for r in e["text"]["runs"])
                assert joined == page.evaluate(DOM_TEXT, e["id"]), (s["id"], e["id"])
                checked += 1
        assert checked >= 10, name


def test_text_runs_carry_font_style_and_alignment(scenes):
    doc = scenes["core"]
    title = next(e for e in slide(doc, "c-1")["elements"] if e["role"] == "title")
    runs = title["text"]["runs"]
    assert [r["text"] for r in runs if r["italic"]] == ["any"]
    assert all(r["font"] == "Newsreader" and r["size"] > 30 for r in runs)
    kicker = next(e for e in slide(doc, "c-2")["elements"] if e["role"] == "kicker")
    assert kicker["text"]["runs"][0]["caps"] is True and kicker["text"]["runs"][0]["font"] == "Inter"
    assert kicker["text"]["runs"][0]["weight"] == 600
    assert title["text"]["align"] in {"left", "center", "right", "justify"}
    assert title["text"]["lines"] >= 1
    cite = next(r for e in slide(doc, "c-4")["elements"] if e["text"] for r in e["text"]["runs"] if r.get("href"))
    assert cite["href"] == "https://example.org/review"


# ---------- colour and effects ----------

def test_themed_colours_resolve_to_palette_role_names(scenes):
    doc = scenes["core"]
    assert doc["palette"]["paper"]["slots"] == ["lt1"] and doc["palette"]["accent"]["rgb"] == "86BC25"
    title = next(e for e in slide(doc, "c-2")["elements"] if e["role"] == "title")
    kicker = next(e for e in slide(doc, "c-2")["elements"] if e["role"] == "kicker")
    assert {r["colour"]["role"] for r in title["text"]["runs"]} == {"ink"}
    assert kicker["text"]["runs"][0]["colour"]["role"] == "accent-ink"
    assert slide(doc, "c-2")["background"]["role"] == "paper"
    assert el(doc, "c-3", "c3-a")["fill"]["role"] == "tile"
    assert el(doc, "c-3", "c3-e2")["stroke"]["role"] == "accent"
    assert el(doc, "c-3", "c3-e3")["stroke"]["role"] == "loss"
    key = el(doc, "c-3", "c3-c")["fill"]  # accent mixed into tile: no single role, so a raw colour
    assert key["role"] is None and re.fullmatch(r"[0-9A-F]{6}", key["rgb"])


def test_effects_are_tagged_with_the_styles_declared_band(scenes):
    doc = scenes["core"]
    fx = {f["kind"]: f for f in el(doc, "c-2", "c2-insight")["effects"]}
    assert fx["shadow"]["token"] == "sys.shadow.overlay" and fx["shadow"]["band"] == "approximated"
    assert fx["backdrop-blur"]["token"] == "sys.material.blur" and fx["backdrop-blur"]["band"] == "lost"
    orbs = [e for e in slide(doc, "c-1")["elements"] if e["role"] == "orb"]
    assert len(orbs) == 17
    far = next(e for e in orbs if "orb--far" in e["classes"])
    kinds = {f["kind"]: f for f in far["effects"]}
    assert kinds["blur"]["token"] == "sys.ambient.far.blur" and kinds["blur"]["band"] == "approximated"
    assert kinds["opacity"]["token"] == "sys.ambient.far.opacity" and kinds["opacity"]["band"] == "native"
    tile_fx = {f["kind"]: f for f in el(doc, "c-3", "c3-a")["effects"]}
    assert tile_fx["svg-filter"]["value"] == "#lift" and tile_fx["svg-filter"]["band"] == "approximated"


# ---------- SVG primitives ----------

ABSOLUTE = re.compile(r"^M(?: -?\d+(?:\.\d+)?){2}(?: (?:[MLC](?: -?\d+(?:\.\d+)?)+|Z))*$")


def _paths(doc):
    for s in doc["slides"]:
        for e in s["elements"]:
            for p in e["svg"] or []:
                if p["type"] == "path":
                    yield s["id"], e["id"], p


def test_svg_paths_are_absolute(scenes):
    found = list(p for doc in scenes.values() for p in _paths(doc))
    assert len(found) >= 8
    for sid, eid, p in found:
        assert ABSOLUTE.match(p["d"]), (sid, eid, p["d"])


def test_a_tiles_rect_matches_its_screen_box(scenes, pages):
    for name, sid, step, tid in (("core", "c-3", 3, "c3-a"), ("shapes", "g-1", 0, "g-tile"),
                                 ("mods", "m-2", 3, "p-a")):  # plain, group-transformed, camera-scaled
        e = el(scenes[name], sid, tid)
        rect = next(p for p in e["svg"] if p["type"] == "rect")
        go(pages[name], sid, step)
        assert near(rect, screen_box(pages[name], f"#{tid} rect")), (tid, rect)
        assert rect["rx"] > 0


def test_a_transformed_relative_arc_path_lands_on_its_screen_box(scenes, pages):
    e = el(scenes["shapes"], "g-1", "g-free")
    assert e["role"] == "shape"
    p = next(p for p in e["svg"] if p["type"] == "path")
    assert ABSOLUTE.match(p["d"]) and " C " in p["d"]
    go(pages["shapes"], "g-1", 0)
    assert near(p["box"], screen_box(pages["shapes"], "#g-free")), p["box"]


def test_svg_text_is_a_positioned_text_primitive(scenes, pages):
    e = el(scenes["core"], "c-3", "c3-b")
    t = next(p for p in e["svg"] if p["type"] == "text")
    assert "".join(r["text"] for r in t["runs"]) == "Checker"
    assert t["runs"][0]["colour"]["role"] == "ink"
    go(pages["core"], "c-3", 3)
    assert near(t["box"], screen_box(pages["core"], "#c3-b text"))


def test_normalise_path_makes_every_command_absolute():
    segs = scene_mod.normalise_path("m 10 20 l 5 5 h 10 v -5 q 5 5 10 0 t 10 0 c 1 1 2 2 3 3 s 4 4 5 5 z")
    assert [s[0] for s in segs] == ["M", "L", "L", "L", "C", "C", "C", "C", "Z"]
    assert segs[0] == ("M", 10, 20) and segs[1] == ("L", 15, 25) and segs[2] == ("L", 25, 25)
    assert segs[3] == ("L", 25, 20)
    assert segs[4][-2:] == (35, 20) and segs[5][-2:] == (45, 20)
    assert segs[6] == ("C", 46, 21, 47, 22, 48, 23)
    assert segs[7][1:3] == (49, 24) and segs[7][-2:] == (53, 28)  # s reflects the previous control point
    arc = scene_mod.normalise_path("M 0 0 A 10 10 0 0 1 20 0")  # semicircle about (10, 0), sweeping up
    assert all(s[0] in "MC" for s in arc) and arc[-1][-2:] == pytest.approx((20, 0), abs=1e-6)
    ends = [s[-2:] for s in arc[1:]]
    assert len(ends) >= 2 and all(((x - 10) ** 2 + y ** 2) ** .5 == pytest.approx(10, abs=1e-6) for x, y in ends)
    assert min(y for _, y in ends) == pytest.approx(-10, abs=1e-6)


# ---------- timeline ----------

def test_a_show_at_element_enters_at_its_step(scenes):
    doc = scenes["core"]
    step0 = next(t for t in slide(doc, "c-2")["timeline"] if t["step"] == 0)
    assert "c2-lede" in step0["visible"] and "c2-b" not in step0["visible"]
    assert deltas(doc, "c-2", 1, "c2-b") == []
    (d,) = deltas(doc, "c-2", 2, "c2-b")
    assert d["kind"] == "enter" and d["effect"] in {"appear", "fade_in"}
    (ins,) = deltas(doc, "c-2", 3, "c2-insight")
    assert ins["kind"] == "enter" and ins["effect"] in {"appear", "fade_in"}


def test_children_enter_with_their_parent_not_separately(scenes):
    doc = scenes["mods"]
    entered = {d["el"] for d in deltas(doc, "m-4", 2) if d["kind"] == "enter"}
    assert "t-2" in entered
    kids = {e["id"] for e in slide(doc, "m-4")["elements"] if e["parent"] == "t-2"}
    assert kids and not (kids & entered)


def test_overlays_and_tiles_exit_at_their_exit_step(scenes):
    mods, core = scenes["mods"], scenes["core"]
    (pop,) = [d for d in deltas(mods, "m-3", 2, "m3-pop") if d["kind"] == "exit"]
    assert pop["effect"] in {"disappear", "fade_out"}
    assert any(d["kind"] == "exit" and d["effect"] in {"disappear", "fade_out"} for d in deltas(mods, "m-2", 2, "n-1"))
    assert any(d["kind"] == "exit" for d in deltas(core, "c-3", 3, "c3-n1"))
    assert not any(d["kind"] == "exit" for d in deltas(core, "c-3", 2, "c3-n1"))


def test_a_scene_camera_move_is_flagged_unsupported_for_morph(scenes):
    doc = scenes["mods"]
    cams = [d for d in deltas(doc, "m-2", 2) if d["property"] == "camera"]
    assert len(cams) == 1
    assert cams[0]["effect"] == "unsupported" and cams[0]["fallback"] == "morph" and cams[0]["reason"]
    parts = {e["id"] for e in slide(doc, "m-2")["elements"] if e["scene_part"]}
    assert not [d for d in deltas(doc, "m-2", 2) if d["el"] in parts and d["property"] in {"position", "scale"}]
    assert not [d for d in deltas(doc, "m-2", 1) if d["property"] == "camera"]


def test_a_step_list_marker_changes_fill_at_its_step(scenes, pages):
    doc = scenes["core"]
    (d,) = [d for d in deltas(doc, "c-3", 1, "c3-s1::before") if d["property"] == "fill"]
    assert d["effect"] == "fill_colour" and d["params"]["rgb"] == doc["palette"]["accent"]["rgb"]
    marker = el(doc, "c-3", "c3-s1::before")
    assert marker["role"] == "marker" and marker["pseudo"] == "before" and marker["parent"] == "c3-s1"
    assert "".join(r["text"] for r in marker["text"]["runs"]) == "1"


def test_supported_deltas_are_valid_pb022_inputs_and_the_rest_say_why(scenes):
    n = 0
    for doc in scenes.values():
        for s in doc["slides"]:
            for t in s["timeline"]:
                for d in t["deltas"]:
                    n += 1
                    if d["effect"] == "unsupported":
                        assert d["reason"] and d["fallback"] in {"morph", "none"}
                    else:
                        assert d["effect"] in anim.EFFECTS
                        assert set(d["params"]) <= anim._PARAMS[d["effect"]] | {"duration_ms"}, d
                        assert isinstance(d["params"].get("duration_ms", 1), int) and d["params"].get("duration_ms", 1) > 0
                        anim._check_params(d["effect"], d["params"])
    assert n >= 20


# ---------- notes ----------

def test_reader_notes_are_captured_with_target_and_source(scenes):
    notes = slide(scenes["core"], "c-2")["notes"]
    assert [n["target"] for n in notes] == ["c2-lede", "c2-b"]
    assert notes[0]["heading"] == "Settling in" and notes[0]["text"] == ["Entry is a rise and fade, staggered."]
    assert notes[0]["sources"] == [{"text": "Entry source", "href": "https://example.org/entry"}]
    assert "Settling in" in slide(scenes["core"], "c-2")["notes_text"]
    scene_note = slide(scenes["mods"], "m-3")["notes"][0]
    assert scene_note["target"] == "p-b"  # a scene part, resolved outside the slide
    assert slide(scenes["core"], "c-5")["notes"] == []


# ---------- determinism, CLI, refusals ----------

def test_two_runs_give_identical_json(browser, decks, scenes):
    again = scene_mod.extract(decks["mods"], browser=browser)
    assert len(again["slides"]) == 5 and sum(len(s["elements"]) for s in again["slides"]) > 50
    assert json.dumps(again, sort_keys=True) == json.dumps(scenes["mods"], sort_keys=True)


def test_cli_writes_one_valid_scene_json_per_deck(decks, tmp_path):
    out = tmp_path / "out.scene.json"
    assert scene_mod.main([str(decks["shapes"]), "-o", str(out)]) == 0
    doc = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads(scene_mod.SCHEMA_PATH.read_text(encoding="utf-8"))
    assert scene_mod.validate(doc, schema) == [] and [s["id"] for s in doc["slides"]] == ["g-1"]


def test_a_page_that_is_not_a_skill_deck_is_refused(browser, tmp_path, capsys):
    plain = tmp_path / "plain.html"
    plain.write_text("<!doctype html><title>x</title><p>Hello</p>", encoding="utf-8")
    with pytest.raises(scene_mod.SceneError, match="not a skill deck"):
        scene_mod.extract(plain, browser=browser)
    assert scene_mod.main([str(plain), "-o", str(tmp_path / "x.json")]) == 1
    assert "not a skill deck" in capsys.readouterr().err
    assert not (tmp_path / "x.json").exists()


def test_a_deck_missing_a_marker_is_refused_naming_it(browser, decks, tmp_path):
    broken = tmp_path / "broken.html"
    broken.write_text(decks["shapes"].read_text(encoding="utf-8").replace("/* ENGINE:END */", ""), encoding="utf-8")
    with pytest.raises(scene_mod.SceneError, match=r"ENGINE:END"):
        scene_mod.extract(broken, browser=browser)
