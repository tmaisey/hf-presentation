"""Write build steps as native PowerPoint animations on a python-pptx slide.

python-pptx 1.0.2 has no animation API, so this module writes the slide's `p:timing` tree
directly. One *step* is one click; every effect in a step starts on that click (the first
as `clickEffect`, the rest `withEffect`).

Usage::

    from animations import write_steps
    write_steps(slide, [
        [(title, "fade_in")],
        [(box, "appear"), (arrow, "motion_path", {"path": "M 0 0 L 0.2 0 E"})],
        [(box, "fill_colour", {"rgb": "C0392B"})],
        [(title, "fade_out")],
    ])

XML basis (ECMA-376 Part 1 / ISO/IEC 29500-1 §19.5 *Animation*; schema `pml.xsd`):

- `p:timing` sits after `p:cSld`, `p:clrMapOvr` and `p:transition`, before `p:extLst`
  (CT_Slide). It holds `p:tnLst` then `p:bldLst` (CT_SlideTiming).
- The tree follows the shape PowerPoint saves: `par/cTn[tmRoot]` → `seq[concurrent=1,
  nextAc=seek]/cTn[mainSeq]` with `onPrev`/`onNext` slide conditions → one `par` per click
  (`cond delay="indefinite"`, i.e. wait for a click) → one `par` at delay 0 → one effect
  `par` per shape, whose `cTn` carries `presetClass`/`presetID`/`presetSubtype`, `grpId` and
  `nodeType` (CT_TLCommonTimeNodeData §19.5.33).
- Behaviours are `p:set`, `p:animEffect`, `p:animScale`, `p:animClr`, `p:animMotion`, each a
  `p:cBhvr` (cTn → tgtEl/spTgt → attrNameLst) plus its values (§19.5.1–§19.5.66).
- `p:bldP` (§19.5.12) is written per (text shape, grpId), as PowerPoint does; shapes without
  a text body (lines, pictures) get none.
- Preset ids are PowerPoint's preset-library numbers (see `EFFECTS`); PowerPoint uses them
  to label effects in the Animation pane, the XML behaviours drive playback.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from lxml import etree

_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_A = "http://schemas.openxmlformats.org/drawingml/2006/main"

#: Effect name → (presetClass, presetID, presetSubtype), as PowerPoint saves them.
EFFECTS: dict[str, tuple[str, int, int]] = {
    "appear": ("entr", 1, 0),
    "fade_in": ("entr", 10, 0),
    "disappear": ("exit", 1, 0),
    "fade_out": ("exit", 10, 0),
    "transparency": ("emph", 9, 0),
    "grow_shrink": ("emph", 6, 0),
    "fill_colour": ("emph", 1, 2),
    "motion_path": ("path", 0, 0),
}

# PowerPoint's default durations (ms) per effect.
_DEFAULT_MS = {
    "appear": 1,
    "disappear": 1,
    "fade_in": 500,
    "fade_out": 500,
    "transparency": 500,
    "grow_shrink": 2000,
    "fill_colour": 2000,
    "motion_path": 2000,
}

_PARAMS = {
    "appear": set(),
    "disappear": set(),
    "fade_in": set(),
    "fade_out": set(),
    "transparency": {"opacity"},
    "grow_shrink": {"scale"},
    "fill_colour": {"rgb", "scheme"},
    "motion_path": {"path"},
}

#: Scheme colour names a `fill_colour` may reference instead of a literal (ST_SchemeColorVal).
SCHEME_COLOURS = {"bg1", "tx1", "bg2", "tx2", "accent1", "accent2", "accent3", "accent4", "accent5",
                  "accent6", "hlink", "folHlink", "dk1", "lt1", "dk2", "lt2", "phClr"}

_PATH_TOKEN = re.compile(r"[MLCZEmlcze]|-?\d*\.?\d+(?:[eE]-?\d+)?")


def _p(tag: str, parent=None, **attrs):
    """Make a `p:` element (optionally appended to `parent`) with string attributes."""
    el = etree.Element(f"{{{_P}}}{tag}") if parent is None else etree.SubElement(parent, f"{{{_P}}}{tag}")
    for k, v in attrs.items():
        el.set(k, str(v))
    return el


class _Ids:
    """Sequential cTn id source (ST_TLTimeNodeID: unique per slide)."""

    def __init__(self) -> None:
        self.n = 0

    def __call__(self) -> int:
        self.n += 1
        return self.n


def _check(slide, steps) -> list[list[tuple[Any, str, dict]]]:
    """Validate steps against the slide and normalise entries to (shape, effect, params).

    Raises:
        ValueError: on an empty step, a shape not directly on `slide`, an unknown effect,
            an unknown or missing parameter, or an out-of-range value.
    """
    tree = slide.shapes._spTree
    out = []
    for n, step in enumerate(steps):
        if not step:
            raise ValueError(f"step {n} is empty: every click needs at least one effect")
        norm = []
        for entry in step:
            shape, effect, params = (*entry, {}) if len(entry) == 2 else entry
            params = dict(params or {})
            if shape._element.getparent() is not tree:
                raise ValueError(f"shape {shape.name!r} (step {n}) is not on this slide")
            if effect not in EFFECTS:
                raise ValueError(f"unknown effect {effect!r}; known: {sorted(EFFECTS)}")
            extra = set(params) - _PARAMS[effect] - {"duration_ms"}
            if extra:
                raise ValueError(f"{effect} does not take {sorted(extra)}")
            dur = params.setdefault("duration_ms", _DEFAULT_MS[effect])
            if not isinstance(dur, int) or dur < 1:
                raise ValueError(f"duration_ms must be a positive int, got {dur!r}")
            _check_params(effect, params)
            norm.append((shape, effect, params))
        out.append(norm)
    return out


def _check_params(effect: str, params: dict) -> None:
    """Raise ValueError when an effect's required parameter is missing or out of range."""
    if effect == "transparency":
        op = params.get("opacity")
        if not isinstance(op, (int, float)) or not 0 <= op <= 1:
            raise ValueError(f"transparency needs opacity in [0, 1], got {op!r}")
    elif effect == "grow_shrink":
        sc = params.get("scale")
        if not isinstance(sc, (int, float)) or sc <= 0:
            raise ValueError(f"grow_shrink needs scale > 0, got {sc!r}")
    elif effect == "fill_colour":
        rgb = params.get("rgb")
        if not isinstance(rgb, str) or not re.fullmatch(r"[0-9A-Fa-f]{6}", rgb):
            raise ValueError(f"fill_colour needs rgb as 6 hex digits, got {rgb!r}")
        if params.get("scheme") is not None and params["scheme"] not in SCHEME_COLOURS:
            raise ValueError(f"fill_colour scheme must be one of {sorted(SCHEME_COLOURS)}, got {params['scheme']!r}")
    elif effect == "motion_path":
        path = params.get("path")
        if not isinstance(path, str) or not path.strip().startswith("M"):
            raise ValueError(f"motion_path needs a path starting with 'M', got {path!r}")
        if "".join(_PATH_TOKEN.findall(path)).replace(" ", "") != re.sub(r"\s+", "", path):
            raise ValueError(f"motion_path path has unsupported tokens: {path!r}")


def _cbhvr(parent, ids: _Ids, spid: int, dur: int, attrs: Sequence[str] = (), delay: int | None = None, **cb):
    """Append `p:cBhvr` (cTn, tgtEl/spTgt, attrNameLst) to a behaviour element."""
    cbhvr = _p("cBhvr", parent, **cb)
    ctn = _p("cTn", cbhvr, id=ids(), dur=dur, fill="hold")
    if delay is not None:
        _p("cond", _p("stCondLst", ctn), delay=delay)
    _p("spTgt", _p("tgtEl", cbhvr), spid=spid)
    if attrs:
        lst = _p("attrNameLst", cbhvr)
        for a in attrs:
            _p("attrName", lst).text = a
    return cbhvr


def _set(parent, ids, spid, attr: str, val: str, dur: int = 1, delay: int | None = 0):
    """Append a `p:set` of `attr` to the string `val`."""
    s = _p("set", parent)
    _cbhvr(s, ids, spid, dur, [attr], delay=delay)
    _p("strVal", _p("to", s), val=val)


def _behaviours(lst, ids: _Ids, spid: int, effect: str, params: dict) -> None:
    """Append the behaviour elements PowerPoint writes for `effect` to childTnLst `lst`."""
    dur = params["duration_ms"]
    if effect in ("appear", "fade_in"):
        _set(lst, ids, spid, "style.visibility", "visible")
        if effect == "fade_in":
            fx = _p("animEffect", lst, transition="in", filter="fade")
            _cbhvr(fx, ids, spid, dur)
    elif effect == "disappear":
        _set(lst, ids, spid, "style.visibility", "hidden", delay=dur - 1 if dur > 1 else 0)
    elif effect == "fade_out":
        fx = _p("animEffect", lst, transition="out", filter="fade")
        _cbhvr(fx, ids, spid, dur)
        _set(lst, ids, spid, "style.visibility", "hidden", delay=dur - 1)
    elif effect == "transparency":
        op = f"{params['opacity']:g}"
        _set(lst, ids, spid, "style.opacity", op, dur=dur, delay=None)
        fx = _p("animEffect", lst, filter="image", prLst=f"opacity: {op}")
        _cbhvr(fx, ids, spid, dur, rctx="IE")
    elif effect == "grow_shrink":
        sc = _p("animScale", lst)
        _cbhvr(sc, ids, spid, dur)
        pct = round(params["scale"] * 100000)
        _p("by", sc, x=pct, y=pct)
    elif effect == "fill_colour":
        clr = _p("animClr", lst, clrSpc="rgb", dir="cw")
        _cbhvr(clr, ids, spid, dur, ["fillcolor"])
        to = _p("to", clr)
        if params.get("scheme"):  # a theme colour stays a theme reference (re-themes with the deck)
            etree.SubElement(to, f"{{{_A}}}schemeClr").set("val", params["scheme"])
        else:
            etree.SubElement(to, f"{{{_A}}}srgbClr").set("val", params["rgb"].upper())
        _set(lst, ids, spid, "fill.type", "solid", dur=dur, delay=None)
        _set(lst, ids, spid, "fill.on", "true", dur=dur, delay=None)
    elif effect == "motion_path":
        path = params["path"].strip()
        mo = _p("animMotion", lst, origin="layout", path=path, pathEditMode="relative", rAng=0)
        nums = [float(t) for t in _PATH_TOKEN.findall(path) if t not in "MLCZEmlcze"]
        cmds = [t for t in _PATH_TOKEN.findall(path) if t in "MLCZEmlcze"]
        if set(cmds) <= {"M", "L", "E", "Z"} and len(nums) % 2 == 0:
            mo.set("ptsTypes", "A" * (len(nums) // 2))
        _cbhvr(mo, ids, spid, dur, ["ppt_x", "ppt_y"])
        if nums:
            xs, ys = nums[0::2], nums[1::2]
            _p("rCtr", mo, x=round((min(xs) + max(xs)) / 2 * 100000), y=round((min(ys) + max(ys)) / 2 * 100000))


def write_steps(slide, steps: Sequence[Sequence[tuple]]):
    """Write `steps` as the slide's click-by-click animation, replacing any existing timing.

    Args:
        slide: A python-pptx `Slide`.
        steps: Ordered clicks. Each step is a non-empty sequence of `(shape, effect)` or
            `(shape, effect, params)` entries; shapes must sit directly on `slide` (not in a
            group). Effects and params (all accept `duration_ms`, a positive int):

            - `appear`, `fade_in`: entrances.
            - `disappear`, `fade_out`: exits.
            - `transparency` (`opacity`: 0–1 end opacity), `grow_shrink` (`scale`: > 0, e.g.
              1.5 grows 150 %), `fill_colour` (`rgb`: `"RRGGBB"`; optional `scheme`: a scheme
              colour name such as `accent1`, written instead of the literal): emphasis.
            - `motion_path` (`path`: PowerPoint path string in slide-size fractions, relative
              to the shape, e.g. `"M 0 0 L 0.25 0 E"`).

    Returns:
        The written `p:timing` element, or None when `steps` is empty (any existing timing
        is then removed).

    Raises:
        ValueError: when a step is empty, a shape is not on this slide, or an effect or
            parameter is unknown or invalid. Nothing is written in that case.
    """
    norm = _check(slide, steps)
    sld = slide._element
    for old in sld.findall(f"{{{_P}}}timing"):
        sld.remove(old)
    if not norm:
        return None

    ids = _Ids()
    timing = _p("timing")
    root = _p("cTn", _p("par", _p("tnLst", timing)), id=ids(), dur="indefinite", restart="never", nodeType="tmRoot")
    seq = _p("seq", _p("childTnLst", root), concurrent=1, nextAc="seek")
    main = _p("cTn", seq, id=ids(), dur="indefinite", nodeType="mainSeq")
    clicks = _p("childTnLst", main)
    for lst, evt in (("prevCondLst", "onPrev"), ("nextCondLst", "onNext")):
        _p("sldTgt", _p("tgtEl", _p("cond", _p(lst, seq), evt=evt, delay=0)))

    grp_next: dict[int, int] = defaultdict(int)
    builds: list[tuple[int, int]] = []
    for step in norm:
        click = _p("cTn", _p("par", clicks), id=ids(), fill="hold")
        _p("cond", _p("stCondLst", click), delay="indefinite")
        group = _p("cTn", _p("par", _p("childTnLst", click)), id=ids(), fill="hold")
        _p("cond", _p("stCondLst", group), delay=0)
        effects = _p("childTnLst", group)
        for i, (shape, effect, params) in enumerate(step):
            spid = shape.shape_id
            grp = grp_next[spid]
            grp_next[spid] += 1
            cls, pid, sub = EFFECTS[effect]
            ctn = _p(
                "cTn",
                _p("par", effects),
                id=ids(),
                presetID=pid,
                presetClass=cls,
                presetSubtype=sub,
            )
            if effect == "motion_path":
                ctn.set("accel", "50000")
                ctn.set("decel", "50000")
            ctn.set("fill", "hold")
            ctn.set("grpId", str(grp))
            ctn.set("nodeType", "clickEffect" if i == 0 else "withEffect")
            _p("cond", _p("stCondLst", ctn), delay=0)
            _behaviours(_p("childTnLst", ctn), ids, spid, effect, params)
            if shape._element.find(f"{{{_P}}}txBody") is not None:
                builds.append((spid, grp))

    if builds:
        bld = _p("bldLst", timing)
        for spid, grp in builds:
            _p("bldP", bld, spid=spid, grpId=grp, animBg=1)

    ext = sld.find(f"{{{_P}}}extLst")
    if ext is not None:
        ext.addprevious(timing)
    else:
        sld.append(timing)
    return timing
