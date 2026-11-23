"""Spec: PB-027

The skill defects two cold builds reported (``evals-runs/261123-baseline/COLD-BUILD-FEEDBACK.md``)
are fixed, one or more tests per fixed row (row number in each test's section heading).

Coverage: happy (guard callable inside a sync Playwright session and with a given browser; the
project template's guard test runs green on a clean deck; ``shoot --slides`` keeps other slides'
shots; ``assemble slides`` round-trips and replaces only SLIDES; template index rows only for shipped
files; visible words counted as the content part defines, matching CN-04; closing slide with prompts
layout-clean at every review size; standalone timeline; chart parts render (square swatch, no lift,
start/end anchored labels); a one-line tile centres among two-line siblings; any CSS selector in
``data-for``; a documented unlinked source passes RS-05) · edge (new module triggers in replaced
slides pull their module in; a slide no longer in the deck loses its shots; an invalid ``data-for``
selector leaves the other notes working) · negative (template guard test fails on a faulty deck;
unsafe replacement slides are refused and the deck is left as found; a label spilling past its
diagram's viewBox is flagged; a bare plain-text source still fails RS-05; titles are never
self-approved by a test build).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from helper_engine import FIXTURE_SLIDES, REVIEW_SIZES, load_assemble
from helper_eval import EVAL_DIR, _import, loader
from helper_skill import SKILL_DIR

SCRIPTS = SKILL_DIR / "scripts"
TPL = SKILL_DIR / "assets" / "templates" / "project"
PROCESS = SKILL_DIR / "process" / "PROCESS.md"
STORYBOARD = SKILL_DIR / "content" / "STORYBOARD.md"
LAYOUT = SKILL_DIR / "design" / "LAYOUT.md"
ARCH = SKILL_DIR / "architecture" / "ARCHITECTURE.md"
RESEARCH = SKILL_DIR / "research" / "RESEARCH.md"
BRIEFS = SKILL_DIR / "evals" / "briefs" / "BRIEFS.md"
PROFILE = SKILL_DIR / "voice" / "profiles" / "twm.md"
VOICE = SKILL_DIR / "voice" / "VOICE.md"
CRITERIA_MD = SKILL_DIR / "evals" / "CRITERIA.md"


def _text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _load(path: Path, name: str):
    """Import a shipped script by path (``scripts/`` is not a package)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def guard():
    return _load(SCRIPTS / "layout_guard.py", "pb027_layout_guard")


@pytest.fixture(scope="module")
def shoot():
    return _load(SCRIPTS / "shoot.py", "pb027_shoot")


@pytest.fixture(scope="module")
def gates():
    return _import(EVAL_DIR / "gates.py", "pb027_gates")


@pytest.fixture(scope="module")
def browser():
    """System Chrome held open for the whole module: the guard must work beside it."""
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        yield b
        b.close()


def _deck(path: Path, slides: str, deck_css: str = "") -> Path:
    asm = load_assemble()
    asm.new(path, "Cold Fixture", "PB-027", slides=slides)
    if deck_css:
        path.write_text(asm.fill(path.read_text(encoding="utf-8"), {"DECK": deck_css}), encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def core_deck(tmp_path_factory):
    return _deck(tmp_path_factory.mktemp("core") / "core.html", FIXTURE_SLIDES)


def _page(browser, deck: Path, w=1280, h=720):
    ctx = browser.new_context(viewport={"width": w, "height": h})
    pg = ctx.new_page()
    errors: list[str] = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(deck.resolve().as_uri())
    pg.wait_for_function("window.deck && window.deck.ready === true")
    pg.wait_for_function("document.fonts.status === 'loaded'")
    return ctx, pg, errors


def _faults(guard, browser, deck: Path, sid: str, sizes=REVIEW_SIZES) -> list[str]:
    out = []
    for w, h in sizes:
        ctx, pg, errors = _page(browser, deck, w, h)
        out += [f"{w}x{h} {f}" for f in guard.slide_faults(pg, sid)]
        ctx.close()
        assert errors == [], errors
    return out


# ---------- row 1: the layout guard from a test session, and the template's guard test ----------

def test_guard_runs_inside_an_open_sync_playwright_session(guard, browser, core_deck):
    """The module's ``browser`` fixture holds a sync Playwright session open, as a deck's suite does."""
    assert browser.is_connected()
    report = guard.guard(core_deck, [(1280, 720)])
    assert report["ok"] is True and report["states"] > 0, report["faults"]


def test_guard_reuses_a_given_browser_and_leaves_it_open(guard, browser, core_deck):
    report = guard.guard(core_deck, [(1288, 598)], slides=["s-3"], browser=browser)
    assert report["ok"] is True and report["states"] == 3
    assert browser.is_connected(), "the caller's browser must not be closed by the guard"


def _project(tmp_path: Path, deck_css: str = "") -> Path:
    proj = tmp_path / "proj"
    shutil.copytree(TPL / "tests", proj / "tests")
    _deck(proj / "deck" / "deck.html", FIXTURE_SLIDES, deck_css)
    return proj


def _pytest(proj: Path):
    env = dict(os.environ, PRESENTATION_SKILL_DIR=str(SKILL_DIR))
    return subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "no:xdist", "tests"],
                          cwd=proj, env=env, capture_output=True, text=True, timeout=600)


def test_template_guard_test_is_green_on_a_clean_deck(tmp_path):
    files = sorted(p.name for p in (TPL / "tests").glob("*.py"))
    assert "test_layout_guard.py" in files and any(f.startswith("helper_") for f in files), files
    r = _pytest(_project(tmp_path))
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-2000:]
    assert re.search(r"\b4 passed\b", r.stdout), "one guard case per slide"


def test_template_guard_test_fails_on_a_faulty_deck_naming_the_slide(tmp_path):
    r = _pytest(_project(tmp_path, "@layer deck { #s-2 > .body { translate: 0 -30vh; } }"))
    assert r.returncode == 1, r.stdout[-3000:]
    assert "s-2" in r.stdout and "covers title" in r.stdout
    assert re.search(r"\b1 failed, 3 passed\b", r.stdout), r.stdout[-1500:]


# ---------- row 2: shoot --slides keeps other slides' shots ----------

def test_shoot_slides_keeps_the_other_slides_shots_and_indexes_them(shoot, core_deck, tmp_path):
    shoot.shoot(core_deck, tmp_path, [(1280, 720)])
    before = {p.name for p in tmp_path.glob("*.png")}
    index = shoot.shoot(core_deck, tmp_path, [(1280, 720)], slides=["s-2"])
    assert {p.name for p in tmp_path.glob("*.png")} == before, "other slides' shots kept, s-2's replaced"
    assert {e["file"] for e in index["shots"]} == before
    assert [s["id"] for s in index["slides"]] == ["s-1", "s-2", "s-3", "s-4"], "deck order, all shot slides"
    assert json.loads((tmp_path / "shots.json").read_text(encoding="utf-8")) == index


def test_shoot_slides_drops_shots_of_slides_no_longer_in_the_deck(shoot, core_deck, tmp_path):
    (tmp_path / "s-9-0-1280x720.png").write_bytes(b"stale")
    (tmp_path / "shots.json").write_text(json.dumps({"shots": [
        {"file": "s-9-0-1280x720.png", "slide": "s-9", "step": 0, "size": "1280x720", "mode": "step"}]}))
    shoot.shoot(core_deck, tmp_path, [(1280, 720)], slides=["s-4"])
    assert not (tmp_path / "s-9-0-1280x720.png").exists()


def test_process_documents_that_slides_filter_keeps_other_shots():
    tools = _text(PROCESS).split("## Tools", 1)[1].split("\n## ", 1)[0]
    assert re.search(r"--slides[^\n]*\n?[^\n]*keeps?", tools), "PROCESS Tools says --slides keeps other shots"


# ---------- row 3: assemble slides (replace / extract) and the source of truth ----------

def _asm_cli(*args):
    return subprocess.run([sys.executable, str(SCRIPTS / "assemble.py"), *map(str, args)],
                          capture_output=True, text=True, cwd=SKILL_DIR)


def test_assemble_slides_extracts_and_replaces_only_the_slides_block(tmp_path):
    asm = load_assemble()
    deck = _deck(tmp_path / "deck.html", FIXTURE_SLIDES)
    before = _text(deck)
    r = _asm_cli("slides", deck, "--to", tmp_path / "slides.html")
    assert r.returncode == 0, r.stderr
    assert _text(tmp_path / "slides.html").strip("\n") == asm.read_block(before, "SLIDES").strip("\n")
    r = _asm_cli("slides", deck, "--from", tmp_path / "slides.html")
    assert r.returncode == 0, r.stderr
    assert _text(deck) == before, "extract then replace is a byte-identical round trip"
    new = FIXTURE_SLIDES.replace("The end", "The very end")
    (tmp_path / "edited.html").write_text(new, encoding="utf-8")
    assert _asm_cli("slides", deck, "--from", tmp_path / "edited.html").returncode == 0
    after = _text(deck)
    assert "The very end" in asm.read_block(after, "SLIDES")
    for name in asm.BLOCKS:
        if name != "SLIDES":
            assert asm.read_block(after, name) == asm.read_block(before, name), name


def test_assemble_slides_pulls_in_a_module_the_new_slides_trigger(tmp_path):
    asm = load_assemble()
    deck = _deck(tmp_path / "deck.html", FIXTURE_SLIDES)
    assert "narration" not in asm.read_block(_text(deck), "MODULES")
    slides = FIXTURE_SLIDES.replace('<div class="body"><p>No steps here.</p></div>',
                                    '<div class="body"><p>No steps here.</p></div>\n  <div class="narration">'
                                    '<article class="narr-tile" data-at="1"><p>Told.</p></article></div>')
    (tmp_path / "s.html").write_text(slides, encoding="utf-8")
    assert _asm_cli("slides", deck, "--from", tmp_path / "s.html").returncode == 0
    assert "narration" in asm.read_block(_text(deck), "MODULES")


def test_assemble_slides_refuses_unsafe_slides_and_leaves_the_deck(tmp_path):
    deck = _deck(tmp_path / "deck.html", FIXTURE_SLIDES)
    before = deck.read_bytes()
    (tmp_path / "bad.html").write_text(FIXTURE_SLIDES + "<script>alert(1)</script>", encoding="utf-8")
    r = _asm_cli("slides", deck, "--from", tmp_path / "bad.html")
    assert r.returncode == 1 and deck.read_bytes() == before


def test_source_of_truth_for_slides_is_stated_in_architecture_and_process():
    for p in (ARCH, PROCESS):
        assert re.search(r"source of truth", _text(p), re.I) and "assemble.py slides" in _text(p), p.name


# ---------- rows 4–5: template rows born on content, deck path from the project, install list ----------

def _index_rows(md: str) -> list[str]:
    table = md.split("### Repo Index", 1)[1].split("\n### ", 1)[0].split("\n## ", 1)[0]
    rows = [r for r in table.splitlines() if r.startswith("| `")]
    return [re.match(r"\| `([^`]+)`", r).group(1) for r in rows]


def test_template_index_has_live_rows_only_for_files_the_template_ships():
    rows = _index_rows(_text(TPL / "AGENTS.md"))
    assert rows, "the template keeps a repo index"
    missing = [p for p in rows if not (TPL / p).exists()]
    assert missing == [], f"index rows for files the template never creates: {missing}"


def test_template_lists_born_later_rows_and_defers_the_deck_path_to_house_rules():
    t = _text(TPL / "AGENTS.md")
    for path in ("docs/STORYBOARD.md", "docs/VOICE.md", "docs/DESIGN.md", "docs/research/RESEARCH.md",
                 "design/prototypes/PROTOTYPES.md", "docs/ADR.jsonl", "evals/runs/"):
        assert f"`{path}`" in t, path
    assert re.search(r"born", t, re.I)
    assert re.search(r"house rules?", t, re.I), "the deck path follows the project's house rules"


def test_install_list_names_every_template_file_and_each_born_later_docs_method():
    install = _text(PROCESS).split("## Install into the deck project", 1)[1].split("\n## ", 1)[0]
    for f in sorted(TPL.rglob("*")):
        if f.is_file():
            assert f.relative_to(TPL).as_posix() in install, f.relative_to(TPL).as_posix()
    for doc, part in (("STORYBOARD", "content part"), ("VOICE", "voice part"), ("DESIGN", "layout part"),
                      ("research", "research part")):
        line = next((l for l in install.splitlines() if doc in l), "")
        assert part in line or part in install.split(doc, 1)[1][:240], (doc, part)


# ---------- row 6: visible words, as CN-04 counts them ----------

WORDS_SLIDES = """
<section class="slide" id="w-1" data-chapter="Words">
  <p class="kicker">01 · Words</p>
  <h2 class="title">Five words in this title</h2>
  <div class="body body--split">
    <div><p>Three body words.</p><p class="cite">Two cite</p></div>
    <svg class="diagram" viewBox="0 0 600 200" role="img" aria-label="A labelled tile">
      <g class="layer-nodes"><g class="tile" id="w1-t"><rect x="40" y="40" width="300" height="120"/><text class="tile-title">Tile title</text></g></g>
      <g class="layer-labels"><text class="label" x="470" y="100">ONE</text></g>
    </svg>
  </div>
  <aside class="overlay overlay--insight" data-at="1"><p>Four words of insight.</p></aside>
  <aside class="note" data-for="#w1-t"><h3>Many words that never count</h3><p>Reader notes are excluded from the visible count whatever their length.</p>
    <a class="src" href="https://www.gov.uk/words">Words source</a></aside>
</section>
"""
# step 0: kicker 2 ("01", "Words"; the dot is not a word) + title 5 + body 3 + cite 2 + tile 2 + label 1 = 15
# step 1: + Insight 4 = 19 (the wordiest step decides)


def _crit(cid: str, **params) -> dict:
    lib = loader().load_library(EVAL_DIR)
    return dict(lib[cid], weight=1, gate=False, params=params)


def test_cn04_counts_every_visible_word_at_the_wordiest_step(gates, browser, tmp_path):
    deck = _deck(tmp_path / "w.html", WORDS_SLIDES)
    ok = gates.deck_verdicts(deck, [_crit("CN-04", max_words=19)], sizes=[(1280, 720)], browser=browser)
    over = gates.deck_verdicts(deck, [_crit("CN-04", max_words=18)], sizes=[(1280, 720)], browser=browser)
    assert [v["result"] for v in ok] == ["pass"], ok
    assert [v["result"] for v in over] == ["fail"] and "19 visible words at step 1" in json.dumps(over)


def test_content_part_defines_visible_words_as_the_gate_counts_them():
    t = _text(STORYBOARD)
    m = re.search(r"\*\*Visible words\b.*?(?=\n\d+\. |\n## |\Z)", t, re.S)
    assert m, "STORYBOARD defines visible words"
    d = m.group(0).lower()
    for counted in ("kicker", "cite", "diagram", "insight", "step"):
        assert counted in d, counted
    for excluded in ("reader note", "bar"):
        assert excluded in d, excluded
    assert re.search(r"voice", d) and re.search(r"note", d), "says how the cap and the voice profile are reconciled"
    assert re.search(r"wordiest step", _text(CRITERIA_MD)), "CRITERIA's CN-04 row matches the definition"


# ---------- row 7: title approval without a presenter ----------

def test_title_approval_is_needed_before_presenting_not_for_done():
    dod = _text(TPL / "AGENTS.md").split("**Definition of done**", 1)[1].split("\n## ", 1)[0]
    assert re.search(r"✎", dod) and re.search(r"present", dod, re.I), "DoD says titles may stay ✎ until presenting"
    board = _text(STORYBOARD)
    assert re.search(r"no presenter|presenter (is )?unavailable", board, re.I)
    briefs = _text(BRIEFS)
    assert not re.search(r"approve titles", briefs, re.I), "a test build never self-approves titles"
    assert "✎" in briefs


# ---------- row 8: byline for teams or no named presenter ----------

def test_byline_rule_has_a_team_or_unnamed_form():
    byline = _text(PROFILE).split("## Kickers and byline", 1)[1].split("\n## ", 1)[0]
    assert re.search(r"team", byline, re.I) and re.search(r"never\**\s+(invent|a person)", byline, re.I), byline
    assert re.search(r"byline", _text(VOICE), re.I), "the profile shape names the byline forms"


# ---------- row 9: closing slide with discussion prompts ----------

CLOSE_SLIDES = """
<section class="slide slide--lead" id="c-1" data-chapter="Opening"><h2 class="title">Opening</h2></section>
<section class="slide slide--lead slide--end" id="c-2" data-chapter="Close">
  <h2 class="title" id="c2-title">Retiming the two cross-town routes for the diversion is the next quarter's test, checked at the end of January</h2>
  <div class="body">
    <ol class="prompts">
      <li class="prompt" data-show-at="1">How much running time does the diversion need at the school run, and where should it come from?</li>
      <li class="prompt" data-show-at="2">What result in January would tell us the vacancies, not the closures, drove October?</li>
      <li class="prompt" data-show-at="3">Should reports to the council show lost mileage beside the target while the works run?</li>
    </ol>
  </div>
</section>
"""


def test_closing_slide_with_prompts_is_layout_clean_and_centred_at_every_size(guard, browser, tmp_path):
    deck = _deck(tmp_path / "close.html", CLOSE_SLIDES)
    assert _faults(guard, browser, deck, "c-2") == []
    for w, h in REVIEW_SIZES:
        ctx, pg, _ = _page(browser, deck, w, h)
        guard.goto_step(pg, "c-2", 3)
        m = pg.evaluate("""() => { const s = document.getElementById('c-2').getBoundingClientRect(),
            t = document.getElementById('c2-title').getBoundingClientRect(),
            p = document.querySelector('#c-2 .prompts').getBoundingClientRect(),
            bar = document.querySelector('.bar').getBoundingClientRect();
          return { sc: s.left + s.width / 2, tc: t.left + t.width / 2, pc: p.left + p.width / 2,
                   tb: t.bottom, pt: p.top, tt: t.top, bb: bar.bottom }; }""")
        ctx.close()
        assert abs(m["tc"] - m["sc"]) < 2 and abs(m["pc"] - m["sc"]) < 2, (w, h, m)
        assert m["tt"] >= m["bb"] and m["pt"] >= m["tb"], (w, h, m)


def test_layout_documents_the_closing_layout_with_prompts():
    rows = [l for l in _text(LAYOUT).splitlines() if l.startswith("| Closing")]
    assert any(".prompts" in r and "slide--end" in r for r in rows), rows


# ---------- row 10: a timeline body outside a scene ----------

TIMELINE_SLIDES = """
<section class="slide" id="t-1" data-chapter="Timeline">
  <p class="kicker">01 · Timeline</p>
  <h2 class="title">Delays rose only after the diversion began</h2>
  <div class="body body--timeline">
    <ol class="steps">
      <li id="t1-a" data-show-at="1"><strong>4 July</strong>Roadworks start on the high street</li>
      <li id="t1-b" data-show-at="2"><strong>11 July</strong>Two routes divert through the estate</li>
      <li class="sub" id="t1-c" data-show-at="2">Stops on the estate move</li>
    </ol>
  </div>
</section>
"""


def test_timeline_body_works_on_a_standard_slide(guard, browser, tmp_path):
    deck = _deck(tmp_path / "t.html", TIMELINE_SLIDES)
    assert _faults(guard, browser, deck, "t-1") == []
    ctx, pg, _ = _page(browser, deck)
    seen = []
    for k in range(3):
        guard.goto_step(pg, "t-1", k)
        seen.append(pg.evaluate("""() => ['t1-a', 't1-b', 't1-c'].map(i => +getComputedStyle(document.getElementById(i)).opacity > .5)"""))
    block = pg.evaluate("getComputedStyle(document.querySelector('#t1-a strong')).display")
    ctx.close()
    assert seen == [[False, False, False], [True, False, False], [True, True, True]], "never shown ahead"
    assert block == "block", "the date sits on its own line"
    row = next((l for l in _text(LAYOUT).splitlines() if l.startswith("| Timeline")), "")
    assert not re.search(r"Use when a scene's body", row) and re.search(r"standard|any", row, re.I), row


# ---------- rows 11–12: chart parts; labels that fit their diagram ----------

CHART_SLIDES = """
<section class="slide" id="k-1" data-chapter="Chart">
  <p class="kicker">01 · Chart</p>
  <h2 class="title">Bars, axis, target and legend come from the diagram kit</h2>
  <div class="body body--stack">
    <svg class="diagram" id="k1-chart" viewBox="0 0 1000 420" role="img" aria-label="Two bars against a target">
      <g class="layer-edges">
        <line class="chart-grid" id="k1-grid" x1="120" y1="200" x2="980" y2="200"/>
        <line class="chart-axis" id="k1-axis" x1="120" y1="360" x2="980" y2="360"/>
        <line class="chart-target" id="k1-target" x1="120" y1="120" x2="980" y2="120" data-show-at="1"/>
      </g>
      <g class="layer-nodes">
        <rect class="chart-bar" id="k1-bar" x="200" y="160" width="80" height="200"/>
        <rect class="chart-bar chart-bar--key" id="k1-key" x="300" y="200" width="80" height="160" data-show-at="1"/>
      </g>
      <g class="layer-key">
        <rect class="chart-swatch" id="k1-sw" x="600" y="12" width="24" height="24"/>
        <rect class="chart-swatch chart-swatch--key" id="k1-sw-key" x="760" y="12" width="24" height="24"/>
      </g>
      <g class="layer-labels">
        <text class="label label--start" id="k1-start" x="636" y="32">Q2</text>
        <text class="label label--start" x="796" y="32">Q3</text>
        <text class="label label--end" id="k1-end" x="110" y="366">0%</text>
        <text class="label" x="240" y="400">North</text>
      </g>
    </svg>
  </div>
</section>
"""

RESOLVE = """tok => { const p = document.createElement('i'); p.style.color = 'var(' + tok + ')'; document.body.append(p);
  const c = getComputedStyle(p).color; p.remove(); return c; }"""


def test_chart_parts_render_square_swatches_unlifted_bars_and_anchored_labels(guard, browser, tmp_path):
    deck = _deck(tmp_path / "k.html", CHART_SLIDES)
    assert _faults(guard, browser, deck, "k-1") == []
    ctx, pg, _ = _page(browser, deck, 1920, 1080)
    guard.goto_step(pg, "k-1", 1)
    m = pg.evaluate("""() => { const cs = id => getComputedStyle(document.getElementById(id)), r = id => document.getElementById(id).getBoundingClientRect();
      return { bar: [cs('k1-bar').fill, cs('k1-bar').filter], key: [cs('k1-key').fill, cs('k1-key').filter],
        sw: [r('k1-sw').width, r('k1-sw').height, parseFloat(cs('k1-sw').rx) || 0, cs('k1-sw').filter, cs('k1-sw').fill],
        swk: cs('k1-sw-key').fill,
        anchors: [cs('k1-start').textAnchor, cs('k1-end').textAnchor],
        lines: ['k1-grid', 'k1-axis', 'k1-target'].map(i => [cs(i).stroke, parseFloat(cs(i).strokeWidth)]),
        dash: cs('k1-target').strokeDasharray }; }""")
    accent = pg.evaluate(RESOLVE, "--sys-color-accent")
    ctx.close()
    assert m["bar"][1] == "none" and m["key"][1] == "none", "bars carry no lift shadow"
    assert m["bar"][0] not in ("rgb(0, 0, 0)", "none") and m["key"][0] == accent and m["bar"][0] != m["key"][0], m
    w, h, rx, filt, fill = m["sw"]
    assert abs(w - h) < 0.5 and rx <= 0.25 * 24 and filt == "none", "a square swatch, never a pill or circle"
    assert fill == m["bar"][0] and m["swk"] == m["key"][0], "swatches match their series"
    assert m["anchors"] == ["start", "end"]
    assert all(s != "none" and sw >= 1.5 for s, sw in m["lines"]), m["lines"]
    assert m["dash"] != "none", "the target line is dashed"


def test_layout_documents_chart_parts_and_label_fitting():
    t = _text(LAYOUT)
    for cls in (".chart-bar", ".chart-bar--key", ".chart-axis", ".chart-grid", ".chart-target", ".chart-swatch",
                ".label--start", ".label--end"):
        assert cls in t, cls
    assert re.search(r"tspan", t) and re.search(r"viewBox", t), "label fitting: tspans and the viewBox rule"


SPILL_SLIDES = """
<section class="slide" id="l-1" data-chapter="Labels">
  <p class="kicker">01 · Labels</p>
  <h2 class="title">A label must stay inside its diagram</h2>
  <div class="body body--stack">
    <svg class="diagram" viewBox="0 0 1000 300" role="img" aria-label="One tile and its label">
      <g class="layer-nodes"><g class="tile" id="l1-t"><rect x="0" y="40" width="260" height="150"/><text class="tile-title">Array</text></g></g>
      <g class="layer-labels"><text class="label" id="l1-label" x="130" y="260">{label}</text></g>
    </svg>
  </div>
</section>
"""


def test_guard_flags_a_label_spilling_past_its_diagrams_viewbox(guard, browser, tmp_path):
    bad = _deck(tmp_path / "spill.html", SPILL_SLIDES.replace("{label}", "INSPECTED ONCE EVERY SINGLE YEAR"))
    faults = _faults(guard, browser, bad, "l-1", [(1920, 1080)])
    assert any("outside diagram" in f and "l1-label" in f for f in faults), faults
    assert guard.classify("outside diagram: #l1-label \"x\"")[0] == "overflow"
    ok = _deck(tmp_path / "fit.html", SPILL_SLIDES.replace("{label}", "YEARLY"))
    assert _faults(guard, browser, ok, "l-1") == []


# ---------- row 13: a one-line tile centred among two-line siblings ----------

TILE_SLIDES = """
<section class="slide" id="r-1" data-chapter="Tiles">
  <p class="kicker">01 · Tiles</p>
  <h2 class="title">Tiles in one row share a baseline unless one opts out</h2>
  <div class="body">
    <svg class="diagram" viewBox="0 0 900 240" role="img" aria-label="Three tiles">
      <g class="layer-nodes">
        <g class="tile" id="r1-a"><rect x="0" y="40" width="260" height="160"/><text class="tile-title">Two</text><text class="tile-sub">lines here</text></g>
        <g class="tile tile--centred" id="r1-b"><rect x="320" y="40" width="260" height="160"/><text class="tile-title">Centred</text></g>
        <g class="tile" id="r1-c"><rect x="640" y="40" width="260" height="160"/><text class="tile-title">Shared</text></g>
      </g>
    </svg>
  </div>
</section>
"""


def test_a_centred_tile_centres_its_line_while_siblings_share_the_row_baseline(guard, browser, tmp_path):
    deck = _deck(tmp_path / "r.html", TILE_SLIDES)
    ctx, pg, _ = _page(browser, deck)
    guard.goto_step(pg, "r-1", 0)
    ys = pg.evaluate("""() => ['r1-a', 'r1-b', 'r1-c'].map(i => +document.querySelector('#' + i + ' text').getAttribute('y'))""")
    ctx.close()
    centre = 40 + 160 / 2
    assert abs(ys[1] - centre) < 0.5, ys
    assert abs(ys[2] - ys[0]) < 0.5 and abs(ys[2] - centre) > 5, "unmarked tiles keep the shared title baseline"
    assert "tile--centred" in _text(LAYOUT) and "tile--centred" in _text(ARCH)


# ---------- row 14: data-for selectors ----------

NOTES_SLIDES = """
<section class="slide" id="n-1" data-chapter="Notes">
  <p class="kicker">01 · Notes</p>
  <h2 class="title" id="n1-title">Notes can target any element on their slide</h2>
  <div class="body"><ul class="points"><li class="n-first">First point</li><li data-key="z">Second point</li><li>Third point</li></ul></div>
  <aside class="note" data-for="#n1-title"><h3>By id</h3><p>Id.</p><a class="src" href="https://www.gov.uk/a">A</a></aside>
  <aside class="note" data-for=".n-first"><h3>By class</h3><p>Class.</p><a class="src" href="https://www.gov.uk/b">B</a></aside>
  <aside class="note" data-for="[data-key='z']"><h3>By attribute</h3><p>Attr.</p><a class="src" href="https://www.gov.uk/c">C</a></aside>
  <aside class="note" data-for=".points li:nth-child(3)"><h3>By position</h3><p>Pos.</p><a class="src" href="https://www.gov.uk/d">D</a></aside>
  <aside class="note" data-for="##broken"><h3>Invalid</h3><p>Dropped.</p><a class="src" href="https://www.gov.uk/e">E</a></aside>
</section>
"""


def test_data_for_takes_any_css_selector_and_an_invalid_one_is_dropped_safely(guard, browser, tmp_path):
    deck = _deck(tmp_path / "n.html", NOTES_SLIDES)
    ctx, pg, errors = _page(browser, deck)
    guard.goto_step(pg, "n-1", 0)
    pg.keyboard.press("n")
    pg.wait_for_function("document.body.classList.contains('notes-on')")
    guard.settle(pg)
    pins = pg.evaluate("document.querySelectorAll('.pin').length")
    ctx.close()
    assert errors == [] and pins == 4, (pins, errors)
    row = next((l for l in _text(ARCH).splitlines() if l.startswith("| `data-for")), "")
    assert re.search(r"any CSS selector", row) and re.search(r"invalid", row, re.I), row


# ---------- row 15: sources without a URL ----------

def _note_deck(tmp_path: Path, name: str, note_body: str) -> Path:
    return _deck(tmp_path / name, f"""
<section class="slide" id="u-1" data-chapter="Sources">
  <p class="kicker">01 · Sources</p>
  <h2 class="title" id="u1-title">Departures fell after the diversion</h2>
  <div class="body"><p>Logged by the depot.</p></div>
  <aside class="note" data-for="#u1-title"><h3>Departure log</h3><p>Counts come from the depot log.</p>{note_body}</aside>
</section>""")


def test_rs05_accepts_the_documented_unlinked_source_and_still_fails_bare_text(gates, browser, tmp_path):
    crit = [_crit("RS-05")]
    good = _note_deck(tmp_path, "good.html", '<p class="src-unlinked">Unlinked source: Depot departure log, '
                      'Q3 2026 (internal, not published; held by service planning; accessed 2026-10-04)</p>')
    bare = _note_deck(tmp_path, "bare.html", "<p>Source: depot departure log, 2026.</p>")
    todo = _note_deck(tmp_path, "todo.html", '<p class="src-unlinked">Unlinked source: TODO</p>')
    res = {n: gates.deck_verdicts(d, crit, sizes=[(1280, 720)], browser=browser)[0]["result"]
           for n, d in (("good", good), ("bare", bare), ("todo", todo))}
    assert res == {"good": "pass", "bare": "fail", "todo": "fail"}, res


def test_research_part_documents_the_unlinked_source_form():
    t = _text(RESEARCH)
    assert "src-unlinked" in t and re.search(r"unlinked", t, re.I)
    assert re.search(r"src-unlinked", _text(ARCH)), "the note markup contract names it"


# ---------- row 17: ${CLAUDE_SKILL_DIR} may show a symlink path ----------

def test_skill_md_notes_the_skill_dir_may_be_a_symlink_path():
    t = _text(SKILL_DIR / "SKILL.md")
    assert "${CLAUDE_SKILL_DIR}" in t and re.search(r"symlink", t, re.I)
