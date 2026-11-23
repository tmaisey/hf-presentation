"""Spec: PB-008

Second palette, colour scheme only (PRD Decisions, 22 Nov): ``bright-primaries`` (four bright primaries
on white, near-black ink, grey secondary, light-grey surfaces) over the same components and editorial
style; the HF reference subset re-themed by ``assemble.py swap --palette`` as
``examples/hf-incident/deck-bright.html``; judged only by the eval's blind subagents (run folder under
``evals-runs/``).

Coverage: happy (valid DTCG, every paper-green role and tier, usage rules, 12 slots once, gate passes;
the scheme's colours sit in their roles; swap output is the committed deck and only PALETTE differs; the
rendered title ink, accent fills and accent text compute to the new roles; layout guard clean at every
review size; the run folder holds a valid aggregate report with the calibration line) · edge (each
bright under 4.5:1 is never text and accent text uses a darker shade of the same hue; text slots are
text-safe) · negative (no organisation named in the new files; no rendered text is drawn in a bright).
"""

from __future__ import annotations

import colorsys
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from helper_engine import ASSEMBLE, BANNED, REVIEW_SIZES, block, layout_faults, open_deck, settle
from helper_skill import SKILL_DIR
from helper_tokens import PALETTE as PAPER_GREEN, SLOTS, TOKENS_DIR, load_script, read_json, tokens

NAME = "bright-primaries"
BRIGHT = TOKENS_DIR / "palettes" / f"{NAME}.tokens.json"
EXAMPLE = SKILL_DIR / "examples" / "hf-incident"
DECK, DECK_BRIGHT = EXAMPLE / "deck.html", EXAMPLE / "deck-bright.html"
RUN_DIR = SKILL_DIR.parent / "twm-presentation-builder-docs" / "evals-runs" / "261123-pb008-bright"
ARTIFACTS = Path(__file__).parent / "artifacts" / "pb-008"
SLIDE_IDS = ["s-1", "s-2", "s-4", "s-5", "s-9", "s-12"]
# The scheme (PRD Decisions): the four brights, near-black ink, grey secondary.
BRIGHTS = {"#4285F4", "#EA4335", "#FBBC05", "#34A853"}
SCHEME = {"ink": "#202124", "ink-2": "#5F6368", "paper": "#FFFFFF", "accent": "#4285F4", "alarm": "#EA4335"}
# The judged screenshot criteria (design-palette + design-style, evidence S, editorial-talk profile).
JUDGED = {"DP-04", "DP-06", "DS-02", "DS-04", "DS-05", "DS-06"}
# sha256 of lower-case organisation/brand words this palette could be mistaken for: hashed so that this
# file, a new file of the second theme, names no organisation either (PRD Decisions).
ORG_WORD_HASHES = {
    "bbdefa2950f49882f295b1285d4fa9dec45fc4144bfb07ee6acc68762d12c2e3",
    "4dd4f3835505cd95950fc062a9b9418958b2d820eb07ef5d545f7c99de091e3b",
    "f60ed56a9c8275894022fe5a7a1625c33bdb55b729bb4e38962af4d1613eda25",
    "24e6654bfd1ab85bebb1f721a4be46e6fdb9ea8974d14442d3aaecd1f971fcbb",
    "576ba7c2e4abb7184ca409154dbbbd5306c1a80747fbce4148ea6271fd21e776",
}


def _sha(word: str) -> str:
    return hashlib.sha256(word.encode()).hexdigest()


# ---------- fixtures ----------

@pytest.fixture(scope="module")
def tok():
    return load_script()


@pytest.fixture(scope="module")
def pal():
    assert BRIGHT.is_file(), f"{BRIGHT.name} missing"
    return read_json(BRIGHT)


@pytest.fixture(scope="module")
def theme(tok, pal):
    return tok.load(NAME, "editorial")


def _roles(tree: dict) -> dict:
    return {k: v for k, v in tree["sys"]["color"].items() if not k.startswith("$")}


def _hex(tok, theme, role: str) -> str:
    return tok.hex_of(theme, f"sys.color.{role}").upper()


def _rgb(hexval: str) -> str:
    r, g, b = (int(hexval.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgb({r}, {g}, {b})"


# ---------- the token file ----------

def test_palette_is_valid_and_passes_the_contrast_gate(tok, theme):
    assert tok.validate(theme) == []
    rows = tok.gate(theme)
    assert rows and all(r["ok"] for r in rows)


def test_palette_has_every_paper_green_role_in_the_same_tiers(pal):
    base = read_json(PAPER_GREEN)
    assert {k for k in pal if not k.startswith("$")} == {k for k in base if not k.startswith("$")}
    assert set(_roles(base)) <= set(_roles(pal)), "components read every paper-green role"
    assert len(pal.get("$description", "")) >= 20
    for path in tokens(pal):
        assert path.split(".")[0] in ("ref", "sys"), path


def test_every_role_carries_a_usage_rule_text_flag_and_slots_claimed_once(pal):
    claimed = []
    for role, node in _roles(pal).items():
        assert len(node.get("$description", "")) >= 20, f"{role} lacks a usage rule"
        assert isinstance(node["$extensions"]["com.twm.palette"]["textSafe"], bool), role
        claimed += node["$extensions"]["com.twm.pptx"]["slots"]
    assert sorted(claimed) == sorted(SLOTS), "all 12 clrScheme slots, each exactly once"


def test_scheme_colours_sit_in_their_roles(tok, theme, pal):
    for role, want in SCHEME.items():
        assert _hex(tok, theme, role) == want, role
    ref_hexes = {n["$value"]["hex"].upper() for p, (n, _) in tokens(pal).items() if p.startswith("ref.color.")}
    assert BRIGHTS <= ref_hexes, "all four brights are in the palette"
    assert _hex(tok, theme, "paper-deep") != "#FFFFFF", "light-grey quiet surface"


def test_brights_under_text_contrast_are_never_text(tok, theme, pal):
    paper = _hex(tok, theme, "paper")
    for role, node in _roles(pal).items():
        h = _hex(tok, theme, role)
        if h in BRIGHTS and tok.contrast(h, paper) < 4.5:
            assert node["$extensions"]["com.twm.palette"]["textSafe"] is False, f"{role} ({h}) must be fill/stroke only"


def test_accent_text_is_a_darker_shade_of_the_accent_hue(tok, theme):
    acc, ink = _hex(tok, theme, "accent"), _hex(tok, theme, "accent-ink")
    hue = lambda h: colorsys.rgb_to_hls(*(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)))  # noqa: E731
    (h1, l1, _), (h2, l2, _) = hue(acc), hue(ink)
    assert min(abs(h1 - h2), 1 - abs(h1 - h2)) * 360 <= 10, "same hue family"
    assert l2 < l1, "darker"
    for bg in ("paper", "paper-deep", "tile"):
        assert tok.contrast(ink, _hex(tok, theme, bg)) >= 4.5, bg


def test_text_slots_are_text_safe_roles(pal):
    by_slot = {s: r for r, n in _roles(pal).items() for s in n["$extensions"]["com.twm.pptx"]["slots"]}
    for s in ("dk1", "dk2", "hlink", "folHlink"):
        assert _roles(pal)[by_slot[s]]["$extensions"]["com.twm.palette"]["textSafe"] is True, s


def _org_hits(text: str) -> list[str]:
    hits = [w for w in set(re.findall(r"[a-z0-9]+", text.lower())) if _sha(w) in ORG_WORD_HASHES]
    return hits + [p for p in BANNED[:6] if re.search(p, text, re.I)]


def test_new_theme_files_name_no_organisation():
    """The palette file, the deck's palette block and the run's own records (not the judges' verdicts,
    nor the example's slide copy, which tells a story about named organisations)."""
    assert _sha("example") not in ORG_WORD_HASHES and len(ORG_WORD_HASHES) >= 1
    files = {BRIGHT.name: BRIGHT.read_text(encoding="utf-8"),
             "deck-bright PALETTE": block(DECK_BRIGHT.read_text(encoding="utf-8"), "PALETTE").group(1)}
    for f in ("manifest.json", "NOTES.md"):
        if (RUN_DIR / f).is_file():
            files[f] = (RUN_DIR / f).read_text(encoding="utf-8")
    for name, text in files.items():
        assert _org_hits(text) == [], name


def test_org_check_catches_a_named_palette():
    """Negative control: the hashed list must catch its own words, or a clean pass proves nothing."""
    assert _org_hits("a palette after OpenAI's look") != []


# ---------- the re-themed example ----------

def test_deck_bright_is_the_swap_of_the_reference_deck(tmp_path):
    out = tmp_path / "deck-bright.html"
    r = subprocess.run([sys.executable, str(ASSEMBLE), "swap", str(DECK), "--palette", NAME, "-o", str(out)],
                       capture_output=True, text=True, cwd=SKILL_DIR)
    assert r.returncode == 0, r.stderr
    assert DECK_BRIGHT.is_file() and out.read_bytes() == DECK_BRIGHT.read_bytes(), "regenerate deck-bright.html"


def test_swap_changes_only_the_palette_block():
    a, b = DECK.read_text(encoding="utf-8"), DECK_BRIGHT.read_text(encoding="utf-8")
    assert block(a, "SLIDES").group(1).encode() == block(b, "SLIDES").group(1).encode(), "SLIDES byte-identical"
    for name in ("DECK", "FONTS", "COMPONENTS", "STYLE", "ARCH", "DEFS", "MODULES", "ENGINE"):
        assert block(a, name).group(1) == block(b, name).group(1), name
    pa, pb = block(a, "PALETTE"), block(b, "PALETTE")
    assert pa.group(1) != pb.group(1) and f"/* palette: {NAME} */" in pb.group(1)
    assert a.replace(pa.group(0), "") == b.replace(pb.group(0), ""), "nothing outside the blocks changes"


@pytest.fixture(scope="module")
def browser():
    """System Chrome, once per module (no conftest: other suites share this folder)."""
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        yield b
        b.close()


def _open(browser, w=1920, h=1080):
    c = browser.new_context(viewport={"width": w, "height": h})
    pg = c.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and errors.append(m.text))
    open_deck(pg, DECK_BRIGHT)
    pg.wait_for_function("document.fonts.status === 'loaded'")
    return c, pg, errors


def _at(page, slide, step):
    page.evaluate("([s, k]) => deck.goto(s, k)", [slide, step])
    page.wait_for_function("([s, k]) => deck.state().slide === s && deck.state().step === k", arg=[slide, step])
    settle(page)


@pytest.fixture(scope="module")
def page(browser):
    c, pg, errors = _open(browser)
    yield pg
    c.close()
    assert errors == [], errors


# (what, slide, step, selector, property, role)
COLOURS = [
    ("page ground", "s-2", 0, "body", "backgroundColor", "paper"),
    ("title ink", "s-2", 0, "#s-2 > .title", "color", "ink"),
    ("lead title ink", "s-1", 0, "#s-1 > .title", "color", "ink"),
    ("body secondary", "s-1", 0, "#s1-sub", "color", "ink-2"),
    ("kicker is accent text", "s-2", 0, "#s-2 > .kicker", "color", "accent-ink"),
    ("annotation lead is accent text", "s-2", 2, "#s2-why .annot-lead", "color", "accent-ink"),
    ("progress is an accent fill", "s-2", 0, ".progress", "backgroundColor", "accent"),
    ("ok edge is an accent stroke", "s-2", 4, "#s2-pass", "stroke", "accent"),
    ("loss edge", "s-2", 4, "#s2-hack-in", "stroke", "loss"),
    ("loss badge", "s-4", 3, "#w-lock circle", "fill", "loss"),
    ("alarm light", "s-5", 0, ".dot--alarm", "fill", "alarm"),
    ("lit link is accent ink", "s-4", 3, "#w-admin line", "stroke", "accent-ink"),
    ("pop-over tile surface", "s-4", 2, "#s4-pop-flag", "backgroundColor", "tile"),
]


@pytest.mark.parametrize("what, sid, k, sel, prop, role", COLOURS, ids=[c[0] for c in COLOURS])
def test_key_parts_compute_to_the_new_roles(page, tok, theme, what, sid, k, sel, prop, role):
    _at(page, sid, k)
    got = page.evaluate("([s, p]) => { const e = document.querySelector(s); return e && getComputedStyle(e)[p]; }",
                        [sel, prop])
    assert got == _rgb(_hex(tok, theme, role)), f"{what}: {got}"


TEXT_COLOURS = """() => { const out = new Set();
  const w = document.createTreeWalker(document.querySelector('.slide.is-active') || document.body, NodeFilter.SHOW_TEXT);
  while (w.nextNode()) { const n = w.currentNode; if (!n.textContent.trim()) continue;
    const e = n.parentElement, s = getComputedStyle(e);
    if (s.visibility === 'hidden' || s.display === 'none' || +s.opacity === 0) continue;
    out.add(e.closest('svg') ? s.fill : s.color); }
  return [...out]; }"""


def test_no_rendered_text_is_drawn_in_a_bright(page):
    """Edge of the role rule: brights under 4.5:1 are fills/strokes; text uses ink roles or accent-ink."""
    bad = {_rgb(h) for h in BRIGHTS}
    seen = []
    for sid, last in page.evaluate("deck.plan()"):
        for k in range(last + 1):
            _at(page, sid, k)
            seen += [(sid, k, c) for c in page.evaluate(TEXT_COLOURS) if c in bad]
    assert seen == []


@pytest.mark.parametrize("size", REVIEW_SIZES, ids=[f"{w}x{h}" for w, h in REVIEW_SIZES])
def test_deck_bright_has_no_overlap_clipping_or_offcanvas_text(browser, size):
    w, h = size
    c, pg, errors = _open(browser, w, h)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    faults = []
    for sid in SLIDE_IDS:
        faults += layout_faults(pg, sid, shoot=lambda k, sid=sid: pg.screenshot(
            path=str(ARTIFACTS / f"{sid}-{k}-{w}x{h}.png")))
    c.close()
    assert errors == []
    assert faults == [], "\n".join(faults)


# ---------- the blind evaluation ----------

def _aggregate():
    import importlib.util
    spec = importlib.util.spec_from_file_location("pb008_aggregate", SKILL_DIR / "evals" / "aggregate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_blind_eval_run_has_a_valid_report_with_the_calibration_line(tmp_path):
    agg = _aggregate()
    manifest = json.loads((RUN_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["profile"] == "editorial-talk" and manifest["k"] == 3 and manifest["mode"] == "pointwise"
    assert set(manifest["concerns"]) == {"design-palette", "design-style"}
    assert "deck-bright.html" in manifest["target"]
    stem = f"{manifest['date']}-{manifest['label']}"
    assert RUN_DIR.name == stem
    copy = tmp_path / stem
    shutil.copytree(RUN_DIR, copy, ignore=shutil.ignore_patterns("*.png"))
    json_path, md_path = agg.run(copy)
    report = json.loads(json_path.read_text(encoding="utf-8"))
    committed = json.loads((RUN_DIR / f"{stem}.json").read_text(encoding="utf-8"))
    assert report == committed, "the committed report is the aggregator's output for the committed verdicts"
    assert agg.CALIBRATION_LINE in (RUN_DIR / f"{stem}.md").read_text(encoding="utf-8")
    assert report["calibration"] == agg.CALIBRATION_LINE
    for cid in JUDGED:
        units = report["criteria"][cid]["units"]
        assert units and all(u["k"] == 3 for u in units.values()), cid


def test_judge_verdicts_cite_only_the_runs_evidence():
    """Judges see the evidence files only: every cited slide is a deck slide, every size a shot size."""
    shots = json.loads((RUN_DIR / "evidence" / "shots.json").read_text(encoding="utf-8"))
    sizes = set(shots["sizes"])
    for f in sorted((RUN_DIR / "verdicts").glob("*.json")):
        v = json.loads(f.read_text(encoding="utf-8"))
        for item in v["evidence"]:
            assert item.get("slide", SLIDE_IDS[0]) in SLIDE_IDS, f.name
            assert item.get("size", next(iter(sizes))) in sizes, f.name
