"""Spec: PB-005

Palette and style as DTCG 2025.10 token files (ref → sys → comp), and the Python generator that
turns one palette + one style into the skeleton's PALETTE/STYLE CSS blocks and the PPTX
``a:clrScheme``/``a:fontScheme``, behind a WCAG 2 contrast gate over each palette's declared pairs.

Coverage: happy (valid DTCG, tiers, roles carry usage + slot, 12 slots once, style bands, CSS in
the right layer and usable by a browser, theme XML matches tokens, gate passes, deterministic CLI,
values faithful to deck-v2, TOKENS part) · edge (gate never rounds up at the 4.5 boundary; aliases
across palette and style) · negative (gate fails loudly on a low-contrast pair and on a never-text
role used as text; validator flags cycles, dangling aliases, missing types and tier breaches).
"""

from __future__ import annotations

import copy
import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

import pytest

import helper_tokens as h

A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
A = "{%s}" % A_NS


@pytest.fixture(scope="module")
def tok():
    return h.load_script()


@pytest.fixture(scope="module")
def theme(tok):
    return tok.load("paper-green", "editorial")


@pytest.fixture(scope="module")
def pal():
    return h.read_json(h.PALETTE)


@pytest.fixture(scope="module")
def sty():
    return h.read_json(h.STYLE)


def _write(tmp_path, name, tree):
    path = tmp_path / f"{name}.tokens.json"
    path.write_text(json.dumps(tree, indent=2), encoding="utf-8")
    return path


def _set_ref_hex(tree, dotted, hexval):
    node = tree
    for part in dotted.split("."):
        node = node[part]
    node["$value"] = {"colorSpace": "srgb",
                      "components": [round(int(hexval[i:i + 2], 16) / 255, 4) for i in (1, 3, 5)],
                      "hex": hexval.lower()}


def _role_ref(tree, role):
    """The ref path a palette role aliases."""
    return h.ALIAS.match(tree["sys"]["color"][role]["$value"]).group(1)


# ---------- DTCG validity and tiers ----------

def test_shipped_palette_and_style_validate_clean(tok, theme):
    assert tok.validate(theme) == []


@pytest.mark.parametrize("path", [h.PALETTE, h.STYLE], ids=["palette", "style"])
def test_every_node_is_a_typed_token_or_a_group(path):
    for p, node, etype, is_token in h.walk(h.read_json(path)):
        if is_token:
            assert etype, f"{'.'.join(p)} has no own or inherited $type"
        else:
            kids = {k: v for k, v in node.items() if not k.startswith("$")}
            assert all(isinstance(v, dict) for v in kids.values()), f"group {'.'.join(p)} holds a non-node"
        assert not any(c in k for k in node if not k.startswith("$") for c in "{}."), p


def test_every_alias_resolves_without_a_cycle(pal, sty):
    merged = {**h.tokens(pal), **h.tokens(sty)}
    for start in merged:
        seen, frontier = set(), [start]
        while frontier:
            cur = frontier.pop()
            assert cur in merged, f"{start} reaches unknown alias {cur}"
            for target in h.aliases_in(merged[cur][0]["$value"]):
                assert target != start, f"alias cycle through {start}"
                if target not in seen:
                    seen.add(target)
                    frontier.append(target)


def test_tiers_flow_ref_to_sys_to_comp(pal, sty):
    """ref holds raw values only; sys never reads comp; comp never reads ref (Material tiers)."""
    for tree in (pal, sty):
        assert set(k for k in tree if not k.startswith("$")) <= {"ref", "sys", "comp"}
        for dotted, (node, _) in h.tokens(tree).items():
            targets = h.aliases_in(node["$value"])
            tier = dotted.split(".")[0]
            if tier == "ref":
                assert targets == [], f"ref token {dotted} aliases {targets}"
            elif tier == "sys":
                assert not [t for t in targets if t.startswith("comp.")], dotted
            else:
                assert targets and all(t.split(".")[0] in {"sys", "comp"} for t in targets), dotted


def test_raw_colours_and_fonts_live_only_in_palette_ref_and_style_ref(pal, sty):
    """A palette swap must retint everything, so the style file holds no colour literal at all."""
    for label, tree in (("palette", pal), ("style", sty)):
        for dotted, (node, etype) in h.tokens(tree).items():
            literal = not h.aliases_in(node["$value"])
            if etype == "color" and literal:
                assert label == "palette" and dotted.startswith("ref."), dotted
            if etype == "fontFamily" and literal:
                assert dotted.startswith("ref."), dotted
    assert not [a for _, (n, _) in h.tokens(pal).items() for a in h.aliases_in(n["$value"])
                if a not in h.tokens(pal)], "palette must not alias style tokens"


def test_shipped_colours_are_srgb_objects_whose_components_match_hex(pal):
    for dotted, (node, etype) in h.tokens(pal).items():
        if etype == "color" and not h.aliases_in(node["$value"]):
            v = node["$value"]
            assert v["colorSpace"] == "srgb" and re.fullmatch(r"#[0-9a-f]{6}", v["hex"]), dotted
            want = [int(v["hex"][i:i + 2], 16) / 255 for i in (1, 3, 5)]
            assert all(abs(a - b) < 0.001 for a, b in zip(v["components"], want)), dotted


# ---------- palette roles ----------

def test_every_colour_role_carries_a_usage_rule_and_pptx_slots(pal):
    roles = pal["sys"]["color"]
    names = [k for k in roles if not k.startswith("$")]
    assert len(names) >= 8
    for role in names:
        node = roles[role]
        assert len(node.get("$description", "")) >= 20, f"{role} lacks a usage rule"
        slots = h.node_ext(node, "com.twm.pptx", "slots")
        assert slots and set(slots) <= set(h.SLOTS), f"{role} slots {slots}"
        assert isinstance(h.node_ext(node, "com.twm.palette", "textSafe"), bool), role


def test_accent_is_declared_never_text(pal):
    accent = pal["sys"]["color"]["accent"]
    assert "never text" in accent["$description"].lower()
    assert h.node_ext(accent, "com.twm.palette", "textSafe") is False


def test_all_twelve_clrscheme_slots_are_filled_exactly_once(pal):
    claimed = [s for k, n in pal["sys"]["color"].items() if not k.startswith("$")
               for s in h.node_ext(n, "com.twm.pptx", "slots")]
    assert sorted(claimed) == sorted(h.SLOTS)


def test_text_slots_are_text_safe_roles(pal):
    """dk1/dk2 become tx1/tx2 and hlink is link text, so the roles behind them must be text-safe."""
    for k, n in pal["sys"]["color"].items():
        if k.startswith("$"):
            continue
        if set(h.node_ext(n, "com.twm.pptx", "slots")) & {"dk1", "dk2", "hlink", "folHlink"}:
            assert h.node_ext(n, "com.twm.palette", "textSafe") is True, k


# ---------- style bands ----------

def test_every_style_effect_declares_a_pptx_band(sty):
    for dotted in h.tokens(sty):
        if dotted.startswith("ref."):
            continue
        band = h.extension(sty, dotted, "com.twm.pptx", "band")
        assert band in h.BANDS, f"{dotted} band {band!r}"


def test_style_covers_fonts_type_shadows_frost_bokeh_and_motion(sty):
    assert {"font", "type", "shadow", "material", "ambient", "motion"} <= set(sty["sys"])
    assert {"serif", "sans"} <= set(sty["sys"]["font"])
    assert {"rest", "lift", "soft", "key", "overlay"} <= set(sty["sys"]["shadow"])


def test_bands_state_what_pptx_cannot_do(sty):
    """Backdrop blur and ambient drift have no PowerPoint equivalent; named fonts aren't embedded."""
    assert h.extension(sty, "sys.material.blur", "com.twm.pptx", "band") == "lost"
    assert h.extension(sty, "sys.ambient.drift", "com.twm.pptx", "band") == "lost"
    assert h.extension(sty, "sys.font.serif", "com.twm.pptx", "band") == "approximated"


# ---------- CSS output ----------

def _block_vars(css):
    return set(re.findall(r"(--[\w-]+)\s*:", css))


def test_palette_css_holds_every_palette_token_inside_layer_palette(tok, theme, pal):
    css = tok.palette_css(theme)
    assert css.lstrip().startswith("@layer palette {") and css.rstrip().endswith("}")
    want = {"--" + d.replace(".", "-") for d in h.tokens(pal)}
    assert _block_vars(css) == want


def test_style_css_holds_every_style_token_inside_layer_style(tok, theme, sty):
    css = tok.style_css(theme)
    assert css.lstrip().startswith("@layer style {") and css.rstrip().endswith("}")
    want = {"--" + d.replace(".", "-") for d in h.tokens(sty)}
    got = _block_vars(css)
    assert want <= got
    assert not {v for v in got if v.startswith("--sys-color-") or v.startswith("--ref-color-")}


def test_css_keeps_aliases_as_var_references(tok, theme, pal):
    css = tok.palette_css(theme)
    target = "--" + _role_ref(pal, "paper").replace(".", "-")
    assert re.search(r"--sys-color-paper:\s*var\(" + re.escape(target) + r"\);", css)
    assert "var(--sys-color-ink)" in tok.style_css(theme), "style shadows tint from the palette role"


def test_generated_css_computes_in_a_browser(tok, theme):
    """Custom properties accept any tokens, so prove the values are valid where they are used."""
    from playwright.sync_api import sync_playwright
    css = tok.palette_css(theme) + "\n" + tok.style_css(theme)
    page_css = css + """
      #a { background: var(--sys-material-frost); box-shadow: var(--sys-shadow-overlay);
           font-family: var(--sys-font-serif); transition: opacity var(--sys-motion-duration-base) var(--sys-motion-ease);
           font-size: var(--sys-type-title-size); letter-spacing: var(--sys-type-title-tracking);
           backdrop-filter: blur(var(--sys-material-blur)); color: var(--sys-color-ink); }"""
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        page = b.new_page(viewport={"width": 1920, "height": 1080})
        page.set_content(f"<style>{page_css}</style><div id=a>x</div>")
        got = page.evaluate("""() => { const s = getComputedStyle(document.getElementById('a'));
            return { bg: s.backgroundColor, sh: s.boxShadow, ff: s.fontFamily, td: s.transitionDuration,
                     tf: s.transitionTimingFunction, fs: s.fontSize, ls: s.letterSpacing,
                     bf: s.backdropFilter, c: s.color }; }""")
        b.close()
    assert got["bg"].replace(" ", "").endswith(",0.55)") or got["bg"].endswith("/ 0.55)")
    assert got["sh"].count("inset") == 1 and "0px 40px 80px -40px" in got["sh"]
    assert got["ff"].startswith("Newsreader")
    assert got["td"] == "0.6s" and got["tf"] == "cubic-bezier(0.2, 0.7, 0.2, 1)"
    assert got["fs"] == "57.6px" and got["ls"] == "-0.576px"
    assert got["bf"] == "blur(18px)" and got["c"] == "rgb(43, 42, 39)"


# ---------- PPTX theme XML ----------

def test_clrscheme_is_well_formed_in_schema_order_and_matches_tokens(tok, theme, pal):
    root = ET.fromstring(tok.clr_scheme(theme))
    assert root.tag == A + "clrScheme" and root.get("name") == "paper-green"
    assert [c.tag.removeprefix(A) for c in root] == list(h.SLOTS)
    by_slot = {s: r for r, n in pal["sys"]["color"].items() if not r.startswith("$")
               for s in h.node_ext(n, "com.twm.pptx", "slots")}
    for child in root:
        (clr,) = list(child)
        role = by_slot[child.tag.removeprefix(A)]
        assert clr.tag == A + "srgbClr"
        assert clr.get("val") == tok.hex_of(theme, f"sys.color.{role}").lstrip("#").upper()


def test_fontscheme_names_the_serif_major_and_sans_minor(tok, theme):
    root = ET.fromstring(tok.font_scheme(theme))
    assert root.tag == A + "fontScheme" and root.get("name") == "editorial"
    major, minor = root.find(A + "majorFont"), root.find(A + "minorFont")
    assert [c.tag.removeprefix(A) for c in major] == ["latin", "ea", "cs"]
    assert [c.tag.removeprefix(A) for c in minor] == ["latin", "ea", "cs"]
    assert major.find(A + "latin").get("typeface") == "Newsreader"
    assert minor.find(A + "latin").get("typeface") == "Inter"


# ---------- contrast gate ----------

def test_gate_passes_paper_green_with_every_declared_pair_checked(tok, theme, pal):
    report = tok.gate(theme)
    pairs = h.node_ext(pal, "com.twm.palette", "pairs")
    assert len(report) == len(pairs) >= 8
    assert all(r["ok"] for r in report)
    texts = {(r["fg"], r["bg"]) for r in report if r["use"] == "text"}
    assert ("sys.color.ink", "sys.color.paper") in texts
    assert ("sys.color.accent-ink", "sys.color.paper") in texts


def test_contrast_ratios_match_the_deck_design_figures(tok):
    """DESIGN §1 quotes these ratios on paper; the gate's maths must reproduce them."""
    paper = "#F6F3EC"
    got = {c: tok.contrast(c, paper) for c in ("#2B2A27", "#5C5A55", "#8A867E", "#4B6E10")}
    assert got["#2B2A27"] == pytest.approx(12.9, abs=0.1)
    assert got["#5C5A55"] == pytest.approx(6.2, abs=0.1)
    assert got["#8A867E"] == pytest.approx(3.3, abs=0.1)
    assert got["#4B6E10"] == pytest.approx(5.4, abs=0.1)


def test_gate_never_rounds_up_at_the_text_boundary(tok):
    """#777 on white is 4.48:1: it must fail 4.5 and must never be reported as 4.5."""
    low, ok = tok.contrast("#777777", "#FFFFFF"), tok.contrast("#767676", "#FFFFFF")
    assert 4.45 < low < 4.5 < ok
    assert tok.fmt_ratio(low) == "4.47:1" or tok.fmt_ratio(low) == "4.48:1"
    assert not tok.fmt_ratio(low).startswith("4.5")
    assert tok.fmt_ratio(4.4999) == "4.49:1"


def test_gate_fails_loudly_on_a_low_contrast_text_pair(tok, tmp_path, pal):
    bad = copy.deepcopy(pal)
    _set_ref_hex(bad, _role_ref(bad, "ink-2"), "#999999")
    theme = tok.load(_write(tmp_path, "low-contrast", bad), "editorial")
    with pytest.raises(tok.GateError) as e:
        tok.gate(theme)
    msg = str(e.value)
    assert "sys.color.ink-2" in msg and "sys.color.paper" in msg and "4.5" in msg


def test_gate_fails_when_a_never_text_role_is_paired_as_text(tok, tmp_path, pal):
    bad = copy.deepcopy(pal)
    pairs = bad["$extensions"]["com.twm.palette"]["pairs"]
    pairs.append({"fg": "{sys.color.accent}", "bg": "{sys.color.ink}", "use": "text"})
    theme = tok.load(_write(tmp_path, "accent-text", bad), "editorial")
    with pytest.raises(tok.GateError, match=r"sys\.color\.accent.*never text|not text-safe"):
        tok.gate(theme)


def test_emitters_refuse_a_palette_that_fails_the_gate(tok, tmp_path, pal):
    bad = copy.deepcopy(pal)
    _set_ref_hex(bad, _role_ref(bad, "ink"), "#BBBBBB")
    theme = tok.load(_write(tmp_path, "pale", bad), "editorial")
    for emit in (tok.palette_css, tok.clr_scheme):
        with pytest.raises(tok.GateError):
            emit(theme)


# ---------- validator negatives ----------

def _style_with(sty, path, node):
    tree = copy.deepcopy(sty)
    cur = tree
    for part in path[:-1]:
        cur = cur.setdefault(part, {})
    cur[path[-1]] = node
    return tree


@pytest.mark.parametrize("path,node,expect", [
    (("comp", "x", "a"), {"$value": "{comp.x.b}"}, "cycle"),
    (("sys", "motion", "ghost"), {"$type": "duration", "$value": "{sys.motion.nope}"}, "unresolved"),
    (("comp", "x", "raw"), {"$type": "fontFamily", "$value": "{ref.font.inter}"}, "tier"),
    (("sys", "motion", "untyped"), {"$value": 3}, "type"),
], ids=["cycle", "dangling", "comp-reads-ref", "untyped"])
def test_validator_flags_broken_trees(tok, tmp_path, sty, path, node, expect):
    tree = _style_with(sty, path, node)
    if expect == "cycle":
        tree["comp"]["x"]["a"] = {"$type": "number", "$value": "{comp.x.b}",
                                  "$extensions": {"com.twm.pptx": {"band": "lost"}}}
        tree["comp"]["x"]["b"] = {"$type": "number", "$value": "{comp.x.a}",
                                  "$extensions": {"com.twm.pptx": {"band": "lost"}}}
    theme = tok.load("paper-green", _write(tmp_path, "broken", tree))
    errors = tok.validate(theme)
    assert any(expect in e.lower() for e in errors), errors


def test_validator_flags_a_style_effect_without_a_band(tok, tmp_path, sty):
    tree = _style_with(sty, ("sys", "motion", "orphan"), {"$type": "number", "$value": 1})
    tree["sys"]["motion"].get("$extensions", {}).pop("com.twm.pptx", None)
    tree["sys"].get("$extensions", {}).pop("com.twm.pptx", None)
    errors = tok.validate(tok.load("paper-green", _write(tmp_path, "noband", tree)))
    assert any("sys.motion.orphan" in e and "band" in e for e in errors), errors


# ---------- CLI ----------

def _cli(*args):
    uv = shutil.which("uv")
    if not uv:
        pytest.skip("uv not installed")
    return subprocess.run([uv, "run", "--quiet", str(h.SCRIPT), *args],
                          capture_output=True, text=True, timeout=120)


def test_cli_output_is_deterministic_and_marked_for_the_skeleton():
    a, b = _cli("css", "--palette", "paper-green", "--style", "editorial"), _cli(
        "css", "--palette", "paper-green", "--style", "editorial")
    assert a.returncode == 0, a.stderr
    assert a.stdout == b.stdout
    for name in ("PALETTE", "STYLE"):
        assert f"/* {name}:BEGIN */" in a.stdout and f"/* {name}:END */" in a.stdout
    x1, x2 = _cli("pptx", "--palette", "paper-green", "--style", "editorial"), _cli(
        "pptx", "--palette", "paper-green", "--style", "editorial")
    assert x1.returncode == 0 and x1.stdout == x2.stdout and "<a:clrScheme" in x1.stdout


def test_cli_check_exits_nonzero_and_names_the_failure(tmp_path, pal):
    bad = copy.deepcopy(pal)
    _set_ref_hex(bad, _role_ref(bad, "ink-2"), "#999999")
    path = _write(tmp_path, "low-contrast", bad)
    good, res = _cli("check", "--palette", "paper-green", "--style", "editorial"), _cli(
        "check", "--palette", str(path), "--style", "editorial")
    assert good.returncode == 0, good.stderr
    assert res.returncode != 0
    assert "FAIL" in res.stderr and "sys.color.ink-2" in res.stderr


# ---------- faithful to deck-v2 ----------

DECK_COLOURS = ("paper", "paper-deep", "tile", "ink", "ink-2", "ink-3", "accent", "accent-ink",
                "loss", "alarm")
DECK_SIZES = {"body": "body", "text": "text", "small": "small", "kicker": "kicker", "title": "title",
              "lead": "lead", "overlay": "overlay", "msg": "msg", "stat": "stat",
              "d-title": "d-title", "d-sub": "d-sub"}


def test_colour_roles_match_deck_v2_root(tok, theme):
    root = h.deck_root_vars()
    for role in DECK_COLOURS:
        assert tok.hex_of(theme, f"sys.color.{role}").upper() == root[role].upper(), role


def test_fonts_and_type_sizes_match_deck_v2_root(tok, theme):
    root = h.deck_root_vars()
    css = tok.style_css(theme)
    fams = {"serif": root["serif"], "sans": root["sans"]}
    for name, deck in fams.items():
        want = [f.strip().strip('"') for f in deck.split(",")]
        assert [f.strip().strip('"') for f in tok.resolve(theme, f"sys.font.{name}")] == want
    for role, deck_name in DECK_SIZES.items():
        m = re.search(rf"--sys-type-{role}-size:\s*([^;]+);", css)
        assert m, role
        assert m.group(1).replace(" ", "") == root[f"fs-{deck_name}"].replace(" ", ""), role


def test_motion_curves_and_frost_match_deck_v2_root(tok, theme):
    root = h.deck_root_vars()
    for name, deck in (("ease", "ease"), ("ease-rack", "ease-rack"), ("ease-late", "ease-late")):
        want = [float(x) for x in re.findall(r"-?\d*\.?\d+", root[deck])]
        assert tok.resolve(theme, f"sys.motion.{name}") == want, name
    css = tok.style_css(theme)
    frost = re.search(r"--sys-material-frost:\s*([^;]+);", css).group(1)
    assert frost == "color-mix(in srgb, var(--sys-color-paper) 55%, transparent)"
    assert root["frost"] == "color-mix(in srgb, var(--paper) 55%, transparent)"


def test_shadows_match_deck_v2_root(tok, theme):
    root = h.deck_root_vars()
    css = tok.style_css(theme)
    for name in ("rest", "lift", "soft", "key", "overlay"):
        gen = re.search(rf"--sys-shadow-{name}:\s*([^;]+);", css).group(1)
        got = h.parse_shadow(gen.replace("--sys-color-", "--"))
        assert got == h.parse_shadow(root[f"shadow-{name}"]), name


def test_bokeh_and_frost_blurs_match_deck_v2_rules(tok, theme):
    for plane in ("far", "mid", "near"):
        rule = h.deck_rule(f".orb.{plane}")
        blur = float(re.search(r"blur\((\d+)px\)", rule).group(1))
        op = float(re.search(r"opacity:\s*([\d.]+)", rule).group(1))
        assert tok.resolve(theme, f"sys.ambient.{plane}.blur") == {"value": blur, "unit": "px"}
        assert tok.resolve(theme, f"sys.ambient.{plane}.opacity") == op
    over = re.search(r"\.overlay\s*\{[^}]*backdrop-filter: blur\((\d+)px\) saturate\(([\d.]+)\)",
                     h.DECK_V2.read_text(encoding="utf-8"))
    assert tok.resolve(theme, "sys.material.blur") == {"value": float(over.group(1)), "unit": "px"}
    assert tok.resolve(theme, "sys.material.saturate") == float(over.group(2))


def test_no_organisation_is_named_in_the_tokens(pal, sty):
    text = (json.dumps(pal) + json.dumps(sty)).lower()
    for banned in ("hugging", "openai", "deloitte", "google", "anthropic", "hf-"):
        assert banned not in text, banned


# ---------- the design part ----------

def test_tokens_part_documents_tiers_schema_adding_and_running():
    text = h.TOKENS_MD.read_text(encoding="utf-8")
    for must in ("ref", "sys", "comp", "$description", "$extensions", "com.twm.pptx",
                 "com.twm.palette", "band", "uv run", "scripts/tokens.py", "check", "css", "pptx",
                 "4.5", "3:1"):
        assert must in text, must
    assert re.search(r"add(ing)? a palette", text, re.I) and re.search(r"add(ing)? a style", text, re.I)
