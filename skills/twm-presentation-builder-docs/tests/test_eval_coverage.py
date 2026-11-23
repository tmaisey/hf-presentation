"""Spec: PB-021

Feature coverage check: ``evals/features.json`` lists every observable capability of the skill, each
mapped to the criteria that judge it; the bundled briefs claim the features they exercise; and
``evals/coverage.py`` fails when any feature lacks a brief or a criterion, or a brief that judges it.

Coverage: happy (the shipped files pass, via import and CLI; feature schema; every non-excluded spec
maps to a feature, every feature's spec is done or in build; every shipped module, palette, style,
assembler command, tool and PPTX script has its feature) · edge (a feature counts as judged only
where a claiming brief's profile selects one of its criteria in a concern the brief scopes) ·
negative (a feature with no brief, an unknown criterion id, a brief claiming an unknown feature, a
brief whose id is not its folder, and a feature no claiming brief judges each fail, by name, and
the CLI exits 1 listing them).
"""

from __future__ import annotations

import json
import re
import subprocess

import pytest

from helper_eval import EVAL_DIR, _import, copy_eval
from helper_skill import REPO, SKILL_DIR

FEATURES = EVAL_DIR / "features.json"
COVERAGE = EVAL_DIR / "coverage.py"
SPEC = REPO / "skills" / "twm-presentation-builder-docs" / "SPEC.jsonl"
FEATURE_ORDER = ("id", "area", "spec", "criteria", "description")
AREAS = {"arch", "engine", "module", "layout", "comp", "tokens", "assemble", "tools", "pptx",
         "content", "research", "voice", "process", "examples", "eval"}
# Specs with no capability of their own to judge in a deck: the skill's packaging/router (checked
# structurally by PB-001's tests), this coverage check itself, and the baseline eval run (an activity).
NOT_FEATURES = {"PB-001", "PB-021", "PB-025"}


def cov():
    return _import(COVERAGE, "skill_eval_coverage")


@pytest.fixture(scope="module")
def features():
    assert FEATURES.is_file(), "evals/features.json missing"
    return json.loads(FEATURES.read_text(encoding="utf-8"))["features"]


@pytest.fixture(scope="module")
def specs():
    return [json.loads(ln) for ln in SPEC.read_text(encoding="utf-8").splitlines() if ln.strip()]


def test_shipped_files_pass_the_coverage_check():
    assert cov().check(EVAL_DIR) == []


def test_cli_passes_on_shipped_files():
    proc = subprocess.run(["uv", "run", "--no-project", str(COVERAGE)], capture_output=True,
                          text=True, cwd=SKILL_DIR, timeout=120)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert re.search(r"\d+ features", proc.stdout)


def test_feature_fields_in_order_with_unique_ids(features):
    ids = [f["id"] for f in features]
    assert len(ids) == len(set(ids))
    for f in features:
        assert tuple(f) == FEATURE_ORDER, f["id"]
        assert re.fullmatch(r"[a-z]+\.[a-z0-9-]+", f["id"]), f["id"]
        assert f["area"] in AREAS and f["id"].split(".")[0] == f["area"], f["id"]
        assert re.fullmatch(r"PB-\d{3}", f["spec"]), f["id"]
        assert f["criteria"] and len(set(f["criteria"])) == len(f["criteria"]), f["id"]
        assert 20 <= len(f["description"]) <= 300, f["id"]


def test_every_spec_but_the_excluded_maps_to_a_feature(features, specs):
    """A new spec must add its features, so new capabilities can't land without eval coverage."""
    by_spec = {f["spec"] for f in features}
    missing = [s["id"] for s in specs if s["id"] not in NOT_FEATURES and s["id"] not in by_spec]
    assert missing == []


def test_every_feature_derives_from_a_done_or_build_spec(features, specs):
    status = {s["id"]: s["status"] for s in specs}
    for f in features:
        assert status.get(f["spec"]) in ("done", "build"), (f["id"], f["spec"])
        assert f["spec"] not in NOT_FEATURES, f["id"]


def _ids(features):
    return {f["id"] for f in features}


def test_every_shipped_module_palette_and_style_has_a_feature(features):
    ids = _ids(features)
    modules = {p.stem for p in (SKILL_DIR / "assets" / "engine" / "modules").glob("*.js")}
    assert modules and {f"module.{m}" for m in modules} <= ids
    palettes = {p.name.split(".")[0] for p in (SKILL_DIR / "assets" / "tokens" / "palettes").glob("*.tokens.json")}
    assert palettes and {f"tokens.palette-{p}" for p in palettes} <= ids
    styles = {p.name.split(".")[0] for p in (SKILL_DIR / "assets" / "tokens" / "styles").glob("*.tokens.json")}
    assert styles and {f"tokens.style-{s}" for s in styles} <= ids


def test_every_tool_command_and_pptx_step_has_a_feature(features):
    ids = _ids(features)
    src = (SKILL_DIR / "scripts" / "assemble.py").read_text(encoding="utf-8")
    commands = set(re.findall(r"add_parser\(\s*[\"'](\w+)[\"']", src))
    assert commands == {"new", "swap", "check"}
    assert {f"assemble.{c}" for c in commands} <= ids
    assert {"tools.shoot", "tools.layout-guard", "tokens.generator", "tokens.contrast-gate"} <= ids
    steps = {p.stem for p in (SKILL_DIR / "pptx" / "scripts").glob("*.py")}
    assert steps and {f"pptx.{s}" for s in steps} | {"pptx.reflow"} <= ids


def test_core_engine_parts_and_eval_features_are_listed(features):
    ids = _ids(features)
    assert {"engine.navigation", "engine.steps", "engine.title-bar-agenda", "engine.overlays",
            "engine.notes", "engine.ambient", "engine.diagram-layout", "engine.api"} <= ids
    assert {"content.storyboard", "research.flagging", "research.quotes", "voice.profile",
            "process.install", "process.merge"} <= ids
    assert {"eval.criteria", "eval.profiles", "eval.gates", "eval.judges", "eval.aggregate",
            "eval.anchors", "eval.briefs"} <= ids
    assert sum(i.startswith("layout.") for i in ids) >= 8
    assert sum(i.startswith("comp.") for i in ids) >= 15


# --- negatives: corrupt a copy of the eval folder -------------------------------------------------

def _brief(evals, bid):
    p = evals / "briefs" / bid / "brief.json"
    return p, json.loads(p.read_text(encoding="utf-8"))


def _write(p, data):
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _drop_feature_from_briefs(evals, fid):
    for p in sorted((evals / "briefs").glob("*/brief.json")):
        b = json.loads(p.read_text(encoding="utf-8"))
        b["features"] = [f for f in b["features"] if f != fid]
        _write(p, b)


def test_a_feature_no_brief_claims_fails(tmp_path):
    evals = copy_eval(tmp_path)
    _drop_feature_from_briefs(evals, "module.scene")
    errs = cov().check(evals)
    assert any("module.scene" in e and "no brief" in e for e in errs), errs


def test_an_unknown_criterion_id_fails(tmp_path):
    evals = copy_eval(tmp_path)
    data = json.loads((evals / "features.json").read_text(encoding="utf-8"))
    data["features"][0]["criteria"].append("ZZ-99")
    _write(evals / "features.json", data)
    errs = cov().check(evals)
    assert any("ZZ-99" in e and "unknown criterion" in e for e in errs), errs


def test_a_feature_with_no_criterion_fails(tmp_path):
    evals = copy_eval(tmp_path)
    data = json.loads((evals / "features.json").read_text(encoding="utf-8"))
    fid = data["features"][0]["id"]
    data["features"][0]["criteria"] = []
    _write(evals / "features.json", data)
    errs = cov().check(evals)
    assert any(fid in e and "no criterion" in e for e in errs), errs


def test_a_brief_claiming_an_unknown_feature_fails(tmp_path):
    evals = copy_eval(tmp_path)
    p, b = _brief(evals, "hf-subset")
    b["features"].append("comp.unicorn")
    _write(p, b)
    errs = cov().check(evals)
    assert any("hf-subset" in e and "comp.unicorn" in e and "unknown feature" in e for e in errs), errs


def test_a_brief_whose_id_is_not_its_folder_fails(tmp_path):
    evals = copy_eval(tmp_path)
    p, b = _brief(evals, "hf-subset-bright")
    b["id"] = "hf-subset-brite"
    _write(p, b)
    errs = cov().check(evals)
    assert any("hf-subset-brite" in e and "unknown brief" in e for e in errs), errs


def test_a_feature_judged_by_no_claiming_brief_fails(tmp_path):
    """Claimed but never judged: its only criterion sits outside every claiming brief's scope."""
    evals = copy_eval(tmp_path)
    data = json.loads((evals / "features.json").read_text(encoding="utf-8"))
    feat = next(f for f in data["features"] if f["id"] == "pptx.reflow")
    feat["criteria"] = ["CN-15"]  # internal-update only: no brief uses that profile
    _write(evals / "features.json", data)
    errs = cov().check(evals)
    assert any("pptx.reflow" in e and "not judged" in e for e in errs), errs


def test_concern_scope_limits_what_a_brief_judges(tmp_path):
    """A brief judges only its concerns: drop pptx from every brief and the PPTX features fail."""
    evals = copy_eval(tmp_path)
    for p in sorted((evals / "briefs").glob("*/brief.json")):
        b = json.loads(p.read_text(encoding="utf-8"))
        b["concerns"] = [c for c in b["concerns"] if c != "pptx"]
        _write(p, b)
    errs = cov().check(evals)
    assert any("pptx.emit" in e and "not judged" in e for e in errs), errs


def test_cli_exits_one_listing_every_fault(tmp_path):
    evals = copy_eval(tmp_path)
    _drop_feature_from_briefs(evals, "module.popover")
    p, b = _brief(evals, "pitch-solar-coop")
    b["features"].append("comp.unicorn")
    _write(p, b)
    proc = subprocess.run(["uv", "run", "--no-project", str(COVERAGE), "--evals", str(evals)],
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 1
    fails = [ln for ln in proc.stdout.splitlines() + proc.stderr.splitlines() if ln.startswith("FAIL")]
    assert any("module.popover" in ln for ln in fails) and any("comp.unicorn" in ln for ln in fails)
