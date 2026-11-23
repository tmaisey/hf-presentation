# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Deck assembler: build a single-file deck from the skeleton, swap its theme, check it is endpoint-safe.

Contract: ``architecture/ARCHITECTURE.md`` (blocks and markers, layer order, module inclusion rule).
Every block is filled between its markers as ``BEGIN\\n<contents>\\nEND``, so output is deterministic and
a swap that changes nothing rewrites nothing.

Usage (stdlib only, so ``uv run`` needs no project)::

    uv run scripts/assemble.py new deck.html --title "Title" [--subtitle "Sub"] [--slides slides.html]
        [--palette paper-green] [--style editorial] [--layout components]
    uv run scripts/assemble.py swap deck.html [--palette P] [--style S] [--layout L] [--refresh-engine] [-o out.html]
    uv run scripts/assemble.py slides deck.html (--from slides.html | --to slides.html)
    uv run scripts/assemble.py check deck.html

- ``new`` fills FONTS (the faces of every family the style names, base64 woff2), ARCH (``arch.css`` +
  the triggered modules' CSS), COMPONENTS (``assets/components/<layout>.css`` or a path), PALETTE and
  STYLE (``scripts/tokens.py``), MODULES (only modules whose ``Triggers:`` appear in the slides), ENGINE
  and SLIDES (``--slides`` file, else one title slide). DECK starts empty.
- ``swap`` regenerates only the theme blocks (FONTS, COMPONENTS, PALETTE, STYLE) from the given names,
  falling back to the names recorded in each block's first-line comment; with ``--refresh-engine`` it
  also rewrites ARCH, DEFS, MODULES and ENGINE from the shipped assets (modules re-detected from SLIDES).
  SLIDES, DECK and everything outside the blocks are copied byte for byte.
- ``slides`` replaces SLIDES from a file (``--from``) or extracts it (``--to``). The deck's SLIDES block
  is the source of truth; a slides file is a working copy. When the new slides trigger a different set
  of modules, ARCH and MODULES are rewritten to match; everything else is copied byte for byte.
- ``check`` prints endpoint-safety faults (``endpoint_faults``); ``new``/``swap`` run it and refuse
  to write a faulty deck.

Exit codes: 0 ok, 1 refused (bad markers, unsafe output, token gate, missing font). Messages go to stderr.
"""

from __future__ import annotations

import argparse
import base64
import html
import importlib.util
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
ASSETS = SKILL_DIR / "assets"
SKELETON = ASSETS / "templates" / "deck-skeleton.html"
ENGINE_DIR = ASSETS / "engine"
MODULES_DIR = ENGINE_DIR / "modules"
COMPONENTS_DIR = ASSETS / "components"
FONTS_DIR = ASSETS / "fonts"
TOKENS_PY = SKILL_DIR / "scripts" / "tokens.py"

CSS_BLOCKS = ("FONTS", "ARCH", "COMPONENTS", "PALETTE", "STYLE", "DECK", "MODULES", "ENGINE")
HTML_BLOCKS = ("DEFS", "SLIDES")
BLOCKS = CSS_BLOCKS[:6] + HTML_BLOCKS + CSS_BLOCKS[6:]
THEME_BLOCKS = ("FONTS", "COMPONENTS", "PALETTE", "STYLE")
ENGINE_BLOCKS = ("ARCH", "DEFS", "MODULES", "ENGINE")
PROVENANCE = {"COMPONENTS": "layout", "PALETTE": "palette", "STYLE": "style"}
GENERIC_FAMILIES = {"serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui", "ui-serif",
                    "ui-sans-serif", "ui-monospace", "ui-rounded", "math", "emoji"}


class AssembleError(Exception):
    """A refusal: broken markers, unsafe output, a missing font or an unknown theme part."""


# ---------- markers and blocks ----------

def _markers(name: str) -> tuple[str, str]:
    if name in HTML_BLOCKS:
        return f"<!-- {name}:BEGIN -->", f"<!-- {name}:END -->"
    return f"/* {name}:BEGIN */", f"/* {name}:END */"


def spans(src: str) -> dict[str, tuple[int, int]]:
    """Locate every block's contents, refusing a deck whose markers are missing, duplicated or out of order.

    Args:
        src: Deck or skeleton source.

    Returns:
        ``{name: (start, end)}`` of each block's contents (between its markers).

    Raises:
        AssembleError: Naming every marker that is missing, appears more than once, or ends before it begins.
    """
    out, faults = {}, []
    for name in BLOCKS:
        begin, end = _markers(name)
        nb, ne = src.count(f"{name}:BEGIN"), src.count(f"{name}:END")
        if nb != 1 or ne != 1 or src.count(begin) != 1 or src.count(end) != 1:
            for tag, n in ((begin, nb), (end, ne)):
                if n == 0 or src.count(tag) == 0:
                    faults.append(f"{tag} marker missing")
                elif n > 1:
                    faults.append(f"{tag} marker appears more than once")
            continue
        s, e = src.index(begin) + len(begin), src.index(end)
        if e < s:
            faults.append(f"{end} comes before {begin}")
            continue
        out[name] = (s, e)
    if faults:
        raise AssembleError("; ".join(faults))
    return out


def read_block(src: str, name: str) -> str:
    """Return a block's contents without the fill newlines.

    Args:
        src: Deck source (markers validated).
        name: Block name.

    Returns:
        The contents as written by ``fill``.
    """
    s, e = spans(src)[name]
    text = src[s:e]
    return text[1:-1] if text.startswith("\n") and text.endswith("\n") and len(text) >= 2 else text


def fill(src: str, contents: dict[str, str]) -> str:
    """Replace the contents of the named blocks, keeping their markers and every other byte.

    Args:
        src: Deck or skeleton source.
        contents: ``{block name: new contents}``.

    Returns:
        The new source.

    Raises:
        AssembleError: When the markers are broken.
    """
    where = spans(src)
    for name in sorted(contents, key=lambda n: where[n][0], reverse=True):
        s, e = where[name]
        src = src[:s] + "\n" + contents[name] + "\n" + src[e:]
    return src


# ---------- modules ----------

def module_triggers(js: Path) -> list[str]:
    """Read a module file's ``Triggers:`` header: the simple selectors that make a deck need it.

    Args:
        js: A module file, ``modules/<name>.js``.

    Returns:
        Selectors, each ``[data-attr]`` or ``.class``; empty when the header is missing.
    """
    m = re.search(r"Triggers:\s*([^\n*]+)", js.read_text(encoding="utf-8"))
    return m.group(1).split() if m else []


class _Markup(HTMLParser):
    """Collects every attribute name and class token in a markup fragment."""

    def __init__(self) -> None:
        super().__init__()
        self.attrs: set[str] = set()
        self.classes: set[str] = set()

    def handle_starttag(self, tag, attrs):  # noqa: D102
        for k, v in attrs:
            self.attrs.add(k)
            if k == "class" and v:
                self.classes.update(v.split())

    handle_startendtag = handle_starttag


def detect_modules(slides: str) -> list[str]:
    """Name the modules a deck needs: those with a trigger attribute or class in its slide markup.

    Args:
        slides: Slide markup (the SLIDES block).

    Returns:
        Module names (file stems), sorted.
    """
    mk = _Markup()
    mk.feed(slides)
    found = []
    for js in sorted(MODULES_DIR.glob("*.js")):
        for t in module_triggers(js):
            if (t.startswith("[") and t.strip("[]") in mk.attrs) or (t.startswith(".") and t[1:] in mk.classes):
                found.append(js.stem)
                break
    return found


def engine_blocks(slides: str, extra_modules: str = "") -> dict[str, str]:
    """Return the ARCH, DEFS, MODULES and ENGINE contents for a deck with these slides.

    Args:
        slides: Slide markup; decides which modules ship.
        extra_modules: Extra module scripts appended after the detected ones (tests, rare decks).

    Returns:
        Block contents by name.
    """
    names = detect_modules(slides)
    js = [(MODULES_DIR / f"{n}.js").read_text(encoding="utf-8") for n in names]
    arch = [(ENGINE_DIR / "arch.css").read_text(encoding="utf-8")]
    arch += [(MODULES_DIR / f"{n}.css").read_text(encoding="utf-8") for n in names
             if (MODULES_DIR / f"{n}.css").is_file()]
    return {"ARCH": "\n".join(arch), "DEFS": read_block(SKELETON.read_text(encoding="utf-8"), "DEFS"),
            "MODULES": "\n".join(js + ([extra_modules] if extra_modules else [])),
            "ENGINE": (ENGINE_DIR / "engine.js").read_text(encoding="utf-8")}


# ---------- theme: tokens, layout, fonts ----------

def _tokens():
    spec = importlib.util.spec_from_file_location("pb_tokens", TOKENS_PY)
    if "pb_tokens" in sys.modules:
        return sys.modules["pb_tokens"]
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve annotations through sys.modules
    spec.loader.exec_module(module)
    return module


def theme_css(palette: str | Path, style: str | Path) -> tuple[str, str]:
    """Generate the PALETTE and STYLE block contents with ``scripts/tokens.py`` (validated, contrast-gated).

    Args:
        palette: Shipped palette name or ``.tokens.json`` path.
        style: Shipped style name or ``.tokens.json`` path.

    Returns:
        ``(palette_css, style_css)``.

    Raises:
        AssembleError: When the tokens are invalid or fail the contrast gate.
    """
    tok = _tokens()
    try:
        theme = tok.load(palette, style)
        return tok.palette_css(theme), tok.style_css(theme)
    except (tok.TokenError, tok.GateError, OSError, json.JSONDecodeError) as e:
        raise AssembleError(f"tokens: {e}") from e


def style_families(style: str | Path) -> list[str]:
    """Name the font families a style renders with: the first family of each of its font tokens.

    Args:
        style: Shipped style name or ``.tokens.json`` path.

    Returns:
        Families in first-use order, generic families excluded.
    """
    tok = _tokens()
    path = tok._locate("styles", style)
    tree = json.loads(path.read_text(encoding="utf-8"))
    theme = tok.Theme({}, tree, "", path.name)
    fams: list[str] = []
    for t in tok.flatten(tree, "style"):
        if t.type == "fontFamily" and not t.path.startswith("ref."):
            v = tok.resolve(theme, t.path)
            first = (v if isinstance(v, str) else v[0]).strip().strip("'\"")
            if first.lower() not in GENERIC_FAMILIES and first not in fams:
                fams.append(first)
    return fams


def _manifest() -> dict:
    return json.loads((FONTS_DIR / "fonts.json").read_text(encoding="utf-8"))


def font_faces(family: str) -> list[dict]:
    """Return the shipped faces of a family (``style``, ``weight``, ``file`` under ``assets/fonts/``).

    Args:
        family: CSS family name, e.g. ``Newsreader``.

    Returns:
        Face records; empty when the skill ships no file for the family.
    """
    return _manifest().get(family, {}).get("faces", [])


def font_licence(family: str) -> str:
    """Return the licence file name (under ``assets/fonts/``) of a shipped family.

    Args:
        family: CSS family name.

    Returns:
        File name, or ``""`` when unknown.
    """
    return _manifest().get(family, {}).get("licence", "")


def fonts_css(families: list[str]) -> str:
    """Return ``@font-face`` rules embedding every face of the families as base64 woff2.

    Args:
        families: CSS family names, each shipped in ``assets/fonts/fonts.json``.

    Returns:
        CSS for the FONTS block (unlayered).

    Raises:
        AssembleError: When a family has no shipped file (it would silently fall back offline).
    """
    rules = []
    for fam in families:
        faces = font_faces(fam)
        if not faces:
            raise AssembleError(f"font {fam!r} has no file in assets/fonts/fonts.json: add its woff2 and licence")
        for f in faces:
            data = base64.b64encode((FONTS_DIR / f["file"]).read_bytes()).decode("ascii")
            rules.append(f'@font-face {{ font-family: "{fam}"; font-style: {f["style"]}; font-weight: {f["weight"]}; '
                         f'font-display: block; src: url(data:font/woff2;base64,{data}) format("woff2"); }}')
    return "\n".join(rules)


def layout_css(layout: str | Path) -> str:
    """Read a layout (components) CSS by shipped name (``assets/components/<name>.css``) or path.

    Args:
        layout: Name such as ``components``, or a ``.css`` path.

    Returns:
        CSS for the COMPONENTS block.

    Raises:
        AssembleError: When the file does not exist.
    """
    p = Path(layout)
    if not (p.suffix == ".css" or p.exists()):
        p = COMPONENTS_DIR / f"{layout}.css"
    if not p.is_file():
        raise AssembleError(f"layout {layout!r} not found")
    return p.read_text(encoding="utf-8")


def _tag(kind: str, ref: str | Path) -> str:
    ref = str(ref)
    if "*/" in ref or "\n" in ref:
        raise AssembleError(f"{kind} name {ref!r} may not contain '*/' or a newline")
    return f"/* {kind}: {ref} */"


def recorded(src: str, name: str) -> str | None:
    """Return the theme part name recorded in a block's first-line comment, if any.

    Args:
        src: Deck source.
        name: ``COMPONENTS``, ``PALETTE`` or ``STYLE``.

    Returns:
        The recorded name or path, or ``None``.
    """
    m = re.match(rf"/\* {PROVENANCE[name]}: (.+?) \*/", read_block(src, name))
    return m.group(1) if m else None


def theme_blocks(palette: str | Path, style: str | Path, layout: str | Path) -> dict[str, str]:
    """Return the FONTS, COMPONENTS, PALETTE and STYLE contents, each theme part tagged with its name.

    Args:
        palette: Palette name or path.
        style: Style name or path.
        layout: Layout name or path.

    Returns:
        Block contents by name.
    """
    pal, sty = theme_css(palette, style)
    return {"FONTS": fonts_css(style_families(style)),
            "COMPONENTS": _tag("layout", layout) + "\n" + layout_css(layout),
            "PALETTE": _tag("palette", palette) + "\n" + pal,
            "STYLE": _tag("style", style) + "\n" + sty}


# ---------- endpoint safety ----------

RISKY = ((r"<script\b[^>]*\bsrc\s*=", "remote or external <script src>"),
         (r"<link\b", "<link> element (external stylesheet or resource)"),
         (r"@import\b", "CSS @import"),
         (r"<(iframe|frame|object|embed|form|base|applet)\b", "embedding, form or base element"),
         (r"http-equiv\s*=\s*['\"]?refresh", "meta refresh"),
         (r"type\s*=\s*['\"]?password", "password field"),
         (r"\beval\s*\(", "eval()"),
         (r"\bnew\s+Function\b", "new Function"),
         (r"\batob\s*\(", "atob()"),
         (r"\bbtoa\s*\(", "btoa()"),
         (r"document\s*\.\s*write", "document.write"),
         (r"\b(innerHTML|outerHTML|insertAdjacentHTML)\b", "HTML string injection (innerHTML etc.)"),
         (r"\bfetch\s*\(", "fetch()"),
         (r"\bXMLHttpRequest\b", "XMLHttpRequest"),
         (r"\bWebSocket\b|\bEventSource\b|\bsendBeacon\b", "network API"),
         (r"\bimport\s*\(", "dynamic import()"),
         (r"\bset(Timeout|Interval)\s*\(\s*['\"`]", "string-evaluated timer"),
         (r"\bjavascript:", "javascript: URL"),
         (r"\bwindow\s*\.\s*open\s*\(", "window.open()"))


def endpoint_faults(src: str) -> list[str]:
    """List what in a deck would trip endpoint or mail-gateway heuristics, or break offline use.

    Rules (ARCHITECTURE §1): one inline ``<script>``; no remote scripts, stylesheets, ``@import``,
    iframes, forms or objects; no ``eval``, ``new Function``, ``atob``, ``document.write``,
    ``innerHTML``/``outerHTML``, ``fetch`` or dynamic ``import``; ``url()`` only to ``data:`` or ``#id``;
    remote URLs only as ``<a href>`` citation targets.

    Args:
        src: Deck source.

    Returns:
        One fault string per problem; empty when the deck is safe.
    """
    faults = []
    if not src.lstrip().lower().startswith("<!doctype html>"):
        faults.append("does not start with <!doctype html>")
    n = len(re.findall(r"<script\b", src, re.I))
    if n != 1:
        faults.append(f"{n} <script> elements (exactly one inline script expected)")
    body = re.sub(r"data:[\w/+.-]+;base64,[A-Za-z0-9+/=]+", "data:", src)
    for pat, what in RISKY:
        for m in re.finditer(pat, body, re.I):
            line = body.count("\n", 0, m.start()) + 1
            faults.append(f"line {line}: {what}: {m.group(0)!r}")
    for m in re.finditer(r"url\(\s*(['\"]?)([^)'\"]*)\1\s*\)", body, re.I):
        if not m.group(2).startswith(("data:", "#")):
            faults.append(f"url() to {m.group(2)!r} (only data: or #id allowed)")
    bare = re.sub(r"<a\b[^>]*>", "", body).replace("http://www.w3.org/2000/svg", "")
    for m in re.finditer(r"(?:https?:)?//[a-z0-9.-]+\.[a-z]{2,}[^\s\"')<]*", bare, re.I):
        faults.append(f"remote URL outside a citation link: {m.group(0)!r}")
    return faults


# ---------- build, new, swap ----------

def default_slides(title: str, subtitle: str) -> str:
    """Return one lead slide carrying the deck title, for a deck started without slides.

    Args:
        title: Deck title.
        subtitle: Deck subtitle.

    Returns:
        Slide markup.
    """
    t, s = html.escape(title), html.escape(subtitle)
    return (f'<section class="slide slide--lead" id="s-1" data-chapter="Opening">\n'
            f'  <h2 class="title">{t}</h2>\n  <div class="body"><p>{s}</p></div>\n</section>')


def build(slides: str, title: str, subtitle: str = "", *, fonts: str = "", components: str = "", palette: str = "",
          style: str = "", deck: str = "", extra_modules: str = "") -> str:
    """Fill the skeleton: engine blocks for these slides, the given theme contents, title and subtitle.

    Args:
        slides: Slide markup for SLIDES.
        title: Deck title (bar and ``<title>``), HTML-escaped here.
        subtitle: Deck subtitle, HTML-escaped here.
        fonts: FONTS contents.
        components: COMPONENTS contents.
        palette: PALETTE contents.
        style: STYLE contents.
        deck: DECK contents.
        extra_modules: Extra module scripts after the detected ones.

    Returns:
        The deck source (not yet safety-checked).
    """
    src = SKELETON.read_text(encoding="utf-8")
    src = src.replace("{{title}}", html.escape(title)).replace("{{subtitle}}", html.escape(subtitle))
    blocks = engine_blocks(slides, extra_modules)
    blocks |= {"FONTS": fonts, "COMPONENTS": components, "PALETTE": palette, "STYLE": style, "DECK": deck,
               "SLIDES": slides}
    return fill(src, blocks)


def _write(out: Path, src: str) -> None:
    faults = endpoint_faults(src)
    if faults:
        raise AssembleError("unsafe deck, not written:\n  " + "\n  ".join(faults))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(src.encode("utf-8"))


def new(out: Path, title: str, subtitle: str = "", slides: str | None = None, palette: str = "paper-green",
        style: str = "editorial", layout: str = "components") -> Path:
    """Write a new single-file deck.

    Args:
        out: Deck file to write.
        title: Deck title.
        subtitle: Deck subtitle.
        slides: Starting slide markup (default: one title slide).
        palette: Palette name or path.
        style: Style name or path.
        layout: Layout name or path.

    Returns:
        ``out``.

    Raises:
        AssembleError: On any refusal; nothing is written.
    """
    slides = default_slides(title, subtitle) if slides is None else slides.strip("\n")
    t = theme_blocks(palette, style, layout)
    _write(out, build(slides, title, subtitle, fonts=t["FONTS"], components=t["COMPONENTS"],
                      palette=t["PALETTE"], style=t["STYLE"]))
    return out


def swap(deck: Path, palette: str | None = None, style: str | None = None, layout: str | None = None,
         refresh_engine: bool = False, out: Path | None = None) -> Path:
    """Regenerate an existing deck's theme blocks (and engine blocks on request); copy all else byte for byte.

    Args:
        deck: Existing deck file.
        palette: New palette (default: the one recorded in the deck).
        style: New style (default: recorded).
        layout: New layout (default: recorded).
        refresh_engine: Also rewrite ARCH, DEFS, MODULES and ENGINE from the shipped assets.
        out: Write here instead of over ``deck``.

    Returns:
        The file written.

    Raises:
        AssembleError: On broken markers, an unknown theme part, or unsafe output; nothing is written.
    """
    src = deck.read_bytes().decode("utf-8")
    spans(src)
    chosen = {}
    for name, given in (("PALETTE", palette), ("STYLE", style), ("COMPONENTS", layout)):
        chosen[name] = given or recorded(src, name)
        if not chosen[name]:
            raise AssembleError(f"{name} block records no {PROVENANCE[name]}: pass --{PROVENANCE[name]}")
    blocks = theme_blocks(chosen["PALETTE"], chosen["STYLE"], chosen["COMPONENTS"])
    if refresh_engine:
        engine = engine_blocks(read_block(src, "SLIDES"))
        blocks |= engine
    target = out or deck
    _write(target, fill(src, blocks))
    return target


def slides_block(deck: Path, src_file: Path | None = None, to_file: Path | None = None) -> Path:
    """Replace a deck's SLIDES block from a file, or extract it to one.

    The deck's SLIDES block is the slides' source of truth; a slides file is a working copy taken
    out with ``to_file`` and put back with ``src_file``. A replacement whose module triggers differ
    from the old slides' also rewrites ARCH and MODULES (the modules the new slides need); every other
    block and byte is copied unchanged.

    Args:
        deck: Existing deck file.
        src_file: Slide markup to put in SLIDES.
        to_file: File to write the current SLIDES markup to.

    Returns:
        The file written (the deck, or ``to_file``).

    Raises:
        AssembleError: On broken markers, both or neither of the files, or unsafe output; nothing is written.
    """
    if (src_file is None) == (to_file is None):
        raise AssembleError("give exactly one of --from (replace SLIDES) or --to (extract SLIDES)")
    src = deck.read_bytes().decode("utf-8")
    old = read_block(src, "SLIDES")
    if to_file is not None:
        to_file.parent.mkdir(parents=True, exist_ok=True)
        to_file.write_bytes((old + "\n").encode("utf-8"))
        return to_file
    new = src_file.read_text(encoding="utf-8").strip("\n")
    blocks = {"SLIDES": new}
    if detect_modules(new) != detect_modules(old):
        eng = engine_blocks(new)
        blocks |= {"ARCH": eng["ARCH"], "MODULES": eng["MODULES"]}
    _write(deck, fill(src, blocks))
    return deck


def main(argv: list[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv: Arguments (defaults to ``sys.argv[1:]``).

    Returns:
        Exit code: 0 ok, 1 refused.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = ap.add_subparsers(dest="command", required=True)
    n = sub.add_parser("new", help="build a new deck from the skeleton")
    n.add_argument("out", type=Path)
    n.add_argument("--title", required=True)
    n.add_argument("--subtitle", default="")
    n.add_argument("--slides", type=Path, help="starting slide markup (default: one title slide)")
    n.add_argument("--palette", default="paper-green", help="palette name or .tokens.json path")
    n.add_argument("--style", default="editorial", help="style name or .tokens.json path")
    n.add_argument("--layout", default="components", help="layout name (assets/components/<name>.css) or path")
    s = sub.add_parser("swap", help="replace an existing deck's theme blocks only")
    s.add_argument("deck", type=Path)
    s.add_argument("--palette")
    s.add_argument("--style")
    s.add_argument("--layout")
    s.add_argument("--refresh-engine", action="store_true", help="also rewrite ARCH, DEFS, MODULES, ENGINE")
    s.add_argument("-o", "--out", type=Path, help="write here instead of over the deck")
    sl = sub.add_parser("slides", help="replace the SLIDES block from a file (--from) or extract it to one (--to)")
    sl.add_argument("deck", type=Path)
    g = sl.add_mutually_exclusive_group(required=True)
    g.add_argument("--from", dest="src", type=Path, help="slide markup to put in SLIDES")
    g.add_argument("--to", type=Path, help="write the current SLIDES markup here")
    c = sub.add_parser("check", help="list endpoint-safety faults")
    c.add_argument("deck", type=Path)
    args = ap.parse_args(argv)
    try:
        if args.command == "new":
            slides = args.slides.read_text(encoding="utf-8") if args.slides else None
            f = new(args.out, args.title, args.subtitle, slides, args.palette, args.style, args.layout)
            print(f"wrote {f} ({f.stat().st_size:,} bytes)")
        elif args.command == "slides":
            f = slides_block(args.deck, args.src, args.to)
            print(f"wrote {f} ({f.stat().st_size:,} bytes)")
        elif args.command == "swap":
            f = swap(args.deck, args.palette, args.style, args.layout, args.refresh_engine, args.out)
            print(f"wrote {f} ({f.stat().st_size:,} bytes)")
        else:
            faults = endpoint_faults(args.deck.read_text(encoding="utf-8"))
            for x in faults:
                print(f"FAIL {x}", file=sys.stderr)
            if faults:
                return 1
            print(f"{args.deck}: endpoint-safe")
    except (AssembleError, OSError) as e:
        print(f"FAIL {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
