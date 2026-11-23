"""Lint helpers for the components layer: colour literals, token tiers and undefined custom properties.

A components layer may read only ``--sys-*`` roles (defined by the generated PALETTE/STYLE blocks), its
own ``--comp-*`` aliases, and engine-set contract properties; it holds no colour literal. ``transparent``
and ``currentColor`` carry no hue, so they are allowed (for ``color-mix`` fades and inherited strokes).
"""

from __future__ import annotations

import re

# Properties the engine or arch layer sets for design layers to read (ARCHITECTURE §5).
ENGINE_PROPS = {"--k"}

# CSS named colours (Level 4) plus the system colours, all banned in the components layer.
NAMED = set("""aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue blueviolet brown
burlywood cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan darkblue darkcyan darkgoldenrod
darkgray darkgreen darkgrey darkkhaki darkmagenta darkolivegreen darkorange darkorchid darkred darksalmon
darkseagreen darkslateblue darkslategray darkslategrey darkturquoise darkviolet deeppink deepskyblue dimgray dimgrey
dodgerblue firebrick floralwhite forestgreen fuchsia gainsboro ghostwhite gold goldenrod gray green greenyellow grey
honeydew hotpink indianred indigo ivory khaki lavender lavenderblush lawngreen lemonchiffon lightblue lightcoral
lightcyan lightgoldenrodyellow lightgray lightgreen lightgrey lightpink lightsalmon lightseagreen lightskyblue
lightslategray lightslategrey lightsteelblue lightyellow lime limegreen linen magenta maroon mediumaquamarine
mediumblue mediumorchid mediumpurple mediumseagreen mediumslateblue mediumspringgreen mediumturquoise
mediumvioletred midnightblue mintcream mistyrose moccasin navajowhite navy oldlace olive olivedrab orange orangered
orchid palegoldenrod palegreen paleturquoise palevioletred papayawhip peachpuff peru pink plum powderblue purple
rebeccapurple red rosybrown royalblue saddlebrown salmon sandybrown seagreen seashell sienna silver skyblue slateblue
slategray slategrey snow springgreen steelblue tan teal thistle tomato turquoise violet wheat white whitesmoke yellow
yellowgreen canvas canvastext linktext visitedtext activetext buttonface buttontext buttonborder field fieldtext
highlight highlighttext selecteditem selecteditemtext mark marktext graytext accentcolor accentcolortext""".split())
COLOUR_FUNCS = re.compile(r"\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\(", re.I)
HEX = re.compile(r"#[0-9a-f]{3,8}\b", re.I)


def strip_comments(css: str) -> str:
    """Remove ``/* … */`` comments.

    Args:
        css: CSS text.

    Returns:
        The CSS without comments.
    """
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def declarations(css: str) -> list[tuple[str, str]]:
    """Return every ``property: value`` declaration (selectors, at-rule preludes and comments excluded).

    Args:
        css: CSS text (nesting allowed).

    Returns:
        ``(property, value)`` pairs in source order.
    """
    body = strip_comments(css)
    out = []
    # a declaration sits after `{` or `;` and ends at `;` or `}`; selectors end at `{` so they never match
    for m in re.finditer(r"(?:(?<=[{;])|^)\s*(--[\w-]+|-?[a-z][\w-]*)\s*:\s*([^;{}]+?)\s*(?=[;}])", body, re.M):
        out.append((m.group(1), m.group(2)))
    return out


def colour_literals(css: str) -> list[str]:
    """List colour literals in declaration values: hex, colour functions, named and system colours.

    ``url(#id)`` references to shared SVG defs are not colours and are ignored.

    Args:
        css: CSS text.

    Returns:
        ``"<property>: <literal>"`` hits; empty when clean.
    """
    hits = []
    for prop, value in declarations(css):
        v = re.sub(r"url\([^)]*\)", "", value)
        v = re.sub(r"var\(\s*--[\w-]+", "var(", v)       # custom-property names are not literals
        hits += [f"{prop}: {h}" for h in HEX.findall(v)]
        hits += [f"{prop}: {h.group(0)}" for h in COLOUR_FUNCS.finditer(v)]
        if prop in {"content", "font", "font-family", "grid-template", "grid-template-areas", "grid-area",
                    "transition", "transition-property", "counter-reset", "counter-increment", "quotes",
                    "will-change"}:
            continue   # identifiers and strings here are names, not colours
        words = re.findall(r"(?<![\w-])([a-z]+)(?![\w(-])", re.sub(r'"[^"]*"', "", v), re.I)
        hits += [f"{prop}: {w}" for w in words if w.lower() in NAMED]
    return hits


def var_reads(css: str) -> set[str]:
    """Return every custom property read through ``var(--…)``.

    Args:
        css: CSS text.

    Returns:
        Property names, e.g. ``{"--sys-color-ink", "--comp-bar-height"}``.
    """
    return set(re.findall(r"var\(\s*(--[\w-]+)", strip_comments(css)))


def defined_props(css: str) -> set[str]:
    """Return every custom property the CSS defines.

    Args:
        css: CSS text.

    Returns:
        Property names.
    """
    return {p for p, _ in declarations(css) if p.startswith("--")}


def lint(css: str, theme_css: str) -> list[str]:
    """Check a components layer against the token contract.

    Args:
        css: Components CSS.
        theme_css: The generated PALETTE + STYLE CSS it is assembled with.

    Returns:
        Fault strings; empty when the layer reads only sys/comp tokens and holds no colour literal.
    """
    faults = [f"colour literal: {h}" for h in colour_literals(css)]
    defined_here = defined_props(css)
    faults += [f"defines a non-comp property: {p}" for p in sorted(defined_here)
               if not p.startswith("--comp-") and p not in ENGINE_PROPS]
    theme = defined_props(theme_css)
    for v in sorted(var_reads(css)):
        if v.startswith("--ref-"):
            faults.append(f"reads a ref token: {v}")
        elif v.startswith("--sys-") and v not in theme:
            faults.append(f"reads an undefined sys token: {v}")
        elif v.startswith("--comp-") and v not in defined_here:
            faults.append(f"reads an undefined comp token: {v}")
        elif not v.startswith(("--sys-", "--comp-", "--ref-")) and v not in ENGINE_PROPS:
            faults.append(f"reads a property outside the token tiers: {v}")
    return faults
