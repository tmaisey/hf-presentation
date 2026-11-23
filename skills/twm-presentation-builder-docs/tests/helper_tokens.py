"""Helpers for token tests: load the shipped generator, walk DTCG trees independently, read deck-v2.

The DTCG walkers here are deliberately independent of the generator's own validator, so a bug in
one is caught by the other. Rules follow the Design Tokens Format Module 2025.10 (tokens carry
``$value`` and an own-or-inherited ``$type``; anything else is a group; aliases are ``{a.b.c}``).
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

from helper_skill import REPO, SKILL_DIR

SCRIPT = SKILL_DIR / "scripts" / "tokens.py"
TOKENS_DIR = SKILL_DIR / "assets" / "tokens"
PALETTE = TOKENS_DIR / "palettes" / "paper-green.tokens.json"
STYLE = TOKENS_DIR / "styles" / "editorial.tokens.json"
TOKENS_MD = SKILL_DIR / "design" / "TOKENS.md"
DECK_V2 = REPO / "deck" / "deck-v2.html"
ALIAS = re.compile(r"^\{([^{}]+)\}$")
SLOTS = ("dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5",
         "accent6", "hlink", "folHlink")
BANDS = {"native", "approximated", "lost"}


def load_script():
    """Import the shipped generator by path (``scripts/`` is not a package).

    Returns:
        The imported ``tokens`` module.
    """
    spec = importlib.util.spec_from_file_location("pb_tokens", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve annotations through sys.modules
    spec.loader.exec_module(module)
    return module


def read_json(path: Path) -> dict:
    """Parse a token file.

    Args:
        path: ``.tokens.json`` file.

    Returns:
        The parsed tree.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def walk(tree: dict, path: tuple = (), inherited_type: str | None = None):
    """Yield every node of a DTCG tree with its path and effective ``$type``.

    Args:
        tree: A DTCG group (the file root at first call).
        path: Path of ``tree``.
        inherited_type: Nearest ancestor group's ``$type``.

    Yields:
        ``(path, node, effective_type, is_token)`` tuples, groups and tokens alike.
    """
    etype = tree.get("$type", inherited_type)
    is_token = "$value" in tree
    yield path, tree, etype, is_token
    if is_token:
        return
    for key, child in tree.items():
        if key.startswith("$"):
            continue
        yield from walk(child, path + (key,), etype)


def tokens(tree: dict) -> dict[str, tuple[dict, str | None]]:
    """Map dotted token paths to ``(node, effective_type)``.

    Args:
        tree: DTCG tree.

    Returns:
        One entry per token (groups excluded).
    """
    return {".".join(p): (n, t) for p, n, t, is_tok in walk(tree) if is_tok}


def aliases_in(value) -> list[str]:
    """Return every alias target inside a token value (composites and arrays included).

    Args:
        value: A ``$value``.

    Returns:
        Dotted target paths.
    """
    if isinstance(value, str):
        m = ALIAS.match(value)
        return [m.group(1)] if m else []
    if isinstance(value, dict):
        return [a for v in value.values() for a in aliases_in(v)]
    if isinstance(value, list):
        return [a for v in value for a in aliases_in(v)]
    return []


def extension(tree: dict, dotted: str, key: str, field: str):
    """Look up an ``$extensions[key][field]`` on a token or its nearest ancestor group.

    Args:
        tree: DTCG tree.
        dotted: Token path.
        key: Extension namespace, e.g. ``com.twm.pptx``.
        field: Field inside the namespace.

    Returns:
        The value, or ``None`` when no node on the path declares it.
    """
    node, found = tree, node_ext(tree, key, field)
    for part in dotted.split("."):
        node = node[part]
        here = node_ext(node, key, field)
        found = here if here is not None else found
    return found


def node_ext(node: dict, key: str, field: str):
    """Return ``node["$extensions"][key][field]`` or ``None``."""
    return node.get("$extensions", {}).get(key, {}).get(field)


def deck_root_vars() -> dict[str, str]:
    """Read deck-v2's ``:root`` custom properties (the first ``:root {…}`` rule; fonts skipped).

    Returns:
        Mapping of property name (without ``--``) to its raw value text.
    """
    text = DECK_V2.read_text(encoding="utf-8")
    end_fonts = text.index("/* FONTS:END */")
    m = re.search(r":root\s*\{(.*?)\n\s*\}", text[end_fonts:], re.S)
    body = re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.S)
    return {k: " ".join(v.split()) for k, v in re.findall(r"--([\w-]+)\s*:\s*([^;]+);", body)}


def deck_rule(selector: str) -> str:
    """Return the declarations of the first deck-v2 rule whose selector is exactly ``selector``.

    Args:
        selector: e.g. ``.orb.far``.

    Returns:
        The declaration text, whitespace-collapsed.
    """
    text = DECK_V2.read_text(encoding="utf-8")
    css = text[text.index("/* FONTS:END */"):text.index("</style>")]
    m = re.search(r"(?:^|\n)\s*" + re.escape(selector) + r"\s*\{([^}]*)\}", css)
    assert m, f"deck-v2 has no rule {selector}"
    return " ".join(m.group(1).split())


def parse_shadow(css: str) -> list[dict]:
    """Parse a deck-v2 ``box-shadow`` into layers (names normalised to colour roles).

    Handles ``<x> <y> <blur> [<spread>] <colour> [inset]`` with ``var(--role)`` or
    ``color-mix(in srgb, var(--role) N%, transparent)`` colours.

    Args:
        css: The shadow value.

    Returns:
        One dict per layer: ``x y blur spread`` (px numbers), ``inset``, ``role``, ``weight``.
    """
    layers = []
    for part in split_top(css):
        inset = "inset" in part.split()
        mix = re.search(r"color-mix\(in srgb, var\(--([\w-]+)\) (\d+)%, transparent\)", part)
        var = re.search(r"var\(--([\w-]+)\)", part)
        role, weight = (mix.group(1), int(mix.group(2)) / 100) if mix else (var.group(1), 1.0)
        lengths = re.sub(r"color-mix\([^()]*(?:\([^()]*\)[^()]*)*\)|var\([^()]*\)", "", part).split()
        vals = [float(t[:-2]) if t.endswith("px") else float(t) for t in lengths if t != "inset"]
        layers.append({"x": vals[0], "y": vals[1], "blur": vals[2],
                       "spread": vals[3] if len(vals) > 3 else 0.0,
                       "inset": inset, "role": role, "weight": weight})
    return layers


def split_top(css: str) -> list[str]:
    """Split a CSS list on top-level commas (commas inside brackets are kept).

    Args:
        css: e.g. a multi-layer ``box-shadow``.

    Returns:
        The stripped items.
    """
    items, depth, cur = [], 0, ""
    for ch in css:
        depth += (ch == "(") - (ch == ")")
        if ch == "," and depth == 0:
            items.append(cur.strip())
            cur = ""
        else:
            cur += ch
    return items + [cur.strip()]
