"""Spec: PB-006

The assemble and theme-swap tool (``scripts/assemble.py``): ``new`` builds a single-file deck from the
skeleton with a layout, palette, style, embedded fonts and only the modules its slides trigger;
``swap`` replaces only the theme blocks (and the engine blocks on ``--refresh-engine``) of an existing
deck, leaving SLIDES and DECK byte-identical; ``check`` is the endpoint-safety check both run.

Coverage: happy (every block once, engine runs and navigates in Chrome, embedded Newsreader/Inter used,
starting slides file, palette/style/layout swaps, engine refresh, idempotent swap, uv run, assembled
screenshots layout-clean at every review size) · edge (style whose fonts change rewrites FONTS, swap
back restores the original bytes, default title slide) · negative (no module code without triggers, no
remote request, checker flags each risky pattern, unsafe slides refused, missing/duplicated markers
refused with the file untouched, swap without --refresh-engine keeps engine blocks).
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from helper_engine import (FIXTURE_SLIDES, MODULES_DIR, REVIEW_SIZES, block, layout_faults, load_assemble,
                           open_deck, settle)
from helper_skill import SKILL_DIR

SCRIPT = SKILL_DIR / "scripts" / "assemble.py"
FONTS_DIR = SKILL_DIR / "assets" / "fonts"
PALETTE_SRC = SKILL_DIR / "assets" / "tokens" / "palettes" / "paper-green.tokens.json"
STYLE_SRC = SKILL_DIR / "assets" / "tokens" / "styles" / "editorial.tokens.json"
ARTIFACTS = Path(__file__).parent / "artifacts" / "pb-006"
THEME = ("FONTS", "COMPONENTS", "PALETTE", "STYLE")
ENGINE_BLOCKS = ("ARCH", "DEFS", "MODULES", "ENGINE")
CONTENT = ("SLIDES", "DECK")
ALL = THEME + ENGINE_BLOCKS + CONTENT
FIXTURE_IDS = re.findall(r'<section class="[^"]*" id="([\w-]+)"', FIXTURE_SLIDES)


# ---------- helpers and fixtures ----------

def run(*args, uv=False):
    """Run the shipped CLI (with the test interpreter, or through ``uv run`` to prove PEP 723)."""
    cmd = [shutil.which("uv"), "run", "--quiet", str(SCRIPT)] if uv else [sys.executable, str(SCRIPT)]
    return subprocess.run(cmd + [str(a) for a in args], capture_output=True, text=True, timeout=120)


def regions(src: str) -> dict[str, str]:
    """Split a deck into each block's contents plus everything outside the blocks (``_outside``)."""
    out, rest = {}, src
    for name in ALL:
        m = block(src, name)
        assert m, f"{name} block missing"
        out[name] = m.group(1)
        rest = rest.replace(m.group(0), f"[{name}]", 1)
    out["_outside"] = rest
    return out


def changed(a: str, b: str) -> set[str]:
    ra, rb = regions(a), regions(b)
    return {k for k in ra if ra[k] != rb[k]}


@pytest.fixture(scope="module")
def asm():
    return load_assemble()


@pytest.fixture(scope="module")
def browser():
    """System Chrome, once per module (no conftest: other suites share this folder)."""
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        yield b
        b.close()


@pytest.fixture(scope="module")
def slides_file(tmp_path_factory):
    f = tmp_path_factory.mktemp("in") / "slides.html"
    f.write_text(FIXTURE_SLIDES, encoding="utf-8")
    return f


@pytest.fixture(scope="module")
def deck_file(tmp_path_factory, slides_file):
    out = tmp_path_factory.mktemp("new") / "deck.html"
    r = run("new", out, "--title", "Fixture Deck", "--subtitle", "Assembled", "--slides", slides_file)
    assert r.returncode == 0, r.stderr
    return out


@pytest.fixture(scope="module")
def other_palette(tmp_path_factory):
    """A gate-passing palette that differs from paper-green only in its accent hue."""
    tree = json.loads(PALETTE_SRC.read_text(encoding="utf-8"))
    tree["ref"]["color"]["green"]["500"]["$value"] = {"colorSpace": "srgb", "components": [0.2314, 0.5098, 0.9647],
                                                     "hex": "#3b82f6"}
    f = tmp_path_factory.mktemp("pal") / "test-blue.tokens.json"
    f.write_text(json.dumps(tree, indent=2), encoding="utf-8")
    return f


@pytest.fixture(scope="module")
def sans_style(tmp_path_factory):
    """The editorial style with its serif role pointed at Inter: its font set shrinks to one family."""
    tree = json.loads(STYLE_SRC.read_text(encoding="utf-8"))
    tree["ref"]["font"]["newsreader"]["$value"] = ["Inter", "system-ui", "sans-serif"]
    f = tmp_path_factory.mktemp("sty") / "all-sans.tokens.json"
    f.write_text(json.dumps(tree, indent=2), encoding="utf-8")
    return f


def _copy(deck_file, tmp_path, name="d.html"):
    f = tmp_path / name
    f.write_bytes(deck_file.read_bytes())
    return f


def _page(browser, deck_file, w=1280, h=720):
    c = browser.new_context(viewport={"width": w, "height": h})
    pg = c.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    return c, pg, errors


# ---------- new ----------

def test_new_deck_holds_every_block_exactly_once(deck_file):
    src = deck_file.read_text(encoding="utf-8")
    assert src.lstrip().lower().startswith("<!doctype html>")
    for name in ALL:
        assert src.count(f"{name}:BEGIN") == 1 and src.count(f"{name}:END") == 1, name
    for name in ("FONTS", "ARCH", "COMPONENTS", "PALETTE", "STYLE", "ENGINE", "SLIDES"):
        assert block(src, name).group(1).strip(), f"{name} left empty"
    assert "@layer components" in block(src, "COMPONENTS").group(1)
    assert "--sys-color-paper" in block(src, "PALETTE").group(1)
    assert "{{" not in src and "<title>Fixture Deck · Assembled</title>" in src
    assert block(src, "SLIDES").group(1).strip() == FIXTURE_SLIDES.strip()


def test_new_deck_runs_in_chrome_and_navigates(browser, deck_file):
    c, pg, errors = _page(browser, deck_file)
    open_deck(pg, deck_file)
    assert pg.evaluate("deck.state().slide") == "s-1"
    pg.keyboard.press("ArrowRight")
    pg.wait_for_function("deck.state().slide === 's-2'")
    c.close()
    assert errors == []


def test_new_deck_embeds_and_uses_the_styles_fonts(browser, deck_file):
    src = deck_file.read_text(encoding="utf-8")
    faces = re.findall(r"@font-face\s*\{[^}]*\}", block(src, "FONTS").group(1))
    assert faces and all("url(data:font/woff2;base64," in f for f in faces)
    c, pg, _ = _page(browser, deck_file)
    open_deck(pg, deck_file)
    pg.evaluate("document.fonts.ready.then(() => true)")
    loaded = pg.evaluate("[...document.fonts].filter(f => f.status === 'loaded').map(f => f.family.replace(/\"/g, ''))")
    first = pg.evaluate("""s => getComputedStyle(document.querySelector(s)).fontFamily.split(',')[0]
                           .replace(/["']/g, '').trim()""", "#s-2 .title")
    body = pg.evaluate("""s => getComputedStyle(document.querySelector(s)).fontFamily.split(',')[0]
                          .replace(/["']/g, '').trim()""", "#s-2 .body li")
    c.close()
    assert {"Newsreader", "Inter"} <= set(loaded), loaded
    assert (first, body) == ("Newsreader", "Inter")


def test_new_deck_fetches_nothing_remote(browser, deck_file):
    c = browser.new_context()
    seen = []

    def route(r):
        seen.append(r.request.url)
        return r.continue_() if r.request.url.startswith(("file:", "data:")) else r.abort()

    c.route("**/*", route)
    pg = c.new_page()
    open_deck(pg, deck_file)
    pg.evaluate("document.fonts.ready.then(() => true)")
    settle(pg)
    c.close()
    assert seen and all(u.startswith(("file:", "data:")) for u in seen), seen


def test_new_deck_passes_the_shipped_endpoint_check(asm, deck_file):
    assert asm.endpoint_faults(deck_file.read_text(encoding="utf-8")) == []
    r = run("check", deck_file)
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("plant", [
    '<script src="https://cdn.example.org/x.js"></script>', "<script>eval('1')</script>",
    "<script>atob('eA==')</script>", "<script>document.write('x')</script>",
    "<script>new Function('x')</script>", "<script>el.innerHTML = 'x'</script>",
    "<script>fetch('/x')</script>", '<link rel="stylesheet" href="https://example.org/a.css">',
    "<style>@import url(https://example.org/a.css);</style>", '<iframe src="x.html"></iframe>',
    '<form action="/x"></form>', "<style>.x { background: url(https://example.org/a.png); }</style>"])
def test_endpoint_check_flags_each_risky_pattern(asm, deck_file, plant):
    src = deck_file.read_text(encoding="utf-8").replace("</body>", plant + "\n</body>")
    assert asm.endpoint_faults(src), plant


def test_endpoint_check_allows_citation_links(asm, deck_file):
    """Remote URLs are fine as ``a.src[href]`` citation targets (the fixture has several)."""
    src = deck_file.read_text(encoding="utf-8")
    assert 'href="https://example.org/lead"' in src
    assert asm.endpoint_faults(src) == []


def test_new_refuses_unsafe_slides_and_writes_nothing(tmp_path):
    bad = tmp_path / "bad.html"
    bad.write_text(FIXTURE_SLIDES + '<script>eval("x")</script>', encoding="utf-8")
    out = tmp_path / "deck.html"
    r = run("new", out, "--title", "T", "--slides", bad)
    assert r.returncode != 0 and "eval" in r.stderr
    assert not out.exists()


def test_new_without_slides_starts_with_one_title_slide(browser, tmp_path):
    out = tmp_path / "deck.html"
    r = run("new", out, "--title", "Quarterly Review", "--subtitle", "Draft")
    assert r.returncode == 0, r.stderr
    c, pg, errors = _page(browser, out)
    open_deck(pg, out)
    plan = pg.evaluate("deck.plan()")
    title = pg.inner_text(".slide .title")
    c.close()
    assert len(plan) == 1 and "Quarterly Review" in title and errors == []


def test_a_deck_without_module_triggers_carries_no_module_code(deck_file):
    src = deck_file.read_text(encoding="utf-8")
    assert "window.deckModules || []).push(" not in src
    assert block(src, "MODULES").group(1).strip() == ""
    for f in MODULES_DIR.glob("*"):
        assert f.read_text(encoding="utf-8").strip() not in src, f.name


def test_a_deck_carries_only_the_modules_its_triggers_name(tmp_path):
    slides = tmp_path / "s.html"
    slides.write_text("""<section class="slide" id="a" data-chapter="A"><h2 class="title">One</h2>
      <div class="popover" data-show-at="1" data-hide-at="2"><p>Pop</p></div></section>""", encoding="utf-8")
    out = tmp_path / "deck.html"
    assert run("new", out, "--title", "T", "--slides", slides).returncode == 0
    src = out.read_text(encoding="utf-8")
    assert (MODULES_DIR / "popover.js").read_text(encoding="utf-8").strip() in block(src, "MODULES").group(1)
    assert (MODULES_DIR / "popover.css").read_text(encoding="utf-8").strip() in block(src, "ARCH").group(1)
    for name in ("narration", "scene", "tile-row"):
        assert (MODULES_DIR / f"{name}.js").read_text(encoding="utf-8").strip() not in src, name


def test_cli_runs_through_uv_with_its_inline_metadata(tmp_path):
    if not shutil.which("uv"):
        pytest.skip("uv not installed")
    assert SCRIPT.read_text(encoding="utf-8").startswith("# /// script")
    out = tmp_path / "deck.html"
    r = run("new", out, "--title", "T", uv=True)
    assert r.returncode == 0, r.stderr
    assert out.stat().st_size > 100_000, "fonts embedded"


# ---------- fonts shipped with the skill ----------

def test_every_shipped_style_font_has_a_file_and_an_ofl_licence(asm):
    for style in (SKILL_DIR / "assets" / "tokens" / "styles").glob("*.tokens.json"):
        fams = asm.style_families(style)
        assert fams, style.name
        for fam in fams:
            faces = asm.font_faces(fam)
            assert faces, f"{style.name}: {fam} has no font file"
            for face in faces:
                assert (FONTS_DIR / face["file"]).is_file(), face
            lic = FONTS_DIR / asm.font_licence(fam)
            text = lic.read_text(encoding="utf-8")
            assert "SIL Open Font License" in text and "Version 1.1" in text and fam in text, lic.name


# ---------- swap ----------

def test_swap_palette_changes_only_the_palette_block(deck_file, other_palette, tmp_path):
    f = _copy(deck_file, tmp_path)
    before = f.read_text(encoding="utf-8")
    r = run("swap", f, "--palette", other_palette)
    assert r.returncode == 0, r.stderr
    after = f.read_text(encoding="utf-8")
    assert changed(before, after) == {"PALETTE"}
    assert "#3b82f6" in block(after, "PALETTE").group(1)
    for name in CONTENT:   # byte-identical, not just equal after decoding
        assert block(after, name).group(1).encode() == block(before, name).group(1).encode()


def test_swap_is_idempotent_and_swapping_back_restores_the_original(deck_file, other_palette, tmp_path):
    f = _copy(deck_file, tmp_path)
    original = f.read_bytes()
    assert run("swap", f, "--palette", other_palette).returncode == 0
    once = f.read_bytes()
    assert run("swap", f, "--palette", other_palette).returncode == 0
    assert f.read_bytes() == once
    assert run("swap", f, "--palette", "paper-green").returncode == 0
    assert f.read_bytes() == original


def test_swap_style_rewrites_fonts_only_when_the_styles_fonts_change(deck_file, sans_style, tmp_path):
    f = _copy(deck_file, tmp_path)
    before = f.read_text(encoding="utf-8")
    assert run("swap", f, "--style", "editorial").returncode == 0
    assert f.read_text(encoding="utf-8") == before, "same style: nothing changes"
    assert run("swap", f, "--style", sans_style).returncode == 0
    after = f.read_text(encoding="utf-8")
    assert changed(before, after) == {"STYLE", "FONTS"}
    fonts = block(after, "FONTS").group(1)
    assert "Inter" in fonts and "Newsreader" not in fonts


def test_swap_layout_changes_only_the_components_block(deck_file, tmp_path):
    f = _copy(deck_file, tmp_path)
    css = tmp_path / "plain.css"
    css.write_text("@layer components { .slide { padding: 2rem; } }", encoding="utf-8")
    before = f.read_text(encoding="utf-8")
    assert run("swap", f, "--layout", css).returncode == 0
    after = f.read_text(encoding="utf-8")
    assert changed(before, after) == {"COMPONENTS"}
    assert ".slide { padding: 2rem; }" in block(after, "COMPONENTS").group(1)


def test_swap_writes_to_another_file_when_asked(deck_file, other_palette, tmp_path):
    f = _copy(deck_file, tmp_path)
    out = tmp_path / "blue.html"
    assert run("swap", f, "--palette", other_palette, "-o", out).returncode == 0
    assert f.read_bytes() == deck_file.read_bytes()
    assert changed(f.read_text(encoding="utf-8"), out.read_text(encoding="utf-8")) == {"PALETTE"}


@pytest.mark.parametrize("fault", ["missing", "duplicated", "end-missing"])
@pytest.mark.parametrize("name", ["PALETTE", "SLIDES"])
def test_swap_refuses_a_deck_with_broken_markers(deck_file, other_palette, tmp_path, fault, name):
    f = _copy(deck_file, tmp_path)
    src = f.read_text(encoding="utf-8")
    m = block(src, name)
    begin = src[m.start():m.start(1)]
    if fault == "missing":
        src = src.replace(begin, "", 1)
    elif fault == "duplicated":
        src = src.replace(begin, begin + begin, 1)
    else:
        src = src[:m.end(1)] + src[m.end():]
    f.write_text(src, encoding="utf-8")
    before = f.read_bytes()
    r = run("swap", f, "--palette", other_palette)
    assert r.returncode != 0
    assert name in r.stderr and ("missing" in r.stderr or "more than once" in r.stderr), r.stderr
    assert f.read_bytes() == before, "a refused swap leaves the file untouched"


def test_refresh_engine_updates_the_engine_blocks_only(deck_file, tmp_path):
    f = _copy(deck_file, tmp_path)
    fresh = f.read_text(encoding="utf-8")
    stale = fresh
    for name in ENGINE_BLOCKS:   # plant an old engine
        m = block(stale, name)
        stale = stale[:m.start(1)] + f"\n/* old {name} */\n" + stale[m.end(1):]
    f.write_text(stale, encoding="utf-8")
    assert run("swap", f, "--palette", "paper-green").returncode == 0
    assert f.read_text(encoding="utf-8") == stale, "without --refresh-engine the engine blocks stay"
    assert run("swap", f, "--refresh-engine").returncode == 0
    assert f.read_text(encoding="utf-8") == fresh
    assert changed(stale, fresh) == set(ENGINE_BLOCKS)


# ---------- the look: assembled screenshots at every review size ----------

def test_new_deck_is_layout_clean_at_every_step_and_review_size(browser, deck_file):
    """Saves screenshots to ``tests/artifacts/pb-006/`` for the done-time look."""
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    faults = []
    for w, h in REVIEW_SIZES:
        c, pg, errors = _page(browser, deck_file, w, h)
        open_deck(pg, deck_file)
        pg.evaluate("document.fonts.ready.then(() => true)")
        for sid in FIXTURE_IDS:
            faults += layout_faults(pg, sid, shoot=lambda k, sid=sid: pg.screenshot(
                path=str(ARTIFACTS / f"new-{sid}-{k}-{w}x{h}.png")))
        c.close()
        assert errors == []
    assert faults == []
