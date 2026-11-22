"""Shared helpers for the skill's PPTX tests: build slides, reopen files, read timing trees.

Structural rules checked here come from ECMA-376 Part 1 (ISO/IEC 29500-1) §19.5 *Animation*
and its schema `pml.xsd` (complex types named inline below). When a copy of the transitional
schema set is available (`PB_OOXML_SCHEMAS` env var, or the Anthropic pptx skill's bundled
`schemas/ISO-IEC29500-4_2016/`), `find_pml_xsd` returns it for full XSD validation.
"""

from __future__ import annotations

import glob
import importlib.util
import os
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "skills" / "twm-presentation-builder" / "pptx" / "scripts"
ARTIFACTS = Path(__file__).resolve().parent / "artifacts"

NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}
P = "{%s}" % NS["p"]


def load_script(name: str):
    """Import a shipped PPTX script by file stem (the scripts dir is not a package).

    Args:
        name: File stem under `pptx/scripts/`, e.g. ``"animations"``.

    Returns:
        The imported module.
    """
    spec = importlib.util.spec_from_file_location(f"pb_{name}", SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def new_deck(n_shapes: int = 3, n_slides: int = 1):
    """Build an in-memory deck of blank slides, each with labelled rectangles.

    Args:
        n_shapes: Text-bearing rectangles per slide.
        n_slides: Number of slides.

    Returns:
        Tuple of (presentation, list of slides, list of per-slide shape lists).
    """
    prs = Presentation()
    slides, shapes = [], []
    for s in range(n_slides):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        row = []
        for i in range(n_shapes):
            shp = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.5 + 3 * i), Inches(1), Inches(2.5), Inches(1)
            )
            shp.text = f"s{s} shape {i}"
            row.append(shp)
        slides.append(slide)
        shapes.append(row)
    return prs, slides, shapes


def reopen(prs, path: Path, index: int = 0):
    """Save, reopen with python-pptx and return the slide element at `index`.

    Args:
        prs: Presentation to save.
        path: Destination file.
        index: Slide index to return.

    Returns:
        The reopened slide's `p:sld` lxml element.
    """
    prs.save(path)
    return Presentation(path).slides[index]._element


def timing(sld):
    """Return the slide's single `p:timing` element, or None."""
    found = sld.findall("p:timing", NS)
    assert len(found) <= 1, "more than one p:timing on the slide"
    return found[0] if found else None


def click_groups(sld):
    """Read the main sequence as click groups of effect summaries.

    Path: timing/tnLst/par/cTn[tmRoot]/childTnLst/seq/cTn[mainSeq]/childTnLst/par (one per
    click; ECMA-376 §19.5.65 `seq`, §19.5.53 `par`).

    Args:
        sld: `p:sld` element.

    Returns:
        List (one per click) of lists of dicts with keys spid, presetClass, presetID,
        presetSubtype, nodeType, grpId, ctn (the effect `p:cTn` element).
    """
    main = sld.find(
        "p:timing/p:tnLst/p:par/p:cTn[@nodeType='tmRoot']/p:childTnLst/p:seq/"
        "p:cTn[@nodeType='mainSeq']",
        NS,
    )
    assert main is not None, "slide has no tmRoot/mainSeq timing tree"
    groups = []
    for click in main.findall("p:childTnLst/p:par", NS):
        effects = []
        for ctn in click.iter(P + "cTn"):
            if ctn.get("presetClass") is None:
                continue
            spids = {t.get("spid") for t in ctn.iter(P + "spTgt")}
            assert len(spids) == 1, "an effect must target exactly one shape"
            effects.append(
                {
                    "spid": spids.pop(),
                    "presetClass": ctn.get("presetClass"),
                    "presetID": ctn.get("presetID"),
                    "presetSubtype": ctn.get("presetSubtype"),
                    "nodeType": ctn.get("nodeType"),
                    "grpId": ctn.get("grpId"),
                    "ctn": ctn,
                }
            )
        groups.append(effects)
    return groups


# Child order of the complex types this module writes (pml.xsd, ECMA-376 Part 1 §19.5/§19.3).
_CHILD_ORDER = {
    "sld": ["cSld", "clrMapOvr", "transition", "timing", "extLst"],  # CT_Slide
    "timing": ["tnLst", "bldLst", "extLst"],  # CT_SlideTiming §19.5.87
    "cTn": ["stCondLst", "endCondLst", "endSync", "iterate", "childTnLst", "subTnLst"],
    "cBhvr": ["cTn", "tgtEl", "attrNameLst"],  # CT_TLCommonBehaviorData §19.5.22
    "seq": ["cTn", "prevCondLst", "nextCondLst"],  # CT_TLTimeNodeSequence §19.5.65
    "animMotion": ["cBhvr", "by", "from", "to", "rCtr"],  # CT_TLAnimateMotionBehavior
    "animScale": ["cBhvr", "by", "from", "to"],  # CT_TLAnimateScaleBehavior
    "animClr": ["cBhvr", "by", "from", "to"],  # CT_TLAnimateColorBehavior
    "animEffect": ["cBhvr", "progress"],  # CT_TLAnimateEffectBehavior
    "set": ["cBhvr", "to"],  # CT_TLSetBehavior
}
_PRESET_CLASSES = {"entr", "exit", "emph", "path", "verb", "mediacall"}  # ST_TLTimeNodePresetClassType


def _local(el) -> str:
    return etree.QName(el).localname


def structural_errors(sld) -> list[str]:
    """Check the slide's timing tree against the structure PowerPoint relies on.

    Covers: element child order (pml.xsd sequences above); tmRoot → mainSeq skeleton with
    onPrev/onNext slide conditions (§19.5.65, as PowerPoint saves it); unique numeric cTn ids
    (ST_TLTimeNodeID, §19.7.42); click pars start at `delay="indefinite"`; each click's first
    effect is a `clickEffect` and the rest `withEffect` (ST_TLTimeNodeType §19.7.38); every
    `spTgt` names a shape on the slide; `bldP` entries pair with effect grpIds (§19.5.11).

    Args:
        sld: `p:sld` element.

    Returns:
        Human-readable error strings; empty when the structure holds.
    """
    errs: list[str] = []
    for el in sld.iter():
        if not isinstance(el.tag, str):
            continue
        order = _CHILD_ORDER.get(_local(el))
        if order is None or etree.QName(el).namespace != NS["p"]:
            continue
        names = [_local(c) for c in el if isinstance(c.tag, str)]
        ranks = [order.index(n) if n in order else -1 for n in names]
        if -1 in ranks or ranks != sorted(ranks):
            errs.append(f"{_local(el)} children out of schema order: {names}")

    tm = timing(sld)
    if tm is None:
        return errs + ["no p:timing"]
    roots = tm.findall("p:tnLst/p:par/p:cTn[@nodeType='tmRoot']", NS)
    if len(roots) != 1:
        errs.append("expected exactly one tmRoot cTn")
    seq = tm.find("p:tnLst/p:par/p:cTn/p:childTnLst/p:seq", NS)
    if seq is None or seq.find("p:cTn[@nodeType='mainSeq']", NS) is None:
        errs.append("missing mainSeq seq")
    else:
        for lst, evt in (("prevCondLst", "onPrev"), ("nextCondLst", "onNext")):
            if seq.find(f"p:{lst}/p:cond[@evt='{evt}']/p:tgtEl/p:sldTgt", NS) is None:
                errs.append(f"seq lacks {lst} {evt} slide condition")

    ids = [c.get("id") for c in tm.iter(P + "cTn")]
    if any(i is None or not i.isdigit() for i in ids) or len(ids) != len(set(ids)):
        errs.append(f"cTn ids must be unique integers: {ids}")

    spids = {
        el.get("id")
        for el in sld.find("p:cSld/p:spTree", NS).iter("{%s}cNvPr" % NS["p"])
    }
    for t in tm.iter(P + "spTgt"):
        if t.get("spid") not in spids:
            errs.append(f"spTgt spid {t.get('spid')} not on slide")

    if seq is not None:
        for n, click in enumerate(seq.findall("p:cTn/p:childTnLst/p:par", NS)):
            if click.find("p:cTn/p:stCondLst/p:cond[@delay='indefinite']", NS) is None:
                errs.append(f"click {n} does not wait for a click (delay=indefinite)")
        for n, group in enumerate(click_groups(sld)):
            types = [e["nodeType"] for e in group]
            if not types or types[0] != "clickEffect" or set(types[1:]) - {"withEffect"}:
                errs.append(f"click {n} node types {types}")
            for e in group:
                if e["presetClass"] not in _PRESET_CLASSES:
                    errs.append(f"bad presetClass {e['presetClass']}")

        effect_keys = {(e["spid"], e["grpId"]) for g in click_groups(sld) for e in g}
        for b in tm.findall("p:bldLst/p:bldP", NS):
            if (b.get("spid"), b.get("grpId")) not in effect_keys:
                errs.append(f"bldP {b.get('spid')}/{b.get('grpId')} has no matching effect")
    return errs


def find_pml_xsd() -> Path | None:
    """Locate a transitional `pml.xsd` (with its sibling imports) for XSD validation.

    Returns:
        Path to `pml.xsd`, or None when no schema set is available on this machine.
    """
    env = os.environ.get("PB_OOXML_SCHEMAS")
    candidates = [Path(env) / "pml.xsd"] if env else []
    pattern = str(
        Path.home() / ".claude/skills/**/pptx/scripts/office/schemas/ISO-IEC29500-4_2016/pml.xsd"
    )
    candidates += [Path(p) for p in sorted(glob.glob(pattern, recursive=True))]
    return next((c for c in candidates if c.is_file()), None)
