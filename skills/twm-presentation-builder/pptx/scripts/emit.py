# /// script
# requires-python = ">=3.12"
# dependencies = ["python-pptx>=1.0.2", "lxml>=5", "playwright>=1.49"]
# ///
"""Emit an editable PowerPoint file from a deck's PPTX scene (``pptx/scripts/scene.py``).

The target is an **editable hand-off**, not pixel fidelity: native text in placeholders of named
layouts, theme colours and fonts from the design tokens, named native shapes, speaker notes, and
build steps as native animations. Contract: ``pptx/PPTX.md`` (pipeline, bands, step policy);
input schema: ``pptx/scene.schema.json``.

Usage (run from the skill folder)::

    uv run pptx/scripts/emit.py deck.html [-o deck.pptx]        # measures first (needs Chrome)
    uv run pptx/scripts/emit.py deck.scene.json [-o deck.pptx]

or, imported: ``emit(scene_or_path, out) -> Path``. Writes ``<name>.pptx`` and the sidecar
``<name>.pptx-report.json`` (every approximated or dropped item); from a deck it also writes the
measured ``<name>.scene.json`` beside the output, so ``check.py`` can compare against it.

**Seed template, generated per theme.** python-pptx cannot create layouts, so the emitter starts
from python-pptx's default template, sets the slide to 16:9 widescreen (13.333 × 7.5 in; the
scene's px scale uniformly), writes the theme ``a:clrScheme``/``a:fontScheme`` from
``scripts/tokens.py pptx`` (the scene's palette and fonts when the tokens are not found), and
rewrites the master and six layouts in place with lxml (the other default layouts are dropped):

==================== ======================================================================
Layout               Placeholders (name: type, idx)
==================== ======================================================================
Title / lead         Title: ctrTitle · Subtitle: subTitle 1 · Kicker: body 10 · Byline: body 11
Standard             Title · Kicker: body 10 · Body: obj 1
Split                Title · Kicker: body 10 · Left: obj 1 · Right: obj 2
Three-column scene   Title · Kicker: body 10 · Steps: obj 1 · Scene: pic 13
Tile row             Title · Kicker: body 10 · Tile 1–3: obj 1–3 (round-rect cards)
End                  Title: ctrTitle
==================== ======================================================================

Placeholder geometry and text styles come from the scene (the first slide of each kind), so a
colleague adding a slide gets the deck's look; slide placeholders override position only where
the measured content differs.

**Roles → PowerPoint** (one slide per HTML slide; a scene camera move starts a duplicate slide
with a Morph transition and ``!!``-named shapes, per the PRD step-delta policy):

- title, kicker, lead subtitle/byline → their placeholders; body flow text (paragraphs, points,
  steps, prompts, stat, quote, cite, caption) → the body placeholder(s) as paragraphs, list
  markers as native bullets/autonumbers;
- cards (insight, narration, message, pop-over panel, tile-row card, annotation, term) → named
  round rectangles holding their text (generated labels and quote marks merged in);
- diagram tiles → named ``roundRect`` with their labels as paragraphs; edges → straight
  connectors or ``cubicBezTo`` freeforms with ``a:tailEnd`` arrowheads; SVG labels → text boxes;
- inline SVG illustrations (an ``image`` with measured primitives and no raster source, e.g.
  pop-over art inside a card) → named native shapes with their words as text boxes, never dropped
  with the card that holds them; their style effects (opacity, lift) are applied and reported;
- tables → native tables (split into stacked tables where rows build on separate steps);
- orbs (bokeh) → radial-gradient ellipses with soft edges, marked decorative;
- every colour with a palette role → ``a:schemeClr`` (a role-less mix → a theme colour with
  ``a:tint``; else a literal, reported); fonts → ``+mj-lt``/``+mn-lt``.

**Effects by band** (style tokens' ``com.twm.pptx`` band, carried by the scene): shadow and SVG
lift → ``a:outerShdw`` (inset lost); frost → translucent fill (backdrop blur lost); bokeh blur →
``a:softEdge``; opacity → ``a:alpha``; anything ``lost`` is dropped and reported.

**Steps** → ``animations.write_steps`` (PB-022): one click per HTML step, in order; an element
inside a placeholder builds by paragraph (``p:txEl/p:pRg``, ``bldP build="p"``). Unsupported
deltas: camera → Morph slide; text/stroke colour, marker fills on bullets and filter softening →
dropped (the slide keeps its measured look) and reported.

Exit codes: 0 written, 1 refused (invalid scene, unreadable deck); messages on stderr.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

from lxml import etree
from pptx import Presentation
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.oxml import oxml_parser, parse_xml
from pptx.util import Emu

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parents[1]
SCHEMA_PATH = HERE.parent / "scene.schema.json"
TOKENS_PY = SKILL_DIR / "scripts" / "tokens.py"
REPORT_SCHEMA = "pb-pptx-report/1"

SLIDE_W, SLIDE_H = 12192000, 6858000  # 16:9 widescreen, EMU
LAYOUTS = ("Title / lead", "Standard", "Split", "Three-column scene", "Tile row", "End")

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "p14": "http://schemas.microsoft.com/office/powerpoint/2010/main",
    "p159": "http://schemas.microsoft.com/office/powerpoint/2015/09/main",
    "adec": "http://schemas.microsoft.com/office/drawing/2017/decorative",
}
_A, _P, _R = (f"{{{NS[k]}}}" for k in ("a", "p", "r"))
NSDECL = f'xmlns:a="{NS["a"]}" xmlns:r="{NS["r"]}" xmlns:p="{NS["p"]}"'
#: Theme slot → the scheme colour name slides use (through the master's p:clrMap).
SLOT_ALIAS = {"dk1": "tx1", "lt1": "bg1", "dk2": "tx2", "lt2": "bg2"}
DECORATIVE_URI = "{C183D7F6-B498-43B3-948B-1728B52AA6E4}"
NO_STYLE_TABLE = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"  # "No Style, No Grid"

FLOW = {"paragraph", "point", "step-item", "prompt", "stat", "quote", "cite", "caption", "heading",
        "byline", "message", "sender", "term-title", "term-text", "generated-text", "label", "tag"}
CARDS = {"insight", "overlay", "message-card", "narration-tile", "pop-panel", "tile-card",
         "annotation", "term"}
DIAGRAM_PARTS = {"tile", "key-tile", "edge", "label", "tag", "shape"}
CONTAINERS = {"body", "scene", "diagram", "popover", "table"}


class EmitError(Exception):
    """A refusal: invalid scene or unreadable deck."""


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _scene_mod():
    return sys.modules.get("pb_emit_scene") or _load("pb_emit_scene", HERE / "scene.py")


def _anim_mod():
    return sys.modules.get("pb_emit_animations") or _load("pb_emit_animations", HERE / "animations.py")


# ---------- small XML helpers ----------

def _el(tag: str, parent=None, **attrs):
    """Make a namespaced element (``"a:solidFill"``), optionally appended to ``parent``."""
    pfx, local = tag.split(":")
    qn = f"{{{NS[pfx]}}}{local}"
    e = oxml_parser.makeelement(qn, nsmap={pfx: NS[pfx]}) if parent is None else etree.SubElement(parent, qn)
    for k, v in attrs.items():
        e.set(k, str(v))
    return e


def _parse(xml: str):
    """Parse with python-pptx's parser, so its element classes (and proxies) work on the result."""
    return parse_xml(xml)


@dataclass
class Geo:
    """Scene px → EMU / hundredths of a point, uniform scale onto a 16:9 slide."""

    width: int
    height: int

    @property
    def k(self) -> float:
        return SLIDE_W / self.width

    def emu(self, px: float) -> int:
        return int(round(px * self.k))

    def pt100(self, px: float) -> int:
        return int(round(px * self.k / 12700 * 100))

    def box(self, b: dict) -> tuple[int, int, int, int]:
        return self.emu(b["x"]), self.emu(b["y"]), max(self.emu(b["w"]), 1), max(self.emu(b["h"]), 1)


# ---------- colours ----------

class Colours:
    """Map scene colours to theme references: palette role → scheme slot."""

    def __init__(self, scene: dict, report: "Report"):
        self.pal = scene["palette"]
        self.report = report
        self.by_rgb = {}
        for role, v in self.pal.items():
            self.by_rgb.setdefault(v["rgb"], role)

    def slot(self, role: str) -> str:
        s = self.pal[role]["slots"][0]
        return SLOT_ALIAS.get(s, s)

    def element(self, colour: dict | None, opacity: float = 1.0, where=None):
        """Return an ``a:schemeClr``/``a:srgbClr`` element for a scene colour (alpha applied)."""
        if colour is None:
            return None
        alpha = max(0.0, min(1.0, colour.get("alpha", 1.0) * opacity))
        role = colour.get("role") or self.by_rgb.get(colour["rgb"])
        tint = None
        if role is None or role not in self.pal:
            role, tint = self._tint(colour["rgb"])
            if role is not None and where:
                self.report.add(where[0], where[1], "colour mix", "approximated",
                                f"#{colour['rgb']} → theme {self.slot(role)} tint {tint / 1000:.0f}%")
        if role is not None:
            c = _el("a:schemeClr", val=self.slot(role))
            if tint is not None:
                _el("a:tint", c, val=tint)
        else:
            c = _el("a:srgbClr", val=colour["rgb"])
            if where:
                self.report.add(where[0], where[1], "literal colour", "approximated",
                                f"#{colour['rgb']} has no theme slot: kept literal")
        if alpha < 0.999:
            _el("a:alpha", c, val=int(round(alpha * 100000)))
        return c

    def _tint(self, rgb: str):
        """Find palette colour c and t with rgb ≈ t·c + (1 − t)·white (DrawingML ``a:tint``)."""
        tgt = [int(rgb[i:i + 2], 16) for i in (0, 2, 4)]
        best = (None, None, 1e9)
        for role, v in self.pal.items():
            c = [int(v["rgb"][i:i + 2], 16) for i in (0, 2, 4)]
            ts = [(255 - t) / (255 - ci) for t, ci in zip(tgt, c) if ci < 250]
            if not ts:
                continue
            t = sum(ts) / len(ts)
            if not 0.02 <= t <= 1:
                continue
            err = max(abs(t * ci + (1 - t) * 255 - ti) for ci, ti in zip(c, tgt))
            if err < best[2]:
                best = (role, int(round(t * 100000)), err)
        return (best[0], best[1]) if best[2] <= 8 else (None, None)

    def fill(self, colour, opacity=1.0, where=None):
        if colour is None or colour.get("alpha", 1) * opacity <= 0.001:
            return _el("a:noFill")
        f = _el("a:solidFill")
        f.append(self.element(colour, opacity, where))
        return f


# ---------- report ----------

class Report:
    """Collects every approximated, lost or dropped item for the sidecar JSON."""

    def __init__(self):
        self.items: list[dict] = []
        self._seen = set()
        self.slides: list[dict] = []

    def add(self, slide, el, what, result, how, band=None, token=None):
        key = (slide, el, what)
        if key in self._seen:
            return
        self._seen.add(key)
        self.items.append({"slide": slide, "el": el, "what": what, "band": band, "token": token,
                           "result": result, "how": how})


# ---------- text ----------

@dataclass
class Para:
    """One paragraph: runs plus layout (px values, converted when written)."""

    runs: list[dict]
    align: str = "left"
    line: float | None = None
    before: float = 0.0
    bullet: tuple | None = None     # ("num", start, colour) | ("char", ch, colour)
    mar: float = 0.0
    els: list[str] = field(default_factory=list)


class Text:
    """Writes runs and paragraphs as DrawingML with theme font and colour references."""

    def __init__(self, scene: dict, geo: Geo, colours: Colours, slide_part=None):
        f = scene.get("fonts") or {}
        self.major = (f.get("major") or "").lower()
        self.minor = (f.get("minor") or "").lower()
        self.geo, self.colours, self.part = geo, colours, slide_part

    def font_ref(self, font: str) -> str:
        low = (font or "").lower()
        if self.major and low == self.major:
            return "+mj-lt"
        if self.minor and low == self.minor:
            return "+mn-lt"
        return font or "+mn-lt"

    def rpr(self, run: dict, tag="a:rPr", opacity=1.0, where=None):
        r = _el(tag, lang="en-GB", sz=max(100, self.geo.pt100(run["size"])))
        if run["weight"] >= 600:
            r.set("b", "1")
        if run["italic"]:
            r.set("i", "1")
        if run["underline"] and not run.get("href"):
            r.set("u", "sng")
        if run["caps"]:
            r.set("cap", "all")
        if abs(run["tracking"]) > 0.01:
            r.set("spc", str(self.geo.pt100(run["tracking"])))
        r.set("dirty", "0")
        if run.get("colour"):
            fill = _el("a:solidFill", r)
            fill.append(self.colours.element(run["colour"], opacity, where))
        _el("a:latin", r, typeface=self.font_ref(run["font"]))
        if run.get("href") and self.part is not None and tag == "a:rPr":
            rid = self.part.relate_to(run["href"], RT.HYPERLINK, is_external=True)
            _el("a:hlinkClick", r).set(f"{_R}id", rid)
        return r

    def paragraph(self, para: Para, opacity=1.0, where=None):
        p = _el("a:p")
        algn = {"left": "l", "center": "ctr", "right": "r", "justify": "just"}.get(para.align, "l")
        ppr = _el("a:pPr", p, algn=algn)
        if para.bullet:
            ppr.set("marL", str(self.geo.emu(para.mar)))
            ppr.set("indent", str(-self.geo.emu(para.mar)))
        else:
            ppr.set("marL", "0")
            ppr.set("indent", "0")
        if para.line:
            _el("a:spcPts", _el("a:lnSpc", ppr), val=self.geo.pt100(para.line))
        _el("a:spcPts", _el("a:spcBef", ppr), val=self.geo.pt100(max(0.0, para.before)))
        if para.bullet:
            kind, val, colour = para.bullet
            if colour is not None:
                _el("a:buClr", ppr).append(self.colours.element(colour, 1.0, where))
            if kind == "num":
                _el("a:buFont", ppr, typeface="+mn-lt")
                bu = _el("a:buAutoNum", ppr, type="arabicPlain")
                if val and val != 1:
                    bu.set("startAt", str(val))
            else:
                _el("a:buChar", ppr, char=val)
        else:
            _el("a:buNone", ppr)
        for i, run in enumerate(para.runs):
            prev = para.runs[i - 1] if i else None
            if prev and not prev["text"][-1:].isspace() and not run["text"][:1].isspace() and \
                    max(prev["size"], run["size"]) >= 1.5 * min(prev["size"], run["size"]):
                # a block-level run (e.g. a stat's figure over its label): keep the line break
                _el("a:br", p).append(self.rpr(run, opacity=opacity))
            r = _el("a:r", p)
            r.append(self.rpr(run, opacity=opacity, where=where))
            _el("a:t", r).text = run["text"]
        if para.runs:
            p.append(self.rpr(para.runs[-1], tag="a:endParaRPr", opacity=opacity))
        return p

    def body(self, paras: list[Para], tag="p:txBody", insets=(0, 0, 0, 0), anchor="t", wrap="square",
             autofit="none", opacity=1.0, where=None):
        tb = _el(tag)
        l, t, r, b = (self.geo.emu(max(0.0, v)) for v in insets)
        bp = _el("a:bodyPr", tb, wrap=wrap, lIns=l, tIns=t, rIns=r, bIns=b, anchor=anchor, rtlCol="0")
        if autofit == "shape":
            _el("a:spAutoFit", bp)
        else:
            _el("a:noAutofit", bp)
        _el("a:lstStyle", tb)
        for para in paras or [Para(runs=[])]:
            tb.append(self.paragraph(para, opacity, where))
        return tb


def _is_vector_art(e: dict) -> bool:
    """True for an inline SVG image (no raster source) whose primitives were measured."""
    return e["role"] == "image" and bool(e.get("svg")) and not (e.get("image") or {}).get("src")


def _el_text(e: dict) -> str:
    return "".join(r["text"] for r in e["text"]["runs"]) if e.get("text") else ""


# ---------- effects ----------

_LOST_HOW = {"backdrop-blur": "no backdrop blur in PowerPoint: translucent fill only",
             "blur": "no live blur on shapes", "filter": "CSS filter dropped", "svg-filter": "SVG filter dropped",
             "shadow": "shadow dropped", "opacity": "opacity dropped"}

_LAYER = re.compile(r"(rgba?\([^)]*\)|color\(srgb[^)]*\)|#[0-9a-fA-F]{3,8})\s+((?:-?[\d.]+px\s*){2,4})(inset)?")


_CSS_COLOUR = re.compile(r"color\(srgb[^)]*\)|rgba?\([^)]*\)|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b")


def _css_colour(text: str) -> tuple[str, float] | None:
    """The first CSS colour in ``text`` (``color(srgb …)``, ``rgb()``/``rgba()``, hex) as (RRGGBB, alpha)."""
    m = _CSS_COLOUR.search(text or "")
    if not m:
        return None
    c = m.group(0)
    if c.startswith("color("):
        parts = [float(x) for x in re.findall(r"[\d.]+", c.split("srgb", 1)[1])]
        return "".join(f"{round(v * 255):02X}" for v in parts[:3]), (parts[3] if len(parts) > 3 else 1.0)
    if c.startswith("rgb"):
        parts = [float(x) for x in re.findall(r"[\d.]+", c)]
        return "".join(f"{int(v):02X}" for v in parts[:3]), (parts[3] if len(parts) > 3 else 1.0)
    h = c.lstrip("#")
    h = "".join(ch * 2 for ch in h) if len(h) == 3 else h
    return h.upper(), 1.0


def _parse_shadow(value: str) -> dict | None:
    """First non-inset layer of a CSS box-shadow: colour, x, y, blur, spread (px)."""
    for layer in re.split(r",\s*(?![^()]*\))", value or ""):
        if "inset" in layer:
            continue
        m = _LAYER.search(layer)
        if not m:
            continue
        nums = [float(n) for n in re.findall(r"-?[\d.]+", m.group(2))] + [0, 0]
        rgb, alpha = _css_colour(m.group(1))
        return {"rgb": rgb, "alpha": alpha, "x": nums[0], "y": nums[1], "blur": nums[2], "spread": nums[3]}
    return None


# ---------- the seed template ----------

def theme_schemes(scene: dict) -> tuple[str, str]:
    """``a:clrScheme`` and ``a:fontScheme`` XML: from the tokens, else from the scene."""
    d = scene["deck"]
    if d.get("palette") and d.get("style") and TOKENS_PY.is_file():
        try:
            tok = sys.modules.get("pb_emit_tokens") or _load("pb_emit_tokens", TOKENS_PY)
            theme = tok.load(d["palette"], d["style"])
            return tok.clr_scheme(theme), tok.font_scheme(theme)
        except Exception:  # noqa: BLE001 — unknown names fall back to the scene's own values
            pass
    order = ("dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6",
             "hlink", "folHlink")
    by_slot = {s: v["rgb"] for v in scene["palette"].values() for s in v["slots"]}
    missing = [s for s in order if s not in by_slot]
    if missing:
        raise EmitError(f"palette does not fill theme slots {missing}")
    name = quoteattr(d.get("palette") or "deck")
    clr = [f'<a:clrScheme xmlns:a="{NS["a"]}" name={name}>']
    clr += [f'<a:{s}><a:srgbClr val="{by_slot[s]}"/></a:{s}>' for s in order] + ["</a:clrScheme>"]
    f = scene.get("fonts") or {}
    font = [f'<a:fontScheme xmlns:a="{NS["a"]}" name={quoteattr(d.get("style") or "deck")}>']
    for slot, fam in (("major", f.get("major") or "Calibri Light"), ("minor", f.get("minor") or "Calibri")):
        font.append(f'<a:{slot}Font><a:latin typeface={quoteattr(fam)}/><a:ea typeface=""/><a:cs typeface=""/></a:{slot}Font>')
    font.append("</a:fontScheme>")
    return "".join(clr), "".join(font)


def _first(scene, pred):
    for s in scene["slides"]:
        for e in s["elements"]:
            if pred(s, e):
                return s, e
    return None, None


def _is_lead(s):
    return "slide--lead" in s["classes"] and "slide--end" not in s["classes"]


def _is_end(s):
    return "slide--end" in s["classes"]


def frames_from(scene: dict) -> dict[str, dict[str, dict]]:
    """Placeholder boxes (scene px) per layout, measured from the first slide of each kind."""
    W, H = scene["size"]["width"], scene["size"]["height"]
    std = lambda s: not _is_lead(s) and not _is_end(s)  # noqa: E731
    _, kick = _first(scene, lambda s, e: std(s) and e["role"] == "kicker")
    _, title = _first(scene, lambda s, e: std(s) and e["role"] == "title")
    pad = kick["box"]["x"] if kick else round(W * 0.07)
    kick_b = dict(kick["box"]) if kick else {"x": pad, "y": round(H * 0.1), "w": W - 2 * pad, "h": 20}
    kick_b["h"] = max(kick_b["h"], 28)
    titles = [e for s in scene["slides"] if std(s) for e in s["elements"] if e["role"] == "title"]
    title_b = dict(title["box"]) if title else {"x": pad, "y": kick_b["y"] + 45, "w": W - 2 * pad, "h": 120}
    title_b["w"] = max(e["box"]["w"] for e in titles) if titles else title_b["w"]
    title_b["h"] = max([e["box"]["h"] for e in titles] + [title_b["h"]])
    bodies = [e for s in scene["slides"] if std(s) for e in s["elements"] if e["role"] == "body"]
    bottom = max([e["box"]["y"] + e["box"]["h"] for e in bodies] + [H * 0.9])
    top = title_b["y"] + title_b["h"] + 24
    body = {"x": pad, "y": top, "w": W - 2 * pad, "h": bottom - top}
    gap = round(W * 0.03)
    half = (body["w"] - gap) / 2
    left = {**body, "w": half}
    right = {**body, "x": body["x"] + half + gap, "w": half}

    out = {
        "Standard": {"title": title_b, "kicker": kick_b, "body1": body},
        "Split": {"title": title_b, "kicker": kick_b, "body1": left, "body2": right},
    }
    s_scene, sc = _first(scene, lambda s, e: e["role"] == "scene" and s["scene"] == "live")
    col = {**body, "w": body["w"] * 0.28}
    pic = {**body, "x": body["x"] + body["w"] * 0.31, "w": body["w"] * 0.38}
    if s_scene:
        b = next((e for e in s_scene["elements"] if e["role"] == "body"), None)
        if b:
            col = {**body, "x": b["box"]["x"], "w": b["box"]["w"]}
        pic = {**body, "x": sc["box"]["x"], "w": sc["box"]["w"]}
    out["Three-column scene"] = {"title": title_b, "kicker": kick_b, "body1": col, "pic13": pic}
    s_tiles, _ = _first(scene, lambda s, e: e["role"] == "tile-card")
    third = (body["w"] - 2 * gap) / 3
    tiles = [{"x": body["x"] + i * (third + gap), "y": body["y"] + body["h"] * 0.3, "w": third, "h": body["h"] * 0.3}
             for i in range(3)]
    if s_tiles:
        cards = sorted((e for e in s_tiles["elements"] if e["role"] == "tile-card"), key=lambda e: e["box"]["x"])
        for i, c in enumerate(cards[:3]):
            tiles[i] = dict(c["box"])
    out["Tile row"] = {"title": title_b, "kicker": kick_b, **{f"body{i + 1}": t for i, t in enumerate(tiles)}}

    s_lead = next((s for s in scene["slides"] if _is_lead(s)), None)
    lead = {"title": {"x": pad, "y": H * 0.35, "w": W * 0.55, "h": H * 0.2},
            "kicker": {"x": pad, "y": H * 0.3, "w": W - 2 * pad, "h": 28},
            "body1": {"x": pad, "y": H * 0.6, "w": W * 0.5, "h": H * 0.12},
            "body11": {"x": pad, "y": H * 0.88, "w": W * 0.4, "h": 30}}
    if s_lead:
        for e in s_lead["elements"]:
            key = {"title": "title", "kicker": "kicker", "body": "body1", "byline": "body11"}.get(e["role"])
            if key and e["parent"] is None:
                lead[key] = dict(e["box"])
    lead["kicker"]["h"] = max(lead["kicker"]["h"], 28)
    out["Title / lead"] = lead
    s_end = next((s for s in scene["slides"] if _is_end(s)), None)
    end = {"title": {"x": W * 0.2, "y": H * 0.42, "w": W * 0.6, "h": H * 0.16}}
    if s_end:
        t = next((e for e in s_end["elements"] if e["role"] == "title"), None)
        if t:
            end["title"] = dict(t["box"])
    out["End"] = end
    return out


def _style_runs(scene: dict) -> dict[str, dict]:
    """A sample run per text kind, for layout and master text styles."""
    want = {"title": ("title",), "kicker": ("kicker",), "body": ("paragraph", "point", "step-item"),
            "byline": ("byline",), "tile": ("heading",)}
    out = {}
    for kind, roles in want.items():
        _, e = _first(scene, lambda s, e: e["role"] in roles and e.get("text") and not _is_lead(s) or
                      (kind == "byline" and e["role"] == "byline"))
        if e and e.get("text"):
            out[kind] = e["text"]["runs"][0] | {"line": e["text"]["line_height"]}
    return out


class Seed:
    """Builds the seed template in place on a fresh python-pptx Presentation."""

    PH = {  # layout → [(key, name, ph attrs, style kind)]
        "Title / lead": [("title", "Title", 'type="ctrTitle"', "title"), ("body1", "Subtitle", 'type="subTitle" idx="1"', "body"),
                         ("kicker", "Kicker", 'type="body" sz="quarter" idx="10"', "kicker"),
                         ("body11", "Byline", 'type="body" sz="quarter" idx="11"', "byline")],
        "Standard": [("title", "Title", 'type="title"', "title"), ("kicker", "Kicker", 'type="body" sz="quarter" idx="10"', "kicker"),
                     ("body1", "Body", 'idx="1"', "body")],
        "Split": [("title", "Title", 'type="title"', "title"), ("kicker", "Kicker", 'type="body" sz="quarter" idx="10"', "kicker"),
                  ("body1", "Left", 'sz="half" idx="1"', "body"), ("body2", "Right", 'sz="half" idx="2"', "body")],
        "Three-column scene": [("title", "Title", 'type="title"', "title"),
                               ("kicker", "Kicker", 'type="body" sz="quarter" idx="10"', "kicker"),
                               ("body1", "Steps", 'sz="quarter" idx="1"', "body"), ("pic13", "Scene", 'type="pic" idx="13"', None)],
        "Tile row": [("title", "Title", 'type="title"', "title"), ("kicker", "Kicker", 'type="body" sz="quarter" idx="10"', "kicker"),
                     ("body1", "Tile 1", 'sz="quarter" idx="1"', "tile"), ("body2", "Tile 2", 'sz="quarter" idx="2"', "tile"),
                     ("body3", "Tile 3", 'sz="quarter" idx="3"', "tile")],
        "End": [("title", "Title", 'type="ctrTitle"', "title")],
    }
    TYPE = {"Title / lead": "title", "Standard": "obj", "Split": "twoObj", "Three-column scene": "cust",
            "Tile row": "cust", "End": "titleOnly"}
    PROMPT = {"title": "Click to edit title", "kicker": "Kicker", "body": "Click to add text", "byline": "Byline",
              "tile": "Tile heading", None: "Picture"}

    def __init__(self, scene: dict, geo: Geo, colours: Colours):
        self.scene, self.geo, self.colours = scene, geo, colours
        self.frames = frames_from(scene)
        self.runs = _style_runs(scene)
        tiles = [e for s in scene["slides"] for e in s["elements"] if e["role"] == "tile-card"]
        self.tile_look = tiles[0] if tiles else None

    # -- text styles --
    def _defrpr(self, kind: str, tag: str = "a:defRPr") -> str:
        run = self.runs.get(kind) or self.runs.get("body")
        font = "+mj-lt" if kind == "title" else "+mn-lt"
        if not run:
            return f'<{tag} sz="1800"><a:solidFill><a:schemeClr val="tx1"/></a:solidFill><a:latin typeface="{font}"/></{tag}>'
        f = self.scene.get("fonts") or {}
        if (run["font"] or "").lower() == (f.get("major") or "").lower():
            font = "+mj-lt"
        elif (run["font"] or "").lower() == (f.get("minor") or "").lower():
            font = "+mn-lt"
        attrs = f'sz="{max(100, self.geo.pt100(run["size"]))}"'
        attrs += ' b="1"' if run["weight"] >= 600 else ' b="0"'
        if run["caps"]:
            attrs += ' cap="all"'
        if abs(run["tracking"]) > 0.01:
            attrs += f' spc="{self.geo.pt100(run["tracking"])}"'
        clr = etree.tostring(self.colours.element(run["colour"])).decode() if run.get("colour") else \
            '<a:schemeClr val="tx1"/>'
        clr = re.sub(r'\sxmlns:a="[^"]+"', "", clr)
        return f'<{tag} {attrs}><a:solidFill>{clr}</a:solidFill><a:latin typeface="{font}"/></{tag}>'

    def _lvl(self, kind: str, n: int = 1, algn: str = "l") -> str:
        run = self.runs.get(kind) or {}
        line = f'<a:lnSpc><a:spcPts val="{self.geo.pt100(run["line"])}"/></a:lnSpc>' if run.get("line") else \
            '<a:lnSpc><a:spcPct val="100000"/></a:lnSpc>'
        return (f'<a:lvl{n}pPr marL="0" indent="0" algn="{algn}">{line}<a:spcBef><a:spcPts val="0"/></a:spcBef>'
                f'<a:buNone/>{self._defrpr(kind)}</a:lvl{n}pPr>')

    # -- parts --
    def _sp(self, sid: int, name: str, ph: str, box: dict, kind, algn="l", anchor="t", extra_sppr="") -> str:
        x, y, w, h = self.geo.box(box)
        lst = self._lvl(kind, 1, algn) if kind else ""
        prompt = escape(self.PROMPT[kind])
        return (f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="{escape(name)}"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>'
                f'<p:nvPr><p:ph {ph}/></p:nvPr></p:nvSpPr><p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>'
                f'{extra_sppr}</p:spPr><p:txBody><a:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" anchor="{anchor}">'
                f'<a:noAutofit/></a:bodyPr><a:lstStyle>{lst}</a:lstStyle><a:p><a:r><a:rPr lang="en-GB"/><a:t>{prompt}</a:t>'
                f'</a:r></a:p></p:txBody></p:sp>')

    def _tile_sppr(self) -> str:
        t = self.tile_look
        if not t:
            return ""
        fill = etree.tostring(self.colours.fill(t["fill"])).decode()
        adj = min(50000, round((t["radius"] or 0) / max(1, min(t["box"]["w"], t["box"]["h"])) * 100000))
        geom = f'<a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val {adj}"/></a:avLst></a:prstGeom>'
        return re.sub(r'\sxmlns:a="[^"]+"', "", geom + fill)

    def _tree(self, shapes: list[str]) -> str:
        return ('<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr>'
                '<a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm>'
                f'</p:grpSpPr>{"".join(shapes)}</p:spTree>')

    def layout_xml(self, name: str) -> str:
        boxes = self.frames[name]
        shapes = []
        for n, (key, label, ph, kind) in enumerate(self.PH[name], start=2):
            algn = "ctr" if name == "End" else "l"
            extra = self._tile_sppr() if name == "Tile row" and key.startswith("body") else ""
            ins = ""
            if extra and self.tile_look:
                ins = extra
            shapes.append(self._sp(n, label, ph, boxes[key], kind, algn, "ctr" if name == "End" else "t", ins))
        return (f'<p:sldLayout {NSDECL} type="{self.TYPE[name]}" preserve="1"><p:cSld name="{escape(name)}">'
                f'{self._tree(shapes)}</p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>')

    def master_parts(self) -> tuple[str, str]:
        std = self.frames["Standard"]
        shapes = [self._sp(2, "Title", 'type="title"', std["title"], "title"),
                  self._sp(3, "Body", 'type="body" idx="1"', std["body1"], "body")]
        csld = (f'<p:cSld {NSDECL}><p:bg><p:bgRef idx="1001"><a:schemeClr val="bg1"/></p:bgRef></p:bg>'
                f'{self._tree(shapes)}</p:cSld>')
        styles = (f'<p:txStyles {NSDECL}><p:titleStyle>{self._lvl("title")}</p:titleStyle>'
                  f'<p:bodyStyle>{self._lvl("body")}{self._lvl("body", 2)}</p:bodyStyle>'
                  f'<p:otherStyle>{self._lvl("body")}</p:otherStyle></p:txStyles>')
        # master placeholders carry the style via txStyles, not their own lstStyle
        csld = re.sub(r"<a:lstStyle>.*?</a:lstStyle>", "<a:lstStyle/>", csld)
        return csld, styles

    def build(self) -> Presentation:
        prs = Presentation()
        prs.slide_width, prs.slide_height = Emu(SLIDE_W), Emu(round(self.scene["size"]["height"] * self.geo.k))
        master = prs.slide_master
        # theme
        theme = master.part.part_related_by(RT.THEME)
        root = etree.fromstring(theme.blob)
        clr, font = theme_schemes(self.scene)
        te = root.find("a:themeElements", NS)
        te.replace(te.find("a:clrScheme", NS), _parse(clr))
        te.replace(te.find("a:fontScheme", NS), _parse(font))
        d = self.scene["deck"]
        root.set("name", f"{d.get('palette') or 'deck'} · {d.get('style') or 'style'}")
        theme.blob = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
        # master
        m = master._element
        csld, styles = self.master_parts()
        m.replace(m.find("p:cSld", NS), _parse(csld))
        m.replace(m.find("p:txStyles", NS), _parse(styles))
        # layouts: rewrite the first six in place, drop the rest
        id_lst = m.find("p:sldLayoutIdLst", NS)
        entries = list(id_lst)
        for i, entry in enumerate(entries):
            rid = entry.get(f"{_R}id")
            part = master.part.related_part(rid)
            if i < len(LAYOUTS):
                new = _parse(self.layout_xml(LAYOUTS[i]))
                el = part._element
                for k in list(el.attrib):
                    del el.attrib[k]
                for k, v in new.attrib.items():
                    el.set(k, v)
                for c in list(el):
                    el.remove(c)
                for c in list(new):
                    el.append(c)
            else:
                id_lst.remove(entry)
                master.part.drop_rel(rid)
        return prs


# ---------- per-slide model ----------

@dataclass
class Target:
    """Where an element landed: a shape (proxy) and optionally its paragraph indices."""

    shape: object
    paras: list[int] | None = None


class SlideBuilder:
    """Emits one PowerPoint slide for steps [lo, hi] of one HTML slide."""

    def __init__(self, em: "Emitter", s: dict, layout_name: str, lo: int, hi: int, morph: bool, part_no: int):
        self.em, self.s, self.lo, self.hi, self.morph = em, s, lo, hi, morph
        self.layout_name = layout_name
        self.geo, self.colours, self.report = em.geo, em.colours, em.report
        self.byid = {e["id"]: e for e in s["elements"]}
        self.kids: dict[str, list[dict]] = {}
        for e in s["elements"]:
            self.kids.setdefault(e["parent"], []).append(e)
        self.vis = {e["id"] for e in s["elements"] if any(lo <= k <= hi for k in e["visible_steps"])}
        self.slide = em.prs.slides.add_slide(em.layout(layout_name))
        name = s["id"] if part_no == 0 else f"{s['id']} (step {lo})"
        self.slide._element.find("p:cSld", NS).set("name", name)
        self.text = Text(em.scene, self.geo, self.colours, self.slide.part)
        self.targets: dict[str, Target] = {}
        self.z: dict[object, tuple] = {}   # element → sort key
        self.consumed: set[str] = set()
        self.bullets: set[str] = set()
        self.shapes: list = []

    # -- helpers --
    def name(self, eid: str) -> str:
        return ("!!" if self.morph else "") + eid

    def ancestors(self, e: dict):
        p = e["parent"]
        while p is not None and p in self.byid:
            yield self.byid[p]
            p = self.byid[p]["parent"]

    def opacity(self, e: dict) -> float:
        o = e["opacity"]
        for a in self.ancestors(e):
            o *= a["opacity"]
        return o

    def geom(self, e: dict) -> tuple[dict, list | None]:
        """Box and SVG primitives at this segment (camera frames honoured)."""
        if e.get("frames"):
            steps = [k for k in e["visible_steps"] if self.lo <= k <= self.hi]
            want = steps[0] if steps else self.lo
            fr = min(e["frames"], key=lambda f: (abs(f["step"] - want), f["step"]))
            return fr["box"], fr["svg"]
        return e["box"], e["svg"]

    def descendants(self, eid: str):
        for k in self.kids.get(eid, []):
            yield k
            yield from self.descendants(k["id"])

    def where(self, e):
        return (self.s["id"], e["id"])

    def _register(self, el, e: dict, key: tuple | None = None):
        self.z[el] = key or (2, e["z"])

    def _shape(self, el):
        tree = self.slide.shapes._spTree
        tree.append(el)
        proxy = self.slide.shapes._shape_factory(el)
        self.shapes.append(proxy)
        return proxy

    def _nv(self, kind: str, name: str, txbox=False, decorative=False, descr=None):
        sid = self.slide.shapes._next_shape_id
        nv = _el(f"p:nv{kind}Pr")
        c = _el("p:cNvPr", nv, id=sid, name=name)
        if descr:
            c.set("descr", descr)
        if decorative:
            ext = _el("a:ext", _el("a:extLst", c), uri=DECORATIVE_URI)
            d = etree.SubElement(ext, f"{{{NS['adec']}}}decorative", nsmap={"adec": NS["adec"]})
            d.set("val", "1")
        if kind == "Sp":
            cn = _el("p:cNvSpPr", nv)
            if txbox:
                cn.set("txBox", "1")
        else:
            _el("p:cNvCxnSpPr", nv)
        _el("p:nvPr", nv)
        return nv

    def _xfrm(self, parent, box: dict, flip=None):
        x, y, w, h = self.geo.box(box)
        xf = _el("a:xfrm", parent)
        if flip:
            for f in flip:
                xf.set(f, "1")
        _el("a:off", xf, x=x, y=y)
        _el("a:ext", xf, cx=w, cy=h)
        return xf

    def _effects(self, e: dict, parent, box: dict):
        """Write ``a:effectLst`` for an element's style effects and report each by band."""
        lst = None
        for fx in e["effects"]:
            kind, band = fx["kind"], fx["band"]
            what = kind
            if band == "lost":
                self.report.add(*self.where(e), what, "lost", _LOST_HOW.get(kind, "declared lost: dropped"), band,
                                fx["token"])
                continue
            if kind in ("shadow", "svg-filter"):
                sh = _parse_shadow(fx["value"]) if kind == "shadow" else self.em.lift_shadow(fx["value"])
                if sh is None:
                    self.report.add(*self.where(e), what, "lost", "unparsed shadow", band, fx["token"])
                    continue
                if lst is None:
                    lst = _el("a:effectLst")
                k = self.geo.k
                dist = math.hypot(sh["x"], sh["y"]) * k
                ang = (math.degrees(math.atan2(sh["y"], sh["x"])) % 360) if dist else 90
                o = _el("a:outerShdw", None, blurRad=int(sh["blur"] * k), dist=int(dist), dir=int(ang * 60000),
                        algn="ctr", rotWithShape="0")
                if sh["spread"]:
                    sx = max(0.5, (box["w"] + 2 * sh["spread"]) / max(1, box["w"]))
                    sy = max(0.5, (box["h"] + 2 * sh["spread"]) / max(1, box["h"]))
                    o.set("sx", str(int(sx * 100000)))
                    o.set("sy", str(int(sy * 100000)))
                o.append(self.colours.element({"rgb": sh["rgb"], "alpha": sh["alpha"], "role": None}))
                lst.append(o)
                self.report.add(*self.where(e), what, band if band in ("native", "approximated") else "approximated",
                                "outer shadow (inset highlight and spread approximated)", band, fx["token"])
            elif kind == "blur" and e["role"] == "orb":
                if lst is None:
                    lst = _el("a:effectLst")
                px = float(re.findall(r"[\d.]+", fx["value"])[0]) if re.findall(r"[\d.]+", fx["value"]) else 0
                rad = min(px, min(box["w"], box["h"]) / 4)
                lst.append(_el("a:softEdge", None, rad=int(rad * self.geo.k)))
                self.report.add(*self.where(e), what, "approximated", "soft-edged ellipse", band, fx["token"])
            elif kind == "opacity":
                res = {"native": "native", "approximated": "approximated"}.get(band, "approximated")
                self.report.add(*self.where(e), what, res, "applied as colour alpha", band, fx["token"])
            else:
                self.report.add(*self.where(e), what, "lost", _LOST_HOW.get(kind, "dropped"), band, fx["token"])
        if lst is not None:
            # schema order inside effectLst: … outerShdw … softEdge
            order = {"outerShdw": 0, "softEdge": 1}
            for c in sorted(list(lst), key=lambda c: order.get(etree.QName(c).localname, 9)):
                lst.append(c)
            parent.append(lst)

    def _sppr(self, box, geom, fill, ln=None, effects_of=None, flip=None):
        sp = _el("p:spPr")
        self._xfrm(sp, box, flip)
        sp.append(geom)
        if fill is not None:
            sp.append(fill)
        if ln is None:
            ln = _el("a:ln")
            _el("a:noFill", ln)
        sp.append(ln)
        if effects_of is not None:
            self._effects(effects_of, sp, box)
        return sp

    @staticmethod
    def _prst(prst: str, adj: float | None = None):
        g = _el("a:prstGeom", prst=prst)
        av = _el("a:avLst", g)
        if adj is not None:
            _el("a:gd", av, name="adj", fmla=f"val {int(round(adj * 100000))}")
        return g

    def _adj(self, radius, box) -> float:
        if not radius:
            return 0.0
        return min(0.5, radius / max(1.0, min(box["w"], box["h"])))

    # -- paragraphs from elements --
    def para_of(self, e: dict, before: float = 0.0) -> Para:
        runs = [dict(r) for r in e["text"]["runs"]] if e.get("text") else []
        for k in self.kids.get(e["id"], []):
            if k["role"] == "generated-text" and k.get("text") and k["id"] in self.vis:
                if k["pseudo"] == "before":
                    runs = [dict(r) for r in k["text"]["runs"]] + runs
                else:
                    runs += [dict(r) for r in k["text"]["runs"]]
                self.consumed.add(k["id"])
        p = Para(runs=runs, align=e["text"]["align"] if e.get("text") else "left",
                 line=e["text"]["line_height"] if e.get("text") else None, before=before, els=[e["id"]])
        marker = next((k for k in self.kids.get(e["id"], []) if k["role"] == "marker"), None)
        if marker is not None:
            self.consumed.add(marker["id"])
            self.bullets.add(marker["id"])
            mtext = _el_text(marker).strip()
            if e.get("text"):
                p.mar = max(0.0, e["text"]["box"]["x"] - e["box"]["x"])
            if mtext.isdigit():
                col = marker["text"]["runs"][0]["colour"] if marker.get("text") else None
                p.bullet = ("num", int(mtext), col)
                self.report.add(*self.where(marker), "marker", "approximated",
                                "numbered marker → native autonumber (its circle is lost)")
            else:
                p.bullet = ("char", "–", marker["fill"] or (marker["stroke"] and {**marker["stroke"]}))
                self.report.add(*self.where(marker), "marker", "approximated", "list marker → native bullet")
        return p

    def merged_paras(self, items: list[dict], prev_bottom: float | None = None) -> list[Para]:
        """Paragraphs for text elements in DOM order, spacing from their measured gaps."""
        paras = []
        for e in items:
            box = e["box"]
            before = 0.0 if prev_bottom is None else box["y"] - prev_bottom
            paras.append(self.para_of(e, before))
            prev_bottom = box["y"] + box["h"]
        return paras

    def text_desc(self, root: dict) -> list[dict]:
        """Visible text-bearing descendants of a card, in paint order (generated text merged later)."""
        out = []
        for d in self.descendants(root["id"]):
            if d["id"] not in self.vis or d["role"] == "marker":
                continue
            if d["role"] == "generated-text":
                par = self.byid.get(d["parent"])
                if par is not None and par.get("text") and par["id"] != root["id"]:
                    continue  # merged into its parent's paragraph
            if d.get("text"):
                out.append(d)
        return sorted(out, key=lambda d: d["z"])

    # -- emitters per kind --
    def placeholder(self, idx: int | None, ph_type: str | None = None):
        for ph in self.slide.placeholders:
            pf = ph.placeholder_format
            if idx is not None and pf.idx == idx:
                return ph
            if ph_type and idx is None and pf.type is not None and str(pf.type).split(".")[-1].split(" ")[0] in ph_type:
                return ph
        return None

    def fill_placeholder(self, ph, paras: list[Para], box: dict | None, owner: dict, layout_key: str,
                         els: list[dict], card: dict | None = None):
        """Write paragraphs into a placeholder; override its position only where content differs."""
        el = ph._element
        lay = self.em.seed.frames[self.layout_name].get(layout_key)
        sp = el.find("p:spPr", NS)
        for c in list(sp):
            sp.remove(c)
        if box is not None and lay is not None and any(abs(box[k] - lay[k]) > 2 for k in ("x", "y", "w")):
            self._xfrm(sp, {**box, "h": max(box["h"], lay["h"] if abs(box["y"] - lay["y"]) <= 2 else box["h"])})
        if card is not None:
            sp.append(self._prst("roundRect", self._adj(card["radius"], card["box"])))
            sp.append(self.colours.fill(card["fill"], self.opacity(card), self.where(card)))
            ln = _el("a:ln", sp)
            _el("a:noFill", ln)
            self._effects(card, sp, card["box"])
        insets = (0, 0, 0, 0)
        if card is not None:
            insets = self.card_insets(card, els)
        tb = self.text.body(paras, insets=insets, anchor="t", opacity=self.opacity(owner), where=self.where(owner))
        old = el.find("p:txBody", NS)
        el.replace(old, tb) if old is not None else el.append(tb)
        el.find("p:nvSpPr/p:cNvPr", NS).set("name", self.name(owner["id"]))
        self._register(el, owner, (1, owner["z"]) if layout_key == "title" else None)
        for i, p in enumerate(paras):
            for eid in p.els:
                self.targets[eid] = Target(ph, [i])
        self.targets.setdefault(owner["id"], Target(ph, None))
        for e in els:
            self.consumed.add(e["id"])
        self.consumed.add(owner["id"])
        return ph

    def card_insets(self, card: dict, els: list[dict]) -> tuple:
        boxes = [(d["text"]["box"] if d.get("text") else d["box"]) for d in els] or [card["box"]]
        b = card["box"]
        l = min(x["x"] for x in boxes) - b["x"]
        t = min(x["y"] for x in boxes) - b["y"]
        r = b["x"] + b["w"] - max(x["x"] + x["w"] for x in boxes)
        bt = b["y"] + b["h"] - max(x["y"] + x["h"] for x in boxes)
        r = max(0.0, min(r, l))  # slack on the right: PowerPoint wraps a little wider than Chrome
        return (max(0, l), max(0, t), r, max(0, min(bt, t)))

    def card(self, e: dict):
        """A card (frosted or opaque) as one named round rectangle holding its text."""
        box, _ = self.geom(e)
        items = self.text_desc(e)
        if e.get("text"):
            items = [e] + [d for d in items if d["id"] != e["id"]]
        paras = self.merged_paras(items)
        if paras:
            paras[0].before = 0
        sp = _el("p:sp")
        sp.append(self._nv("Sp", self.name(e["id"])))
        fill = self.colours.fill(e["fill"], self.opacity(e), self.where(e)) if e["fill"] else _el("a:noFill")
        ln = None
        if e["stroke"] and e["stroke"]["width"] > 0:
            ln = _el("a:ln", w=self.geo.emu(e["stroke"]["width"]))
            ln.append(self.colours.fill(e["stroke"], self.opacity(e), self.where(e)))
        geom = self._prst("roundRect", self._adj(e["radius"], box)) if e["radius"] else self._prst("rect")
        sp.append(self._sppr(box, geom, fill, ln, effects_of=e))
        sp.append(self.text.body(paras, insets=self.card_insets(e, items), opacity=self.opacity(e), where=self.where(e)))
        proxy = self._shape(sp)
        self._register(sp, e)
        self.targets[e["id"]] = Target(proxy)
        for i, p in enumerate(paras):
            for eid in p.els:
                if eid != e["id"]:
                    self.targets[eid] = Target(proxy, [i])
        self.consumed.add(e["id"])
        art = {a["id"] for a in self.descendants(e["id"]) if _is_vector_art(a)}
        art |= {d["id"] for a in art for d in self.descendants(a)}
        self.consumed.update(d["id"] for d in self.descendants(e["id"]) if d["id"] not in art)

    def textbox(self, e: dict, paras: list[Para] | None = None, box=None, anchor="t", wrap="square"):
        box = box or (e["text"]["box"] if e.get("text") else self.geom(e)[0])
        paras = paras or [self.para_of(e)]
        wide = dict(box)
        if wrap == "square":
            slack = box["w"] * 0.06
            if paras[0].align == "center":
                wide["x"] -= slack / 2
            elif paras[0].align == "right":
                wide["x"] -= slack
            wide["w"] += slack
        sp = _el("p:sp")
        sp.append(self._nv("Sp", self.name(e["id"]), txbox=True))
        sp.append(self._sppr(wide, self._prst("rect"), _el("a:noFill")))
        sp.append(self.text.body(paras, anchor=anchor, wrap=wrap, autofit="shape", opacity=self.opacity(e),
                                 where=self.where(e)))
        proxy = self._shape(sp)
        self._register(sp, e)
        self.targets[e["id"]] = Target(proxy)
        for p in paras:
            for eid in p.els:
                self.targets.setdefault(eid, Target(proxy))
        self.consumed.add(e["id"])
        return proxy

    def orb(self, e: dict):
        box, _ = self.geom(e)
        first = _css_colour(e.get("gradient") or "")
        colour = e["fill"] or ({"rgb": first[0], "alpha": first[1], "role": None} if first else None)
        if colour is None:
            return
        op = self.opacity(e)
        pos = re.search(r"at\s+([\d.]+)%\s+([\d.]+)%", e.get("gradient") or "")
        cx, cy = (float(pos.group(1)), float(pos.group(2))) if pos else (50.0, 50.0)
        stop = re.search(r"\)\s*([\d.]+)%\s*\)?\s*$", e.get("gradient") or "")
        end = float(stop.group(1)) if stop else 70.0
        grad = _el("a:gradFill", rotWithShape="1")
        gs = _el("a:gsLst", grad)
        g0 = _el("a:gs", gs, pos=0)
        g0.append(self.colours.element(colour, op, self.where(e)))
        g1 = _el("a:gs", gs, pos=int(end * 1000))
        g1.append(self.colours.element({**colour, "alpha": 0.0}, 1.0))
        path = _el("a:path", grad, path="circle")
        _el("a:fillToRect", path, l=int(cx * 1000), t=int(cy * 1000), r=int((100 - cx) * 1000), b=int((100 - cy) * 1000))
        sp = _el("p:sp")
        sp.append(self._nv("Sp", self.name(e["id"]), decorative=True))
        sp.append(self._sppr(box, self._prst("ellipse"), grad, effects_of=e))
        proxy = self._shape(sp)
        self._register(sp, e, (0, e["z"]))
        self.targets[e["id"]] = Target(proxy)
        self.consumed.add(e["id"])

    def line_el(self, stroke: dict | None, width: float, opacity: float, where, start=None, end=None):
        ln = _el("a:ln", w=max(1, self.geo.emu(width)), cap="rnd")
        if stroke is None:
            _el("a:noFill", ln)
        else:
            ln.append(self.colours.fill(stroke, opacity, where))
        _el("a:round", ln)
        if start:
            _el("a:headEnd", ln, type="triangle", w="med", len="med")
        if end:
            _el("a:tailEnd", ln, type="triangle", w="med", len="med")
        return ln

    def path_shape(self, e: dict, prim: dict, name: str):
        """An SVG path as a named freeform (``cubicBezTo`` kept), or a straight connector."""
        nums = re.findall(r"[MLCZ]|-?[\d.]+", prim["d"])
        segs, i = [], 0
        while i < len(nums):
            c = nums[i]
            n = {"M": 2, "L": 2, "C": 6, "Z": 0}[c]
            segs.append((c, [float(v) for v in nums[i + 1:i + 1 + n]]))
            i += 1 + n
        op = self.opacity(e)
        stroke = prim["stroke"]
        ln = self.line_el(stroke, prim["stroke_width"], op, self.where(e), prim["marker_start"], prim["marker_end"])
        if [s[0] for s in segs] == ["M", "L"] and prim["fill"] is None:
            (x1, y1), (x2, y2) = segs[0][1], segs[1][1]
            box = {"x": min(x1, x2), "y": min(y1, y2), "w": abs(x2 - x1), "h": abs(y2 - y1)}
            flip = [f for f, cond in (("flipH", x2 < x1), ("flipV", y2 < y1)) if cond]
            cx = _el("p:cxnSp")
            cx.append(self._nv("CxnSp", name))
            sp = _el("p:spPr")
            self._xfrm(sp, box, flip)
            sp.append(self._prst("line"))
            _el("a:noFill", sp)
            sp.append(ln)
            cx.append(sp)
            proxy = self._shape(cx)
            return cx, proxy
        b = prim["box"]
        x0, y0 = b["x"], b["y"]
        W, H = max(self.geo.emu(b["w"]), 1), max(self.geo.emu(b["h"]), 1)
        cg = _el("a:custGeom")
        for t in ("avLst", "gdLst", "ahLst", "cxnLst"):
            _el(f"a:{t}", cg)
        _el("a:rect", cg, l="0", t="0", r="r", b="b")
        path = _el("a:path", _el("a:pathLst", cg), w=W, h=H)
        if prim["fill"] is None:
            path.set("fill", "none")
        pt = lambda parent, x, y: _el("a:pt", parent, x=self.geo.emu(x - x0), y=self.geo.emu(y - y0))  # noqa: E731
        for c, v in segs:
            if c == "M":
                pt(_el("a:moveTo", path), *v)
            elif c == "L":
                pt(_el("a:lnTo", path), *v)
            elif c == "C":
                cb = _el("a:cubicBezTo", path)
                for j in range(0, 6, 2):
                    pt(cb, v[j], v[j + 1])
            else:
                _el("a:close", path)
        sp = _el("p:sp")
        sp.append(self._nv("Sp", name))
        fill = self.colours.fill(prim["fill"], op, self.where(e)) if prim["fill"] else _el("a:noFill")
        sp.append(self._sppr(b, cg, fill, ln))
        return sp, self._shape(sp)

    def svg_text(self, e: dict, prim: dict, name: str):
        box = prim["box"]
        align = {"middle": "center", "end": "right"}.get(prim["anchor"], "left")
        para = Para(runs=[dict(r) for r in prim["runs"]], align=align, els=[e["id"]])
        wide = dict(box)
        slack = box["w"] * 0.3 + 4
        wide["x"] -= slack / 2 if align == "center" else (slack if align == "right" else 0)
        wide["w"] += slack
        sp = _el("p:sp")
        sp.append(self._nv("Sp", name, txbox=True))
        sp.append(self._sppr(wide, self._prst("rect"), _el("a:noFill")))
        sp.append(self.text.body([para], anchor="ctr", wrap="none", opacity=self.opacity(e), where=self.where(e)))
        return sp, self._shape(sp)

    def tile(self, e: dict):
        box, prims = self.geom(e)
        prims = prims or []
        rect = next((p for p in prims if p["type"] == "rect"), None)
        texts = [p for p in prims if p["type"] == "text"]
        b = {"x": rect["x"], "y": rect["y"], "w": rect["w"], "h": rect["h"]} if rect else box
        fill = (rect and rect["fill"]) or e["fill"]
        op = self.opacity(e)
        paras = []
        for t in texts:
            paras.append(Para(runs=[dict(r) for r in t["runs"]], align="center",
                              line=max(r["size"] for r in t["runs"]) * 1.25, els=[]))
        sp = _el("p:sp")
        sp.append(self._nv("Sp", self.name(e["id"])))
        radius = rect["rx"] if rect else 0
        geom = self._prst("roundRect", self._adj(radius, b)) if radius else self._prst("rect")
        ln = None
        if rect and rect["stroke"]:
            ln = self.line_el(rect["stroke"], rect["stroke_width"], op, self.where(e))
        sp.append(self._sppr(b, geom, self.colours.fill(fill, op, self.where(e)), ln, effects_of=e))
        sp.append(self.text.body(paras, insets=(8, 4, 8, 4), anchor="ctr", opacity=op, where=self.where(e)))
        proxy = self._shape(sp)
        self._register(sp, e)
        self.targets[e["id"]] = Target(proxy)
        self.consumed.add(e["id"])
        self.consumed.update(d["id"] for d in self.descendants(e["id"]))

    def svg_part(self, e: dict):
        """Edges, labels, tags and other SVG shapes: one named shape per primitive."""
        _, prims = self.geom(e)
        made = []
        for n, prim in enumerate(prims or []):
            name = self.name(e["id"] if n == 0 else f"{e['id']}#{n}")
            if prim["type"] == "path":
                el, proxy = self.path_shape(e, prim, name)
            elif prim["type"] == "line":
                d = {**prim, "type": "path", "d": f"M {prim['x1']} {prim['y1']} L {prim['x2']} {prim['y2']}",
                     "box": {"x": min(prim["x1"], prim["x2"]), "y": min(prim["y1"], prim["y2"]),
                             "w": abs(prim["x2"] - prim["x1"]), "h": abs(prim["y2"] - prim["y1"])}}
                el, proxy = self.path_shape(e, d, name)
            elif prim["type"] == "text":
                el, proxy = self.svg_text(e, prim, name)
            elif prim["type"] in ("rect", "ellipse"):
                if prim["type"] == "rect":
                    b = {"x": prim["x"], "y": prim["y"], "w": prim["w"], "h": prim["h"]}
                    geom = self._prst("roundRect", self._adj(prim["rx"], b)) if prim["rx"] else self._prst("rect")
                else:
                    b = {"x": prim["cx"] - prim["rx"], "y": prim["cy"] - prim["ry"], "w": 2 * prim["rx"], "h": 2 * prim["ry"]}
                    geom = self._prst("ellipse")
                op = self.opacity(e)
                ln = self.line_el(prim["stroke"], prim["stroke_width"], op, self.where(e)) if prim["stroke"] else None
                el = _el("p:sp")
                el.append(self._nv("Sp", name))
                el.append(self._sppr(b, geom, self.colours.fill(prim["fill"], op, self.where(e)), ln))
                proxy = self._shape(el)
            else:
                continue
            self._register(el, e, (2, e["z"], n))
            made.append(proxy)
        if made:
            # the element's style effects (lift shadow, opacity) land on its first shape, and are reported
            sppr = made[0]._element.find("p:spPr", NS)
            if e["effects"] and sppr is not None:
                self._effects(e, sppr, e["box"])
            self.targets[e["id"]] = Target(made[0])
            for extra in made[1:]:
                self.em.extra_targets.setdefault((self.s["id"], e["id"]), []).append(extra)
        self.consumed.add(e["id"])

    def table(self, e: dict):
        cells = [c for c in self.descendants(e["id"]) if c["role"] == "cell" and c["id"] in self.vis]
        if not cells:
            return
        ys = sorted({round(c["box"]["y"]) for c in cells})
        xs = sorted({round(c["box"]["x"]) for c in cells})
        rows = [[c for c in cells if round(c["box"]["y"]) == y] for y in ys]
        for r in rows:
            r.sort(key=lambda c: c["box"]["x"])
        widths = [max(c["box"]["w"] for c in cells if round(c["box"]["x"]) == x) for x in xs]
        steps = lambda r: tuple(k for k in r[0]["visible_steps"] if self.lo <= k <= self.hi)  # noqa: E731
        pieces = []
        for r in rows:
            if pieces and steps(pieces[-1][-1]) == steps(r):
                pieces[-1].append(r)
            else:
                pieces.append([r])
        if len(pieces) > 1:
            self.report.add(self.s["id"], e["id"], "table rows", "approximated",
                            f"rows build on separate steps: split into {len(pieces)} stacked tables")
        for n, piece in enumerate(pieces):
            top = piece[0][0]["box"]["y"]
            height = sum(r[0]["box"]["h"] for r in piece)
            name = self.name(e["id"] if n == 0 else f"{e['id']}#rows{n}")
            gf = self.slide.shapes.add_table(len(piece), len(xs), Emu(self.geo.emu(e["box"]["x"])),
                                             Emu(self.geo.emu(top)), Emu(self.geo.emu(sum(widths))),
                                             Emu(self.geo.emu(height)))
            gf.name = name
            self.shapes.append(gf)
            tbl = gf.table
            tbl.first_row = n == 0 and any(c["tag"] == "th" for c in piece[0])
            tbl.horz_banding = False
            sid = tbl._tbl.find("a:tblPr/a:tableStyleId", NS)
            if sid is None:
                sid = _el("a:tableStyleId", tbl._tbl.find("a:tblPr", NS))
            sid.text = NO_STYLE_TABLE
            for j, w in enumerate(widths):
                tbl.columns[j].width = Emu(self.geo.emu(w))
            for i, r in enumerate(piece):
                tbl.rows[i].height = Emu(self.geo.emu(r[0]["box"]["h"]))
                for j, c in enumerate(r[:len(xs)]):
                    tc = tbl.cell(i, j)._tc
                    pad = c["text"]["padding"] if c.get("text") else [0, 0, 0, 0]
                    paras = [self.para_of(c)] if c.get("text") else [Para(runs=[])]
                    tb = self.text.body(paras, tag="a:txBody", opacity=self.opacity(c), where=self.where(c))
                    tb.replace(tb.find("a:bodyPr", NS), _el("a:bodyPr"))
                    tc.replace(tc.find("a:txBody", NS), tb)
                    tcpr = tc.find("a:tcPr", NS)
                    if tcpr is None:
                        tcpr = _el("a:tcPr", tc)
                    for k, v in zip(("marT", "marR", "marB", "marL"), pad[:4]):
                        tcpr.set(k, str(self.geo.emu(v)))
                    for c2 in list(tcpr):
                        tcpr.remove(c2)
                    for side in ("lnL", "lnR", "lnT"):
                        _el("a:noFill", _el(f"a:{side}", tcpr, w=0))
                    lb = _el("a:lnB", tcpr, w=self.geo.emu(2))
                    rule = next((v for v in self.em.scene["palette"] if "lt2" in self.em.scene["palette"][v]["slots"]), None)
                    lb.append(self.colours.fill({"rgb": "000000", "alpha": 1, "role": rule}) if rule else _el("a:noFill"))
                    _el("a:noFill", tcpr)
                    self.targets[c["id"]] = Target(gf)
                    self.consumed.add(c["id"])
            self._register(gf._element, e, (2, e["z"], n))
        self.consumed.add(e["id"])

    def image(self, e: dict):
        src = (e.get("image") or {}).get("src", "")
        m = re.match(r"data:image/(png|jpeg|jpg|gif);base64,(.*)$", src, re.S)
        if not m:
            self.report.add(*self.where(e), "image", "lost", "only embedded PNG/JPEG/GIF images are carried over")
            self.consumed.add(e["id"])
            return
        import base64
        import io

        box, _ = self.geom(e)
        x, y, w, h = self.geo.box(box)
        pic = self.slide.shapes.add_picture(io.BytesIO(base64.b64decode(m.group(2))), Emu(x), Emu(y), Emu(w), Emu(h))
        pic.name = self.name(e["id"])
        pic._element.find("p:nvPicPr/p:cNvPr", NS).set("descr", e["image"]["alt"] or "")
        self.shapes.append(pic)
        self._register(pic._element, e)
        self.targets[e["id"]] = Target(pic)
        self.consumed.add(e["id"])

    # -- layout of the whole slide --
    def flow_columns(self, body: dict) -> list[list[dict]]:
        """Body flow text (outside cards) clustered into columns by horizontal overlap."""
        items = []
        for d in self.descendants(body["id"]):
            if d["id"] not in self.vis or d["id"] in self.consumed or d["role"] not in FLOW:
                continue
            if any(a["role"] in CARDS | {"table", "diagram", "tile", "key-tile"} for a in self.ancestors(d)):
                continue
            if d["role"] == "generated-text":
                continue
            if any(a["role"] in FLOW for a in self.ancestors(d) if a["id"] != body["id"]):
                continue
            if d.get("text"):
                items.append(d)
        cols: list[list[dict]] = []
        for d in sorted(items, key=lambda d: d["z"]):
            x0, x1 = d["box"]["x"], d["box"]["x"] + d["box"]["w"]
            for col in cols:
                c0 = min(c["box"]["x"] for c in col)
                c1 = max(c["box"]["x"] + c["box"]["w"] for c in col)
                if min(x1, c1) - max(x0, c0) > 0.3 * min(x1 - x0, c1 - c0):
                    col.append(d)
                    break
            else:
                cols.append([d])
        return sorted(cols, key=lambda c: min(d["box"]["x"] for d in c))

    def build(self):
        s = self.s
        els = sorted((e for e in s["elements"] if e["id"] in self.vis), key=lambda e: e["z"])
        top = [e for e in els if e["parent"] is None]
        # 1. title, kicker, byline into placeholders
        for e in top:
            if e["role"] == "title":
                ph = self.placeholder(0)
                self.fill_placeholder(ph, [self.para_of(e)], e["box"], e, "title", [e])
            elif e["role"] == "kicker" and self.placeholder(10) is not None:
                self.fill_placeholder(self.placeholder(10), [self.para_of(e)], e["box"], e, "kicker", [e])
            elif e["role"] == "byline" and self.placeholder(11) is not None:
                self.fill_placeholder(self.placeholder(11), [self.para_of(e)], e["box"], e, "body11", [e])
        # 2. cards first (tile row cards go into the tile placeholders)
        body = next((e for e in top if e["role"] == "body"), None)
        if self.layout_name == "Tile row" and body is not None:
            cards = sorted((d for d in self.descendants(body["id"]) if d["role"] == "tile-card" and d["id"] in self.vis),
                           key=lambda d: d["box"]["x"])
            for i, c in enumerate(cards[:3]):
                items = self.text_desc(c)
                paras = self.merged_paras(items)
                if paras:
                    paras[0].before = 0
                self.fill_placeholder(self.placeholder(i + 1), paras, c["box"], c, f"body{i + 1}", items, card=c)
                self.consumed.update(d["id"] for d in self.descendants(c["id"]))
        # 3. body flow into body placeholders
        if body is not None:
            cols = self.flow_columns(body)
            if self.layout_name == "Title / lead":
                slots = [(1, "body1")]
            elif self.layout_name == "Split":
                slots = [(1, "body1"), (2, "body2")]
            elif self.layout_name in ("Standard", "Three-column scene"):
                slots = [(1, "body1")]
            else:
                slots = []
            if self.layout_name == "Split" and len(cols) == 1:
                lay = self.em.seed.frames["Split"]
                cx = cols[0][0]["box"]["x"]
                if abs(cx - lay["body2"]["x"]) < abs(cx - lay["body1"]["x"]):
                    slots = [(2, "body2")]
            for (idx, key), col in zip(slots, cols):
                col = sorted(col, key=lambda d: d["z"])
                paras = self.merged_paras(col)
                if paras:
                    paras[0].before = 0
                b = {"x": min(d["box"]["x"] for d in col), "y": min(d["box"]["y"] for d in col)}
                b["w"] = max(d["box"]["x"] + d["box"]["w"] for d in col) - b["x"]
                b["h"] = max(d["box"]["y"] + d["box"]["h"] for d in col) - b["y"]
                lay = self.em.seed.frames[self.layout_name].get(key)
                if lay is not None:
                    # the measured line length plus slack, so PowerPoint wraps where Chrome did
                    b["w"] = min(b["w"] * 1.06, lay["x"] + lay["w"] - b["x"])
                self.fill_placeholder(self.placeholder(idx), paras, b, body, key, col)
                for d in col:
                    self.consumed.add(d["id"])
            for col in cols[len(slots):]:
                for d in col:
                    if d["id"] not in self.consumed:
                        self.textbox(d)
            self.consumed.add(body["id"])
        # 4. everything else, in paint order
        for e in els:
            if e["id"] in self.consumed:
                continue
            role = e["role"]
            if role == "orb":
                self.orb(e)
            elif role in ("tile", "key-tile"):
                self.tile(e)
            elif (role in ("edge", "label", "tag", "shape") and e.get("svg")) or _is_vector_art(e):
                self.svg_part(e)  # vector art (e.g. a pop-over illustration): native shapes + text boxes
            elif role == "table":
                self.table(e)
            elif role == "image":
                self.image(e)
            elif role in CARDS or (e["fill"] and role not in CONTAINERS and role != "marker"
                                   and (e.get("text") or any(True for _ in self.text_desc(e)))):
                self.card(e)
            elif role == "marker":
                self.report.add(*self.where(e), "marker", "lost", "free-standing marker dropped")
                self.consumed.add(e["id"])
            elif role == "generated-text" and e.get("text"):
                par = self.byid.get(e["parent"])
                if par is not None and par["id"] in self.targets:
                    self.consumed.add(e["id"])
                else:
                    self.textbox(e)
            elif e.get("text") and role not in CONTAINERS:
                self.textbox(e)
            elif role in CONTAINERS or role in ("scene", "diagram"):
                self.consumed.add(e["id"])
            elif e["fill"] or e["stroke"]:
                box, _ = self.geom(e)
                sp = _el("p:sp")
                sp.append(self._nv("Sp", self.name(e["id"])))
                ln = None
                if e["stroke"]:
                    ln = self.line_el(e["stroke"], e["stroke"]["width"], self.opacity(e), self.where(e))
                geom = self._prst("roundRect", self._adj(e["radius"], box)) if e["radius"] else self._prst("rect")
                sp.append(self._sppr(box, geom, self.colours.fill(e["fill"], self.opacity(e), self.where(e)), ln, effects_of=e))
                self.targets[e["id"]] = Target(self._shape(sp))
                self._register(sp, e)
                self.consumed.add(e["id"])
        # effects on elements that never became shapes (containers) are still reported
        for e in els:
            if e["effects"] and not any(it["el"] == e["id"] and it["slide"] == s["id"] for it in self.report.items):
                anchor = _el("p:spPr")
                self._effects(e, anchor, e["box"])
        # 5. remove unused placeholders, order the tree
        for ph in list(self.slide.placeholders):
            if ph._element not in self.z:
                ph._element.getparent().remove(ph._element)
        tree = self.slide.shapes._spTree
        body_els = [c for c in tree if c in self.z]
        for c in sorted(body_els, key=lambda c: self.z[c]):
            tree.append(c)

    # -- steps --
    def resolve(self, eid: str) -> list[tuple[object, tuple | None]]:
        """Shapes (and paragraph ranges) a delta on ``eid`` animates."""
        if eid in self.targets:
            t = self.targets[eid]
            out = [(t.shape, (min(t.paras), max(t.paras)) if t.paras else None)]
            out += [(x, None) for x in self.em.extra_targets.get((self.s["id"], eid), [])]
            return out
        found: dict[int, tuple[object, set]] = {}
        whole: set[int] = set()
        for d in self.descendants(eid):
            t = self.targets.get(d["id"])
            if t is None:
                continue
            key = id(t.shape)
            found.setdefault(key, (t.shape, set()))
            if t.paras is None:
                whole.add(key)
            else:
                found[key][1].update(t.paras)
            for x in self.em.extra_targets.get((self.s["id"], d["id"]), []):
                found.setdefault(id(x), (x, set()))
                whole.add(id(x))
        out = []
        for key, (shape, paras) in found.items():
            if key in whole or not paras:
                out.append((shape, None))
                continue
            ps = sorted(paras)
            start = prev = ps[0]
            for p in ps[1:] + [None]:
                if p is not None and p == prev + 1:
                    prev = p
                    continue
                out.append((shape, (start, prev)))
                if p is not None:
                    start = prev = p
        return out

    def steps(self) -> list[list[tuple]]:
        out = []
        for t in self.s["timeline"]:
            k = t["step"]
            if k == self.lo and k > 0:
                for d in t["deltas"]:  # absorbed into this Morph slide's starting state
                    if d["effect"] == "unsupported" and d["property"] != "camera":
                        self.report.add(self.s["id"], d["el"], f"step {k}: {d['property']}", "dropped",
                                        f"{d.get('reason', 'no native effect')}; the slide keeps its measured look",
                                        d.get("band"))
                continue
            if not self.lo < k <= self.hi:
                continue
            entries, seen = [], set()
            for d in t["deltas"]:
                what = f"step {k}: {d['property']}"
                if d["effect"] == "unsupported":
                    if d["property"] != "camera":
                        self.report.add(self.s["id"], d["el"], what, "dropped",
                                        f"{d.get('reason', 'no native effect')}; the slide keeps its measured look",
                                        d.get("band"))
                    continue
                if d["el"] in self.bullets:
                    self.report.add(self.s["id"], d["el"], what, "dropped",
                                    "marker became a native bullet; bullet colour cannot animate")
                    continue
                tg = self.resolve(d["el"])
                if not tg:
                    self.report.add(self.s["id"], d["el"], what, "dropped", "element was not emitted on this slide")
                    continue
                for shape, rng in tg:
                    key = (shape.shape_id, rng, d["effect"])
                    if key in seen:
                        continue
                    seen.add(key)
                    params = {k2: v for k2, v in d["params"].items()}
                    if d["effect"] == "fill_colour":
                        role = d.get("role") or self.colours.by_rgb.get(params["rgb"].upper())
                        if role in self.colours.pal and self.colours.pal[role]["rgb"] == params["rgb"].upper():
                            params["scheme"] = self.colours.slot(role)
                    entries.append((shape, d["effect"], params, rng))
            if entries:
                out.append(entries)
            else:
                self.report.add(self.s["id"], self.s["id"], f"step {k}", "dropped",
                                "no delta at this step has a native effect: no click")
        return out


class Emitter:
    """Holds the presentation, theme maps and report while slides are emitted."""

    def __init__(self, scene: dict):
        self.scene = scene
        self.geo = Geo(scene["size"]["width"], scene["size"]["height"])
        self.report = Report()
        self.colours = Colours(scene, self.report)
        self.seed = Seed(scene, self.geo, self.colours)
        self.prs = self.seed.build()
        self.extra_targets: dict = {}
        lifts = [fx["value"] for s in scene["slides"] for e in s["elements"] for fx in e["effects"]
                 if fx["kind"] == "shadow" and fx["token"] == "sys.shadow.lift"]
        self._lift = _parse_shadow(lifts[0]) if lifts else None

    def layout(self, name: str):
        return next(l for l in self.prs.slide_layouts if l.name == name)

    def lift_shadow(self, value: str) -> dict:
        """The style's lift shadow stands in for the SVG ``#lift`` filter."""
        if self._lift:
            return self._lift
        ink = next((v["rgb"] for v in self.scene["palette"].values() if "dk1" in v["slots"]), "000000")
        return {"rgb": ink, "alpha": 0.35, "x": 0, "y": 8, "blur": 18, "spread": -10}

    def choose_layout(self, s: dict) -> str:
        if _is_end(s):
            return "End"
        if _is_lead(s):
            return "Title / lead"
        if s["scene"] == "live":
            return "Three-column scene"
        if any(e["role"] == "tile-card" for e in s["elements"]):
            return "Tile row"
        body = next((e for e in s["elements"] if e["role"] == "body" and e["parent"] is None), None)
        if body is not None and "body--split" in body["classes"]:
            return "Split"
        return "Standard"

    def emit_slide(self, s: dict):
        cams = sorted({t["step"] for t in s["timeline"] for d in t["deltas"] if d["property"] == "camera"})
        bounds = [0, *cams, s["steps"] + 1]
        name = self.choose_layout(s)
        morph = bool(cams)
        anim = _anim_mod()
        for n, (lo, hi) in enumerate(zip(bounds, bounds[1:])):
            b = SlideBuilder(self, s, name, lo, hi - 1, morph, n)
            b.build()
            self.notes(b.slide, s)
            steps = b.steps()
            if steps:
                write_steps(anim, b.slide, steps)
            if n > 0:
                add_morph(b.slide)
                d = next(d for t in s["timeline"] if t["step"] == lo for d in t["deltas"] if d["property"] == "camera")
                self.report.add(s["id"], d["el"], f"step {lo}: camera", "morph",
                                "camera move: duplicate slide with a Morph transition and !!-named shapes")
            self.report.slides.append({"html": s["id"], "pptx": len(self.prs.slides), "layout": name,
                                       "steps": [lo, hi - 1], "morph": n > 0, "clicks": len(steps)})

    def notes(self, slide, s: dict):
        if not s["notes_text"]:
            return
        tf = slide.notes_slide.notes_text_frame
        lines = []
        for n, note in enumerate(s["notes"]):
            if n and lines:
                lines.append(("", None))
            if note["heading"]:
                lines.append((note["heading"], "b"))
            lines += [(t, None) for t in note["text"]]
            lines += [(f"Source: {src['text']} ({src['href']})", src) for src in note["sources"]]
        if "\n".join(t for t, _ in lines) != s["notes_text"]:
            tf.text = s["notes_text"]
            return
        tf.text = ""
        for i, (text, kind) in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            if isinstance(kind, dict):
                r = p.add_run()
                r.text = "Source: "
                r = p.add_run()
                r.text = kind["text"]
                r.hyperlink.address = kind["href"]
                r = p.add_run()
                r.text = f" ({kind['href']})"
            else:
                r = p.add_run()
                r.text = text
                if kind == "b":
                    r.font.bold = True

    def run(self) -> Presentation:
        bar = self.scene["chrome"].get("bar")
        if bar:
            self.report.add("deck", "chrome", "title bar", "lost", "deck chrome is not exported (sys.material.chip)")
        for s in self.scene["slides"]:
            self.emit_slide(s)
        return self.prs


def write_steps(anim, slide, steps: list[list[tuple]]):
    """Write clicks with PB-022, then retarget paragraph entries (``p:txEl/p:pRg``, ``build="p"``)."""
    plain = [[(shape, effect, {k: v for k, v in params.items()}) for shape, effect, params, _ in step] for step in steps]
    timing = anim.write_steps(slide, plain)
    if timing is None:
        return
    flat = [entry for step in steps for entry in step]
    ctns = [c for c in timing.iter(f"{_P}cTn") if c.get("presetClass") is not None]
    assert len(ctns) == len(flat)
    para_grp: dict[tuple, int] = {}
    next_grp: dict[int, int] = {}
    for ctn in ctns:
        spid = int(ctn.find(f".//{_P}spTgt").get("spid"))
        next_grp[spid] = max(next_grp.get(spid, 0), int(ctn.get("grpId")) + 1)
    for (shape, effect, params, rng), ctn in zip(flat, ctns):
        if rng is None:
            continue
        for tgt in ctn.iter(f"{_P}spTgt"):
            for old in tgt.findall(f"{_P}txEl"):
                tgt.remove(old)
            _el("p:pRg", _el("p:txEl", tgt), st=rng[0], end=rng[1])
        key = (shape.shape_id, ctn.get("presetClass"))
        if key not in para_grp:
            para_grp[key] = next_grp[shape.shape_id]
            next_grp[shape.shape_id] += 1
        ctn.set("grpId", str(para_grp[key]))
    # rebuild the build list: whole-shape text groups animBg, paragraph groups build="p", tables bldGraphic
    old = timing.find(f"{_P}bldLst")
    if old is not None:
        timing.remove(old)
    para_keys = {(sp, g) for (sp, _), g in para_grp.items()}
    entries, seen = [], set()
    by_id = {s.shape_id: s for s, _, _, _ in flat}
    for ctn in ctns:
        spid = int(ctn.find(f".//{_P}spTgt").get("spid"))
        grp = int(ctn.get("grpId"))
        if (spid, grp) in seen:
            continue
        seen.add((spid, grp))
        el = by_id[spid]._element
        if (spid, grp) in para_keys:
            entries.append(("bldP", {"spid": spid, "grpId": grp, "build": "p"}))
        elif el.find(f"{_P}txBody") is not None:
            entries.append(("bldP", {"spid": spid, "grpId": grp, "animBg": 1}))
        elif etree.QName(el).localname == "graphicFrame":
            entries.append(("bldGraphic", {"spid": spid, "grpId": grp}))
    if entries:
        bl = _el("p:bldLst")
        for tag, attrs in entries:
            b = _el(f"p:{tag}", bl, **attrs)
            if tag == "bldGraphic":
                _el("p:bldAsOne", b)
        timing.append(bl)


def add_morph(slide):
    """Give a slide the Morph transition (by object), wrapped for readers without Morph."""
    xml = (f'<mc:AlternateContent xmlns:mc="{NS["mc"]}"><mc:Choice xmlns:p159="{NS["p159"]}" Requires="p159">'
           f'<p:transition xmlns:p="{NS["p"]}" spd="slow"><p159:morph option="byObject"/></p:transition></mc:Choice>'
           f'<mc:Fallback><p:transition xmlns:p="{NS["p"]}" spd="slow"><p:fade/></p:transition></mc:Fallback>'
           "</mc:AlternateContent>")
    ac = _parse(xml)
    sld = slide._element
    anchor = sld.find("p:timing", NS)
    if anchor is None:
        anchor = sld.find("p:extLst", NS)
    if anchor is not None:
        anchor.addprevious(ac)
    else:
        sld.append(ac)


# ---------- entry points ----------

def load_scene(src) -> dict:
    """Read a scene: a dict, a ``.json`` path, or a deck HTML path (measured with ``scene.py``)."""
    if isinstance(src, dict):
        return src
    p = Path(src)
    if not p.is_file():
        raise EmitError(f"no such file: {p}")
    if p.suffix == ".json":
        return json.loads(p.read_text(encoding="utf-8"))
    sm = _scene_mod()
    try:
        return sm.extract(p)
    except sm.SceneError as e:
        raise EmitError(str(e)) from e


def emit(scene, out) -> Path:
    """Emit a scene (dict, scene JSON or deck HTML path) to an editable ``.pptx``.

    Args:
        scene: The scene document, a ``.scene.json`` path or an assembled deck path.
        out: Output ``.pptx`` path; the report goes to ``<stem>.pptx-report.json`` beside it.

    Returns:
        The written ``.pptx`` path.

    Raises:
        EmitError: The scene fails its schema or the deck cannot be measured.
    """
    doc = load_scene(scene)
    errs = _scene_mod().validate(doc, json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
    if errs:
        raise EmitError("scene fails its schema:\n  " + "\n  ".join(errs[:20]))
    em = Emitter(doc)
    prs = em.run()
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(out)
    rep = {"schema": REPORT_SCHEMA, "deck": doc["deck"]["file"], "pptx": out.name,
           "size": {"width": SLIDE_W, "height": int(prs.slide_height)},
           "layouts": list(LAYOUTS), "slides": em.report.slides, "items": em.report.items,
           "counts": {r: sum(1 for i in em.report.items if i["result"] == r)
                      for r in ("native", "approximated", "lost", "dropped", "morph")}}
    out.with_name(out.stem + ".pptx-report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False) + "\n",
                                                              encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    """Command line: emit a deck or scene to PPTX.

    Args:
        argv: Arguments (default ``sys.argv[1:]``).

    Returns:
        Exit code: 0 written, 1 refused.
    """
    ap = argparse.ArgumentParser(prog="emit.py", description="Emit an editable PPTX from a deck or its scene JSON.")
    ap.add_argument("src", type=Path, help="assembled deck HTML or its .scene.json")
    ap.add_argument("-o", "--out", type=Path, help="output .pptx (default: beside the input)")
    a = ap.parse_args(argv)
    try:
        out = a.out or a.src.with_name(a.src.name.split(".")[0] + ".pptx")
        doc = load_scene(a.src)
        if a.src.suffix != ".json":
            sc = out.with_name(out.stem + ".scene.json")
            sc.parent.mkdir(parents=True, exist_ok=True)
            sc.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        path = emit(doc, out)
    except EmitError as e:
        print(f"emit: {e}", file=sys.stderr)
        return 1
    rep = json.loads(path.with_name(path.stem + ".pptx-report.json").read_text(encoding="utf-8"))
    print(f"wrote {path} ({len(rep['slides'])} slides; " +
          ", ".join(f"{v} {k}" for k, v in rep["counts"].items() if v) + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())
