"""Spec: PB-024

PPTX emitter and checks: `pptx/scripts/emit.py` turns a PB-023 scene (or a deck, measured first)
into an editable .pptx from a generated seed template (named layouts with placeholders in one
master, theme colours and fonts from the tokens), with named native shapes, speaker notes, steps as
native animations (duplicated slides + Morph only for camera moves) and a sidecar report of
everything approximated or dropped. `pptx/scripts/check.py` gives the deterministic `pptx`
criteria verdicts in the eval schema, validates the package and re-flows slides into a foreign
template.

Decks: the core component fixture and the module fixture (scene, narration, pop-over, tile row,
camera move), assembled with `scripts/assemble.py new`; the worked example deck when present.

Coverage: happy (opens, slide count, named layouts used, text in placeholders, theme = tokens,
scheme colour refs, named round-rect tiles, arrowed edges, cubic curves, notes with sources, click
order = HTML steps, Morph pair for the camera move, effect bands, report, verdicts pass, package
and schema valid, re-flow inherits the foreign theme, CLI) · edge (paragraph-level builds in a
body placeholder, a stepped table, exits, a step softening the body, the Morph slide's clicks) ·
negative (check fails text flattened to a picture, literal RGB, missing animations, missing notes,
a dropped Morph; emit refuses an invalid scene).
"""

from __future__ import annotations

import copy
import io
import json
import re
import shutil
import subprocess
import zipfile

import helper_engine as he
import helper_pptx as hp
import pytest
from lxml import etree
from playwright.sync_api import sync_playwright
from pptx import Presentation

emit = hp.load_script("emit")
check = hp.load_script("check")
scene_mod = hp.load_script("scene")
asm = he.load_assemble()

SKILL = hp.SCRIPTS.parents[1]
EVALS = SKILL / "evals"
OUT = hp.ARTIFACTS / "pb-024"
EXAMPLE = SKILL / "examples" / "hf-incident" / "deck.html"

NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "p159": "http://schemas.microsoft.com/office/powerpoint/2015/09/main",
}
A = "{%s}" % NS["a"]
P = "{%s}" % NS["p"]
SLOT_ALIAS = {"dk1": "tx1", "lt1": "bg1", "dk2": "tx2", "lt2": "bg2"}


def _load(path, name):
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclasses resolve their module by name
    spec.loader.exec_module(mod)
    return mod


tokens = _load(SKILL / "scripts" / "tokens.py", "pb_tokens_for_emit")
criteria = _load(EVALS / "criteria.py", "pb_criteria_for_emit")
aggregate = _load(EVALS / "aggregate.py", "pb_aggregate_for_emit")


# ---------- fixtures ----------

@pytest.fixture(scope="module")
def browser():
    """System Chrome, once per module (no conftest: other suites share this folder)."""
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        yield b
        b.close()


@pytest.fixture(scope="module")
def built(browser, tmp_path_factory):
    """Assemble both fixture decks, measure them and emit each to a .pptx (once per module)."""
    d = tmp_path_factory.mktemp("emit")
    decks = {
        "core": asm.new(d / "core.html", "Core Fixture", "Emit", slides=he.COMPONENT_SLIDES),
        "modules": asm.new(d / "modules.html", "Module Fixture", "Emit", slides=he.MODULE_SLIDES),
    }
    out = {}
    for k, deck in decks.items():
        scene = scene_mod.extract(deck, browser=browser)
        path = emit.emit(scene, d / f"{k}.pptx")
        report = json.loads((d / f"{k}.pptx-report.json").read_text(encoding="utf-8"))
        out[k] = {"deck": deck, "scene": scene, "path": path, "prs": Presentation(path), "report": report}
    OUT.mkdir(parents=True, exist_ok=True)
    for k, v in out.items():
        shutil.copy(v["path"], OUT / f"{k}.pptx")
        shutil.copy(d / f"{k}.pptx-report.json", OUT / f"{k}.pptx-report.json")
    return out


@pytest.fixture(scope="module")
def library():
    return criteria.load_library(EVALS)


@pytest.fixture(scope="module")
def profile(library):
    return criteria.load_profile(EVALS / "profiles" / "editorial-talk.json", library)


# ---------- scene-side expectations (independent of the emitter) ----------

def sslide(scene, sid):
    return next(s for s in scene["slides"] if s["id"] == sid)


def sel(scene, sid, eid):
    return next(e for e in sslide(scene, sid)["elements"] if e["id"] == eid)


def run_text(runs):
    return "".join(r["text"] for r in runs)


def camera_steps(sl):
    return [t["step"] for t in sl["timeline"] if any(d["property"] == "camera" for d in t["deltas"])]


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


# ---------- pptx-side readers ----------

def pslides_for(prs, sid):
    """PPTX slides emitted for HTML slide `sid` (the slide name carries the HTML id)."""
    return [s for s in prs.slides if s._element.find("p:cSld", NS).get("name", "").split(" ")[0] == sid]


def shape_named(slide, name):
    """Find a shape (any depth) whose name is `name` or `!!name`."""
    for el in slide._element.iter(P + "cNvPr"):
        if el.get("name") in (name, "!!" + name):
            return el.getparent().getparent()
    return None


def shape_text(sp):
    return "\n".join("".join(t.text or "" for t in p.iter(A + "t")) for p in sp.iter(A + "p"))


def placeholders(slide):
    return {(ph.placeholder_format.type, ph.placeholder_format.idx): ph for ph in slide.placeholders}


def clicks(slide):
    return hp.click_groups(slide._element) if slide._element.find("p:timing", NS) is not None else []


def target_texts(slide, effect):
    """Texts an effect targets: the whole shape's text, or only its paragraph range."""
    tgt = effect["ctn"].find(".//p:spTgt", NS)
    sp = next(e.getparent().getparent() for e in slide._element.iter(P + "cNvPr") if e.get("id") == tgt.get("spid"))
    rng = tgt.find("p:txEl/p:pRg", NS)
    paras = [norm("".join(t.text or "" for t in p.iter(A + "t"))) for p in sp.iter(A + "p")]
    name = sp.find(".//p:cNvPr", NS).get("name").removeprefix("!!")
    if rng is not None:
        return name, paras[int(rng.get("st")): int(rng.get("end")) + 1]
    return name, paras


def theme_xml(prs):
    from pptx.opc.constants import RELATIONSHIP_TYPE as RT

    return etree.fromstring(prs.slide_master.part.part_related_by(RT.THEME).blob)


def verdicts_by(vs):
    out = {}
    for v in vs:
        out.setdefault(v["criterion"], {})[v["unit"]] = v
    return out


# ---------- structure: file, slides, layouts, placeholders ----------

def test_file_opens_with_one_slide_per_html_slide_plus_one_per_camera_move(built):
    for k, b in built.items():
        prs = Presentation(b["path"])
        want = sum(1 + len(camera_steps(s)) for s in b["scene"]["slides"])
        assert len(prs.slides) == want, k
        for s in b["scene"]["slides"]:
            assert len(pslides_for(prs, s["id"])) == 1 + len(camera_steps(s)), s["id"]
    assert len(built["core"]["prs"].slides) == 8
    assert len(built["modules"]["prs"].slides) == 6


def test_slides_use_named_layouts_from_one_master(built):
    want = {"Title / lead", "Standard", "Split", "Three-column scene", "Tile row", "End"}
    for k, b in built.items():
        prs = b["prs"]
        assert len(prs.slide_masters) == 1
        names = {l.name for l in prs.slide_layouts}
        assert want <= names, names
        for l in prs.slide_layouts:
            assert any(True for _ in l.placeholders), f"layout {l.name} has no placeholders"
        for s in prs.slides:
            assert s.slide_layout.name in want, s.slide_layout.name
    core, mods = built["core"]["prs"], built["modules"]["prs"]
    layout = lambda prs, sid: pslides_for(prs, sid)[0].slide_layout.name  # noqa: E731
    assert layout(core, "c-1") == "Title / lead"
    assert layout(core, "c-8") == "End"
    assert layout(core, "c-2") == "Standard"
    assert layout(core, "c-3") == "Split"
    assert layout(mods, "m-2") == "Three-column scene"
    assert layout(mods, "m-4") == "Tile row"


def test_titles_kickers_and_body_text_sit_in_placeholders(built):
    for k, b in built.items():
        for s in b["scene"]["slides"]:
            titles = [e for e in s["elements"] if e["role"] == "title"]
            for ps in pslides_for(b["prs"], s["id"]):
                assert ps.shapes.title is not None, s["id"]
                assert norm(ps.shapes.title.text_frame.text) == norm(run_text(titles[0]["text"]["runs"]))
                for sh in ps.shapes:
                    if not sh.is_placeholder and sh.has_text_frame:
                        assert norm(sh.text_frame.text) != norm(run_text(titles[0]["text"]["runs"]))
    c2 = pslides_for(built["core"]["prs"], "c-2")[0]
    body = [ph for ph in c2.placeholders if ph.placeholder_format.type in (2, 7)]  # BODY, OBJECT
    texts = [norm(ph.text_frame.text) for ph in body]
    assert any("02 · Method" == t for t in texts), "kicker in a body-type placeholder"
    main = next(ph for ph in body if "Content settles in" in ph.text_frame.text)
    paras = [norm(p.text) for p in main.text_frame.paragraphs]
    assert paras[1].startswith("A point appears") and paras[2].startswith("Earlier points stay")
    c1 = pslides_for(built["core"]["prs"], "c-1")[0]
    sub = [ph for ph in c1.placeholders if ph.placeholder_format.type == 4]  # SUBTITLE
    assert sub and sub[0].text_frame.text.startswith("One component set")
    m4 = pslides_for(built["modules"]["prs"], "m-4")[0]
    tiles = sorted((ph for ph in m4.placeholders if ph.placeholder_format.idx in (1, 2, 3)),
                   key=lambda ph: ph.left)
    assert [t.text_frame.paragraphs[0].text for t in tiles] == ["First", "Second", "Third"]


def test_unused_layout_placeholders_are_removed_from_slides(built):
    """An empty placeholder would show 'Click to add text' to the colleague."""
    for b in built.values():
        for s in b["prs"].slides:
            assert len(s.placeholders) >= 1, "every slide keeps at least its title placeholder"
            for ph in s.placeholders:
                if ph.has_text_frame:
                    assert ph.text_frame.text.strip(), (s._element.find("p:cSld", NS).get("name"), ph.name)


# ---------- theme ----------

def test_theme_colour_and_font_schemes_equal_the_tokens(built):
    for b in built.values():
        d = b["scene"]["deck"]
        theme = tokens.load(d["palette"], d["style"])
        want_clr = etree.fromstring(tokens.clr_scheme(theme))
        want_font = etree.fromstring(tokens.font_scheme(theme))
        got = theme_xml(b["prs"])
        clr = got.find(".//a:clrScheme", NS)
        slots = lambda e: {c.tag.split("}")[1]: c[0].get("val") for c in e}  # noqa: E731
        assert slots(clr) == slots(want_clr)
        font = got.find(".//a:fontScheme", NS)
        for slot in ("majorFont", "minorFont"):
            assert font.find(f"a:{slot}/a:latin", NS).get("typeface") == \
                want_font.find(f"a:{slot}/a:latin", NS).get("typeface")


def test_palette_roles_become_scheme_colour_references(built):
    b = built["core"]
    palette = b["scene"]["palette"]
    slot = lambda role: SLOT_ALIAS.get(palette[role]["slots"][0], palette[role]["slots"][0])  # noqa: E731
    c3 = pslides_for(b["prs"], "c-3")[0]
    tile = shape_named(c3, "c3-a")
    assert tile.find("p:spPr/a:solidFill/a:schemeClr", NS).get("val") == slot("tile")
    edge = shape_named(c3, "c3-e2")
    assert edge.find("p:spPr/a:ln/a:solidFill/a:schemeClr", NS).get("val") == slot("accent")
    title = pslides_for(b["prs"], "c-2")[0].shapes.title._element
    assert {c.get("val") for c in title.iter(A + "schemeClr")} == {slot("ink")}
    theme_vals = {c.get("val") for c in theme_xml(b["prs"]).find(".//a:clrScheme", NS).iter(A + "srgbClr")}
    for k, bb in built.items():
        for s in bb["prs"].slides:
            lits = {c.get("val") for c in s._element.iter(A + "srgbClr")}
            assert not lits & theme_vals, (k, lits & theme_vals)


def test_runs_use_theme_font_references(built):
    for b in built.values():
        fonts = b["scene"]["fonts"]
        for s in b["prs"].slides:
            for latin in s._element.iter(A + "latin"):
                assert latin.get("typeface") not in (fonts["major"], fonts["minor"]), latin.get("typeface")
    title = pslides_for(built["core"]["prs"], "c-2")[0].shapes.title._element
    assert {l.get("typeface") for l in title.iter(A + "latin")} <= {"+mj-lt"}


# ---------- diagrams ----------

def test_diagram_tiles_are_named_round_rects_with_their_text(built):
    scene = built["core"]["scene"]
    c3 = pslides_for(built["core"]["prs"], "c-3")[0]
    for eid in ("c3-a", "c3-b", "c3-c"):
        sp = shape_named(c3, eid)
        assert sp is not None, eid
        assert sp.find("p:spPr/a:prstGeom", NS).get("prst") == "roundRect"
        words = [run_text(p["runs"]) for p in sel(scene, "c-3", eid)["svg"] if p["type"] == "text"]
        assert [norm(t) for t in shape_text(sp).split("\n") if t.strip()] == words


def test_edges_carry_arrowheads_and_curves_stay_cubic(built):
    c3 = pslides_for(built["core"]["prs"], "c-3")[0]
    for eid in ("c3-e1", "c3-e2", "c3-e3"):
        sp = shape_named(c3, eid)
        assert sp is not None, eid
        tail = sp.find("p:spPr/a:ln/a:tailEnd", NS)
        assert tail is not None and tail.get("type") not in (None, "none"), eid
    assert shape_named(c3, "c3-e2").find(".//a:custGeom//a:cubicBezTo", NS) is not None
    for eid in ("c-3/label-1", "c-3/tag-1"):
        assert shape_named(c3, eid) is not None, eid


# ---------- notes ----------

def test_speaker_notes_carry_the_reader_note_and_its_sources(built):
    for b in built.values():
        for s in b["scene"]["slides"]:
            for ps in pslides_for(b["prs"], s["id"]):
                text = norm(ps.notes_slide.notes_text_frame.text) if ps.has_notes_slide else ""
                assert text == norm(s["notes_text"]), s["id"]
    ps = pslides_for(built["core"]["prs"], "c-1")[0]
    rels = [r for r in ps.notes_slide.part.rels.values() if r.is_external]
    assert "https://example.org/layer" in {r.target_ref for r in rels}


# ---------- steps → animations ----------

def test_each_html_step_is_one_click_in_order(built):
    for k, b in built.items():
        for s in b["scene"]["slides"]:
            cams = camera_steps(s)
            bounds = [0, *cams, s["steps"] + 1]
            emitted = pslides_for(b["prs"], s["id"])
            assert len(emitted) == len(bounds) - 1, s["id"]
            for ps, (lo, hi) in zip(emitted, zip(bounds, bounds[1:])):
                if ps._element.find("p:timing", NS) is not None:
                    assert hp.structural_errors(_without_mc(ps._element)) == [], s["id"]
                assert len(clicks(ps)) == hi - lo - 1, (s["id"], lo, hi)


def test_an_element_shown_at_step_two_enters_on_click_two(built):
    core = built["core"]["prs"]
    c3 = pslides_for(core, "c-3")[0]
    key = shape_named(c3, "c3-c").find(".//p:cNvPr", NS).get("id")
    by_click = [{e["spid"]: e for e in g} for g in clicks(c3)]
    assert key not in by_click[0] and by_click[1][key]["presetClass"] == "entr"
    n1 = shape_named(c3, "c3-n1").find(".//p:cNvPr", NS).get("id")
    assert by_click[1][n1]["presetClass"] == "entr" and by_click[2][n1]["presetClass"] == "exit"


def test_body_points_build_by_paragraph_inside_the_placeholder(built):
    c2 = pslides_for(built["core"]["prs"], "c-2")[0]
    groups = clicks(c2)
    assert len(groups) == 3
    for n, want in ((0, "A point appears"), (1, "Earlier points stay")):
        entr = [e for e in groups[n] if e["presetClass"] == "entr"]
        assert len(entr) == 1
        name, texts = target_texts(c2, entr[0])
        assert len(texts) == 1 and texts[0].startswith(want), texts
        assert entr[0]["ctn"].find(".//p:spTgt/p:txEl/p:pRg", NS) is not None
    third = {target_texts(c2, e)[0]: e["presetClass"] for e in groups[2]}
    assert third.get("c2-insight") == "entr"
    assert "emph" in third.values(), "the body softens (transparency) under the Insight"
    bld = c2._element.findall("p:timing/p:bldLst/p:bldP[@build='p']", NS)
    assert bld, "paragraph builds are declared as build='p'"


def test_a_stepped_table_reveals_its_rows_on_their_clicks(built):
    c5 = pslides_for(built["core"]["prs"], "c-5")[0]
    tables = [sh for sh in c5.shapes if sh.has_table]
    text = " ".join(c.text for t in tables for r in t.table.rows for c in r.cells)
    for w in ("Independent checker", "Scoped credentials", "Alert ownership"):
        assert w in text
    groups = clicks(c5)
    assert len(groups) == 2
    for g, want in zip(groups, ("Scoped credentials", "Alert ownership")):
        ids = {e["spid"] for e in g}
        shown = [t for t in tables if str(t.shape_id) in ids]
        assert shown and all(e["presetClass"] == "entr" for e in g)
        assert any(want in c.text for t in shown for r in t.table.rows for c in r.cells)


def _without_mc(sld):
    """A copy of a slide with mc:AlternateContent resolved to its Fallback (as a non-Morph reader)."""
    sld = copy.deepcopy(sld)
    for ac in sld.findall("mc:AlternateContent", NS):
        fb = ac.find("mc:Fallback", NS)
        for child in list(fb if fb is not None else []):
            ac.addprevious(child)
        sld.remove(ac)
    return sld


def test_camera_move_becomes_a_morph_pair_with_bang_names(built):
    prs, scene = built["modules"]["prs"], built["modules"]["scene"]
    a, bslide = pslides_for(prs, "m-2")
    assert a._element.find("mc:AlternateContent", NS) is None
    morph = bslide._element.find("mc:AlternateContent/mc:Choice/p:transition/p159:morph", NS)
    assert morph is not None
    assert bslide._element.find("mc:AlternateContent/mc:Fallback/p:transition", NS) is not None
    names = lambda s: {e.get("name") for e in s._element.iter(P + "cNvPr") if e.get("id") != "1"}  # noqa: E731
    na, nb = names(a), names(bslide)
    assert all(n.startswith("!!") for n in na | nb)
    assert "!!p-a" in na & nb and "!!m2-title" in na & nb
    box = lambda s: shape_named(s, "p-a").find("p:spPr/a:xfrm/a:ext", NS).get("cx")  # noqa: E731
    assert box(a) != box(bslide), "the camera zoom changes the shared tile's size"
    frames = {f["step"]: f["box"]["w"] for f in sel(scene, "m-2", "p-a")["frames"]}
    assert frames[1] < frames[2]
    for s in prs.slides:
        if s is not bslide:
            assert s._element.find("mc:AlternateContent", NS) is None
            assert s._element.find("p:transition", NS) is None
    for s in built["core"]["prs"].slides:
        assert s._element.find("mc:AlternateContent", NS) is None


# ---------- effects and report ----------

def test_style_effects_follow_their_bands(built):
    core = built["core"]
    c1 = pslides_for(core["prs"], "c-1")[0]
    orb = shape_named(c1, "c-1/orb-1")
    assert orb.find("p:spPr/a:prstGeom", NS).get("prst") == "ellipse"
    assert orb.find("p:spPr/a:effectLst/a:softEdge", NS) is not None, "blur → soft edge (approximated)"
    assert orb.find(".//a:gradFill//a:alpha", NS) is not None, "opacity → alpha (native)"
    c2 = pslides_for(core["prs"], "c-2")[0]
    card = shape_named(c2, "c2-insight")
    assert card.find("p:spPr/a:prstGeom", NS).get("prst") == "roundRect"
    alpha = card.find("p:spPr/a:solidFill/a:schemeClr/a:alpha", NS)
    assert alpha is not None and int(alpha.get("val")) == 55000, "frost → translucent fill"
    assert card.find("p:spPr/a:effectLst/a:outerShdw", NS) is not None, "shadow → outer shadow"
    assert norm(shape_text(card)).startswith("Insight An Insight card")
    for b in built.values():
        for s in b["prs"].slides:
            assert s._element.find(".//a:blur", NS) is None, "backdrop blur is lost, never faked"


def test_report_lists_every_dropped_or_approximated_item(built):
    for k, b in built.items():
        rep = b["report"]
        assert rep["schema"] == "pb-pptx-report/1"
        items = rep["items"]
        keyed = {(i["slide"], i["el"], i["what"]): i for i in items}
        for s in b["scene"]["slides"]:
            for e in s["elements"]:
                for fx in e["effects"]:
                    hit = keyed.get((s["id"], e["id"], fx["kind"]))
                    assert hit is not None, (k, s["id"], e["id"], fx["kind"])
                    want = {"native": "native", "approximated": "approximated"}.get(fx["band"], "lost")
                    assert hit["result"] == want, hit
            for t in s["timeline"]:
                for d in t["deltas"]:
                    if d["effect"] == "unsupported":
                        hit = keyed.get((s["id"], d["el"], f"step {t['step']}: {d['property']}"))
                        assert hit is not None, (k, s["id"], d)
                        assert hit["result"] == ("morph" if d["property"] == "camera" else "dropped")
    lost = {(i["el"], i["what"]) for i in built["core"]["report"]["items"] if i["result"] == "lost"}
    assert ("c2-insight", "backdrop-blur") in lost
    dropped = [i for i in built["core"]["report"]["items"] if i["result"] == "dropped"]
    assert any(i["el"] == "c3-s1" and "text-colour" in i["what"] for i in dropped)


# ---------- check.py: verdicts, negatives, package, re-flow ----------

def _pptx_d(library):
    return sorted(c for c, x in library.items() if x["target"] == "pptx" and x["evidence"] == "D")


def test_check_covers_every_deterministic_pptx_criterion_and_passes_good_output(built, library, profile):
    want = _pptx_d(library)
    assert want, "library has D pptx criteria"
    assert set(check.CRITERIA) == set(want)
    for k, b in built.items():
        vs = check.verdicts(b["path"], scene=b["scene"], report=b["report"])
        for v in vs:
            aggregate.validate_verdict(v, library, profile)
        got = verdicts_by(vs)
        assert set(got) == set(want), k
        for cid, units in got.items():
            scope = library[cid]["scope"]
            if scope == "deck":
                assert set(units) == {"deck"}
            else:
                assert set(units) == {s["id"] for s in b["scene"]["slides"]}, cid
            bad = {u: v["evidence"] for u, v in units.items() if v["result"] != "pass"}
            assert not bad, (k, cid, bad)


def _mutate(src, dst, fn):
    """Copy a .pptx, letting `fn(prs)` break it, and save."""
    prs = Presentation(src)
    fn(prs)
    prs.save(dst)
    return dst


def _flatten_body_to_picture(prs):
    from PIL import Image

    s = pslides_for(prs, "c-2")[0]
    for ph in list(s.placeholders):
        if "Content settles in" in ph.text_frame.text:
            left, top, w, h = ph.left, ph.top, ph.width, ph.height
            ph._element.getparent().remove(ph._element)
            buf = io.BytesIO()
            Image.new("RGB", (40, 20), "white").save(buf, "PNG")
            buf.seek(0)
            s.shapes.add_picture(buf, left, top, w, h)


def _literal_rgb(prs):
    s = pslides_for(prs, "c-3")[0]
    for c in list(s._element.iter(A + "schemeClr")):
        lit = etree.Element(A + "srgbClr", val="2B2A27")
        for child in c:
            lit.append(child)
        c.getparent().replace(c, lit)


def _drop_timing(prs):
    s = pslides_for(prs, "c-3")[0]
    for t in s._element.findall("p:timing", NS):
        s._element.remove(t)


def _drop_notes(prs):
    s = pslides_for(prs, "c-1")[0]
    s.notes_slide.notes_text_frame.text = ""


@pytest.mark.parametrize("breaker,cid,unit", [
    (_flatten_body_to_picture, "PX-01", "c-2"),
    (_literal_rgb, "PX-03", "deck"),
    (_drop_timing, "PX-04", "c-3"),
    (_drop_notes, "PX-09", "c-1"),
])
def test_check_fails_deliberately_broken_output(built, library, profile, tmp_path, breaker, cid, unit):
    b = built["core"]
    bad = _mutate(b["path"], tmp_path / "bad.pptx", breaker)
    vs = verdicts_by(check.verdicts(bad, scene=b["scene"], report=b["report"]))
    v = vs[cid][unit]
    aggregate.validate_verdict(v, library, profile)
    assert v["result"] == "fail", v
    assert v["flaws"] and v["evidence"]
    others = [u for u, x in vs[cid].items() if x["result"] == "fail" and u != unit]
    assert not others, f"only the broken unit fails: {others}"


def test_check_fails_a_camera_move_without_its_morph(built, tmp_path):
    b = built["modules"]

    def unmorph(prs):
        s = pslides_for(prs, "m-2")[1]
        for ac in s._element.findall("mc:AlternateContent", NS):
            s._element.remove(ac)

    bad = _mutate(b["path"], tmp_path / "nomorph.pptx", unmorph)
    v = verdicts_by(check.verdicts(bad, scene=b["scene"], report=b["report"]))["PX-04"]["m-2"]
    assert v["result"] == "fail", v


def test_package_validates_structurally_and_against_the_schema(built, tmp_path):
    for b in built.values():
        assert check.validate_package(b["path"]) == []
    broken = tmp_path / "broken.pptx"
    with zipfile.ZipFile(built["core"]["path"]) as zin, zipfile.ZipFile(broken, "w") as zout:
        for item in zin.infolist():
            if item.filename != "ppt/slides/slide2.xml":
                zout.writestr(item, zin.read(item.filename))
    assert check.validate_package(broken), "a missing slide part is reported"
    xsd = hp.find_pml_xsd()
    if xsd is None:
        pytest.skip("no transitional pml.xsd found (set PB_OOXML_SCHEMAS)")
    schema = etree.XMLSchema(etree.parse(str(xsd)))
    for k, b in built.items():
        prs = b["prs"]
        parts = [s._element for s in prs.slides] + [l._element for l in prs.slide_layouts]
        parts.append(prs.slide_master._element)
        for el in parts:
            el = _without_mc(el) if etree.QName(el).localname == "sld" else el
            assert schema.validate(el), (k, str(schema.error_log)[:800])


def test_reflow_into_a_foreign_template_inherits_its_theme(built, tmp_path):
    b = built["core"]
    out = check.reflow(b["path"], tmp_path / "reflowed.pptx")
    prs = Presentation(out)
    foreign = Presentation()
    assert len(prs.slides) == len(b["prs"].slides)
    assert (prs.slide_width, prs.slide_height) == (foreign.slide_width, foreign.slide_height)
    foreign_layouts = {l.name for l in foreign.slide_layouts}
    theme = theme_xml(prs)
    ours = theme_xml(b["prs"])
    assert theme.find(".//a:clrScheme", NS).get("name") != ours.find(".//a:clrScheme", NS).get("name")
    for s in prs.slides:
        assert s.slide_layout.name in foreign_layouts
        title = s.shapes.title
        assert title is not None and title.text_frame.text.strip()
        for run in title._element.iter(A + "r"):
            colour = check.resolve_colour(s, run)
            assert colour == check.resolve_colour(s, None, slot="tx1"), "title ink follows the foreign dk1"
            assert check.resolve_font(s, run) == theme.find(".//a:majorFont/a:latin", NS).get("typeface")
    c3 = pslides_for(prs, "c-3")[0]
    assert len(clicks(c3)) == 3, "animations survive the re-flow"
    assert hp.structural_errors(c3._element) == []
    assert check.validate_package(out) == []


def test_emit_refuses_an_invalid_scene(built, tmp_path):
    bad = copy.deepcopy(built["core"]["scene"])
    del bad["slides"][0]["elements"][0]["box"]
    with pytest.raises(emit.EmitError):
        emit.emit(bad, tmp_path / "x.pptx")
    assert not (tmp_path / "x.pptx").exists()


def test_cli_emits_from_a_deck_and_checks_it(built, tmp_path):
    deck = shutil.copy(built["core"]["deck"], tmp_path / "deck.html")
    out = tmp_path / "deck.pptx"
    r = subprocess.run(["uv", "run", str(hp.SCRIPTS / "emit.py"), str(deck), "-o", str(out)],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr
    assert out.is_file() and (tmp_path / "deck.pptx-report.json").is_file()
    assert (tmp_path / "deck.scene.json").is_file()
    vdir = tmp_path / "verdicts"
    r = subprocess.run(["uv", "run", str(hp.SCRIPTS / "check.py"), "verdicts", str(out),
                        "--scene", str(tmp_path / "deck.scene.json"), "--out", str(vdir)],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr + r.stdout
    assert sorted(vdir.glob("PX-0*_*_r1.json"))
    r = subprocess.run(["uv", "run", str(hp.SCRIPTS / "emit.py"), str(tmp_path / "missing.html")],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 1 and "emit:" in r.stderr


def test_worked_example_emits_and_passes_its_checks(browser, tmp_path):
    """Optional: the worked example deck lands in parallel (PB-007)."""
    if not EXAMPLE.is_file():
        pytest.skip("examples/hf-incident/deck.html not built yet")
    scene = scene_mod.extract(EXAMPLE, browser=browser)
    path = emit.emit(scene, tmp_path / "hf-incident.pptx")
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy(path, OUT / "hf-incident.pptx")
    shutil.copy(tmp_path / "hf-incident.pptx-report.json", OUT / "hf-incident.pptx-report.json")
    assert check.validate_package(path) == []
    assert len(Presentation(path).slides) == sum(1 + len(camera_steps(s)) for s in scene["slides"])


def test_renders_saved_for_the_presenter_when_soffice_exists(built):
    """Text wrap is judged by eye (PX-06); this only saves renders when LibreOffice is installed."""
    soffice = shutil.which("soffice")
    if soffice is None:
        pytest.skip("LibreOffice soffice not installed: no PNG renders")
    for k in built:
        r = subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(OUT), str(OUT / f"{k}.pptx")],
                           capture_output=True, text=True, timeout=300)
        assert r.returncode == 0, r.stderr
        assert (OUT / f"{k}.pdf").is_file()


def test_pptx_part_is_routed_and_names_its_pipeline():
    skill_md = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "(pptx/PPTX.md)" in skill_md
    doc = (SKILL / "pptx" / "PPTX.md").read_text(encoding="utf-8")
    for must in ("scene.py", "emit.py", "check.py", "Morph", "native", "approximated", "lost", "re-flow",
                 "PowerPoint"):
        assert must in doc, must
