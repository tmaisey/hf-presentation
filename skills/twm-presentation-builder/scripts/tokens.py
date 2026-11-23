# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Design-token generator: one palette + one style (DTCG 2025.10) → CSS theme blocks and PPTX theme XML.

Token files live in ``assets/tokens/palettes/<name>.tokens.json`` and
``assets/tokens/styles/<name>.tokens.json`` (schema and rules: ``design/TOKENS.md``). Choosing a
theme is one pair of names, the same idea as the DTCG Resolver's two modifiers (``palette`` and
``style``): the two trees are merged, then aliases resolve across them.

Usage (stdlib only, so ``uv run`` needs no project)::

    uv run scripts/tokens.py check --palette paper-green --style editorial
    uv run scripts/tokens.py css   --palette paper-green --style editorial   # PALETTE + STYLE blocks
    uv run scripts/tokens.py pptx  --palette paper-green --style editorial   # a:clrScheme + a:fontScheme

``--palette``/``--style`` take a shipped name or a path to a ``.tokens.json`` file. Every command
validates first and runs the contrast gate; on any failure it prints ``FAIL`` lines to stderr and
exits 1, emitting nothing.

Rules enforced (beyond DTCG structure, types and alias resolution):

- Tiers: ``ref`` holds raw values and never aliases; ``sys`` never reads ``comp``; ``comp`` only
  aliases ``sys``/``comp``. Raw colours, font families and curves live only in ``ref``; the style
  file holds no colour literal at all, and the palette never aliases into the style.
- Palette: every ``sys.color`` role has a usage rule (``$description``), PPTX ``slots`` and a
  ``textSafe`` flag; the 12 ``a:clrScheme`` slots are each claimed exactly once.
- Style: every ``sys``/``comp`` token has a PPTX ``band`` (native / approximated / lost), its own
  or its nearest group's; ``sys.font`` names one ``major`` and one ``minor`` font.
- Contrast gate (WCAG 2): each declared pair meets 4.5:1 (text) or 3:1 (large-text, non-text);
  ``decorative`` pairs are reported only. Ratios are never rounded up. A role with
  ``textSafe: false`` may never be the foreground of a text pair.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import quoteattr

SKILL_DIR = Path(__file__).resolve().parents[1]
TOKENS_DIR = SKILL_DIR / "assets" / "tokens"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
SLOTS = ("dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5",
         "accent6", "hlink", "folHlink")
BANDS = ("native", "approximated", "lost")
TYPES = {"color", "dimension", "fontFamily", "fontWeight", "duration", "cubicBezier", "number",
         "strokeStyle", "border", "transition", "shadow", "gradient", "typography"}
MINIMUM = {"text": 4.5, "large-text": 3.0, "non-text": 3.0, "decorative": None}
GENERIC_FAMILIES = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui",
                    "ui-serif", "ui-sans-serif", "ui-monospace", "ui-rounded", "math", "emoji"}
FONT_WEIGHTS = {"thin": 100, "hairline": 100, "extra-light": 200, "ultra-light": 200, "light": 300,
                "normal": 400, "regular": 400, "book": 400, "medium": 500, "semi-bold": 600,
                "demi-bold": 600, "bold": 700, "extra-bold": 800, "ultra-bold": 800, "black": 900,
                "heavy": 900, "extra-black": 950, "ultra-black": 950}
ALIAS = re.compile(r"^\{([^{}]+)\}$")
PPTX, CSS, PAL = "com.twm.pptx", "com.twm.css", "com.twm.palette"
# Sub-value types inside composites, used to type-check aliases there.
COMPOSITE_FIELDS = {
    "shadow": {"color": "color", "offsetX": "dimension", "offsetY": "dimension",
               "blur": "dimension", "spread": "dimension"},
    "transition": {"duration": "duration", "delay": "duration", "timingFunction": "cubicBezier"},
    "typography": {"fontFamily": "fontFamily", "fontSize": "dimension", "fontWeight": "fontWeight",
                   "letterSpacing": "dimension", "lineHeight": "number"},
}


class TokenError(ValueError):
    """Raised when token files break DTCG or the skill's tier/palette/style rules."""


class GateError(ValueError):
    """Raised when a palette fails the contrast gate."""


@dataclass
class Token:
    """One token, flattened.

    Attributes:
        path: Dotted path, e.g. ``sys.color.ink``.
        type: Effective ``$type`` (own or inherited), or ``None`` when missing.
        value: Raw ``$value``.
        node: The token's JSON object.
        chain: Nodes from the file root down to the token (for inherited extensions).
        source: ``"palette"`` or ``"style"``.
    """

    path: str
    type: str | None
    value: object
    node: dict
    chain: list
    source: str

    def ext(self, ns: str, field: str):
        """Return an extension field from the token or its nearest ancestor that declares it."""
        for node in reversed(self.chain):
            val = node.get("$extensions", {}).get(ns, {}).get(field)
            if val is not None:
                return val
        return None

    def own_ext(self, ns: str, field: str):
        """Return an extension field declared on the token itself."""
        return self.node.get("$extensions", {}).get(ns, {}).get(field)


@dataclass
class Theme:
    """A palette and a style, loaded but not yet validated.

    Attributes:
        palette: Parsed palette tree.
        style: Parsed style tree.
        palette_name: Palette file stem (without ``.tokens``).
        style_name: Style file stem.
    """

    palette: dict
    style: dict
    palette_name: str
    style_name: str

    @property
    def tokens(self) -> dict[str, Token]:
        """All tokens of both files by dotted path (palette first; a duplicate keeps the first)."""
        out: dict[str, Token] = {}
        for source, tree in (("palette", self.palette), ("style", self.style)):
            for tok in flatten(tree, source):
                out.setdefault(tok.path, tok)
        return out


# ---------- loading and walking ----------

def _locate(kind: str, ref: str | Path) -> Path:
    path = Path(ref)
    if path.suffix == ".json" or path.exists():
        return path
    return TOKENS_DIR / kind / f"{ref}.tokens.json"


def load(palette: str | Path, style: str | Path) -> Theme:
    """Load a palette and a style by shipped name or file path.

    Args:
        palette: Name under ``assets/tokens/palettes/`` or a path.
        style: Name under ``assets/tokens/styles/`` or a path.

    Returns:
        The unvalidated theme.
    """
    p, s = _locate("palettes", palette), _locate("styles", style)
    stem = lambda f: f.name.removesuffix(".json").removesuffix(".tokens")  # noqa: E731
    return Theme(json.loads(p.read_text(encoding="utf-8")), json.loads(s.read_text(encoding="utf-8")),
                 stem(p), stem(s))


def flatten(tree: dict, source: str) -> list[Token]:
    """Flatten a DTCG tree into tokens, in file order, with inherited ``$type``.

    Args:
        tree: Parsed token file.
        source: Label for the file (``palette``/``style``).

    Returns:
        Every token in the tree.
    """
    out: list[Token] = []

    def visit(node: dict, path: list[str], etype: str | None, chain: list):
        etype = node.get("$type", etype)
        if "$value" in node:
            out.append(Token(".".join(path), etype, node["$value"], node, chain + [node], source))
            return
        for key, child in node.items():
            if not key.startswith("$") and isinstance(child, dict):
                visit(child, path + [key], etype, chain + [node])

    visit(tree, [], None, [])
    return out


def aliases_in(value) -> list[str]:
    """Return every alias target inside a value (composites and arrays included)."""
    if isinstance(value, str):
        m = ALIAS.match(value)
        return [m.group(1)] if m else []
    if isinstance(value, dict):
        return [a for v in value.values() for a in aliases_in(v)]
    if isinstance(value, list):
        return [a for v in value for a in aliases_in(v)]
    return []


def resolve(theme: Theme, path: str, _seen: tuple = ()):
    """Resolve a token's value with every alias (top-level or inside composites) substituted.

    Args:
        theme: Loaded theme.
        path: Dotted token path.

    Returns:
        The fully resolved ``$value``.

    Raises:
        TokenError: On an unresolved alias or a cycle.
    """
    toks = theme.tokens
    if path in _seen:
        raise TokenError(f"alias cycle: {' -> '.join(_seen + (path,))}")
    if path not in toks:
        raise TokenError(f"unresolved alias {{{path}}}")

    def sub(v):
        if isinstance(v, str) and ALIAS.match(v):
            return resolve(theme, ALIAS.match(v).group(1), _seen + (path,))
        if isinstance(v, dict):
            return {k: sub(x) for k, x in v.items()}
        if isinstance(v, list):
            return [sub(x) for x in v]
        return v

    return sub(toks[path].value)


# ---------- validation ----------

def _check_value(etype: str, v, where: str) -> list[str]:
    """Type-check one literal (non-alias) value; composites recurse into their fields."""
    if isinstance(v, str) and ALIAS.match(v):
        return []
    bad = [f"{where}: invalid {etype} value {v!r}"]
    dim = lambda x, units: isinstance(x, dict) and isinstance(x.get("value"), (int, float)) \
        and x.get("unit") in units  # noqa: E731
    if etype == "color":
        ok = (isinstance(v, dict) and v.get("colorSpace") == "srgb"
              and isinstance(v.get("components"), list) and len(v["components"]) == 3
              and all(isinstance(c, (int, float)) and 0 <= c <= 1 for c in v["components"])
              and (v.get("hex") is None or re.fullmatch(r"#[0-9a-fA-F]{6}", v["hex"]))
              and 0 <= v.get("alpha", 1) <= 1)
        if ok and v.get("hex"):
            want = [int(v["hex"][i:i + 2], 16) / 255 for i in (1, 3, 5)]
            ok = all(abs(a - b) < 0.002 for a, b in zip(v["components"], want))
        return [] if ok else bad
    if etype == "dimension":
        return [] if dim(v, ("px", "rem")) else bad
    if etype == "duration":
        return [] if dim(v, ("ms", "s")) else bad
    if etype == "number":
        return [] if isinstance(v, (int, float)) and not isinstance(v, bool) else bad
    if etype == "fontWeight":
        return [] if (isinstance(v, (int, float)) and 1 <= v <= 1000) or v in FONT_WEIGHTS else bad
    if etype == "fontFamily":
        return [] if isinstance(v, str) or (isinstance(v, list) and v and all(isinstance(f, str) for f in v)) else bad
    if etype == "cubicBezier":
        ok = (isinstance(v, list) and len(v) == 4 and all(isinstance(n, (int, float)) for n in v)
              and 0 <= v[0] <= 1 and 0 <= v[2] <= 1)
        return [] if ok else bad
    if etype in COMPOSITE_FIELDS:
        layers = v if etype == "shadow" and isinstance(v, list) else [v]
        errs = []
        for layer in layers:
            if not isinstance(layer, dict) or not set(COMPOSITE_FIELDS[etype]) <= set(layer):
                return bad
            if not isinstance(layer.get("inset", False), bool):
                return bad
            for field, ftype in COMPOSITE_FIELDS[etype].items():
                errs += _check_value(ftype, layer[field], f"{where}.{field}")
        return errs
    return []


def _alias_types(tok: Token, toks: dict[str, Token]) -> list[str]:
    """Check that each alias points at a token of the type its position expects."""
    errs = []

    def expect(target: str, want: str):
        got = toks.get(target)
        if got and got.type != want:
            errs.append(f"{tok.path}: alias {{{target}}} is {got.type}, expected {want}")

    if isinstance(tok.value, str) and ALIAS.match(tok.value):
        expect(ALIAS.match(tok.value).group(1), tok.type)
    elif tok.type in COMPOSITE_FIELDS:
        layers = tok.value if isinstance(tok.value, list) else [tok.value]
        for layer in layers:
            for field, ftype in COMPOSITE_FIELDS[tok.type].items():
                v = layer.get(field) if isinstance(layer, dict) else None
                if isinstance(v, str) and ALIAS.match(v):
                    expect(ALIAS.match(v).group(1), ftype)
    return errs


def _structure(tree: dict, label: str) -> list[str]:
    errs = []

    def visit(node, path):
        for key, child in node.items():
            if key.startswith("$"):
                continue
            where = ".".join(path + [key])
            if any(c in key for c in "{}."):
                errs.append(f"{label}: illegal name {where!r}")
            if not isinstance(child, dict):
                errs.append(f"{label}: {where} is neither a token nor a group")
            elif "$value" not in child:
                visit(child, path + [key])

    visit(tree, [])
    extra = {k for k in tree if not k.startswith("$")} - {"ref", "sys", "comp"}
    if extra:
        errs.append(f"{label}: tier: top-level groups must be ref/sys/comp, found {sorted(extra)}")
    return errs


def validate(theme: Theme) -> list[str]:
    """Check a theme against DTCG 2025.10 and the skill's token rules (module docstring).

    Args:
        theme: Loaded theme.

    Returns:
        Error strings; empty when the theme is valid.
    """
    errs = _structure(theme.palette, "palette") + _structure(theme.style, "style")
    pal, sty = flatten(theme.palette, "palette"), flatten(theme.style, "style")
    seen = {t.path for t in pal}
    errs += [f"{t.path}: defined in both palette and style" for t in sty if t.path in seen]
    toks = theme.tokens
    for tok in pal + sty:
        if not tok.type:
            errs.append(f"{tok.path}: token has no $type (own or inherited)")
            continue
        if tok.type not in TYPES:
            errs.append(f"{tok.path}: unknown $type {tok.type!r}")
            continue
        errs += _check_value(tok.type, tok.value, tok.path)
        targets = aliases_in(tok.value)
        tier = tok.path.split(".")[0]
        missing = [t for t in targets if t not in toks]
        errs += [f"{tok.path}: unresolved alias {{{t}}}" for t in missing]
        if tier == "ref" and targets:
            errs.append(f"{tok.path}: tier: ref tokens hold raw values, never aliases")
        if tier == "sys" and any(t.startswith("comp.") for t in targets):
            errs.append(f"{tok.path}: tier: sys never reads comp")
        if tier == "comp" and (not targets or any(t.split(".")[0] not in ("sys", "comp") for t in targets)):
            errs.append(f"{tok.path}: tier: comp tokens alias sys/comp only, found {targets or 'a literal'}")
        literal = not targets
        if tok.type in ("color", "fontFamily", "cubicBezier") and literal and tier != "ref":
            errs.append(f"{tok.path}: tier: raw {tok.type} values live in ref only")
        if tok.source == "style" and tok.type == "color" and literal:
            errs.append(f"{tok.path}: style files hold no colour literal (alias a palette role)")
        if tok.source == "palette" and any(t in toks and toks[t].source == "style" for t in targets):
            errs.append(f"{tok.path}: the palette never aliases style tokens")
        if not missing:
            errs += _alias_types(tok, toks)
            try:
                resolve(theme, tok.path)
            except TokenError as e:
                if "cycle" in str(e):
                    errs.append(f"{tok.path}: {e}")
        errs += _check_mix(tok, toks)
    errs += _palette_rules(theme, pal, toks) + _style_rules(sty)
    return errs


def _check_mix(tok: Token, toks: dict[str, Token]) -> list[str]:
    mix = tok.own_ext(CSS, "mix")
    if mix is None:
        return []
    entries = mix if isinstance(mix, list) else [mix]
    errs = []
    for m in entries:
        if m is None:
            continue
        w, other = m.get("weight"), m.get("with")
        if not isinstance(w, (int, float)) or not 0 <= w <= 1:
            errs.append(f"{tok.path}: mix weight must be 0..1")
        if other != "transparent":
            a = ALIAS.match(other or "")
            if not a or a.group(1) not in toks or toks[a.group(1)].type != "color":
                errs.append(f"{tok.path}: mix 'with' must be 'transparent' or a colour alias")
    return errs


def _palette_rules(theme: Theme, pal: list[Token], toks: dict[str, Token]) -> list[str]:
    errs, claimed = [], []
    roles = [t for t in pal if t.path.startswith("sys.color.")]
    if not roles:
        errs.append("palette: no sys.color roles")
    for t in roles:
        if len(t.node.get("$description", "")) < 20:
            errs.append(f"{t.path}: colour role needs a usage rule in $description")
        slots = t.own_ext(PPTX, "slots")
        if not slots or not set(slots) <= set(SLOTS):
            errs.append(f"{t.path}: needs PPTX slots from {SLOTS}, found {slots}")
        claimed += slots or []
        if not isinstance(t.own_ext(PAL, "textSafe"), bool):
            errs.append(f"{t.path}: needs a boolean {PAL}.textSafe")
    for s in SLOTS:
        n = claimed.count(s)
        if n != 1:
            errs.append(f"palette: clrScheme slot {s} claimed {n} times (must be exactly once)")
    pairs = theme.palette.get("$extensions", {}).get(PAL, {}).get("pairs", [])
    if not pairs:
        errs.append("palette: declares no contrast pairs")
    for p in pairs:
        for end in ("fg", "bg"):
            a = ALIAS.match(str(p.get(end, "")))
            if not a or a.group(1) not in toks or not a.group(1).startswith("sys.color."):
                errs.append(f"palette pair {p}: {end} must alias a sys.color role")
        if p.get("use") not in MINIMUM:
            errs.append(f"palette pair {p}: use must be one of {sorted(MINIMUM)}")
    return errs


def _style_rules(sty: list[Token]) -> list[str]:
    errs = []
    for t in sty:
        if t.path.startswith("ref."):
            continue
        if t.ext(PPTX, "band") not in BANDS:
            errs.append(f"{t.path}: style effect declares no PPTX band ({'/'.join(BANDS)})")
    slots = [t.own_ext(PPTX, "fontSlot") for t in sty if t.path.startswith("sys.font.")]
    for want in ("major", "minor"):
        if slots.count(want) != 1:
            errs.append(f"style: sys.font must name exactly one {want} font")
    return errs


def _ready(theme: Theme) -> list[dict]:
    errs = validate(theme)
    if errs:
        raise TokenError("\n".join(f"FAIL {e}" for e in errs))
    return gate(theme)


# ---------- colour and contrast ----------

def hex_of(theme: Theme, path: str) -> str:
    """Return a colour token's resolved sRGB hex (``#RRGGBB``), ignoring any CSS mix.

    Args:
        theme: Loaded theme.
        path: Dotted path of a colour token.

    Returns:
        Upper-case hex.
    """
    v = resolve(theme, path)
    if v.get("hex"):
        return v["hex"].upper()
    return "#" + "".join(f"{round(c * 255):02X}" for c in v["components"])


def _luminance(hexval: str) -> float:
    rgb = [int(hexval.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(fg: str, bg: str) -> float:
    """WCAG 2 contrast ratio between two opaque sRGB hex colours.

    Args:
        fg: e.g. ``#2B2A27``.
        bg: e.g. ``#F6F3EC``.

    Returns:
        The unrounded ratio (1–21).
    """
    a, b = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def fmt_ratio(ratio: float) -> str:
    """Format a ratio truncated (never rounded up) to two decimals, e.g. ``4.49:1``."""
    return f"{math.floor(ratio * 100) / 100:.2f}:1"


def contrast_report(theme: Theme) -> list[dict]:
    """Check every declared fg/bg pair of the palette.

    Args:
        theme: Loaded, valid theme.

    Returns:
        One row per pair: ``fg``, ``bg`` (dotted paths), ``use``, ``ratio``, ``minimum``, ``ok``,
        ``reason``.
    """
    toks, rows = theme.tokens, []
    for p in theme.palette.get("$extensions", {}).get(PAL, {}).get("pairs", []):
        fg, bg = ALIAS.match(p["fg"]).group(1), ALIAS.match(p["bg"]).group(1)
        use, minimum = p["use"], MINIMUM[p["use"]]
        ratio = contrast(hex_of(theme, fg), hex_of(theme, bg))
        ok, reason = True, ""
        if use in ("text", "large-text") and toks[fg].own_ext(PAL, "textSafe") is not True:
            ok, reason = False, f"{fg} is not text-safe (never text), so it cannot be {use}"
        elif minimum is not None and ratio < minimum:
            ok, reason = False, f"{fmt_ratio(ratio)} < {minimum}:1"
        rows.append({"fg": fg, "bg": bg, "use": use, "ratio": ratio, "minimum": minimum,
                     "ok": ok, "reason": reason})
    return rows


def gate(theme: Theme) -> list[dict]:
    """Run the contrast gate.

    Args:
        theme: Loaded theme.

    Returns:
        The report when every pair passes.

    Raises:
        GateError: Listing each failing pair, its ratio and the minimum.
    """
    rows = contrast_report(theme)
    fails = [r for r in rows if not r["ok"]]
    if fails:
        raise GateError(f"contrast gate failed for palette {theme.palette_name}:\n" + "\n".join(
            f"FAIL {r['fg']} on {r['bg']} ({r['use']}): {r['reason']}" for r in fails))
    return rows


# ---------- CSS ----------

def _var(path: str) -> str:
    return "--" + path.replace(".", "-")


def _num(x: float) -> str:
    return f"{x:g}"


def _css_value(tok: Token, v, etype: str, mix=None) -> str:
    if isinstance(v, str) and ALIAS.match(v):
        out = f"var({_var(ALIAS.match(v).group(1))})"
    elif etype == "color":
        out = (v["hex"].lower() if v.get("hex") else
               "#" + "".join(f"{round(c * 255):02x}" for c in v["components"]))
        if v.get("alpha", 1) < 1:
            out = f"rgb(from {out} r g b / {_num(v['alpha'])})"
    elif etype in ("dimension", "duration"):
        out = f"{_num(v['value'])}{v['unit']}" if v["value"] or etype == "duration" else "0"
        fluid = tok.own_ext(CSS, "fluid")
        if fluid and etype == "dimension":
            lo = fluid["min"]
            out = f"clamp({_num(lo['value'])}{lo['unit']}, {fluid['preferred']}, {_num(v['value'])}{v['unit']})"
    elif etype == "fontFamily":
        fams = [v] if isinstance(v, str) else v
        out = ", ".join(f if f in GENERIC_FAMILIES else json.dumps(f) for f in fams)
    elif etype == "fontWeight":
        out = str(FONT_WEIGHTS.get(v, v))
    elif etype == "number":
        unit = tok.own_ext(CSS, "unit") or ""
        out = _num(v) + unit
    elif etype == "cubicBezier":
        out = "cubic-bezier(" + ", ".join(_num(n) for n in v) + ")"
    elif etype == "shadow":
        layers = v if isinstance(v, list) else [v]
        mixes = mix if isinstance(mix, list) else [mix] * len(layers)
        parts = []
        for layer, m in zip(layers, mixes):
            f = COMPOSITE_FIELDS["shadow"]
            lengths = " ".join(_css_value(tok, layer[k], f[k]) for k in ("offsetX", "offsetY", "blur", "spread"))
            colour = _css_value(tok, layer["color"], "color", m)
            parts.append(("inset " if layer.get("inset") else "") + f"{lengths} {colour}")
        return ", ".join(parts)
    elif etype == "transition":
        f = COMPOSITE_FIELDS["transition"]
        return " ".join(_css_value(tok, v[k], f[k]) for k in ("duration", "timingFunction", "delay"))
    else:
        raise TokenError(f"{tok.path}: no CSS form for $type {etype}")
    if mix and etype == "color":
        other = mix["with"]
        other = other if other == "transparent" else f"var({_var(ALIAS.match(other).group(1))})"
        out = f"color-mix(in srgb, {out} {_num(round(mix['weight'] * 100, 4))}%, {other})"
    return out


def _block(theme: Theme, source: str, layer: str) -> str:
    lines = [f"@layer {layer} {{", "  :root {"]
    tier = None
    for tok in flatten(theme.palette if source == "palette" else theme.style, source):
        head = tok.path.split(".")[0]
        if head != tier:
            tier = head
            lines.append(f"    /* {tier} */")
        mix = tok.own_ext(CSS, "mix")
        lines.append(f"    {_var(tok.path)}: {_css_value(tok, tok.value, tok.type, mix)};")
    lines += ["  }", "}"]
    return "\n".join(lines)


def palette_css(theme: Theme) -> str:
    """Return the PALETTE block contents: every palette token as a custom property in ``@layer palette``.

    Args:
        theme: Loaded theme (validated and gated here).

    Returns:
        CSS text; aliases stay as ``var()`` references.

    Raises:
        TokenError: When the theme is invalid.
        GateError: When the palette fails the contrast gate.
    """
    _ready(theme)
    return _block(theme, "palette", "palette")


def style_css(theme: Theme) -> str:
    """Return the STYLE block contents: every style token as a custom property in ``@layer style``.

    Args:
        theme: Loaded theme (validated and gated here).

    Returns:
        CSS text; palette roles are read through ``var(--sys-color-…)``.

    Raises:
        TokenError: When the theme is invalid.
        GateError: When the palette fails the contrast gate.
    """
    _ready(theme)
    return _block(theme, "style", "style")


# ---------- PPTX theme XML ----------

def clr_scheme(theme: Theme) -> str:
    """Return the ``a:clrScheme`` element (12 slots in schema order) for the palette.

    Args:
        theme: Loaded theme (validated and gated here).

    Returns:
        Standalone XML with the DrawingML namespace declared.
    """
    _ready(theme)
    by_slot = {s: t.path for t in flatten(theme.palette, "palette") if t.path.startswith("sys.color.")
               for s in t.own_ext(PPTX, "slots")}
    lines = [f'<a:clrScheme xmlns:a="{A_NS}" name={quoteattr(theme.palette_name)}>']
    for s in SLOTS:
        lines.append(f'  <a:{s}><a:srgbClr val="{hex_of(theme, by_slot[s]).lstrip("#")}"/></a:{s}>')
    lines.append("</a:clrScheme>")
    return "\n".join(lines)


def font_scheme(theme: Theme) -> str:
    """Return the ``a:fontScheme`` element: the major (heading) and minor (body) fonts.

    Args:
        theme: Loaded theme (validated and gated here).

    Returns:
        Standalone XML; ``ea``/``cs`` are present and empty, as the schema requires.
    """
    _ready(theme)
    fonts = {}
    for t in flatten(theme.style, "style"):
        slot = t.own_ext(PPTX, "fontSlot") if t.path.startswith("sys.font.") else None
        if slot:
            fam = resolve(theme, t.path)
            fonts[slot] = fam if isinstance(fam, str) else fam[0]
    lines = [f'<a:fontScheme xmlns:a="{A_NS}" name={quoteattr(theme.style_name)}>']
    for slot in ("major", "minor"):
        lines += [f"  <a:{slot}Font>", f"    <a:latin typeface={quoteattr(fonts[slot])}/>",
                  '    <a:ea typeface=""/>', '    <a:cs typeface=""/>', f"  </a:{slot}Font>"]
    lines.append("</a:fontScheme>")
    return "\n".join(lines)


# ---------- CLI ----------

def _table(rows: list[dict]) -> str:
    out = [f"{'fg':<22} {'bg':<22} {'use':<11} {'ratio':>8} {'min':>5}  result"]
    for r in rows:
        mn = f"{r['minimum']}" if r["minimum"] else "-"
        out.append(f"{r['fg']:<22} {r['bg']:<22} {r['use']:<11} {fmt_ratio(r['ratio']):>8} {mn:>5}  "
                   f"{'ok' if r['ok'] else 'FAIL'}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv: Arguments (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code: 0 on success, 1 on any validation or gate failure.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("command", choices=("check", "css", "pptx"))
    ap.add_argument("--palette", default="paper-green", help="palette name or .tokens.json path")
    ap.add_argument("--style", default="editorial", help="style name or .tokens.json path")
    args = ap.parse_args(argv)
    try:
        theme = load(args.palette, args.style)
        rows = _ready(theme)
        if args.command == "check":
            print(f"palette {theme.palette_name} + style {theme.style_name}: valid; contrast gate passed")
            print(_table(rows))
        elif args.command == "css":
            print("/* PALETTE:BEGIN */\n" + palette_css(theme) + "\n/* PALETTE:END */\n")
            print("/* STYLE:BEGIN */\n" + style_css(theme) + "\n/* STYLE:END */")
        else:
            print(clr_scheme(theme) + "\n" + font_scheme(theme))
    except (TokenError, GateError, OSError, json.JSONDecodeError) as e:
        print(f"FAIL {e}" if not str(e).startswith(("FAIL", "contrast")) else str(e), file=sys.stderr)
        if isinstance(e, GateError):
            print(_table(contrast_report(theme)), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
