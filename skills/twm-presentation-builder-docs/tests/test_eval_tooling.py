"""Spec: PB-026

Eval run tooling shipped in `evals/`: per-slide text extracts for text judges (`extract.py`),
contact sheets of every slide × step at one size (`scripts/shoot.py --contact`), the anchor
judge-accuracy table (`accuracy.py`), several targets in one run folder (sub-runs under a suite
manifest, rolled up by `aggregate.py`), judge prompts filled from a plan (`prompts.py`), and an
explicit reason when a criterion is missing (PX-06 with no PPTX renderer) or an outcome is
incomplete.

Coverage: happy (extract matches the deck's DOM title, kicker, notes and sources on the HF example
and an anchor; contact sheets tile every step in order with labels; accuracy reproduces the
committed baseline's 19/21 judge and 59/59 gate labels from its verdicts; two targets with
colliding verdict names aggregate apart and roll up; prompts filled for every repeat; EVAL.md
names each tool) · edge (states follow show/hide/overlay/scene steps; scale rule boundaries 2/3;
a committed single-run folder still aggregates to its committed outcome; a fake renderer on PATH
clears the PX-06 reason) · negative (no slide word lost by the extract; a suite naming a missing
sub-run is refused; unknown criterion in a prompt plan refused; nothing written into the
committed run; CLI exit codes).
"""

from __future__ import annotations

import importlib.util
import json
import math
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from helper_eval import EVAL_DIR, EVAL_MD, _import, aggregator
from helper_skill import REPO, SKILL_DIR

EXTRACT = EVAL_DIR / "extract.py"
ACCURACY = EVAL_DIR / "accuracy.py"
PROMPTS = EVAL_DIR / "prompts.py"
GATES = EVAL_DIR / "gates.py"
SHOOT = SKILL_DIR / "scripts" / "shoot.py"
HF = SKILL_DIR / "examples" / "hf-incident" / "deck.html"
HF_BRIGHT = SKILL_DIR / "examples" / "hf-incident" / "deck-bright.html"
AN00 = EVAL_DIR / "anchors" / "an-00.html"
BASELINE = REPO / "skills" / "twm-presentation-builder-docs" / "evals-runs" / "261123-baseline"


def norm(s: str) -> str:
    return " ".join((s or "").split())


def _module(path: Path, name: str):
    """Import a shipped script by path, registered in sys.modules (its dataclasses need that)."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def browser():
    """System Chrome, once per module (no conftest: other suites share this folder)."""
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        yield b
        b.close()


@pytest.fixture(scope="module")
def agg():
    return aggregator()


@pytest.fixture(scope="module")
def extract_mod():
    return _import(EXTRACT, "skill_eval_extract")


@pytest.fixture(scope="module")
def hf_text(extract_mod, browser, tmp_path_factory):
    out = tmp_path_factory.mktemp("hf-text")
    return extract_mod.extract(HF, out, browser=browser), out


@pytest.fixture(scope="module")
def an00_text(extract_mod, browser, tmp_path_factory):
    out = tmp_path_factory.mktemp("an00-text")
    return extract_mod.extract(AN00, out, browser=browser), out


def _dom(browser, deck: Path) -> dict:
    """Read titles, kickers, notes and their links straight from the deck's markup in Chrome."""
    page = browser.new_page()
    page.goto(deck.resolve().as_uri())
    page.wait_for_function("window.deck && window.deck.ready === true")
    data = page.evaluate("""() => [...document.querySelectorAll('main section.slide')].map(s => {
        const q = sel => s.querySelector(':scope > ' + sel);
        const notes = [...s.querySelectorAll('aside.note')].map(n => {
            const c = n.cloneNode(true); c.querySelectorAll('h3').forEach(h => h.remove());
            return {for: n.dataset.for || null, heading: (n.querySelector('h3') || {}).textContent || '',
                    text: c.textContent,
                    sources: [...n.querySelectorAll('a[href]')].map(a => ({text: a.textContent, href: a.getAttribute('href')}))};
        });
        const body = s.cloneNode(true);
        body.querySelectorAll('aside.note, title, desc, script, style').forEach(x => x.remove());
        return {id: s.id, title: (q('.title') || {}).textContent || '', kicker: q('.kicker') ? q('.kicker').textContent : null,
                notes, words: body.textContent};
    })""")
    page.close()
    return {d["id"]: d for d in data}


def _words(s: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[A-Za-z0-9’']+", s or "")}


def _extract_words(sl: dict) -> set[str]:
    out = _words(sl["title"]) | _words(sl.get("kicker") or "")
    for st in sl["states"]:
        for ln in st["lines"]:
            out |= _words(ln["text"])
    return out


# ---------- extract ----------

@pytest.mark.parametrize("which", ["hf", "an00"])
def test_extract_matches_the_dom_title_kicker_notes_and_sources(which, hf_text, an00_text, browser):
    (index, out), deck = (hf_text, HF) if which == "hf" else (an00_text, AN00)
    dom = _dom(browser, deck)
    assert [s["id"] for s in index["slides"]] == list(dom)
    for sl in index["slides"]:
        d = dom[sl["id"]]
        assert sl["title"] == norm(d["title"]), sl["id"]
        assert sl["kicker"] == (norm(d["kicker"]) if d["kicker"] is not None else None), sl["id"]
        assert len(sl["notes"]) == len(d["notes"]), sl["id"]
        for got, want in zip(sl["notes"], d["notes"]):
            assert got["for"] == want["for"]
            assert got["heading"] == norm(want["heading"])
            assert got["text"] == norm(want["text"])
            assert got["sources"] == [{"text": norm(x["text"]), "href": x["href"]} for x in want["sources"]]
        txt = (out / f"{sl['id']}.txt").read_text(encoding="utf-8")
        assert sl["title"] in txt
        for n in sl["notes"]:
            for src in n["sources"]:
                assert src["href"] in txt, (sl["id"], src["href"])
        assert [st["step"] for st in sl["states"]] == list(range(sl["steps"] + 1))
    assert json.loads((out / "text.json").read_text(encoding="utf-8")) == index


@pytest.mark.parametrize("which", ["hf", "an00"])
def test_extract_loses_no_visible_slide_word(which, hf_text, an00_text, browser):
    """Every word in a slide's markup (notes, svg titles aside) shows up in some step's lines."""
    index, _ = hf_text if which == "hf" else an00_text
    dom = _dom(browser, HF if which == "hf" else AN00)
    for sl in index["slides"]:
        lost = _words(dom[sl["id"]]["words"]) - _extract_words(sl)
        assert not lost, (sl["id"], sorted(lost)[:20])


def _lines(index, sid, step):
    sl = next(s for s in index["slides"] if s["id"] == sid)
    return [ln for ln in sl["states"][step]["lines"]]


def _has(index, sid, step, needle):
    return any(needle in ln["text"] for ln in _lines(index, sid, step))


def test_extract_states_follow_the_build_steps(hf_text):
    index, out = hf_text
    why, hack = "Aligned reinforcement", "Misaligned reinforcement"
    assert _has(index, "s-2", 2, why) and not _has(index, "s-2", 3, why), "data-hide-at removes it"
    assert _has(index, "s-2", 3, hack) and not _has(index, "s-2", 2, hack), "data-show-at adds it"
    insight = "Alignment of AI agents during reinforcement learning is unsolved"
    assert _has(index, "s-2", 5, insight) and not _has(index, "s-2", 4, insight), "overlay at its step"
    key5 = [ln for ln in _lines(index, "s-5", 5) if ln["text"].startswith("Agent Run")]
    assert key5 and "Coordinator" in key5[0]["text"], "shared scene text belongs to the slide showing it"
    key0 = [ln for ln in _lines(index, "s-5", 0) if ln["text"].startswith("Agent Run")]
    assert key0 and "Coordinator" not in key0[0]["text"], "a scene part enters at its data-scene-at step"
    new = [ln for ln in _lines(index, "s-2", 3) if ln["new"]]
    assert any(hack in ln["text"] for ln in new)
    assert all(ln["new"] for ln in _lines(index, "s-2", 0)), "everything is new on entry"
    assert not any(why in ln["text"] for ln in new)
    assert all(not ln["new"] for ln in _lines(index, "s-2", 3) if ln["text"].startswith("In training")), \
        "a line already shown is not new"
    txt = (out / "s-2.txt").read_text(encoding="utf-8")
    assert re.search(r"^## Step 3", txt, re.M) and re.search(r"^\+ .*Misaligned reinforcement", txt, re.M)


def test_extract_cli_writes_files_and_refuses_a_missing_deck(tmp_path):
    r = subprocess.run(["uv", "run", str(EXTRACT), str(AN00), str(tmp_path / "text")],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr
    assert sorted(p.name for p in (tmp_path / "text").glob("*.txt")) == ["a0-1.txt", "a0-2.txt", "a0-3.txt", "a0-4.txt"]
    r = subprocess.run(["uv", "run", str(EXTRACT), str(tmp_path / "nope.html"), str(tmp_path / "x")],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 2 and "nope.html" in r.stderr


# ---------- contact sheets ----------

def _png_size(path: Path) -> tuple[int, int]:
    head = path.read_bytes()[:24]
    assert head[:8] == b"\x89PNG\r\n\x1a\n", path
    return struct.unpack(">II", head[16:24])


def test_contact_sheets_tile_every_step_of_one_size_in_order_with_labels(tmp_path):
    shoot = _import(SHOOT, "skill_shoot_contact")
    out = tmp_path / "shots"
    index = shoot.shoot(AN00, out, sizes=[(1288, 598)], contact="1288x598", contact_grid=(2, 2))
    steps = [s for s in index["shots"] if s["mode"] == "step"]
    sheets = [s for s in index["shots"] if s["mode"] == "contact"]
    assert len(steps) == 6
    assert len(sheets) == math.ceil(len(steps) / 4)
    tiles = [t for sh in sheets for t in sh["tiles"]]
    assert [t["file"] for t in tiles] == [s["file"] for s in steps], "every step once, deck order"
    for t in tiles:
        assert t["label"] == f"{t['slide']} · step {t['step']}"
    for sh in sheets:
        assert sh["size"] == "1288x598" and re.fullmatch(r"contact-1288x598-\d+\.png", sh["file"])
        w, h = _png_size(out / sh["file"])
        assert w >= 2 * 320 and h >= 320 * 598 / 1288, (w, h)
    assert len(sheets[-1]["tiles"]) == 2
    assert json.loads((out / "shots.json").read_text())["shots"] == index["shots"]
    assert not list(out.glob("*.html")), "no scratch page left behind"


def test_contact_cli_defaults_to_the_first_size_and_one_sheet_for_a_short_deck(tmp_path):
    out = tmp_path / "shots"
    r = subprocess.run(["uv", "run", str(SHOOT), str(AN00), str(out), "--sizes", "1288x598,1280x720", "--contact"],
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stderr
    sheets = [s for s in json.loads((out / "shots.json").read_text())["shots"] if s["mode"] == "contact"]
    assert [s["file"] for s in sheets] == ["contact-1288x598-1.png"]
    assert len(sheets[0]["tiles"]) == 6


# ---------- accuracy ----------

@pytest.fixture(scope="module")
def accuracy_mod():
    return _import(ACCURACY, "skill_eval_accuracy")


def _tracked_state(path: Path) -> str:
    return subprocess.run(["git", "status", "--porcelain", "--", str(path)], capture_output=True, text=True,
                          cwd=REPO, check=True).stdout


def test_accuracy_reproduces_the_baseline_from_its_committed_verdicts(accuracy_mod, tmp_path):
    before = _tracked_state(BASELINE)
    r = subprocess.run(["uv", "run", str(ACCURACY), str(BASELINE / "anchors"), "--out", str(tmp_path)],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr
    data = json.loads((tmp_path / "accuracy.json").read_text())
    assert data["summary"]["judge"] == {"matched": 19, "labels": 21}
    assert data["summary"]["gate"] == {"matched": 59, "labels": 59}
    misses = {(x["anchor"], x["criterion"]) for x in data["rows"] if x["status"] != "match"}
    assert misses == {("AN-05", "DS-06"), ("AN-09", "RS-01")}
    md = (tmp_path / "accuracy.md").read_text()
    assert "19/21" in md and "59/59" in md
    assert _tracked_state(BASELINE) == before, "the committed run is read, never written"


@pytest.mark.parametrize("label,form,outcomes,status", [
    ("must_fail", "scale", {"a": 2}, "match"),
    ("must_fail", "scale", {"a": 3}, "MISMATCH"),
    ("must_pass", "scale", {"a": 3}, "match"),
    ("must_pass", "scale", {"a": 2.5}, "MISMATCH"),
    ("must_fail", "binary", {"a": "pass", "b": "fail"}, "match"),
    ("must_pass", "binary", {"a": "pass", "b": "fail"}, "MISMATCH"),
    ("must_pass", "binary", {"a": "pass"}, "match"),
    ("must_fail", "binary", {"a": "insufficient-evidence"}, "insufficient"),
    ("must_fail", "binary", {}, "not-run"),
])
def test_accuracy_applies_the_anchor_verdict_rule(accuracy_mod, label, form, outcomes, status):
    crit = {"form": form, "units": {u: {"outcome": o, "k": 1, "results": [o]} for u, o in outcomes.items()}}
    assert accuracy_mod.label_status(label, crit if outcomes else None)[0] == status


# ---------- several targets in one run folder ----------

def _copy_run(src: Path, dst: Path) -> Path:
    """Copy a committed run's manifest and verdicts only (no evidence, no reports)."""
    dst.mkdir(parents=True)
    shutil.copy(src / "manifest.json", dst / "manifest.json")
    shutil.copytree(src / "verdicts", dst / "verdicts")
    return dst


def test_two_targets_in_one_run_folder_do_not_collide_and_roll_up(agg, tmp_path):
    suite = tmp_path / "261124-two"
    a = _copy_run(BASELINE / "anchors" / "an-00", suite / "an-00")
    b = _copy_run(BASELINE / "anchors" / "an-07", suite / "an-07")
    shared = {p.name for p in (a / "verdicts").glob("*.json")} & {p.name for p in (b / "verdicts").glob("*.json")}
    assert "AR-01_deck_r1.json" in shared, "same verdict names: one flat folder would collide"
    (suite / "manifest.json").write_text(json.dumps({"label": "two", "date": "261124", "runs": ["an-00", "an-07"]}))
    json_path, md_path = agg.run(suite)
    assert json_path == suite / "261124-two.json" and md_path.is_file()
    roll = json.loads(json_path.read_text())
    reps = {d: json.loads(next((suite / d).glob("261123-*.json")).read_text()) for d in ("an-00", "an-07")}
    assert reps["an-00"]["criteria"]["DP-04"]["status"] == "pass"
    assert reps["an-07"]["criteria"]["DP-04"]["status"] == "fail"
    rows = {r["run"]: r for r in roll["runs"]}
    assert set(rows) == {"an-00", "an-07"}
    for d, rep in reps.items():
        assert rows[d]["outcome"] == rep["outcome"] and rows[d]["target"] == rep["run"]["target"]
    assert rows["an-07"]["gates_failed"] == ["DP-01"]
    assert roll["outcome"] == "fail", "any failed target fails the suite"
    assert agg.CALIBRATION_LINE in md_path.read_text()
    r = subprocess.run(["uv", "run", str(EVAL_DIR / "aggregate.py"), str(suite)], capture_output=True, text=True,
                       timeout=120)
    assert r.returncode == 0, r.stderr


def test_a_suite_naming_a_missing_run_is_refused(agg, tmp_path):
    suite = tmp_path / "s"
    _copy_run(BASELINE / "anchors" / "an-00", suite / "an-00")
    (suite / "manifest.json").write_text(json.dumps({"label": "s", "date": "261124", "runs": ["an-00", "an-99"]}))
    with pytest.raises(agg.VerdictError, match="an-99"):
        agg.run(suite)
    r = subprocess.run(["uv", "run", str(EVAL_DIR / "aggregate.py"), str(suite)], capture_output=True, text=True,
                       timeout=120)
    assert r.returncode == 1 and "an-99" in r.stderr


def test_a_committed_single_run_folder_still_aggregates_to_its_committed_outcome(agg, tmp_path):
    for name in ("hf-subset", "anchors/an-05"):
        run = _copy_run(BASELINE / name, tmp_path / name.replace("/", "-"))
        json_path, _ = agg.run(run)
        committed = json.loads(next((BASELINE / name).glob("261123-*.json")).read_text())
        got = json.loads(json_path.read_text())
        assert got["outcome"] == committed["outcome"], name
        assert got["overall"] == committed["overall"], name


# ---------- missing reasons and incomplete outcomes ----------

def test_an_incomplete_outcome_names_each_undecided_gate_and_why(agg, tmp_path):
    run = _copy_run(BASELINE / "anchors" / "an-00", tmp_path / "an-00")
    json_path, md_path = agg.run(run)
    rep = json.loads(json_path.read_text())
    assert rep["outcome"] == "incomplete"
    assert [g["criterion"] for g in rep["incomplete"]] == ["RS-02"]
    assert rep["incomplete"][0]["status"] == "missing" and rep["incomplete"][0]["reason"].strip()
    md = md_path.read_text()
    assert re.search(r"incomplete[^\n]*no gate failed", md, re.I)
    assert "RS-02" in md.split("## Gates")[0], "the reason sits next to the outcome"


@pytest.fixture(scope="module")
def bright_pptx(browser, tmp_path_factory):
    emit = _module(SKILL_DIR / "pptx" / "scripts" / "emit.py", "skill_emit_for_tooling")
    scene = _module(SKILL_DIR / "pptx" / "scripts" / "scene.py", "skill_scene_for_tooling")
    d = tmp_path_factory.mktemp("bright-pptx")
    return emit.emit(scene.extract(HF_BRIGHT, browser=browser), d / "deck-bright.pptx")


def _pptx_run(tmp_path: Path, name: str) -> Path:
    run = tmp_path / name
    run.mkdir()
    (run / "manifest.json").write_text(json.dumps({
        "label": name, "date": "261124", "target": "deck-bright.pptx", "profile": "editorial-talk",
        "concerns": ["pptx"], "depth": "judges", "k": 1, "transcripts": False, "mode": "pointwise"}))
    return run


def test_px06_is_missing_with_a_reason_when_no_pptx_renderer_is_installed(agg, bright_pptx, tmp_path, monkeypatch):
    gates = _module(GATES, "skill_gates_for_tooling")
    run = _pptx_run(tmp_path, "no-renderer")
    empty = tmp_path / "empty-bin"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    log = gates.run_gates(run, pptx=bright_pptx)
    reason = log["judge_inputs"]["PX-06"]["missing"]
    assert "soffice" in reason
    monkeypatch.undo()
    json_path, md_path = agg.run(run)
    px06 = json.loads(json_path.read_text())["criteria"]["PX-06"]
    assert px06["status"] == "missing" and "soffice" in px06["reason"]
    assert re.search(r"PX-06[^\n]*soffice", md_path.read_text())


def test_a_renderer_on_path_clears_the_px06_reason(bright_pptx, tmp_path, monkeypatch):
    gates = _module(GATES, "skill_gates_for_tooling")
    run = _pptx_run(tmp_path, "renderer")
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    fake = bin_ / "soffice"
    fake.write_text("#!/bin/sh\nexit 0\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_))
    log = gates.run_gates(run, pptx=bright_pptx)
    assert "missing" not in log["judge_inputs"]["PX-06"]
    assert log["judge_inputs"]["PX-06"]["renderer"] == "soffice"


def test_manifest_not_judged_reasons_reach_the_report(agg, tmp_path):
    run = _copy_run(BASELINE / "anchors" / "an-00", tmp_path / "an-00")
    m = json.loads((run / "manifest.json").read_text())
    m["not_judged"] = {"RS-02": "judge budget: labelled criteria only"}
    (run / "manifest.json").write_text(json.dumps(m))
    rep = json.loads(agg.run(run)[0].read_text())
    assert rep["criteria"]["RS-02"]["reason"] == "judge budget: labelled criteria only"


# ---------- prompts ----------

def test_prompts_fill_every_placeholder_for_each_repeat(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    (run / "manifest.json").write_text(json.dumps({
        "label": "p", "date": "261124", "target": "deck.html", "profile": "editorial-talk",
        "concerns": ["content"], "depth": "judges", "k": 2, "transcripts": False, "mode": "pointwise"}))
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps([
        {"criterion": "CN-01", "unit": "s-4", "evidence": ["evidence/s-4-0-1920x1080.png", "evidence/text/s-4.txt"]},
        {"criterion": "CN-06", "unit": "deck", "evidence": ["evidence/contact-1920x1080-1.png"]},
    ]))
    r = subprocess.run(["uv", "run", str(PROMPTS), str(run), str(plan)], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    made = sorted(p.name for p in (run / "prompts").glob("*.md"))
    assert made == ["CN-01_s-4_r1.md", "CN-01_s-4_r2.md", "CN-06_deck_r1.md", "CN-06_deck_r2.md"]
    text = (run / "prompts" / "CN-01_s-4_r2.md").read_text()
    assert "{{" not in text and '"id": "CN-01"' in text
    assert "evidence/text/s-4.txt" in text and "evidence/contact-1920x1080-1.png" not in text
    assert "verdicts/CN-01_s-4_r2.json" in text and "(repeat 2)" in text
    lines = [ln.split("\t") for ln in r.stdout.strip().splitlines()]
    assert len(lines) == 4 and all(len(x) == 2 and x[1].endswith(".json") for x in lines)
    plan.write_text(json.dumps([{"criterion": "ZZ-99", "unit": "s-1", "evidence": []}]))
    r = subprocess.run(["uv", "run", str(PROMPTS), str(run), str(plan)], capture_output=True, text=True, timeout=120)
    assert r.returncode != 0 and "ZZ-99" in r.stderr


# ---------- protocol ----------

def test_eval_md_routes_each_step_to_its_tool():
    text = EVAL_MD.read_text(encoding="utf-8")
    low = text.lower()
    for must in ("evals/extract.py", "--contact", "evals/accuracy.py", "evals/prompts.py", '"runs"',
                 "not_judged"):
        assert must in text, must
    assert re.search(r"px-06[^.]*soffice[^.]*missing|px-06[^.]*missing[^.]*soffice", low)
    assert re.search(r"20[^.]*(concurrent|at once)[^.]*rolling|rolling[^.]*20", low)
    assert re.search(r"incomplete[^.]*(gate|gated)[^.]*(missing|unjudged|not judged)", low)
