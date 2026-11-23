"""Spec: PB-025

The baseline eval run exercises the whole skill end to end: every bundled brief and every anchor
is evaluated per the protocol, results are dated and aggregated, and the report is honest about
calibration and judge accuracy.

Coverage: happy (run dirs per brief + anchors, aggregate reports valid, REPORT.md) · edge (cold
builds are their own git repos, bundled into the run) · negative (anchors fail their labelled
gates; no absolute local paths leak into committed run files).
"""

import json
import re
import subprocess

from helper_eval import aggregator, loader
from helper_skill import REPO, SKILL_DIR

RUN = REPO / "skills" / "twm-presentation-builder-docs" / "evals-runs" / "261123-baseline"
BRIEFS = sorted(p.parent.name for p in (SKILL_DIR / "evals" / "briefs").glob("*/brief.json"))
TARGETS = [*BRIEFS, "anchors"]
BUILT = [b for b in BRIEFS if json.loads((SKILL_DIR / "evals" / "briefs" / b / "brief.json")
                                         .read_text())["target"]["mode"] == "build-from-brief"
         and b != "hf-subset"]


def _report(target):
    d = RUN / target
    reports = sorted(d.glob("261123-*.json"))
    assert reports, f"{target}: no aggregate report"
    return json.loads(reports[-1].read_text())


def test_every_brief_and_the_anchors_have_a_run_dir_with_a_manifest():
    for t in TARGETS:
        assert (RUN / t / "manifest.json").is_file(), t


def test_every_run_has_an_aggregate_report_that_states_calibration():
    agg = aggregator()
    for t in TARGETS:
        rep = _report(t)
        md = next((RUN / t).glob("261123-*.md")).read_text()
        assert agg.CALIBRATION_LINE in md, t
        assert rep.get("outcome") in {"pass", "fail", "incomplete"}, t


def _run_dirs(t):
    """A target is one run folder, or a suite whose sub-runs each hold verdicts (PB-026)."""
    d = RUN / t
    return [d] if (d / "verdicts").is_dir() else sorted(p.parent for p in d.glob("*/manifest.json"))


def test_every_committed_verdict_validates():
    agg, crit = aggregator(), loader()
    library, profiles = crit.load_library(), crit.load_profiles()
    for t in TARGETS:
        dirs = _run_dirs(t)
        assert dirs, f"{t}: no run folders"
        for d in dirs:
            files = list((d / "verdicts").glob("*.json"))
            assert files, f"{d.name}: no verdicts"
            profile = profiles[json.loads((d / "manifest.json").read_text())["profile"]]
            for f in files:
                v = json.loads(f.read_text())
                agg.validate_verdict(v, library, profile, pairwise="order" in v)


def test_anchor_gates_fail_exactly_as_labelled():
    """Every gate label matches; judge misses are only the recorded lenient ones (REPORT.md)."""
    acc = json.loads((RUN / "anchors" / "accuracy.json").read_text())
    rows = acc["rows"]
    gate = [r for r in rows if r["kind"] == "gate"]
    assert gate and all(r["status"] == "match" for r in gate)
    misses = {(r["anchor"], r["criterion"]) for r in rows if r["kind"] != "gate" and r["status"] != "match"}
    assert misses == {("AN-05", "DS-06"), ("AN-09", "RS-01")}
    report = (RUN / "REPORT.md").read_text()
    assert "AN-05" in report and "AN-09" in report


def test_report_has_judge_accuracy_table_and_open_questions():
    md = (RUN / "REPORT.md").read_text()
    assert re.search(r"judge.accuracy", md, re.I)
    assert re.search(r"open questions", md, re.I)
    assert "part 1" not in md.lower() or "part 2" in md.lower(), "report must cover the builds"
    for t in TARGETS:
        assert t in md, t


def test_cold_builds_are_bundled_git_histories():
    for b in BUILT:
        bundle = RUN / f"{b}.bundle"
        assert bundle.is_file(), b
        out = subprocess.run(["git", "bundle", "list-heads", str(bundle)], capture_output=True,
                             text=True, check=True).stdout
        assert "HEAD" in out or "refs/heads" in out


def test_cold_builds_were_judged_on_process():
    for b in BUILT:
        rep = json.dumps(_report(b))
        assert re.search(r'"PR-0\d"', rep), b


def test_no_absolute_local_paths_in_committed_run_files():
    tracked = subprocess.run(["git", "ls-files", str(RUN)], capture_output=True, text=True,
                             cwd=REPO, check=True).stdout.split()
    assert tracked, "run not committed"
    for rel in tracked:
        p = REPO / rel
        if p.suffix in {".json", ".md", ".txt"}:
            assert not re.search(r"/Users/|/private/tmp|/home/", p.read_text(errors="ignore")), rel
