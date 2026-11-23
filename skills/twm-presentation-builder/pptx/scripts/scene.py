# /// script
# requires-python = ">=3.12"
# dependencies = ["playwright>=1.49"]
# ///
"""Measure an assembled deck in Chrome and write its PPTX scene: layout, looks and step timeline.

The scene is the PPTX emitter's only input about the deck (research ``html-to-pptx.md`` §1: measure,
then emit from roles). It never writes PPTX. Contract: ``architecture/ARCHITECTURE.md`` (slides,
steps, component API, ``window.deck``) and ``design/TOKENS.md`` (palette roles + slots, style bands).

Usage (run from the skill folder; needs Chrome or Playwright's Chromium)::

    uv run pptx/scripts/scene.py deck.html [-o deck.scene.json] [--size 1920x1080]

or, imported: ``extract(deck_path, browser=None) -> dict``, ``validate(doc, schema) -> [errors]``.

**How it measures.** The deck opens at the slide size (default 1920×1080 CSS px; 1 px = 9525 EMU)
with reduced motion, so ambient drift is off and design layers keep only fades. Each slide is
stepped from 0 to its last step with ``deck.goto``; after each step every finite animation is
finished (a condition, never a sleep) and every component is measured, visible or not. An
element's **geometry** (box, SVG primitives, text box) comes from the last step it is visible on
(the final state); its **look** (fill, stroke, opacity, effects, run colours) from the first, so
the timeline replays forward from how it enters. Geometry that differs between visible steps (a
camera move) is also listed per step in ``frames``.

**Schema** (``pptx/scene.schema.json``, ``"schema": "pb-scene/1"``)::

    deck     {file, title, subtitle, layout, palette, style}   theme part names as recorded by the assembler
    size     {width, height, unit: "px", emu_per_px: 9525}
    palette  {role: {rgb: "RRGGBB", slots: ["lt1", …]}}         sys.color roles; slots from the tokens
    fonts    {major, minor}                                    the style's theme fonts (null when unknown)
    chrome   {bar: {box, fill}}                                fixed title bar (master material)
    slides[] {id, index, chapter, classes, scene: none|live|backdrop, ambient, steps, background,
              elements[], timeline[], notes[], notes_text}

- **element**: ``id`` (the DOM id, else ``<slide or "scene">/<role>-<n>`` in DOM order; a pseudo
  element is ``<parent id>::before``), ``role`` (below), ``tag``, ``classes`` (state classes
  dropped), ``parent`` (nearest captured ancestor), ``z`` (paint order, 0 = back), ``pseudo``,
  ``scene_part``, ``box`` {x, y, w, h} in slide px, ``measured_at`` (geometry step), ``look_at``,
  ``visible_steps``, ``opacity``, ``fill``/``stroke`` (colour, stroke adds ``width``), ``gradient``
  (raw CSS), ``radius``, ``effects`` [{kind: shadow|backdrop-blur|blur|svg-filter|filter|opacity,
  value, token, band}], ``text`` {runs, align, line_height, lines, box, padding}, ``svg``
  primitives, ``image`` {src, alt}, ``viewbox``, ``frames``.
- **colour**: {rgb: "RRGGBB", alpha, role}; ``role`` is the palette role whose resolved colour
  matches exactly (alpha kept apart), else null (a mix or a literal).
- **effect band**: the style token the value came from (``sys.shadow.overlay``, matched by
  computed value) and its declared ``com.twm.pptx`` band; ``undeclared`` when no style token
  matches (e.g. a components-layer softening). An SVG filter (``#lift``) takes the band shared by
  the ``sys.shadow`` group.
- **run**: {text, font (first family), size (px), weight, italic, caps, tracking (px), underline,
  colour, href}. Joined run text equals the element's DOM text with whitespace collapsed; the text
  of captured children and CSS-generated text (``::before`` labels, counters, quotes) live on
  their own elements.
- **SVG primitive** (slide px, every transform applied, camera included): ``rect`` {x, y, w, h,
  rx, ry} when axis-aligned, ``ellipse`` {cx, cy, rx, ry}, ``line`` {x1, y1, x2, y2}, ``path``
  {d with absolute ``M L C Z`` only (arcs and quadratics become cubics), box = tight bounds},
  ``text`` {x, y anchor point, anchor, baseline, box, runs}; all carry fill, stroke,
  stroke_width, marker_start, marker_end.
- **timeline[k]**: {step, visible: [ids], deltas: [{el, kind: enter|exit|change, property,
  effect, params, …}]}. ``effect`` is a PB-022 effect (``animations.py``) with valid ``params``,
  or ``unsupported`` with ``reason`` and ``fallback`` (``morph``: duplicate slides + Morph;
  ``none``: the effect is lost).

**Roles**: kicker, title, byline, body (the body slot), paragraph, heading, point, step-item, prompt,
stat, quote, cite, caption, table, cell, term, term-title, term-text, insight, overlay,
message-card, sender, message, annotation, narration-tile, popover, pop-panel, tile-card, scene,
diagram, tile, key-tile, edge, label, tag, shape (anything else painted), image, orb, marker
(list discs, bullets, counters), generated-text (CSS ``content`` labels and quotes).

**Delta → effect**: enter → ``fade_in`` (an opacity transition carries it, ``duration_ms`` from
CSS) else ``appear``; exit → ``fade_out``/``disappear``; own opacity → ``transparency``; fill →
``fill_colour``; uniform resize → ``grow_shrink``; move → ``motion_path`` (slide fractions).
Unsupported: a scene camera move (``property: camera``, one delta for the whole scene, morph),
text colour, stroke colour, non-uniform resize and a removed fill (morph); a filter change such
as blur softening (none: lost). A child entering or leaving with its parent gets no delta.

Exit codes: 0 written, 1 refused (not a skill deck, engine never ready, invalid scene); messages
on stderr.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import importlib.util
import json
import math
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2]
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "scene.schema.json"
ASSEMBLE_PY = SKILL_DIR / "scripts" / "assemble.py"
SCHEMA_ID = "pb-scene/1"
EMU_PER_PX = 9525
#: PB-022 effect names (``animations.EFFECTS``); a delta outside them is ``unsupported``.
EFFECTS = ("appear", "fade_in", "disappear", "fade_out", "transparency", "grow_shrink", "fill_colour",
           "motion_path")
MOVE_PX = 1.0       # a box centre shift above this is a move
SCALE_EPS = 0.01    # a size ratio further than this from 1 is a resize
FRAME_PX = 0.5      # geometry within this across visible steps is one frame


class SceneError(Exception):
    """A refusal: not a skill deck, the engine never became ready, or an invalid scene."""


# ---------- SVG paths: absolute M/L/C/Z, transforms, tight bounds ----------

_TOKEN = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")
_ARGS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}


def _arc(x1, y1, rx, ry, phi, large, sweep, x2, y2) -> list[tuple]:
    """Convert an SVG elliptical arc to cubic segments of at most 90° each (SVG 1.1 F.6.5)."""
    if (x1, y1) == (x2, y2):
        return []
    rx, ry = abs(rx), abs(ry)
    if rx == 0 or ry == 0:
        return [("L", x2, y2)]
    cp, sp = math.cos(math.radians(phi)), math.sin(math.radians(phi))
    dx, dy = (x1 - x2) / 2, (y1 - y2) / 2
    x1p, y1p = cp * dx + sp * dy, -sp * dx + cp * dy
    lam = (x1p / rx) ** 2 + (y1p / ry) ** 2
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    co = math.sqrt(max(0.0, num / den)) * (-1 if large == sweep else 1)
    cxp, cyp = co * rx * y1p / ry, -co * ry * x1p / rx
    cx, cy = cp * cxp - sp * cyp + (x1 + x2) / 2, sp * cxp + cp * cyp + (y1 + y2) / 2

    def ang(ux, uy, vx, vy):
        return math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)

    t1 = ang(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dt = ang((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not sweep and dt > 0:
        dt -= 2 * math.pi
    elif sweep and dt < 0:
        dt += 2 * math.pi
    n = max(1, math.ceil(abs(dt) / (math.pi / 2) - 1e-9))
    step = dt / n
    k = 4 / 3 * math.tan(step / 4)
    pt = lambda t: (cx + rx * math.cos(t) * cp - ry * math.sin(t) * sp,
                    cy + rx * math.cos(t) * sp + ry * math.sin(t) * cp)
    dv = lambda t: (-rx * math.sin(t) * cp - ry * math.cos(t) * sp,
                    -rx * math.sin(t) * sp + ry * math.cos(t) * cp)
    out, t = [], t1
    for i in range(n):
        ta, tb = t, t + step
        (ax, ay), (bx, by) = pt(ta), pt(tb)
        (dax, day), (dbx, dby) = dv(ta), dv(tb)
        if i == n - 1:
            bx, by = x2, y2
        out.append(("C", ax + k * dax, ay + k * day, bx - k * dbx, by - k * dby, bx, by))
        t = tb
    return out


def normalise_path(d: str) -> list[tuple]:
    """Rewrite SVG path data as absolute ``M``/``L``/``C``/``Z`` segments.

    Relative commands become absolute, ``H``/``V`` become ``L``, ``S``/``Q``/``T`` and arcs become
    cubics (arcs split at 90°), and implicit repeats are expanded.

    Args:
        d: SVG path data.

    Returns:
        Segments ``("M", x, y)``, ``("L", x, y)``, ``("C", x1, y1, x2, y2, x, y)`` or ``("Z",)``.

    Raises:
        SceneError: On a command missing its arguments.
    """
    toks = _TOKEN.findall(d or "")
    out: list[tuple] = []
    i, cmd = 0, None
    cx = cy = sx = sy = 0.0
    last_c = last_q = None   # reflection points for S and T

    def nums(n: int, arc: bool = False) -> list[float]:
        nonlocal i
        vals: list[float] = []
        while len(vals) < n:
            if i >= len(toks) or toks[i].isalpha():
                raise SceneError(f"path data ends early near token {i}: {d[:60]!r}")
            t = toks[i]
            if arc and len(vals) in (3, 4) and len(t) > 1 and t[0] in "01" and t[1] != ".":
                vals.append(float(t[0]))     # packed flags ("0120" = flag 0, then "120")
                toks[i] = t[1:]
                continue
            vals.append(float(t))
            i += 1
        return vals

    while i < len(toks):
        if toks[i].isalpha():
            cmd = toks[i]
            i += 1
        elif cmd is None:
            raise SceneError(f"path data must start with a command: {d[:60]!r}")
        up, rel = cmd.upper(), cmd.islower()
        if up == "Z":
            out.append(("Z",))
            cx, cy = sx, sy
            last_c = last_q = None
            cmd = None if i >= len(toks) or toks[i].isalpha() else cmd
            if cmd is None:
                continue
            raise SceneError(f"numbers after Z: {d[:60]!r}")
        v = nums(_ARGS[up], arc=up == "A")
        ox, oy = (cx, cy) if rel else (0.0, 0.0)
        if up == "M":
            cx, cy = v[0] + ox, v[1] + oy
            sx, sy = cx, cy
            out.append(("M", cx, cy))
            cmd = "l" if rel else "L"
            last_c = last_q = None
        elif up in ("L", "H", "V"):
            if up == "L":
                cx, cy = v[0] + ox, v[1] + oy
            elif up == "H":
                cx = v[0] + ox
            else:
                cy = v[0] + oy
            out.append(("L", cx, cy))
            last_c = last_q = None
        elif up in ("C", "S"):
            if up == "C":
                x1, y1, x2, y2, x, y = v[0] + ox, v[1] + oy, v[2] + ox, v[3] + oy, v[4] + ox, v[5] + oy
            else:
                x1, y1 = (2 * cx - last_c[0], 2 * cy - last_c[1]) if last_c else (cx, cy)
                x2, y2, x, y = v[0] + ox, v[1] + oy, v[2] + ox, v[3] + oy
            out.append(("C", x1, y1, x2, y2, x, y))
            last_c, last_q = (x2, y2), None
            cx, cy = x, y
        elif up in ("Q", "T"):
            if up == "Q":
                qx, qy, x, y = v[0] + ox, v[1] + oy, v[2] + ox, v[3] + oy
            else:
                qx, qy = (2 * cx - last_q[0], 2 * cy - last_q[1]) if last_q else (cx, cy)
                x, y = v[0] + ox, v[1] + oy
            out.append(("C", cx + 2 / 3 * (qx - cx), cy + 2 / 3 * (qy - cy),
                        x + 2 / 3 * (qx - x), y + 2 / 3 * (qy - y), x, y))
            last_q, last_c = (qx, qy), None
            cx, cy = x, y
        else:  # A
            x, y = v[5] + ox, v[6] + oy
            out.extend(_arc(cx, cy, v[0], v[1], v[2], bool(v[3]), bool(v[4]), x, y))
            cx, cy = x, y
            last_c = last_q = None
    return out


def _apply(m: list[float], x: float, y: float) -> tuple[float, float]:
    a, b, c, dd, e, f = m
    return a * x + c * y + e, b * x + dd * y + f


def transform_segments(segs: list[tuple], m: list[float]) -> list[tuple]:
    """Apply an affine matrix ``[a, b, c, d, e, f]`` to absolute segments (cubics stay cubics).

    Args:
        segs: Output of ``normalise_path``.
        m: SVG matrix mapping user units to slide px.

    Returns:
        The transformed segments.
    """
    out = []
    for s in segs:
        if s[0] == "Z":
            out.append(s)
            continue
        pts = [_apply(m, s[j], s[j + 1]) for j in range(1, len(s), 2)]
        out.append((s[0], *[c for p in pts for c in p]))
    return out


def _cubic_extrema(p0, p1, p2, p3) -> list[float]:
    a = -p0 + 3 * p1 - 3 * p2 + p3
    b = 2 * (p0 - 2 * p1 + p2)
    c = p1 - p0
    ts = []
    if abs(a) < 1e-12:
        if abs(b) > 1e-12:
            ts.append(-c / b)
    else:
        disc = b * b - 4 * a * c
        if disc >= 0:
            r = math.sqrt(disc)
            ts += [(-b + r) / (2 * a), (-b - r) / (2 * a)]
    vals = []
    for t in ts:
        if 0 < t < 1:
            u = 1 - t
            vals.append(u ** 3 * p0 + 3 * u * u * t * p1 + 3 * u * t * t * p2 + t ** 3 * p3)
    return vals


def path_box(segs: list[tuple]) -> dict:
    """Tight bounds of absolute segments (cubic extrema solved, not control points).

    Args:
        segs: Absolute segments.

    Returns:
        ``{x, y, w, h}``.
    """
    xs, ys, cur = [], [], (0.0, 0.0)
    for s in segs:
        if s[0] in "ML":
            cur = (s[1], s[2])
            xs.append(s[1])
            ys.append(s[2])
        elif s[0] == "C":
            x0, y0 = cur
            xs += [x0, s[5]] + _cubic_extrema(x0, s[1], s[3], s[5])
            ys += [y0, s[6]] + _cubic_extrema(y0, s[2], s[4], s[6])
            cur = (s[5], s[6])
    if not xs:
        return {"x": 0, "y": 0, "w": 0, "h": 0}
    return _box(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def _n(v: float) -> float | int:
    """Round to 2 decimals; whole numbers become ints; never ``-0``."""
    r = round(float(v), 2)
    if r == 0:
        return 0
    return int(r) if r == int(r) else r


def _box(x, y, w, h) -> dict:
    return {"x": _n(x), "y": _n(y), "w": _n(w), "h": _n(h)}


def format_d(segs: list[tuple]) -> str:
    """Write segments as path data with single spaces (``M 1 2 L 3 4 Z``)."""
    return " ".join(" ".join([s[0], *[str(_n(c)) for c in s[1:]]]) for s in segs)


# ---------- deck and theme ----------

def _load(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _assemble():
    return _load("pb_assemble", ASSEMBLE_PY)


def read_deck(deck: Path) -> str:
    """Read a deck and refuse anything that is not an assembled skill deck.

    Args:
        deck: Deck HTML file.

    Returns:
        The deck source.

    Raises:
        SceneError: The file is missing, or a block marker is missing, duplicated or out of order.
    """
    try:
        src = Path(deck).read_text(encoding="utf-8")
    except OSError as e:
        raise SceneError(f"cannot read {deck}: {e}") from e
    asm = _assemble()
    try:
        asm.spans(src)
    except asm.AssembleError as e:
        raise SceneError(f"not a skill deck ({Path(deck).name}): {e}") from e
    return src


def theme_info(src: str) -> dict:
    """Read the theme recorded in the deck: palette roles + slots, style effect tokens + bands, fonts.

    Falls back to the PALETTE block's role names (no slots, no bands) when the recorded names do
    not load (e.g. a deck assembled from raw CSS).

    Args:
        src: Deck source.

    Returns:
        ``{names, roles: {role: slots}, tokens: [{path, var, type, band}], fonts, groups}``.
    """
    asm = _assemble()
    names = {k: asm.recorded(src, b) for k, b in (("layout", "COMPONENTS"), ("palette", "PALETTE"),
                                                   ("style", "STYLE"))}
    info = {"names": names, "roles": {}, "tokens": [], "fonts": None, "groups": {}}
    try:
        if not (names["palette"] and names["style"]):
            raise ValueError("no recorded theme")
        tok = asm._tokens()
        theme = tok.load(names["palette"], names["style"])
        for t in tok.flatten(theme.palette, "palette"):
            if t.path.startswith("sys.color."):
                info["roles"][t.path[len("sys.color."):]] = list(t.own_ext("com.twm.pptx", "slots") or [])
        fonts = {}
        for t in tok.flatten(theme.style, "style"):
            if t.path.startswith("ref."):
                continue
            band = t.ext("com.twm.pptx", "band")
            info["tokens"].append({"path": t.path, "var": "--" + t.path.replace(".", "-"),
                                   "type": t.type, "band": band})
            slot = t.own_ext("com.twm.pptx", "fontSlot")
            if slot:
                v = tok.resolve(theme, t.path)
                fonts[slot] = v[0] if isinstance(v, list) else v
        info["fonts"] = {"major": fonts.get("major"), "minor": fonts.get("minor")}
    except Exception:  # noqa: BLE001 - any failure means "theme unknown": fall back to the CSS
        pal = asm.read_block(src, "PALETTE")
        info["roles"] = {r: [] for r in dict.fromkeys(re.findall(r"--sys-color-([a-z0-9-]+)\s*:", pal))}
        info["tokens"] = []
    for prefix in ("sys.shadow",):
        bands = {t["band"] for t in info["tokens"] if t["path"].startswith(prefix + ".")}
        info["groups"][prefix] = bands.pop() if len(bands) == 1 else None
    return info


# ---------- in-page scripts ----------

SETTLE_JS = """async () => {
  const raf = () => new Promise(r => requestAnimationFrame(() => r()));
  for (let i = 0; i < 60; i++) {
    await raf(); await raf();
    const live = document.getAnimations().filter(a => a.playState !== 'finished' && a.playState !== 'idle'
      && a.effect && Number.isFinite(a.effect.getComputedTiming().endTime));
    if (!live.length) return true;
    live.forEach(a => { try { a.finish(); } catch (e) { /* already gone */ } });
  }
  return false;
}"""

PROBE_JS = """([roles, vars]) => {
  const root = getComputedStyle(document.documentElement), d = document.createElement('div');
  d.style.position = 'absolute'; d.style.visibility = 'hidden'; document.body.append(d);
  const read = (prop, v) => { d.style[prop] = ''; d.style[prop] = v; const out = getComputedStyle(d)[prop]; d.style[prop] = ''; return out; };
  const colours = {}, shadows = {}, lengths = {}, raw = {};
  roles.forEach(r => { if (root.getPropertyValue('--sys-color-' + r).trim()) colours[r] = read('color', `var(--sys-color-${r})`); });
  vars.forEach(v => { const val = root.getPropertyValue(v).trim(); if (!val) return; raw[v] = val;
    shadows[v] = read('boxShadow', `var(${v})`); lengths[v] = read('width', `var(${v})`); });
  d.remove();
  const bar = document.querySelector('.bar'), sub = document.querySelector('.bar-title em');
  const br = bar && bar.getBoundingClientRect();
  return { colours, shadows, lengths, raw, title: document.title, subtitle: sub ? sub.textContent.trim() : '',
    bar: bar ? { box: { x: br.left, y: br.top, w: br.width, h: br.height }, fill: getComputedStyle(bar).backgroundColor } : null };
}"""

MEASURE_JS = r"""slideId => {
  const s = document.getElementById(slideId);
  const sr = s.getBoundingClientRect(), ox = sr.left, oy = sr.top;
  const sceneEl = s.hasAttribute('data-scene') ? document.querySelector('.scene') : null;
  const R = v => Math.round(v * 100) / 100;
  const cs = (e, p) => getComputedStyle(e, p);
  const bx = r => ({ x: R(r.left - ox), y: R(r.top - oy), w: R(r.width), h: R(r.height) });
  const HTML_ROLES = [['.orb', 'orb'], ['.overlay--insight', 'insight'], ['.overlay', 'overlay'], ['.popover', 'popover'],
    ['.pop-panel', 'pop-panel'], ['.narr-tile', 'narration-tile'], ['.text-tile', 'tile-card'], ['.msg-card', 'message-card'],
    ['.annot', 'annotation'], ['.scene', 'scene'], ['.body', 'body'], ['.kicker', 'kicker'], ['.title', 'title'],
    ['.byline', 'byline'], ['.steps > li', 'step-item'], ['.points > li', 'point'], ['.prompts > li', 'prompt'],
    ['.stat', 'stat'], ['.msg-agent, .msg-from', 'sender'], ['.msg-text', 'message'], ['blockquote', 'quote'],
    ['.cite', 'cite'], ['.caption, figcaption', 'caption'], ['table', 'table'], ['th, td', 'cell'], ['.terms > div', 'term'],
    ['dt', 'term-title'], ['dd', 'term-text'], ['h1, h2, h3, h4, h5, h6', 'heading'], ['img', 'image'], ['p, li', 'paragraph']];
  const SVG_ROLES = [['g.tile.tile--key', 'key-tile'], ['g.tile', 'tile'], ['.edge', 'edge'], ['text.tag', 'tag'],
    ['text', 'label'], ['rect, circle, ellipse, line, path, polyline, polygon', 'shape']];
  const SKIP = '.note, .scene-slot, script, style, template, defs, marker, clipPath, mask, pattern, linearGradient, radialGradient, filter, symbol';
  const NO_PSEUDO = new Set(['orb', 'scene', 'body', 'table']);
  const OWN_SUBTREE = new Set(['tile', 'key-tile', 'edge', 'tag', 'label', 'shape', 'image']);
  const alpha = c => { const m = /\/\s*([\d.]+)\)$|rgba\([^)]*,\s*([\d.]+)\)$/.exec(c || ''); return m ? +(m[1] ?? m[2]) : (c === 'transparent' ? 0 : 1); };
  const painted = e => { const c = cs(e);
    if (['inline', 'contents', 'none'].includes(c.display)) return false;
    return alpha(c.backgroundColor) > 0 || c.backgroundImage !== 'none' || c.boxShadow !== 'none'
      || (parseFloat(c.borderTopWidth) > 0 && c.borderTopStyle !== 'none' && alpha(c.borderTopColor) > 0); };

  // ---- candidates in paint-relevant DOM order (scene first: it sits before the slides) ----
  const cands = [], idOf = new Map(), counters = {};
  const visit = (e, scope) => {
    if (e.matches(SKIP)) return;
    let role = null;
    if (e instanceof SVGElement) {
      if (e.tagName.toLowerCase() === 'svg') role = e.classList.contains('diagram') ? 'diagram' : 'image';
      else role = (SVG_ROLES.find(([sel]) => e.matches(sel)) || [])[1] || null;
    } else {
      role = (HTML_ROLES.find(([sel]) => e.matches(sel)) || [])[1] || null;
      if (!role && painted(e)) role = 'shape';
    }
    if (role) {
      const key = scope + '/' + role; counters[key] = (counters[key] || 0) + 1;
      const id = e.id || (role === 'scene' ? 'scene' : `${scope}/${role}-${counters[key]}`);
      cands.push({ e, role, scope, id, order: cands.length });
      idOf.set(e, id);
      if (e instanceof SVGElement && OWN_SUBTREE.has(role)) return;
    }
    for (const c of e.children) visit(c, scope);
  };
  if (sceneEl) visit(sceneEl, 'scene');
  for (const c of s.children) visit(c, slideId);
  const captured = new Set(cands.map(c => c.e));
  const parentsOf = e => { const out = [];
    for (let n = e.parentElement; n && n !== s && n !== document.body; n = n.parentElement) if (idOf.has(n)) out.push(idOf.get(n));
    return out; };

  const visible = e => {
    let op = 1;
    for (let n = e; n && n.nodeType === 1; n = n.parentElement) { const c = cs(n); if (c.display === 'none') return false; op *= +c.opacity; }
    const r = e.getBoundingClientRect();
    return cs(e).visibility !== 'hidden' && op > 0.01 && (r.width > 0 || r.height > 0);
  };
  const ztop = e => { let n = e; while (n.parentElement && n.parentElement !== s && n !== sceneEl) n = n.parentElement;
    return parseInt(cs(n).zIndex) || 0; };
  const ms = v => v.trim().endsWith('ms') ? parseFloat(v) : parseFloat(v) * 1000;
  const fadeMs = e => { let best = 0;
    for (let n = e; n && n.nodeType === 1 && n !== s; n = n.parentElement) {
      if (n !== e && captured.has(n)) break;
      const c = cs(n), props = c.transitionProperty.split(','), durs = c.transitionDuration.split(',');
      props.forEach((p, i) => { p = p.trim(); if (p === 'opacity' || p === 'all') best = Math.max(best, ms(durs[i % durs.length])); });
      if (n === sceneEl) break;
    }
    return Math.round(best); };
  const font1 = f => f.split(',')[0].trim().replace(/^["']|["']$/g, '');
  const runOf = (n, text, svg, k) => { const c = cs(n), a = n.closest('a[href]');
    return { text, font: font1(c.fontFamily), size: R(parseFloat(c.fontSize) * k), weight: +c.fontWeight || 400,
      italic: c.fontStyle !== 'normal', caps: c.textTransform === 'uppercase',
      tracking: c.letterSpacing === 'normal' ? 0 : R((parseFloat(c.letterSpacing) || 0) * k),
      underline: c.textDecorationLine.includes('underline'), colour: svg ? c.fill : c.color,
      href: a ? a.getAttribute('href') : null }; };
  const ctmScale = e => { const m = e.getScreenCTM && e.getScreenCTM(); return m ? Math.sqrt(Math.abs(m.a * m.d - m.b * m.c)) : 1; };
  const textOf = (e, svg) => {
    const runs = [], nodes = [], k = svg ? ctmScale(e) : 1;
    const walk = n => { for (const c of n.childNodes) {
      if (c.nodeType === 3) { runs.push(runOf(c.parentElement, c.data, svg, k)); nodes.push(c); }
      else if (c.nodeType === 1) {
        if (captured.has(c) || c.matches(SKIP)) continue;
        if (c.tagName === 'BR') { runs.push(runOf(c.parentElement, '\n', svg, k)); continue; }
        if (cs(c).display === 'none') continue;
        walk(c);
      } } };
    walk(e);
    if (!runs.some(r => r.text.trim())) return null;
    const c = cs(e);
    const al = { start: 'left', end: 'right', '-webkit-center': 'center', '-webkit-left': 'left', '-webkit-right': 'right' }[c.textAlign] || c.textAlign;
    let rects = [];
    if (!svg) rects = nodes.flatMap(n => { const rg = document.createRange(); rg.selectNodeContents(n); return [...rg.getClientRects()]; })
      .filter(q => q.width > 0 && q.height > 0);
    let lines = 1, box = bx(e.getBoundingClientRect());
    if (rects.length) {
      const mids = rects.map(q => [(q.top + q.bottom) / 2, q.height]).sort((a, b) => a[0] - b[0]);
      lines = 1; let last = mids[0][0];
      mids.forEach(([m, h]) => { if (m - last > h / 2) { lines++; last = m; } });
      const l = Math.min(...rects.map(q => q.left)), t = Math.min(...rects.map(q => q.top));
      box = bx({ left: l, top: t, width: Math.max(...rects.map(q => q.right)) - l, height: Math.max(...rects.map(q => q.bottom)) - t });
    }
    const fs = parseFloat(c.fontSize);
    return { runs, align: svg ? ({ middle: 'center', end: 'right' }[c.textAnchor] || 'left') : al,
      line_height: R(c.lineHeight === 'normal' ? fs * 1.2 : parseFloat(c.lineHeight)), lines, box,
      padding: svg ? [0, 0, 0, 0] : [c.paddingTop, c.paddingRight, c.paddingBottom, c.paddingLeft].map(v => R(parseFloat(v) || 0)) };
  };
  const marker = v => { const m = /url\("?#([^")]+)"?\)/.exec(v || ''); return m ? '#' + m[1] : null; };
  const prim = g => {
    const c = cs(g), tag = g.tagName.toLowerCase(), M = g.getScreenCTM();
    if (c.display === 'none' || !M) return null;
    const out = { type: tag, m: [M.a, M.b, M.c, M.d, M.e - ox, M.f - oy], fill: c.fill, stroke: c.stroke,
      sw: parseFloat(c.strokeWidth) || 0, marker_start: marker(c.markerStart), marker_end: marker(c.markerEnd) };
    if (tag === 'rect' || tag === 'circle' || tag === 'ellipse') {
      const b = g.getBBox(); Object.assign(out, { x: b.x, y: b.y, w: b.width, h: b.height });
      if (tag === 'rect') { let rx = parseFloat(c.rx), ry = parseFloat(c.ry);
        if (!isFinite(rx)) rx = isFinite(ry) ? ry : 0; if (!isFinite(ry)) ry = rx;
        out.rx = Math.min(rx, b.width / 2); out.ry = Math.min(ry, b.height / 2); }
    } else if (tag === 'line') {
      Object.assign(out, { x1: g.x1.baseVal.value, y1: g.y1.baseVal.value, x2: g.x2.baseVal.value, y2: g.y2.baseVal.value });
    } else if (tag === 'path') {
      out.d = c.d && c.d !== 'none' ? c.d.slice(6, -2) : (g.getAttribute('d') || '');
    } else if (tag === 'polyline' || tag === 'polygon') {
      out.points = g.getAttribute('points') || '';
    } else if (tag === 'text') {
      const xs = g.x.baseVal, ys = g.y.baseVal;
      Object.assign(out, { x: xs.length ? xs[0].value : 0, y: ys.length ? ys[0].value : 0, anchor: c.textAnchor,
        baseline: c.dominantBaseline, box: bx(g.getBoundingClientRect()), text: textOf(g, true) });
      if (!out.text) return null;
    } else return null;
    return out;
  };
  const prims = e => {
    const GEOM = 'rect, circle, ellipse, line, path, polyline, polygon, text';
    const list = e.matches(GEOM) ? [e] : [...e.querySelectorAll(GEOM)].filter(g => !g.closest(SKIP));
    return list.map(prim).filter(Boolean);
  };
  const gen = (e, content) => { let out = '', m; const re = /"((?:[^"\\]|\\.)*)"|counter\(\s*([\w-]+)[^)]*\)|(no-)?(open|close)-quote/g;
    while ((m = re.exec(content))) {
      if (m[1] != null) out += m[1].replace(/\\(.)/g, '$1');
      else if (m[2]) out += String([...e.parentElement.children].filter(x => x.tagName === e.tagName).indexOf(e) + 1);
      else if (!m[3]) out += m[4] === 'open' ? '“' : '”';
    }
    return out; };
  const border = c => { const ws = ['Top', 'Right', 'Bottom', 'Left'].map(k => parseFloat(c[`border${k}Width`]) || 0);
    if (!ws[0] || c.borderTopStyle === 'none' || ws.some(w => Math.abs(w - ws[0]) > .01)) return null;
    return { c: c.borderTopColor, w: R(ws[0]) }; };

  const recs = [];
  cands.forEach(cd => {
    const e = cd.e, c = cs(e), svg = e instanceof SVGElement;
    const r = { id: cd.id, role: cd.role, tag: e.tagName.toLowerCase(), classes: [...e.classList].filter(k => !/^(is|was)-/.test(k)),
      parents: parentsOf(e), zkey: [ztop(e), cd.order], pseudo: null, scene_part: cd.scope === 'scene', visible: visible(e),
      box: bx(e.getBoundingClientRect()), opacity: R(+c.opacity), fill: null, gradient: null, stroke: null, radius: null,
      shadow: 'none', backdrop: 'none', filters: [c.filter], fade: fadeMs(e), text: null, svg: null, image: null, viewbox: null };
    if (svg) {
      if (cd.role === 'diagram' || cd.role === 'image') {
        const vb = e.viewBox && e.viewBox.baseVal;
        if (vb && vb.width) r.viewbox = [vb.x, vb.y, vb.width, vb.height].map(R);
        if (cd.role === 'image') r.svg = prims(e);
      } else {
        r.svg = prims(e);
        const shape = e.matches('g') ? e.querySelector('rect, circle, ellipse, path, polygon') : e;
        if (shape) { const sc = cs(shape), k = ctmScale(shape);
          r.fill = sc.fill; r.stroke = { c: sc.stroke, w: R((parseFloat(sc.strokeWidth) || 0) * k) };
          if (shape !== e) r.filters.push(sc.filter); }
        if (cd.role === 'label' || cd.role === 'tag') r.text = textOf(e, true);
      }
    } else {
      r.fill = c.backgroundColor;
      r.gradient = c.backgroundImage !== 'none' ? c.backgroundImage : null;
      r.stroke = border(c);
      r.radius = R(parseFloat(c.borderTopLeftRadius) || 0);
      r.shadow = c.boxShadow; r.backdrop = c.backdropFilter || c.webkitBackdropFilter || 'none';
      if (cd.role === 'image') r.image = { src: e.getAttribute('src') || '', alt: e.getAttribute('alt') || '' };
      if (!['orb', 'scene'].includes(cd.role)) r.text = textOf(e, false);
    }
    recs.push(r);
    if (svg || NO_PSEUDO.has(cd.role)) return;
    ['::before', '::after'].forEach((which, wi) => {
      const p = cs(e, which), content = p.content;
      if (!content || content === 'none' || content === 'normal' || p.display === 'none') return;
      const text = gen(e, content), pr = e.getBoundingClientRect();
      const bl = parseFloat(c.borderLeftWidth) || 0, bt = parseFloat(c.borderTopWidth) || 0;
      const fs = parseFloat(p.fontSize), lh = p.lineHeight === 'normal' ? fs * 1.2 : parseFloat(p.lineHeight);
      let w = parseFloat(p.width), h = parseFloat(p.height), x, y;
      if (!isFinite(w)) w = Math.max(fs * .5, text.length * fs * .55);
      if (!isFinite(h)) h = lh;
      if (p.position === 'absolute' || p.position === 'fixed') {
        x = isFinite(parseFloat(p.left)) ? pr.left + bl + parseFloat(p.left) : pr.right - (parseFloat(c.borderRightWidth) || 0) - (parseFloat(p.right) || 0) - w;
        y = isFinite(parseFloat(p.top)) ? pr.top + bt + parseFloat(p.top) : pr.bottom - (parseFloat(c.borderBottomWidth) || 0) - (parseFloat(p.bottom) || 0) - h;
      } else {
        x = pr.left + bl + (parseFloat(c.paddingLeft) || 0); y = pr.top + bt + (parseFloat(c.paddingTop) || 0);
        if (wi === 1) y = pr.bottom - (parseFloat(c.borderBottomWidth) || 0) - (parseFloat(c.paddingBottom) || 0) - h;
      }
      const run = text ? [{ text, font: font1(p.fontFamily), size: R(fs), weight: +p.fontWeight || 400, italic: p.fontStyle !== 'normal',
        caps: p.textTransform === 'uppercase', tracking: p.letterSpacing === 'normal' ? 0 : R(parseFloat(p.letterSpacing) || 0),
        underline: p.textDecorationLine.includes('underline'), colour: p.color, href: null }] : null;
      const al = { start: 'left', end: 'right' }[p.textAlign] || p.textAlign;
      recs.push({ id: `${cd.id}${which}`, role: (text && !/counter\(/.test(content) && !/^["']?\s*["']?$/.test(content)) ? 'generated-text' : 'marker',
        tag: which, classes: [], parents: [cd.id, ...r.parents], zkey: [r.zkey[0], cd.order + .5], pseudo: which.slice(2),
        scene_part: r.scene_part, visible: r.visible, box: bx({ left: x, top: y, width: w, height: h }), opacity: R(+p.opacity),
        fill: p.backgroundColor, gradient: p.backgroundImage !== 'none' ? p.backgroundImage : null, stroke: border(p),
        radius: R(parseFloat(p.borderTopLeftRadius) || 0), shadow: p.boxShadow, backdrop: 'none', filters: [p.filter], fade: 0,
        text: run ? { runs: run, align: al, line_height: R(lh), lines: 1, box: bx({ left: x, top: y, width: w, height: h }),
          padding: [0, 0, 0, 0] } : null, svg: null, image: null, viewbox: null });
    });
  });

  const nearest = t => { for (let n = t; n; n = n.parentElement) if (idOf.has(n)) return idOf.get(n); return null; };
  const notes = [...s.querySelectorAll('aside.note')].map(n => {
    const sel = n.dataset.for || ''; let t = null;
    try { t = (sel && (s.querySelector(sel) || (sceneEl && sceneEl.querySelector(sel)))) || null; } catch (err) { t = null; }
    const h = n.querySelector('h3'), clean = v => (v || '').replace(/\s+/g, ' ').trim();
    return { for: sel, target: t ? nearest(t) : null, heading: clean(h && h.textContent),
      text: [...n.querySelectorAll('p')].map(p => clean(p.textContent)).filter(Boolean),
      sources: [...n.querySelectorAll('a.src')].map(a => ({ text: clean(a.textContent), href: a.getAttribute('href') || '' })) };
  });
  let bg = 'transparent';
  for (const n of [s, document.body, document.documentElement]) { const v = cs(n).backgroundColor; if (alpha(v) > 0) { bg = v; break; } }
  const cam = sceneEl && sceneEl.querySelector('.cam');
  return { recs, notes, camera: cam ? (cam.style.transform || 'none') : null,
    slide: { chapter: s.dataset.chapter || '', classes: [...s.classList].filter(k => k !== 'slide' && !/^(is|was)-/.test(k)),
      scene: s.hasAttribute('data-scene') ? (s.dataset.scene === 'backdrop' ? 'backdrop' : 'live') : 'none',
      ambient: s.hasAttribute('data-ambient'), background: bg } };
}"""


# ---------- colours and effects ----------

def _parse_colour(raw) -> tuple[list[int], float] | None:
    """Parse a computed CSS colour into ``([r, g, b], alpha)``; None for none/transparent/url()."""
    if not raw or raw in ("none", "transparent") or raw.startswith("url"):
        return None
    m = re.fullmatch(r"rgba?\(([^)]*)\)", raw.strip())
    if m:
        p = [float(x) for x in re.split(r"[\s,/]+", m.group(1).strip()) if x]
        return [round(v) for v in p[:3]], (p[3] if len(p) > 3 else 1.0)
    m = re.fullmatch(r"color\(srgb ([^)]*)\)", raw.strip())
    if m:
        p = [float(x) for x in re.split(r"[\s/]+", m.group(1).strip()) if x]
        return [round(v * 255) for v in p[:3]], (p[3] if len(p) > 3 else 1.0)
    return None


class _Ctx:
    """Per-deck lookups: palette role colours and the style's effect tokens with their probed values."""

    def __init__(self, info: dict, probes: dict):
        self.info = info
        self.role_rgb: dict[str, str] = {}
        for role, raw in probes["colours"].items():
            c = _parse_colour(raw)
            if c:
                self.role_rgb[role] = "".join(f"{v:02X}" for v in c[0])
        self.tokens = []
        for t in info["tokens"]:
            if t["var"] not in probes["raw"]:
                continue
            raw = probes["raw"][t["var"]]
            num = None
            try:
                num = float(raw)
            except ValueError:
                pass
            length = None
            if t["type"] == "dimension":
                m = re.fullmatch(r"(-?[\d.]+)px", probes["lengths"].get(t["var"], ""))
                length = float(m.group(1)) if m else None
            self.tokens.append({**t, "num": num, "length": length,
                                "shadow": probes["shadows"].get(t["var"]) if t["type"] == "shadow" else None})

    def colour(self, raw) -> dict | None:
        c = _parse_colour(raw)
        if not c or c[1] <= 0.001:
            return None
        rgb = "".join(f"{v:02X}" for v in c[0])
        role = next((r for r, v in self.role_rgb.items() if v == rgb), None)
        return {"rgb": rgb, "alpha": round(c[1], 3), "role": role}

    def _match(self, pred) -> dict | None:
        return next((t for t in self.tokens if pred(t)), None)

    def _effect(self, kind: str, value: str, tok: dict | None, band=None) -> dict:
        b = tok["band"] if tok else band
        return {"kind": kind, "value": value, "token": tok["path"] if tok else None,
                "band": b if b in ("native", "approximated", "lost") else "undeclared"}

    def blur_token(self, px: float) -> dict | None:
        return self._match(lambda t: "blur" in t["path"] and t["length"] is not None and abs(t["length"] - px) < .01)

    def effects(self, rec: dict) -> list[dict]:
        out = []
        if rec["shadow"] and rec["shadow"] != "none":
            tok = self._match(lambda t: t["shadow"] == rec["shadow"])
            out.append(self._effect("shadow", rec["shadow"], tok, None if tok else self.info["groups"].get("sys.shadow")))
        if rec["backdrop"] and rec["backdrop"] != "none":
            m = re.search(r"blur\(([\d.]+)px\)", rec["backdrop"])
            out.append(self._effect("backdrop-blur", rec["backdrop"], self.blur_token(float(m.group(1))) if m else None))
        for f in rec["filters"]:
            if not f or f == "none":
                continue
            for part in re.findall(r"[a-z-]+\((?:[^()]|\([^()]*\))*\)", f):
                if part.startswith("url("):
                    ref = re.search(r"#([^\")]+)", part)
                    out.append(self._effect("svg-filter", "#" + (ref.group(1) if ref else ""), None,
                                            self.info["groups"].get("sys.shadow")))
                elif part.startswith("blur("):
                    px = float(re.search(r"[\d.]+", part).group(0))
                    out.append(self._effect("blur", part, self.blur_token(px)))
                elif part.startswith("drop-shadow("):
                    out.append(self._effect("shadow", part, None, self.info["groups"].get("sys.shadow")))
                else:   # e.g. saturate(1.15): the style token of that name and value, if any
                    fn, val = part.split("(", 1)
                    num = re.match(r"\s*(-?[\d.]+)", val)
                    want = float(num.group(1)) if num else None
                    tok = self._match(lambda t, fn=fn, want=want: want is not None and fn in t["path"]
                                      and t["num"] is not None and abs(t["num"] - want) < .005)
                    out.append(self._effect("filter", part, tok or None))
        if rec["opacity"] < 0.999:
            tok = self._match(lambda t: t["path"].endswith("opacity") and t["num"] is not None
                              and abs(t["num"] - rec["opacity"]) < .005)
            out.append(self._effect("opacity", str(rec["opacity"]), tok))
        return out


# ---------- per-element records ----------

_STYLE_KEYS = ("font", "size", "weight", "italic", "caps", "tracking", "underline", "colour", "href")


def _runs(raw: list[dict], ctx: _Ctx) -> list[dict]:
    """Collapse whitespace like CSS ``white-space: normal`` and merge same-style runs."""
    runs = []
    for r in raw:
        t = r["text"] if r["text"] == "\n" else re.sub(r"\s+", " ", r["text"])
        runs.append({**{k: r[k] for k in _STYLE_KEYS}, "text": t, "colour": ctx.colour(r["colour"])})
    space = True
    for r in runs:
        if r["text"] == "\n":
            space = True
            continue
        if space and r["text"].startswith(" "):
            r["text"] = r["text"][1:]
        if r["text"]:
            space = r["text"].endswith(" ")
    for r in reversed(runs):
        r["text"] = r["text"].rstrip(" ") if r["text"] != "\n" else ""
        if r["text"]:
            break
    out: list[dict] = []
    for r in runs:
        if not r["text"]:
            continue
        if out and all(out[-1][k] == r[k] for k in _STYLE_KEYS):
            out[-1]["text"] += r["text"]
        else:
            out.append({"text": r["text"], **{k: r[k] for k in _STYLE_KEYS}})
    for r in out:
        r["size"], r["tracking"] = _n(r["size"]), _n(r["tracking"])
    return out


def _text(t: dict | None, ctx: _Ctx) -> dict | None:
    if not t:
        return None
    runs = _runs(t["runs"], ctx)
    if not runs:
        return None
    return {"runs": runs, "align": t["align"], "line_height": _n(t["line_height"]), "lines": t["lines"],
            "box": _box(**t["box"]), "padding": [_n(v) for v in t["padding"]]}


def _primitive(p: dict, ctx: _Ctx) -> dict:
    """Turn an in-page primitive (user units + screen matrix) into slide-px geometry."""
    m = p["m"]
    k = math.sqrt(abs(m[0] * m[3] - m[1] * m[2]))
    axis = abs(m[1]) < 1e-9 and abs(m[2]) < 1e-9
    base = {"fill": ctx.colour(p["fill"]), "stroke": ctx.colour(p["stroke"]), "stroke_width": _n(p["sw"] * k),
            "marker_start": p["marker_start"], "marker_end": p["marker_end"]}
    t = p["type"]
    if t == "rect" and axis:
        x0, y0 = _apply(m, p["x"], p["y"])
        x1, y1 = _apply(m, p["x"] + p["w"], p["y"] + p["h"])
        return {"type": "rect", **_box(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0)),
                "rx": _n(p["rx"] * abs(m[0])), "ry": _n(p["ry"] * abs(m[3])), **base}
    if t in ("circle", "ellipse") and axis:
        cx, cy = _apply(m, p["x"] + p["w"] / 2, p["y"] + p["h"] / 2)
        return {"type": "ellipse", "cx": _n(cx), "cy": _n(cy), "rx": _n(p["w"] / 2 * abs(m[0])),
                "ry": _n(p["h"] / 2 * abs(m[3])), **base}
    if t == "line":
        (x1, y1), (x2, y2) = _apply(m, p["x1"], p["y1"]), _apply(m, p["x2"], p["y2"])
        return {"type": "line", "x1": _n(x1), "y1": _n(y1), "x2": _n(x2), "y2": _n(y2), **base}
    if t == "text":
        x, y = _apply(m, p["x"], p["y"])
        return {"type": "text", "x": _n(x), "y": _n(y), "anchor": p["anchor"], "baseline": p["baseline"],
                "box": _box(**p["box"]), "runs": _runs(p["text"]["runs"], ctx), **base}
    if t == "rect":
        x, y, w, h = p["x"], p["y"], p["w"], p["h"]
        segs = [("M", x, y), ("L", x + w, y), ("L", x + w, y + h), ("L", x, y + h), ("Z",)]
    elif t in ("circle", "ellipse"):
        cx, cy, rx, ry = p["x"] + p["w"] / 2, p["y"] + p["h"] / 2, p["w"] / 2, p["h"] / 2
        segs = normalise_path(f"M {cx - rx} {cy} A {rx} {ry} 0 1 1 {cx + rx} {cy} A {rx} {ry} 0 1 1 {cx - rx} {cy} Z")
    elif t in ("polyline", "polygon"):
        pts = [float(v) for v in re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?", p["points"])]
        pairs = list(zip(pts[0::2], pts[1::2]))
        segs = [("M", *pairs[0])] + [("L", *q) for q in pairs[1:]] if pairs else []
        if t == "polygon" and segs:
            segs.append(("Z",))
    else:
        segs = normalise_path(p["d"])
    segs = transform_segments(segs, m)
    return {"type": "path", "d": format_d(segs), "box": path_box(segs), **base}


def _geometry(rec: dict, ctx: _Ctx) -> tuple:
    svg = [_primitive(p, ctx) for p in rec["svg"]] if rec["svg"] is not None else None
    return _box(**rec["box"]), svg


def _close(a: dict, b: dict, tol: float) -> bool:
    return all(abs(a[k] - b[k]) <= tol for k in ("x", "y", "w", "h"))


def _element(eid: str, snaps: list[dict], steps: list[int], final_ids: set, ctx: _Ctx) -> dict:
    """Combine one element's per-step records: geometry from its last visible step, look from its first."""
    g, look = snaps[steps[-1]][eid], snaps[steps[0]][eid]
    box, svg = _geometry(g, ctx)
    geo = [(k, *_geometry(snaps[k][eid], ctx)) for k in steps]
    varied = any(not _close(b, box, FRAME_PX) for _, b, _ in geo) or any(
        json.dumps(s) != json.dumps(svg) for _, _, s in geo)
    stroke = None
    if look["stroke"]:
        col = ctx.colour(look["stroke"]["c"])
        if col and look["stroke"]["w"] > 0:
            stroke = {**col, "width": _n(look["stroke"]["w"])}
    return {
        "id": eid, "role": g["role"], "tag": g["tag"], "classes": g["classes"],
        "parent": next((p for p in g["parents"] if p in final_ids), None), "z": 0,
        "pseudo": g["pseudo"], "scene_part": g["scene_part"], "box": box, "measured_at": steps[-1],
        "look_at": steps[0], "visible_steps": steps, "opacity": _n(look["opacity"]),
        "fill": ctx.colour(look["fill"]), "gradient": look["gradient"], "stroke": stroke,
        "radius": _n(look["radius"]) if look["radius"] is not None else None,
        "effects": ctx.effects(look), "text": _with_look(_text(g["text"], ctx), look, ctx),
        "svg": svg, "image": g["image"], "viewbox": [_n(v) for v in g["viewbox"]] if g["viewbox"] else None,
        "frames": [{"step": k, "box": b, "svg": s} for k, b, s in geo] if varied else None,
    }


def _with_look(text: dict | None, look: dict, ctx: _Ctx) -> dict | None:
    """Take run colours from the element's first visible step (geometry stays from the last)."""
    if text is None:
        return None
    first = _text(look["text"], ctx)
    if first and len(first["runs"]) == len(text["runs"]):
        for r, f in zip(text["runs"], first["runs"]):
            r["colour"] = f["colour"]
    return text


# ---------- timeline ----------

def _camera(v) -> list[float] | str | None:
    if v is None:
        return None
    m = re.fullmatch(r"translate\((-?[\d.]+)px,\s*(-?[\d.]+)px\)\s*scale\((-?[\d.]+)\)", v.strip())
    return [_n(float(x)) for x in m.groups()] if m else v


def _run_colours(rec: dict, ctx: _Ctx) -> list:
    t = _text(rec["text"], ctx)
    return [r["colour"] for r in t["runs"]] if t else []


def _deltas(k: int, prev: dict, now: dict, order: list[str], cam: tuple, ctx: _Ctx, size: tuple, scene_id) -> list[dict]:
    """Changes from step k-1 to step k, in z order, expressed in the PB-022 vocabulary where possible."""
    W, H = size
    out: list[dict] = []
    moved_cam = cam[0] != cam[1]
    if moved_cam and scene_id:
        out.append({"el": scene_id, "kind": "change", "property": "camera", "effect": "unsupported", "params": {},
                    "reason": "a scene camera move pans and zooms the whole scene at once; no single native effect",
                    "fallback": "morph", "from": cam[0], "to": cam[1]})
    entered = {i for i in order if i in now and now[i]["visible"] and not (i in prev and prev[i]["visible"])}
    left = {i for i in order if i in prev and prev[i]["visible"] and not (i in now and now[i]["visible"])}
    for i in order:
        a, b = prev.get(i), now.get(i)
        if i in entered or i in left:
            rec = b if b is not None else a
            if set(rec["parents"]) & (entered if i in entered else left):
                continue   # carried by its parent
            fade = (b or a)["fade"]
            eff = ("fade_in" if fade else "appear") if i in entered else ("fade_out" if fade else "disappear")
            out.append({"el": i, "kind": "enter" if i in entered else "exit", "property": "visibility",
                        "effect": eff, "params": {"duration_ms": fade} if fade else {}})
            continue
        if not (a and b and a["visible"] and b["visible"]):
            continue

        def change(prop, effect, params=None, _el=i, **extra):
            out.append({"el": _el, "kind": "change", "property": prop, "effect": effect, "params": params or {}, **extra})

        if abs(a["opacity"] - b["opacity"]) > 0.01:
            change("opacity", "transparency", {"opacity": round(min(1.0, max(0.0, b["opacity"])), 3)})
        fa, fb = ctx.colour(a["fill"]), ctx.colour(b["fill"])
        if fa != fb:
            if fb:
                change("fill", "fill_colour", {"rgb": fb["rgb"]}, role=fb["role"])
            else:
                change("fill", "unsupported", reason="the fill is removed", fallback="morph")
        sa = ctx.colour(a["stroke"]["c"]) if a["stroke"] else None
        sb = ctx.colour(b["stroke"]["c"]) if b["stroke"] else None
        if sa != sb:
            change("stroke", "unsupported", reason="line colour is not in the PB-022 vocabulary", fallback="morph",
                   to=sb)
        ca, cb = _run_colours(a, ctx), _run_colours(b, ctx)
        if len(ca) == len(cb) and ca != cb:
            change("text-colour", "unsupported", reason="font colour is not in the PB-022 vocabulary",
                   fallback="morph", to=cb[0] if cb else None)
        if [f for f in a["filters"] if f != "none"] != [f for f in b["filters"] if f != "none"]:
            px = re.search(r"blur\(([\d.]+)px\)", " ".join(b["filters"]))
            tok = ctx.blur_token(float(px.group(1))) if px else None
            change("filter", "unsupported", reason="CSS filter changes (blur softening) have no native animation",
                   fallback="none", to=[f for f in b["filters"] if f != "none"],
                   band=tok["band"] if tok and tok["band"] else "undeclared")
        if b["scene_part"] and moved_cam:
            continue   # the camera delta carries it
        ba, bb = a["box"], b["box"]
        if ba["w"] > 0 and ba["h"] > 0:
            sx, sy = bb["w"] / ba["w"], bb["h"] / ba["h"]
            if abs(sx - 1) > SCALE_EPS or abs(sy - 1) > SCALE_EPS:
                if abs(sx - sy) <= 2 * SCALE_EPS:
                    change("scale", "grow_shrink", {"scale": round(sx, 4)})
                else:
                    change("size", "unsupported", reason="non-uniform resize", fallback="morph")
        dx = (bb["x"] + bb["w"] / 2) - (ba["x"] + ba["w"] / 2)
        dy = (bb["y"] + bb["h"] / 2) - (ba["y"] + ba["h"] / 2)
        if abs(dx) > MOVE_PX or abs(dy) > MOVE_PX:
            change("position", "motion_path", {"path": f"M 0 0 L {dx / W:.4f} {dy / H:.4f} E"})
    return out


# ---------- extraction ----------

def _notes_text(notes: list[dict]) -> str:
    parts = []
    for n in notes:
        lines = [n["heading"]] if n["heading"] else []
        lines += n["text"]
        lines += [f"Source: {s['text']} ({s['href']})" for s in n["sources"]]
        parts.append("\n".join(lines))
    return "\n\n".join(p for p in parts if p)


def _measure(page, deck: Path, src: str, size: tuple) -> dict:
    try:
        page.goto(deck.resolve().as_uri())
        page.wait_for_function("window.deck && window.deck.ready === true", timeout=15000)
    except Exception as e:  # Playwright timeout or navigation error
        raise SceneError(f"not a skill deck ({deck.name}): the engine never became ready ({type(e).__name__})") from e
    page.evaluate("document.fonts ? document.fonts.ready.then(() => true) : true")
    page.evaluate(SETTLE_JS)
    info = theme_info(src)
    probes = page.evaluate(PROBE_JS, [list(info["roles"]), [t["var"] for t in info["tokens"]]])
    ctx = _Ctx(info, probes)
    plan = page.evaluate("deck.plan()")
    if not plan:
        raise SceneError(f"{deck.name} has no slides")
    slides = []
    for index, (sid, nsteps) in enumerate(plan):
        snaps, raw = [], []
        for k in range(nsteps + 1):
            page.evaluate("([id, k]) => deck.goto(id, k)", [sid, k])
            page.wait_for_function("([id, k]) => deck.state().slide === id && deck.state().step === k", arg=[sid, k])
            if not page.evaluate(SETTLE_JS):
                raise SceneError(f"{sid}@{k}: animations never settled")
            got = page.evaluate(MEASURE_JS, sid)
            raw.append(got)
            snaps.append({r["id"]: r for r in got["recs"]})
        final = raw[-1]
        vis = {}
        for k, snap in enumerate(snaps):
            for i, r in snap.items():
                if r["visible"]:
                    vis.setdefault(i, []).append(k)
        zkeys = {}
        for snap in snaps:
            for i, r in snap.items():
                zkeys[i] = r["zkey"]
        order = sorted(vis, key=lambda i: zkeys[i])
        final_ids = set(order)
        elements = [_element(i, snaps, vis[i], final_ids, ctx) for i in order]
        for z, e in enumerate(elements):
            e["z"] = z
        scene_id = next((e["id"] for e in elements if e["role"] == "scene"), None)
        timeline = []
        for k in range(nsteps + 1):
            visible = [i for i in order if k in vis[i]]
            d = [] if k == 0 else _deltas(k, snaps[k - 1], snaps[k], order,
                                          (_camera(raw[k - 1]["camera"]), _camera(raw[k]["camera"])), ctx, size, scene_id)
            timeline.append({"step": k, "visible": visible, "deltas": d})
        sl = final["slide"]
        slides.append({"id": sid, "index": index, "chapter": sl["chapter"], "classes": sl["classes"],
                       "scene": sl["scene"], "ambient": sl["ambient"], "steps": nsteps,
                       "background": ctx.colour(sl["background"]), "elements": elements, "timeline": timeline,
                       "notes": final["notes"], "notes_text": _notes_text(final["notes"])})
    bar = probes["bar"]
    return {
        "schema": SCHEMA_ID,
        "deck": {"file": deck.name, "title": probes["title"], "subtitle": probes["subtitle"], **info["names"]},
        "size": {"width": size[0], "height": size[1], "unit": "px", "emu_per_px": EMU_PER_PX},
        "palette": {r: {"rgb": ctx.role_rgb[r], "slots": info["roles"][r]} for r in info["roles"] if r in ctx.role_rgb},
        "fonts": info["fonts"],
        "chrome": {"bar": {"box": _box(**bar["box"]), "fill": ctx.colour(bar["fill"])} if bar else None},
        "slides": slides,
    }


def _launch(p):
    try:
        return p.chromium.launch(channel="chrome")
    except Exception:  # noqa: BLE001 - no system Chrome: fall back to Playwright's Chromium
        return p.chromium.launch()


def extract(deck: str | Path, browser=None, size: tuple[int, int] = (1920, 1080)) -> dict:
    """Measure every slide of an assembled deck and return its scene.

    Args:
        deck: Assembled deck HTML file.
        browser: An open Playwright ``Browser`` to reuse; when None, Chrome is launched (in a worker
            thread, so this also works inside another sync Playwright session) and closed.
        size: Slide size in CSS px (the viewport).

    Returns:
        The scene document (see the module docstring and ``scene.schema.json``).

    Raises:
        SceneError: Not a skill deck, the engine never became ready, or animations never settled.
    """
    deck = Path(deck)
    src = read_deck(deck)
    if browser is None:
        def run():
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                b = _launch(p)
                try:
                    return extract(deck, browser=b, size=size)
                finally:
                    b.close()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(run).result()
    ctx = browser.new_context(viewport={"width": size[0], "height": size[1]}, device_scale_factor=1,
                              reduced_motion="reduce")
    try:
        return _measure(ctx.new_page(), deck, src, size)
    finally:
        ctx.close()


# ---------- schema validation (the JSON Schema subset scene.schema.json uses) ----------

_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def _is(v, t: str) -> bool:
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, _TYPES[t])


def validate(doc, schema: dict) -> list[str]:
    """Validate against the JSON Schema subset the scene schema uses (stdlib only).

    Supports ``$ref`` (local ``#/$defs/…``), ``type`` (one or a list), ``enum``, ``const``,
    ``required``, ``properties``, ``additionalProperties``, ``items``, ``minItems``, ``minimum``,
    ``maximum``, ``pattern`` and ``anyOf``.

    Args:
        doc: The scene (or any JSON value).
        schema: The root schema.

    Returns:
        Error strings ``"<json path>: <problem>"``; empty when valid.
    """
    errors: list[str] = []

    def ref(s):
        while "$ref" in s:
            node = schema
            for part in s["$ref"].removeprefix("#/").split("/"):
                node = node[part]
            s = node
        return s

    def check(v, s, path):
        s = ref(s)
        if "anyOf" in s:
            if not any(not _collect(v, alt, path) for alt in s["anyOf"]):
                errors.append(f"{path}: {json.dumps(v)[:80]} matches none of the allowed shapes")
            return
        if "type" in s:
            types = s["type"] if isinstance(s["type"], list) else [s["type"]]
            if not any(_is(v, t) for t in types):
                errors.append(f"{path}: {json.dumps(v)[:80]} is not {'/'.join(types)}")
                return
        if "const" in s and v != s["const"]:
            errors.append(f"{path}: {json.dumps(v)[:80]} is not {json.dumps(s['const'])}")
        if "enum" in s and v not in s["enum"]:
            errors.append(f"{path}: {json.dumps(v)[:80]} not in enum {s['enum']}")
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            if "minimum" in s and v < s["minimum"]:
                errors.append(f"{path}: {v} < minimum {s['minimum']}")
            if "maximum" in s and v > s["maximum"]:
                errors.append(f"{path}: {v} > maximum {s['maximum']}")
        if isinstance(v, str) and "pattern" in s and not re.search(s["pattern"], v):
            errors.append(f"{path}: {v!r} does not match {s['pattern']}")
        if isinstance(v, dict):
            for k in s.get("required", []):
                if k not in v:
                    errors.append(f"{path}: missing required {k!r}")
            props = s.get("properties", {})
            for k, x in v.items():
                if k in props:
                    check(x, props[k], f"{path}.{k}")
                elif s.get("additionalProperties") is False:
                    errors.append(f"{path}: unexpected key {k!r}")
                elif isinstance(s.get("additionalProperties"), dict):
                    check(x, s["additionalProperties"], f"{path}.{k}")
        if isinstance(v, list):
            if "minItems" in s and len(v) < s["minItems"]:
                errors.append(f"{path}: fewer than {s['minItems']} items")
            if "items" in s:
                for j, x in enumerate(v):
                    check(x, s["items"], f"{path}[{j}]")

    def _collect(v, s, path):
        before = len(errors)
        check(v, s, path)
        found = errors[before:]
        del errors[before:]
        return found

    check(doc, schema, "$")
    return errors


# ---------- CLI ----------

def main(argv: list[str] | None = None) -> int:
    """Command line: measure a deck and write its scene JSON.

    Args:
        argv: Arguments (default ``sys.argv[1:]``).

    Returns:
        Exit code: 0 written, 1 refused.
    """
    ap = argparse.ArgumentParser(prog="scene.py", description="Measure an assembled deck into a PPTX scene JSON.")
    ap.add_argument("deck", type=Path, help="assembled deck HTML")
    ap.add_argument("-o", "--out", type=Path, help="output path (default: <deck>.scene.json beside the deck)")
    ap.add_argument("--size", default="1920x1080", help="slide size in CSS px, WxH (default 1920x1080)")
    a = ap.parse_args(argv)
    try:
        m = re.fullmatch(r"(\d+)x(\d+)", a.size)
        if not m:
            raise SceneError(f"--size must be WxH, got {a.size!r}")
        doc = extract(a.deck, size=(int(m.group(1)), int(m.group(2))))
        errs = validate(doc, json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))
        if errs:
            raise SceneError("scene fails its schema:\n  " + "\n  ".join(errs[:20]))
    except SceneError as e:
        print(f"scene: {e}", file=sys.stderr)
        return 1
    out = a.out or a.deck.with_suffix(".scene.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(doc['slides'])} slides)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
