# /// script
# requires-python = ">=3.12"
# dependencies = ["python-pptx>=1.0.2", "lxml>=5"]
# ///
"""Deterministic checks for an emitted PPTX: eval verdicts, package validation and template re-flow.

Usage (run from the skill folder)::

    uv run pptx/scripts/check.py verdicts deck.pptx [--scene deck.scene.json] [--report deck.pptx-report.json] [--out verdicts/]
    uv run pptx/scripts/check.py validate deck.pptx
    uv run pptx/scripts/check.py reflow deck.pptx -o reflowed.pptx [--template corporate.pptx]

or, imported: ``verdicts(pptx, scene, report) -> [verdict]``, ``validate_package(path) -> [problem]``,
``reflow(pptx, out, template=None) -> Path``, ``resolve_colour(slide, run)``, ``resolve_font(slide, run)``.

**Verdicts** are one per (criterion, unit) in the eval schema (``evals/aggregate.py``
``validate_verdict``; ``repeat`` 1), for every ``target: "pptx"``, ``evidence: "D"`` criterion
(``CRITERIA``). Units are HTML slide ids for slide-scoped criteria (a Morph duplicate counts with
its HTML slide) and ``deck`` otherwise. The scene (``pptx/scripts/scene.py``) is the reference;
the emitter's sidecar report says what was dropped by policy. Without them, criteria that need
them return ``insufficient-evidence``.

==========  ==================================================================================
PX-01       every scene word (markers and generated quotes aside) is in a text frame
PX-02       every slide uses a master layout; its title is in the title placeholder, nowhere else
PX-03       theme colours/fonts equal the scene palette and fonts; no literal RGB equal to a theme
            colour and no explicit theme font name in slides
PX-04       one click per HTML step (steps the report drops by policy aside), each click animating
            that step's elements; Morph only on the slide a camera move starts
PX-05       every native/approximated style effect is present on its shape (outer shadow, soft
            edge, alpha); every lost or undeclared one is listed in the report and absent
PX-07       every slide titled, titles unique (Morph continuations aside), title first in reading
            order after decorative shapes, alt text on pictures
PX-08       every diagram part is a shape named by its element id (or an SVG picture with PNG)
PX-09       speaker notes equal the slide's reader note text
==========  ==================================================================================

**Re-flow** copies every slide into a foreign template (default: python-pptx's unmodified
default template, Office theme), matching layouts by name, then by layout type; placeholders map
by type (title, subtitle) then body order and drop their position overrides, so they take the
template's geometry; free shapes scale to the new slide size; timing, transitions and notes come
along. Scheme colour and theme font references then resolve to the foreign theme.

Exit codes: 0 all pass / valid, 1 refused (unreadable input), 2 some verdict failed or problems found.
"""

from __future__ import annotations

import argparse
import copy
import importlib.util
import io
import json
import posixpath
import re
import sys
import zipfile
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.opc.constants import RELATIONSHIP_TYPE as RT

HERE = Path(__file__).resolve().parent
EVAL_DIR = HERE.parents[1] / "evals"
CRITERIA = ("PX-01", "PX-02", "PX-03", "PX-04", "PX-05", "PX-07", "PX-08", "PX-09")
DECK_SCOPE = {"PX-03", "PX-05", "PX-07"}
INSUFFICIENT = "insufficient-evidence"

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "p159": "http://schemas.microsoft.com/office/powerpoint/2015/09/main",
    "asvg": "http://schemas.microsoft.com/office/drawing/2016/SVG/main",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
_A, _P, _R = (f"{{{NS[k]}}}" for k in ("a", "p", "r"))
SLOT_ALIAS = {"dk1": "tx1", "lt1": "bg1", "dk2": "tx2", "lt2": "bg2"}
DECORATIVE_URI = "{C183D7F6-B498-43B3-948B-1728B52AA6E4}"
DIAGRAM_ROLES = {"tile", "key-tile", "edge", "label", "tag", "shape"}
CONTAINER_ROLES = {"body", "scene", "diagram", "popover", "table"}
SLIDE_ORDER = ["cSld", "clrMapOvr", "transition", "timing", "extLst"]


class CheckError(Exception):
    """Unreadable input."""


# ---------- loading ----------

def _json(x, fallback: Path | None):
    if isinstance(x, dict):
        return x
    p = Path(x) if x else fallback
    if p is not None and Path(p).is_file():
        return json.loads(Path(p).read_text(encoding="utf-8"))
    return None


def _sidecar(pptx: Path, suffix: str) -> Path:
    return pptx.with_name(pptx.stem + suffix)


def _html_id(slide) -> str:
    return slide._element.find("p:cSld", NS).get("name", "").split(" ")[0]


def _group(prs, scene, report) -> dict[str, list]:
    """PPTX slides per HTML slide id (slide names first, then the report's order)."""
    out: dict[str, list] = {}
    ids = {s["id"] for s in scene["slides"]} if scene else set()
    named = [(_html_id(s), s) for s in prs.slides]
    if not ids or all(h in ids for h, _ in named):
        for h, s in named:
            out.setdefault(h, []).append(s)
        return out
    if report:
        for row, s in zip(report["slides"], prs.slides):
            out.setdefault(row["html"], []).append(s)
    return out


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _words(s: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Za-z0-9]+", s or "")}


def _run_text(runs) -> str:
    return "".join(r["text"] for r in runs)


def _el_texts(e: dict, sep: str = "") -> list[str]:
    out = []
    if e.get("text"):
        out.append(sep.join(r["text"] for r in e["text"]["runs"]))
    for p in e.get("svg") or []:
        if p["type"] == "text":
            out.append(sep.join(r["text"] for r in p["runs"]))
    return out


def _shape_paras(sp) -> list[str]:
    return [_norm("".join(t.text or "" for t in p.iter(_A + "t"))) for p in sp.iter(_A + "p")]


def _slide_text(slide) -> str:
    return " ".join(t.text or "" for t in slide._element.iter(_A + "t"))


def _name(sp) -> str:
    c = next(sp.iter(_P + "cNvPr"), None)
    return (c.get("name") if c is not None else "") or ""


def _bare(name: str) -> str:
    return name.removeprefix("!!").split("#")[0]


def _shapes_by_name(slides) -> dict[str, list]:
    out: dict[str, list] = {}
    for s in slides:
        tree = s._element.find("p:cSld/p:spTree", NS)
        for c in tree.iter(_P + "cNvPr"):
            sp = c.getparent().getparent()
            if sp is tree:
                continue
            out.setdefault(_bare(c.get("name") or ""), []).append(sp)
    return out


def _has_morph(slide) -> bool:
    return slide._element.find("mc:AlternateContent/mc:Choice/p:transition/p159:morph", NS) is not None


def _theme(prs):
    part = prs.slide_master.part.part_related_by(RT.THEME)
    return etree.fromstring(part.blob)


def _clr_scheme(theme) -> dict[str, str]:
    out = {}
    for c in theme.find(".//a:clrScheme", NS):
        v = c[0]
        out[etree.QName(c).localname] = v.get("val") if etree.QName(v).localname == "srgbClr" else v.get("lastClr")
    return out


def _verdict(cid, unit, ok, evidence, rationale, flaws, file):
    ev = [dict(e, file=file) for e in evidence] or [{"note": rationale[:200], "file": file}]
    result = ok if isinstance(ok, str) else ("pass" if ok else "fail")
    return {"criterion": cid, "unit": unit, "repeat": 1, "evidence": ev if result != INSUFFICIENT else [],
            "rationale": rationale[:600], "flaws": [] if result != "fail" else flaws, "result": result}


# ---------- theme resolution ----------

def resolve_colour(slide, run, slot: str | None = None) -> str | None:
    """Resolve a run's colour (or a scheme name) through the slide's master and theme.

    Args:
        slide: A python-pptx slide.
        run: An ``a:r`` element, or None when ``slot`` is given.
        slot: A scheme colour name (``tx1``, ``accent1``…) to resolve instead of a run.

    Returns:
        ``RRGGBB`` hex, or None when the run sets no colour.
    """
    if slot is None:
        fill = run.find("a:rPr/a:solidFill", NS) if run is not None else None
        if fill is None or len(fill) == 0:
            return None
        c = fill[0]
        if etree.QName(c).localname == "srgbClr":
            return c.get("val")
        slot = c.get("val")
    master = slide.slide_layout.slide_master
    cmap = master._element.find("p:clrMap", NS)
    real = cmap.get(slot, slot) if cmap is not None and slot in ("bg1", "tx1", "bg2", "tx2") else slot
    return _clr_scheme(_theme_of(master)).get(real)


def _theme_of(master):
    return etree.fromstring(master.part.part_related_by(RT.THEME).blob)


def resolve_font(slide, run) -> str | None:
    """Resolve a run's latin typeface (``+mj-lt``/``+mn-lt`` through the theme)."""
    latin = run.find("a:rPr/a:latin", NS)
    if latin is None:
        return None
    face = latin.get("typeface")
    if face in ("+mj-lt", "+mn-lt"):
        theme = _theme_of(slide.slide_layout.slide_master)
        slot = "majorFont" if face == "+mj-lt" else "minorFont"
        return theme.find(f".//a:fontScheme/a:{slot}/a:latin", NS).get("typeface")
    return face


# ---------- criteria ----------

class _Ctx:
    def __init__(self, path: Path, prs, scene, report):
        self.path, self.prs, self.scene, self.report = path, prs, scene, report
        self.file = path.name
        self.groups = _group(prs, scene, report) if scene else {}
        self.items = report["items"] if report else []

    def sl(self, sid):
        return self.groups.get(sid, [])

    def ev(self, note, sid=None):
        e = {"note": note}
        if sid:
            e["slide"] = sid
        return e

    def reported(self, slide, el, what, results) -> bool:
        return any(i["slide"] == slide and i["el"] == el and i["what"] == what and i["result"] in results
                   for i in self.items)


def _px01(c: _Ctx, s):
    sid = s["id"]
    want = set()
    for e in s["elements"]:
        if e["role"] in ("marker", "generated-text"):
            continue
        for t in _el_texts(e, " "):  # run boundaries separate words (a block-level run has no space)
            want |= _words(t)
    have = set()
    for ps in c.sl(sid):
        have |= _words(_slide_text(ps))
    missing = sorted(want - have)
    pics = sum(1 for ps in c.sl(sid) for _ in ps._element.iter(_P + "pic"))
    if not c.sl(sid):
        return False, [c.ev("no PPTX slide for this HTML slide", sid)], f"Slide {sid} was not emitted."
    if missing:
        return False, [c.ev(f"words not in any text frame: {', '.join(missing[:12])}; pictures on slide: {pics}", sid)], \
            f"{len(missing)} of {len(want)} words are not native text."
    return True, [c.ev(f"all {len(want)} words are native text; pictures: {pics}", sid)], "Every word is in a text frame."


def _px02(c: _Ctx, s):
    sid = s["id"]
    title = next((e for e in s["elements"] if e["role"] == "title"), None)
    want = _norm(_run_text(title["text"]["runs"])) if title and title.get("text") else None
    if not c.sl(sid):
        return False, [c.ev("no PPTX slide", sid)], f"Slide {sid} was not emitted."
    for ps in c.sl(sid):
        lay = ps.slide_layout
        if not lay.name or lay.name.lower() == "blank" or not any(True for _ in lay.placeholders):
            return False, [c.ev(f"layout {lay.name!r} has no placeholders", sid)], "A slide uses a blank layout."
        if want is None:
            continue
        t = ps.shapes.title
        if t is None or _norm(t.text_frame.text) != want:
            got = _norm(t.text_frame.text) if t is not None else None
            return False, [c.ev(f"title placeholder holds {got!r}, want {want!r}", sid)], "Title not in its placeholder."
        for sh in ps.shapes:
            if not sh.is_placeholder and sh.has_text_frame and _norm(sh.text_frame.text) == want:
                return False, [c.ev(f"title text also in free shape {sh.name!r}", sid)], "Title in a free text box."
    names = sorted({ps.slide_layout.name for ps in c.sl(sid)})
    return True, [c.ev(f"layout {', '.join(names)}; title in the title placeholder", sid)], \
        "Uses a master layout with the title in its placeholder."


def _px03(c: _Ctx):
    theme = _theme(c.prs)
    clr = _clr_scheme(theme)
    bad = []
    for role, v in c.scene["palette"].items():
        for slot in v["slots"]:
            if clr.get(slot) != v["rgb"]:
                bad.append(f"theme {slot}={clr.get(slot)} but palette {role}={v['rgb']}")
    fonts = c.scene.get("fonts") or {}
    for slot, key in (("majorFont", "major"), ("minorFont", "minor")):
        got = theme.find(f".//a:fontScheme/a:{slot}/a:latin", NS).get("typeface")
        if fonts.get(key) and got != fonts[key]:
            bad.append(f"theme {slot} {got} but style {key} {fonts[key]}")
    theme_vals = set(clr.values())
    face = {f for f in (fonts.get("major"), fonts.get("minor")) if f}
    lits, named, schemes = [], [], 0
    for ps in c.prs.slides:
        sid = _html_id(ps)
        for el in ps._element.iter(_A + "srgbClr"):
            if el.get("val") in theme_vals:
                lits.append((sid, el.get("val")))
        schemes += sum(1 for _ in ps._element.iter(_A + "schemeClr"))
        for el in ps._element.iter(_A + "latin"):
            if el.get("typeface") in face:
                named.append((sid, el.get("typeface")))
    ev = [c.ev(b) for b in bad[:5]]
    ev += [c.ev(f"literal #{v} equals a theme colour", sid) for sid, v in lits[:5]]
    ev += [c.ev(f"explicit font {f} where a theme font slot exists", sid) for sid, f in named[:5]]
    if ev:
        return False, ev, f"{len(bad)} theme mismatches, {len(lits)} literal colours and {len(named)} explicit fonts."
    return True, [c.ev(f"theme slots and fonts match the tokens; {schemes} scheme colour references, no literals")], \
        "Colours and fonts reference the theme."


def _step_keys(s, k) -> tuple[set, list[str], bool]:
    """Element ids and texts a native step k should animate; and whether only markers change."""
    byid = {e["id"]: e for e in s["elements"]}
    kids: dict = {}
    for e in s["elements"]:
        kids.setdefault(e["parent"], []).append(e)

    def desc(eid):
        for x in kids.get(eid, []):
            yield x
            yield from desc(x["id"])

    ids, texts, only_markers = set(), [], True
    for t in s["timeline"]:
        if t["step"] != k:
            continue
        for d in t["deltas"]:
            if d["effect"] == "unsupported":
                continue
            e = byid.get(d["el"])
            if e is not None and e["role"] != "marker":
                only_markers = False
            for x in [e, *desc(d["el"])] if e is not None else []:
                ids.add(x["id"])
                texts += [_norm(t2) for t2 in _el_texts(x) if len(_norm(t2)) >= 3]
    return ids, texts, only_markers


def _clicks(slide) -> list[list]:
    main = slide._element.find("p:timing/p:tnLst/p:par/p:cTn[@nodeType='tmRoot']/p:childTnLst/p:seq/"
                               "p:cTn[@nodeType='mainSeq']", NS)
    if main is None:
        return []
    out = []
    for click in main.findall("p:childTnLst/p:par", NS):
        out.append([c for c in click.iter(_P + "cTn") if c.get("presetClass")])
    return out


def _targets(slide, ctn) -> tuple[set, list[str]]:
    tree = slide._element.find("p:cSld/p:spTree", NS)
    names, texts = set(), []
    for tgt in ctn.iter(_P + "spTgt"):
        sp = next((c.getparent().getparent() for c in tree.iter(_P + "cNvPr") if c.get("id") == tgt.get("spid")), None)
        if sp is None:
            continue
        names.add(_bare(_name(sp)))
        paras = _shape_paras(sp)
        rng = tgt.find("p:txEl/p:pRg", NS)
        if rng is not None:
            paras = paras[int(rng.get("st")): int(rng.get("end")) + 1]
        texts += paras
    return names, texts


def _px04(c: _Ctx, s):
    sid = s["id"]
    slides = c.sl(sid)
    cams = sorted({t["step"] for t in s["timeline"] for d in t["deltas"] if d["property"] == "camera"})
    bounds = [0, *cams, s["steps"] + 1]
    if len(slides) != len(bounds) - 1:
        return False, [c.ev(f"{len(slides)} PPTX slides, want {len(bounds) - 1} (1 + {len(cams)} camera moves)", sid)], \
            "Slide count does not match the camera moves."
    ev = []
    for n, (ps, (lo, hi)) in enumerate(zip(slides, zip(bounds, bounds[1:]))):
        if _has_morph(ps) != (n > 0):
            what = "missing its Morph transition" if n > 0 else "has a Morph with no camera move"
            return False, [c.ev(f"slide for steps {lo}–{hi - 1} {what}", sid)], "Morph used where it should not be, or missing."
        want = []
        for k in range(lo + 1, hi):
            ids, texts, only_markers = _step_keys(s, k)
            dropped = c.reported(sid, sid, f"step {k}", ("dropped",))
            if dropped and (only_markers or not ids):
                continue
            want.append((k, ids, texts))
        got = _clicks(ps)
        if len(got) != len(want):
            return False, [c.ev(f"steps {lo}–{hi - 1}: {len(got)} clicks, want {len(want)}", sid)], \
                "A step has no animation (or an extra click)."
        for (k, ids, texts), click in zip(want, got):
            names, ttexts = set(), []
            for ctn in click:
                nm, tx = _targets(ps, ctn)
                names |= nm
                ttexts += tx
            if not (names & ids or any(w in t for w in texts for t in ttexts)):
                return False, [c.ev(f"click for step {k} animates {sorted(names)}, not that step's elements", sid)], \
                    "Clicks are out of step order."
        ev.append(c.ev(f"steps {lo}–{hi - 1}: {len(got)} clicks in order" + (" after a Morph" if n else ""), sid))
    return True, ev, "Every step is a native click in order; Morph only for camera moves."


def _px05(c: _Ctx):
    bad, ok = [], 0
    for s in c.scene["slides"]:
        shapes = _shapes_by_name(c.sl(s["id"]))
        for e in s["elements"]:
            for fx in e["effects"]:
                kind, band = fx["kind"], fx["band"]
                if band in ("lost", "undeclared") or kind in ("backdrop-blur",):
                    if c.report is None:
                        continue
                    if not c.reported(s["id"], e["id"], kind, ("lost", "approximated")):
                        bad.append((s["id"], f"{e['id']} {kind} ({band}) not listed in the report"))
                    elif kind in ("backdrop-blur", "blur", "filter") and band == "lost":
                        for sp in shapes.get(e["id"], []):
                            if sp.find(".//a:blur", NS) is not None:
                                bad.append((s["id"], f"{e['id']} carries a blur declared lost"))
                    ok += 1
                    continue
                sps = shapes.get(e["id"], [])
                if not sps:
                    if e["role"] in CONTAINER_ROLES:
                        continue
                    bad.append((s["id"], f"{e['id']} has {kind} ({band}) but no shape"))
                    continue
                need = {"shadow": ".//a:outerShdw", "svg-filter": ".//a:outerShdw", "blur": ".//a:softEdge",
                        "opacity": ".//a:alpha"}.get(kind)
                if need and not any(sp.find(need, NS) is not None for sp in sps):
                    bad.append((s["id"], f"{e['id']} {kind} ({band}) not found as {need.split(':')[-1]}"))
                else:
                    ok += 1
    if bad:
        return False, [c.ev(n, sid) for sid, n in bad[:8]], f"{len(bad)} effects differ from their declared band."
    return True, [c.ev(f"{ok} effects match their bands (native/approximated present, lost listed and absent)")], \
        "Every effect is exported as its band declares."


def _decorative(sp) -> bool:
    return any(x.get("uri") == DECORATIVE_URI for x in sp.iter(_A + "ext"))


def _px07(c: _Ctx):
    bad, seen = [], {}
    for n, ps in enumerate(c.prs.slides):
        sid = _html_id(ps) or f"slide {n + 1}"
        t = ps.shapes.title
        text = _norm(t.text_frame.text) if t is not None else ""
        if not text:
            bad.append((sid, "slide has no title", "accessibility-error"))
        elif text in seen and not _has_morph(ps):
            bad.append((sid, f"duplicate title {text!r} (also {seen[text]})", "accessibility-error"))
        seen.setdefault(text, sid)
        tree = ps._element.find("p:cSld/p:spTree", NS)
        first = None
        for sp in tree:
            if etree.QName(sp).localname in ("nvGrpSpPr", "grpSpPr") or _decorative(sp):
                continue
            if any((x.text or "").strip() for x in sp.iter(_A + "t")):
                first = sp
                break
        if t is not None and first is not None and first is not t._element:
            bad.append((sid, f"reading order starts with {_name(first)!r}, not the title", "accessibility-error"))
        for pic in tree.iter(_P + "pic"):
            if not (pic.find("p:nvPicPr/p:cNvPr", NS).get("descr") or "").strip() and not _decorative(pic):
                bad.append((sid, f"picture {_name(pic)!r} has no alt text", "missing-alt-text"))
    if bad:
        return False, [c.ev(n, sid) for sid, n, _ in bad[:8]], f"{len(bad)} accessibility errors.", \
            sorted({f for _, _, f in bad})
    return True, [c.ev(f"{len(c.prs.slides)} slides titled (Morph continuations share their title), title first, alt text set")], \
        "No accessibility-checker errors.", []


def _px08(c: _Ctx, s):
    sid = s["id"]
    parts = [e for e in s["elements"] if e["role"] in DIAGRAM_ROLES and e.get("svg")]
    if not parts:
        return True, [c.ev("no diagram on this slide", sid)], "Nothing to check."
    shapes = _shapes_by_name(c.sl(sid))
    svg_pics = sum(1 for ps in c.sl(sid) for p in ps._element.iter(_P + "pic")
                   if p.find(".//asvg:svgBlip", NS) is not None and p.find(".//a:blip", NS) is not None)
    missing = [e["id"] for e in parts if e["id"] not in shapes]
    if missing and not svg_pics:
        return False, [c.ev(f"diagram parts without a named shape: {', '.join(missing[:10])}", sid)], \
            "Diagram flattened or unnamed."
    return True, [c.ev(f"{len(parts) - len(missing)} diagram parts are named shapes; SVG pictures: {svg_pics}", sid)], \
        "Diagram is named native shapes."


def _px09(c: _Ctx, s):
    sid = s["id"]
    want = _norm(s["notes_text"])
    if not c.sl(sid):
        return False, [c.ev("no PPTX slide", sid)], "Slide not emitted."
    for ps in c.sl(sid):
        got = _norm(ps.notes_slide.notes_text_frame.text) if ps.has_notes_slide else ""
        if got != want:
            return False, [c.ev(f"notes {got[:80]!r} differ from the reader note {want[:80]!r}", sid)], \
                "Notes missing or truncated."
    return True, [c.ev("notes equal the reader note" if want else "no reader note, no notes", sid)], \
        "Notes carry the reader note."


FLAWS = {"PX-01": ["rasterised-text"], "PX-02": ["missing-placeholder"], "PX-03": ["literal-colour"],
         "PX-04": ["missing-animation"], "PX-05": ["undeclared-effect"], "PX-08": ["flattened-diagram"],
         "PX-09": ["missing-notes"]}


def verdicts(pptx, scene=None, report=None) -> list[dict]:
    """Check an emitted PPTX against every deterministic ``pptx`` criterion.

    Args:
        pptx: The ``.pptx`` path.
        scene: The deck's scene (dict or path); default ``<stem>.scene.json`` beside the file.
        report: The emitter's report (dict or path); default ``<stem>.pptx-report.json``.

    Returns:
        Verdicts in the eval schema, one per (criterion, unit), ``repeat`` 1.
    """
    path = Path(pptx)
    try:
        prs = Presentation(path)
    except Exception as e:  # noqa: BLE001
        raise CheckError(f"cannot open {path}: {e}") from e
    scene = _json(scene, _sidecar(path, ".scene.json"))
    report = _json(report, _sidecar(path, ".pptx-report.json"))
    c = _Ctx(path, prs, scene, report)
    out = []
    if scene is None:  # slide units come from the scene; only the deck-level checks can run
        ok, ev, why, flaws = _px07(c)
        out.append(_verdict("PX-07", "deck", ok, ev, why, flaws, c.file))
        for cid in ("PX-03", "PX-05"):
            out.append(_verdict(cid, "deck", INSUFFICIENT, [], "No scene: the HTML reference is needed.", [], c.file))
        return out
    for cid, fn in (("PX-01", _px01), ("PX-02", _px02), ("PX-04", _px04), ("PX-08", _px08), ("PX-09", _px09)):
        for s in scene["slides"]:
            ok, ev, why = fn(c, s)
            out.append(_verdict(cid, s["id"], ok, ev, why, FLAWS[cid], c.file))
    ok, ev, why = _px03(c)
    out.append(_verdict("PX-03", "deck", ok, ev, why, FLAWS["PX-03"], c.file))
    ok, ev, why = _px05(c)
    if report is None and ok:
        ok, why = INSUFFICIENT, "No emitter report: lost effects cannot be confirmed as declared."
    out.append(_verdict("PX-05", "deck", ok, ev, why, FLAWS["PX-05"], c.file))
    ok, ev, why, flaws = _px07(c)
    out.append(_verdict("PX-07", "deck", ok, ev, why, flaws, c.file))
    order = {cid: i for i, cid in enumerate(CRITERIA)}
    return sorted(out, key=lambda v: order[v["criterion"]])


# ---------- package validation ----------

def _resolve_target(src_part: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    base = posixpath.dirname(src_part)
    return posixpath.normpath(posixpath.join(base, target))


def _timing_problems(name: str, sld) -> list[str]:
    errs = []
    kids = [etree.QName(c).localname for c in sld if isinstance(c.tag, str)]
    ranks = [SLIDE_ORDER.index("transition") if k == "AlternateContent" else
             (SLIDE_ORDER.index(k) if k in SLIDE_ORDER else -1) for k in kids]
    if -1 in ranks or ranks != sorted(ranks):
        errs.append(f"{name}: children out of order {kids}")
    tree = sld.find("p:cSld/p:spTree", NS)
    ids = [c.get("id") for c in tree.iter(_P + "cNvPr")] if tree is not None else []
    if len(ids) != len(set(ids)):
        errs.append(f"{name}: duplicate shape ids")
    tm = sld.find("p:timing", NS)
    if tm is None:
        return errs
    ctn = [c.get("id") for c in tm.iter(_P + "cTn")]
    if any(i is None or not i.isdigit() for i in ctn) or len(ctn) != len(set(ctn)):
        errs.append(f"{name}: cTn ids not unique integers")
    for t in tm.iter(_P + "spTgt"):
        if t.get("spid") not in ids:
            errs.append(f"{name}: animation targets missing shape {t.get('spid')}")
    effects = {(t.get("spid"), c.get("grpId")) for c in tm.iter(_P + "cTn") if c.get("presetClass")
               for t in c.iter(_P + "spTgt")}
    for b in list(tm.iterfind("p:bldLst/p:bldP", NS)) + list(tm.iterfind("p:bldLst/p:bldGraphic", NS)):
        if (b.get("spid"), b.get("grpId")) not in effects:
            errs.append(f"{name}: build entry {b.get('spid')}/{b.get('grpId')} has no effect")
    main = tm.find("p:tnLst/p:par/p:cTn/p:childTnLst/p:seq/p:cTn[@nodeType='mainSeq']", NS)
    if main is not None:
        for n, click in enumerate(main.findall("p:childTnLst/p:par", NS)):
            if click.find("p:cTn/p:stCondLst/p:cond[@delay='indefinite']", NS) is None:
                errs.append(f"{name}: click {n} does not wait for a click")
    return errs


def validate_package(path) -> list[str]:
    """Structural validation: zip, content types, relationships, XML well-formedness, slide timing.

    Args:
        path: A ``.pptx`` file.

    Returns:
        Problems found; empty when the package is sound.
    """
    probs: list[str] = []
    try:
        z = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, FileNotFoundError) as e:
        return [f"not a zip package: {e}"]
    names = set(z.namelist())
    for must in ("[Content_Types].xml", "_rels/.rels", "ppt/presentation.xml"):
        if must not in names:
            probs.append(f"missing {must}")
    if probs:
        return probs
    ct = etree.fromstring(z.read("[Content_Types].xml"))
    defaults = {d.get("Extension").lower() for d in ct.findall("ct:Default", NS)}
    overrides = {o.get("PartName").lstrip("/") for o in ct.findall("ct:Override", NS)}
    for o in overrides:
        if o not in names:
            probs.append(f"content type override for missing part {o}")
    xml = {}
    for n in sorted(names):
        if n.endswith("/") or n == "[Content_Types].xml":
            continue
        if n not in overrides and n.rsplit(".", 1)[-1].lower() not in defaults:
            probs.append(f"no content type for {n}")
        if n.endswith((".xml", ".rels")):
            try:
                xml[n] = etree.fromstring(z.read(n))
            except etree.XMLSyntaxError as e:
                probs.append(f"{n}: not well-formed: {e}")
    rels_of: dict[str, set] = {}
    for n, root in xml.items():
        if not n.endswith(".rels"):
            continue
        d, base = posixpath.split(n)
        src = posixpath.join(posixpath.dirname(d), base[:-5])
        ids = set()
        for r in root.findall("rel:Relationship", NS):
            ids.add(r.get("Id"))
            if r.get("TargetMode") == "External":
                continue
            tgt = _resolve_target(src, r.get("Target"))
            if tgt not in names:
                probs.append(f"{n}: {r.get('Id')} → missing part {tgt}")
        rels_of[src] = ids
    for n, root in xml.items():
        if n.endswith(".rels"):
            continue
        have = rels_of.get(n, set())
        for el in root.iter():
            for k, v in el.attrib.items():
                if k.startswith(_R) and v not in have:
                    probs.append(f"{n}: r:{k[len(_R):]}={v} has no relationship")
        if n.startswith("ppt/slides/slide") and n.endswith(".xml"):
            probs += _timing_problems(n, root)
    return probs


# ---------- re-flow into a foreign template ----------

_TITLE_TYPES = {"title", "ctrTitle"}
_SKIP_TYPES = {"dt", "ftr", "sldNum", "hdr"}


def _ph_type(ph) -> str:
    """A placeholder's ``type`` attribute as written (``obj`` when absent)."""
    el = ph._element.find("p:nvSpPr/p:nvPr/p:ph", NS)
    return el.get("type", "obj") if el is not None else "obj"


def _layout_for(dst, src_layout):
    by_name = {l.name: l for l in dst.slide_layouts}
    if src_layout.name in by_name:
        return by_name[src_layout.name]
    kind = src_layout._element.get("type")
    want = {"title": "title", "obj": "obj", "twoObj": "twoObj", "titleOnly": "titleOnly"}.get(kind, "obj")
    for l in dst.slide_layouts:
        if l._element.get("type") == want:
            return l
    return dst.slide_layouts[0]


def _scale_xfrms(sp, rx: float, ry: float):
    for xf in sp.iter(_A + "xfrm", _P + "xfrm"):
        for child in xf:
            loc = etree.QName(child).localname
            if loc in ("off", "chOff"):
                child.set("x", str(int(int(child.get("x")) * rx)))
                child.set("y", str(int(int(child.get("y")) * ry)))
            elif loc in ("ext", "chExt"):
                child.set("cx", str(int(int(child.get("cx")) * rx)))
                child.set("cy", str(int(int(child.get("cy")) * ry)))


def _set_xfrm(sp, x, y, w, h):
    sppr = sp.find("p:spPr", NS)
    old = sppr.find("a:xfrm", NS)
    if old is not None:
        sppr.remove(old)
    xf = etree.Element(_A + "xfrm")
    etree.SubElement(xf, _A + "off", x=str(int(x)), y=str(int(y)))
    etree.SubElement(xf, _A + "ext", cx=str(int(w)), cy=str(int(h)))
    sppr.insert(0, xf)


def reflow(pptx, out, template=None) -> Path:
    """Copy every slide into a foreign template so placeholders take its layouts and theme.

    Args:
        pptx: Source ``.pptx``.
        out: Destination path.
        template: A ``.pptx``/``.potx`` to re-flow into; default python-pptx's default template.

    Returns:
        ``out``.
    """
    from pptx.oxml import parse_xml

    src = Presentation(pptx)
    dst = Presentation(template) if template else Presentation()
    rx, ry = dst.slide_width / src.slide_width, dst.slide_height / src.slide_height
    for s in src.slides:
        layout = _layout_for(dst, s.slide_layout)
        new = dst.slides.add_slide(layout)
        tree = new.shapes._spTree
        for sp in list(tree)[2:]:
            tree.remove(sp)
        new._element.find("p:cSld", NS).set("name", s._element.find("p:cSld", NS).get("name", ""))
        free = [ph for ph in layout.placeholders if _ph_type(ph) not in _SKIP_TYPES]
        title_ph = next((ph for ph in free if _ph_type(ph) in _TITLE_TYPES), None)
        bodies = [ph for ph in free if ph is not title_ph and _ph_type(ph) != "pic"]
        used = set()
        for shape in s.shapes:
            el = parse_xml(etree.tostring(shape._element))
            ph = el.find("p:nvSpPr/p:nvPr/p:ph", NS) if shape.is_placeholder else None
            if ph is not None:
                kind = ph.get("type", "obj")
                target = None
                if kind in _TITLE_TYPES and title_ph is not None and id(title_ph) not in used:
                    target = title_ph
                elif kind not in _TITLE_TYPES:
                    pref = [b for b in bodies if id(b) not in used and
                            (kind != "subTitle" or _ph_type(b) == "subTitle")]
                    target = (pref or [b for b in bodies if id(b) not in used] or [None])[0]
                if target is not None:
                    used.add(id(target))
                    tph = target._element.find("p:nvSpPr/p:nvPr/p:ph", NS)
                    for k in list(ph.attrib):
                        del ph.attrib[k]
                    for k, v in tph.attrib.items():
                        ph.set(k, v)
                    xf = el.find("p:spPr/a:xfrm", NS)
                    if xf is not None:
                        xf.getparent().remove(xf)
                else:  # no slot in the foreign layout: keep it as a free shape where it was
                    ph.getparent().remove(ph)
                    _set_xfrm(el, shape.left * rx, shape.top * ry, shape.width * rx, shape.height * ry)
            else:
                _scale_xfrms(el, rx, ry)
            for node in el.iter():
                for k, v in list(node.attrib.items()):
                    if not k.startswith(_R):
                        continue
                    rel = s.part.rels.get(v)
                    if rel is None:
                        continue
                    if rel.is_external:
                        node.set(k, new.part.relate_to(rel.target_ref, rel.reltype, is_external=True))
                    elif rel.reltype == RT.IMAGE:
                        _, rid = new.part.get_or_add_image_part(io.BytesIO(rel.target_part.blob))
                        node.set(k, rid)
            tree.append(el)
        sld = new._element
        anchor = sld.find("p:extLst", NS)
        for tag in ("mc:AlternateContent", "p:transition", "p:timing"):
            for x in s._element.findall(tag, NS):
                y = copy.deepcopy(x)
                if anchor is not None:
                    anchor.addprevious(y)
                else:
                    sld.append(y)
        if s.has_notes_slide and s.notes_slide.notes_text_frame.text:
            new.notes_slide.notes_text_frame.text = s.notes_slide.notes_text_frame.text
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    dst.save(out)
    return out


# ---------- CLI ----------

def _slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9-]+", "-", s).strip("-")


def _validate_against_library(vs: list[dict], profile: str | None) -> list[str]:
    if not (EVAL_DIR / "aggregate.py").is_file():
        return []
    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod
    crit = load("pb_check_criteria", EVAL_DIR / "criteria.py")
    agg = load("pb_check_aggregate", EVAL_DIR / "aggregate.py")
    lib = crit.load_library(EVAL_DIR)
    prof = crit.load_profile(EVAL_DIR / "profiles" / f"{profile or 'editorial-talk'}.json", lib)
    errs = []
    for v in vs:
        try:
            agg.validate_verdict(v, lib, prof)
        except agg.VerdictError as e:
            errs.append(str(e))
    return errs


def main(argv: list[str] | None = None) -> int:
    """Command line: verdicts, validate or reflow.

    Args:
        argv: Arguments (default ``sys.argv[1:]``).

    Returns:
        Exit code: 0 pass/valid, 1 refused, 2 failures found.
    """
    ap = argparse.ArgumentParser(prog="check.py", description="Deterministic PPTX checks.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verdicts", help="eval verdicts for every deterministic pptx criterion")
    v.add_argument("pptx", type=Path)
    v.add_argument("--scene", type=Path)
    v.add_argument("--report", type=Path)
    v.add_argument("--profile", default="editorial-talk")
    v.add_argument("--out", type=Path, help="write <criterion>_<unit>_r1.json files here")
    va = sub.add_parser("validate", help="structural package validation")
    va.add_argument("pptx", type=Path)
    r = sub.add_parser("reflow", help="copy the slides into a foreign template")
    r.add_argument("pptx", type=Path)
    r.add_argument("-o", "--out", type=Path, required=True)
    r.add_argument("--template", type=Path)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "validate":
            probs = validate_package(a.pptx)
            for p in probs:
                print(p)
            print("valid" if not probs else f"{len(probs)} problems")
            return 2 if probs else 0
        if a.cmd == "reflow":
            print(f"wrote {reflow(a.pptx, a.out, a.template)}")
            return 0
        vs = verdicts(a.pptx, a.scene, a.report)
    except CheckError as e:
        print(f"check: {e}", file=sys.stderr)
        return 1
    errs = _validate_against_library(vs, a.profile)
    if errs:
        print("check: verdicts break the eval schema:\n  " + "\n  ".join(errs), file=sys.stderr)
        return 1
    if a.out:
        a.out.mkdir(parents=True, exist_ok=True)
        for x in vs:
            (a.out / f"{x['criterion']}_{_slug(x['unit'])}_r1.json").write_text(
                json.dumps(x, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    fails = [x for x in vs if x["result"] != "pass"]
    for x in vs:
        print(f"{x['criterion']} {x['unit']:<10} {x['result']:<22} {x['rationale']}")
    return 2 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
