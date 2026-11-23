"""Spec: PB-018

The eval run protocol (`evals/EVAL.md`), the judge prompt templates (`evals/judges/*.md`) and the
verdict aggregator (`evals/aggregate.py`) turn a scoped run's verdicts into a dated, gated,
weighted report that states its calibration status.

Coverage: happy (all-pass deck, weighted concern and overall scores, dated JSON + markdown via
API and CLI, pairwise winner mapped through order) · edge (k=1, even k, majority vs minority
insufficient evidence, spread thresholds either side, all-insufficient criterion, gates-only depth)
· negative (failed gate beats a high score, missing or insufficient gate is not a pass, pairwise
order inconsistency is a tie, malformed / unknown / unselected / out-of-scope verdicts rejected,
CLI exits non-zero; templates and protocol carry the scope questions, transcript consent default
no, isolation, diff/test verification and the calibration line).
"""

import copy
import json
import re
import subprocess
import sys

import pytest

from helper_eval import (AGGREGATOR, EVAL_MD, JUDGES_DIR, PROFILES_DIR, aggregator, copy_eval,
                         loader)
from helper_skill import fenced_blocks, section

TEMPLATES = {"output-judge.md": False, "process-judge.md": False, "pairwise-judge.md": True}
TEST_PROFILE = {"id": "t", "description": "fixture profile",
                "weights": {"CN-01": 3, "CN-02": 1, "CN-03": 2, "DL-01": 3, "VC-01": 1},
                "gates": ["DL-01"]}
MANIFEST = {"label": "fixture", "date": "261123", "target": "deck.html", "profile": "t",
            "concerns": ["content", "design-layout"], "depth": "judges", "k": 3,
            "transcripts": False, "mode": "pointwise"}


@pytest.fixture(scope="module")
def agg():
    return aggregator()


@pytest.fixture(scope="module")
def library():
    return loader().load_library()


@pytest.fixture()
def evals(tmp_path):
    d = copy_eval(tmp_path)
    (d / "profiles" / "t.json").write_text(json.dumps(TEST_PROFILE), encoding="utf-8")
    return d


@pytest.fixture()
def profile(evals, library):
    return loader().load_profile(evals / "profiles" / "t.json", library)


def v(cid, unit, repeat, result, **extra):
    """A well-formed pointwise verdict."""
    ev = [] if result == "insufficient-evidence" else [
        {"slide": unit.split("/")[0], "region": "title", "note": "observed"}]
    out = {"criterion": cid, "unit": unit, "repeat": repeat, "evidence": ev,
           "rationale": "Short reason.", "flaws": [], "result": result}
    out.update(extra)
    return out


def pv(cid, unit, repeat, order, result):
    """A well-formed pairwise verdict."""
    return {"criterion": cid, "unit": unit, "repeat": repeat, "order": order,
            "evidence": [{"candidate": "first", "slide": unit, "note": "observed"}],
            "rationale": "Short reason.", "flaws": [], "result": result}


def repeats(cid, unit, results):
    return [v(cid, unit, i + 1, r) for i, r in enumerate(results)]


def all_pass_run():
    vs = []
    for s in ("s-1", "s-2"):
        vs += repeats("CN-01", s, ["pass"] * 3)
        vs += repeats("CN-02", s, ["pass"] * 3)
        vs += repeats("CN-03", s, [4, 4, 5])
    vs += [v("DL-01", "s-1/1", 1, "pass"), v("DL-01", "s-2/1", 1, "pass")]
    return vs


def run_report(agg, library, profile, verdicts, **manifest):
    return agg.aggregate(verdicts, dict(MANIFEST, **manifest), library, profile)


# --- aggregation: happy ---------------------------------------------------------------------

def test_all_passing_deck_passes_with_weighted_scores(agg, library, profile):
    r = run_report(agg, library, profile, all_pass_run())
    assert r["outcome"] == "pass"
    assert r["criteria"]["CN-03"]["units"]["s-1"]["outcome"] == 4
    assert r["criteria"]["CN-03"]["score"] == pytest.approx(0.8)
    # content: CN-01 w3 ×1, CN-02 w1 ×1, CN-03 w2 ×0.8 ; design-layout: DL-01 w3 ×1
    assert r["concerns"]["content"]["score"] == pytest.approx(5.6 / 6)
    assert r["concerns"]["design-layout"]["score"] == pytest.approx(1.0)
    assert r["overall"]["score"] == pytest.approx(8.6 / 9)


def test_single_repeat_decides_alone(agg, library, profile):
    r = run_report(agg, library, profile, all_pass_run() + repeats("CN-01", "s-3", ["pass"]))
    unit = r["criteria"]["CN-01"]["units"]["s-3"]
    assert unit["outcome"] == "pass" and unit["k"] == 1 and unit["flags"] == []


# --- aggregation: edges ---------------------------------------------------------------------

def test_even_k_scale_takes_middle_median(agg, library, profile):
    vs = [x for x in all_pass_run() if not (x["criterion"] == "CN-03" and x["unit"] == "s-1")]
    r = run_report(agg, library, profile, vs + repeats("CN-03", "s-1", [2, 3]))
    unit = r["criteria"]["CN-03"]["units"]["s-1"]
    assert unit["outcome"] == pytest.approx(2.5)
    assert "high-spread" not in unit["flags"]


def test_even_k_binary_tie_fails_with_flag(agg, library, profile):
    vs = [x for x in all_pass_run() if not (x["criterion"] == "CN-01" and x["unit"] == "s-1")]
    r = run_report(agg, library, profile, vs + repeats("CN-01", "s-1", ["pass", "fail"]))
    unit = r["criteria"]["CN-01"]["units"]["s-1"]
    assert unit["outcome"] == "fail" and "tie" in unit["flags"]


def test_scale_spread_flag_sits_exactly_at_threshold(agg, library, profile):
    t = agg.SCALE_SPREAD_FLAG
    base = [x for x in all_pass_run() if x["criterion"] != "CN-03"]
    below = run_report(agg, library, profile, base + repeats("CN-03", "s-1", [1, 1, 1 + t - 1]))
    at = run_report(agg, library, profile, base + repeats("CN-03", "s-1", [1, 1, 1 + t]))
    assert "high-spread" not in below["criteria"]["CN-03"]["units"]["s-1"]["flags"]
    assert "high-spread" in at["criteria"]["CN-03"]["units"]["s-1"]["flags"]
    assert any(f["unit"] == "s-1" and "high-spread" in f["flags"] for f in at["flags"])


def test_binary_split_flag_threshold(agg, library, profile):
    """A 2–1 split is flagged for review; a 4–1 split is a clear majority."""
    assert 0.2 < agg.BINARY_SPLIT_FLAG <= 1 / 3
    base = [x for x in all_pass_run() if x["criterion"] != "CN-01"]
    two_one = run_report(agg, library, profile, base + repeats("CN-01", "s-1", ["pass", "pass", "fail"]))
    four_one = run_report(agg, library, profile,
                          base + repeats("CN-01", "s-1", ["pass"] * 4 + ["fail"]))
    assert two_one["criteria"]["CN-01"]["units"]["s-1"]["outcome"] == "pass"
    assert "high-spread" in two_one["criteria"]["CN-01"]["units"]["s-1"]["flags"]
    assert "high-spread" not in four_one["criteria"]["CN-01"]["units"]["s-1"]["flags"]


def test_majority_insufficient_unit_is_insufficient_minority_is_flagged(agg, library, profile):
    base = [x for x in all_pass_run() if x["criterion"] != "CN-01"]
    ins = "insufficient-evidence"
    r = run_report(agg, library, profile, base + repeats("CN-01", "s-1", [ins, ins, "pass"])
                   + repeats("CN-01", "s-2", [ins, "pass", "pass"]))
    units = r["criteria"]["CN-01"]["units"]
    assert units["s-1"]["outcome"] == ins
    assert units["s-2"]["outcome"] == "pass" and "partial-evidence" in units["s-2"]["flags"]


def test_all_insufficient_criterion_is_its_own_outcome_and_unweighted(agg, library, profile):
    """Insufficient evidence is never a pass: it drops out of the score and lowers coverage."""
    base = [x for x in all_pass_run() if x["criterion"] != "CN-02"]
    ins = "insufficient-evidence"
    r = run_report(agg, library, profile, base + repeats("CN-02", "s-1", [ins] * 3))
    c = r["criteria"]["CN-02"]
    assert c["status"] == ins and c["score"] is None
    assert r["concerns"]["content"]["score"] == pytest.approx(4.6 / 5)
    assert r["concerns"]["content"]["coverage"] == pytest.approx(5 / 6)
    assert r["outcome"] == "pass"


def test_gates_only_depth_expects_only_deterministic_criteria(agg, library, profile):
    gates = [x for x in all_pass_run() if x["criterion"] == "DL-01"]
    r = run_report(agg, library, profile, gates, depth="gates")
    assert set(r["criteria"]) == {"DL-01"} and r["outcome"] == "pass"
    with pytest.raises(agg.VerdictError):
        run_report(agg, library, profile, gates + repeats("CN-01", "s-1", ["pass"]), depth="gates")


# --- aggregation: gates and negatives -------------------------------------------------------

def test_failed_gate_fails_deck_despite_high_score(agg, library, profile):
    vs = all_pass_run() + [v("DL-01", f"s-{n}/1", 1, "pass") for n in range(3, 20)]
    vs.append(v("DL-01", "s-20/1", 1, "fail"))
    r = run_report(agg, library, profile, vs)
    assert r["overall"]["score"] > 0.9
    assert r["outcome"] == "fail"
    assert r["criteria"]["DL-01"]["status"] == "fail"


@pytest.mark.parametrize("gate_results", [None, ["insufficient-evidence"]])
def test_missing_or_insufficient_gate_is_incomplete_not_pass(agg, library, profile, gate_results):
    vs = [x for x in all_pass_run() if x["criterion"] != "DL-01"]
    if gate_results:
        vs += repeats("DL-01", "s-1/1", gate_results)
    r = run_report(agg, library, profile, vs)
    assert r["outcome"] == "incomplete"
    assert r["criteria"]["DL-01"]["status"] in {"missing", "insufficient-evidence"}


def test_missing_judged_criterion_is_reported_not_scored(agg, library, profile):
    vs = [x for x in all_pass_run() if x["criterion"] != "CN-02"]
    r = run_report(agg, library, profile, vs)
    assert r["criteria"]["CN-02"]["status"] == "missing" and r["criteria"]["CN-02"]["score"] is None


def _malformed():
    good = v("CN-01", "s-1", 1, "pass")
    cases = {}
    cases["missing field"] = {k: x for k, x in good.items() if k != "rationale"}
    cases["extra field"] = dict(good, confidence=0.9)
    cases["score before evidence"] = {"result": "pass", **{k: x for k, x in good.items() if k != "result"}}
    cases["binary given a score"] = dict(good, result=3)
    cases["scale given pass"] = v("CN-03", "s-1", 1, "pass")
    cases["scale out of range"] = v("CN-03", "s-1", 1, 6)
    cases["decided without evidence"] = dict(good, evidence=[])
    cases["evidence without locator"] = dict(good, evidence=[{"note": "looks fine"}])
    cases["evidence without note"] = dict(good, evidence=[{"slide": "s-1"}])
    cases["rationale too long"] = dict(good, rationale="Because. " * 200)
    cases["unknown flaw tag"] = dict(good, result="fail", flaws=["not-a-flaw"])
    cases["repeat zero"] = dict(good, repeat=0)
    cases["deck-scope unit not deck"] = v("CN-06", "s-1", 1, "pass")
    return cases


@pytest.mark.parametrize("case", sorted(_malformed()))
def test_malformed_verdict_is_rejected(agg, library, evals, case):
    prof = dict(TEST_PROFILE, weights=dict(TEST_PROFILE["weights"], **{"CN-06": 1}))
    (evals / "profiles" / "t.json").write_text(json.dumps(prof), encoding="utf-8")
    p = loader().load_profile(evals / "profiles" / "t.json", library)
    with pytest.raises(agg.VerdictError):
        agg.validate_verdict(_malformed()[case], library, p)


@pytest.mark.parametrize("cid", ["CN-99", "CN-11"])
def test_unknown_or_unselected_criterion_is_rejected(agg, library, profile, cid):
    """CN-99 is not in the library; CN-11 is pitch-only and unselected by this profile."""
    with pytest.raises(agg.VerdictError, match=cid):
        agg.validate_verdict(v(cid, "s-1", 1, "pass"), library, profile)


def test_verdict_outside_the_run_concerns_is_rejected(agg, library, profile):
    """VC-01 is selected by the profile but voice is not in this run's concerns."""
    with pytest.raises(agg.VerdictError, match="VC-01"):
        run_report(agg, library, profile, all_pass_run() + repeats("VC-01", "s-1", ["pass"]))


def test_duplicate_repeat_is_rejected(agg, library, profile):
    with pytest.raises(agg.VerdictError):
        run_report(agg, library, profile, all_pass_run() + [v("CN-01", "s-1", 1, "fail")])


# --- pairwise -------------------------------------------------------------------------------

def pair_manifest():
    return dict(MANIFEST, mode="pairwise", versions={"A": "skill@old", "B": "skill@new"})


def test_pairwise_maps_positions_to_versions_through_order(agg, library, profile):
    """AB 'first' and BA 'second' both name version A."""
    vs = [pv("CN-01", "s-1", r, "AB", "first") for r in (1, 2, 3)]
    vs += [pv("CN-01", "s-1", r, "BA", "second") for r in (1, 2, 3)]
    r = agg.aggregate(vs, pair_manifest(), library, profile)
    assert r["criteria"]["CN-01"]["units"]["s-1"]["outcome"] == "A"
    assert r["overall"]["preference"] > 0


def test_pairwise_order_inconsistency_is_a_flagged_tie(agg, library, profile):
    vs = [pv("CN-01", "s-1", 1, "AB", "first"), pv("CN-01", "s-1", 1, "BA", "first")]
    r = agg.aggregate(vs, dict(pair_manifest(), k=1), library, profile)
    unit = r["criteria"]["CN-01"]["units"]["s-1"]
    assert unit["outcome"] == "tie" and "order-inconsistent" in unit["flags"]


def test_pairwise_needs_both_orders(agg, library, profile):
    with pytest.raises(agg.VerdictError):
        agg.aggregate([pv("CN-01", "s-1", 1, "AB", "first")], pair_manifest(), library, profile)


def test_pairwise_rejects_pointwise_result(agg, library, profile):
    bad = dict(pv("CN-01", "s-1", 1, "AB", "first"), result="pass")
    with pytest.raises(agg.VerdictError):
        agg.validate_verdict(bad, library, profile, pairwise=True)


# --- report files and CLI -------------------------------------------------------------------

def write_run(root, verdicts, manifest=MANIFEST):
    run = root / "run"
    (run / "verdicts").mkdir(parents=True)
    (run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    for n, x in enumerate(verdicts):
        (run / "verdicts" / f"{n:03}.json").write_text(json.dumps(x), encoding="utf-8")
    return run


def test_run_writes_dated_json_and_markdown_with_calibration_line(agg, evals, tmp_path):
    run = write_run(tmp_path, all_pass_run())
    json_path, md_path = agg.run(run, evals)
    assert json_path.name == "261123-fixture.json" and md_path.name == "261123-fixture.md"
    report = json.loads(json_path.read_text(encoding="utf-8"))
    assert report["outcome"] == "pass" and report["calibration"] == agg.CALIBRATION_LINE
    md = md_path.read_text(encoding="utf-8")
    assert agg.CALIBRATION_LINE in md
    assert "unmeasured" in agg.CALIBRATION_LINE.lower() and "presenter" in agg.CALIBRATION_LINE.lower()


def test_markdown_report_lists_outcome_gates_and_flags(agg, library, profile):
    vs = [x for x in all_pass_run() if x["criterion"] != "CN-03"]
    r = run_report(agg, library, profile, vs + repeats("CN-03", "s-1", [0, 2, 5]))
    md = agg.render_markdown(r)
    assert "pass" in md.lower() and "DL-01" in md and "high-spread" in md


def test_cli_aggregates_a_run_folder(evals, tmp_path):
    run = write_run(tmp_path, all_pass_run())
    out = subprocess.run([sys.executable, str(evals / "aggregate.py"), str(run)],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert (run / "261123-fixture.md").is_file() and (run / "261123-fixture.json").is_file()


def test_cli_rejects_a_malformed_verdict_naming_its_file(evals, tmp_path):
    bad = dict(v("CN-01", "s-1", 1, "pass"), result="maybe")
    run = write_run(tmp_path, all_pass_run() + [bad])
    out = subprocess.run([sys.executable, str(evals / "aggregate.py"), str(run)],
                         capture_output=True, text=True)
    assert out.returncode == 1
    assert f"{len(all_pass_run()):03}.json" in out.stderr
    assert not list(run.glob("261123-*"))


def test_aggregator_is_a_stdlib_pep723_script():
    text = AGGREGATOR.read_text(encoding="utf-8")
    assert re.search(r"^# /// script\n.*^# dependencies = \[\]\n.*^# ///", text, re.S | re.M)


# --- protocol and templates -----------------------------------------------------------------

@pytest.fixture(scope="module")
def eval_md():
    assert EVAL_MD.is_file(), "evals/EVAL.md missing"
    return EVAL_MD.read_text(encoding="utf-8")


def test_scope_prompt_asks_each_question_before_any_run(eval_md):
    scope = section(eval_md, r"scope")
    assert scope, "EVAL.md needs a scope-prompt section"
    low = scope.lower()
    assert "one question at a time" in low and "before" in low
    for topic in (r"target", r"brief", r"deck path", r"concern", r"output", r"process", r"depth",
                  r"gates only", r"\bk\b", r"transcript"):
        assert re.search(topic, low), topic


def test_transcripts_need_consent_for_this_run_default_no(eval_md):
    scope = section(eval_md, r"scope").lower()
    line = next(ln for ln in scope.splitlines() if "transcript" in ln)
    assert re.search(r"default[^.]*\bno\b", line), line
    assert "only if process" in scope or "only when process" in scope
    assert re.search(r"never[^.]*(self-reported|process log)", eval_md.lower())


def test_protocol_covers_evidence_gates_dispatch_aggregation_and_results(eval_md):
    low = eval_md.lower()
    for topic in (r"screenshot", r"review size", r"pptx", r"deterministic", r"`d`",
                  r"criterion × repeat|criterion x repeat", r"generic subagent", r"aggregate\.py",
                  r"yymmdd-", r"calibration"):
        assert re.search(topic, low), topic
    assert re.search(r"never[^.]*fork", low), "a fork inherits the builder's context"


def test_protocol_names_every_template_by_backtick_path(eval_md):
    for name in TEMPLATES:
        assert (JUDGES_DIR / name).is_file(), name
        assert f"`judges/{name}`" in eval_md, name


def _template(name):
    return (JUDGES_DIR / name).read_text(encoding="utf-8")


def _example_verdict(name):
    blocks = [b for b in fenced_blocks(_template(name)) if b.lstrip().startswith("{")]
    assert len(blocks) == 1, f"{name}: exactly one example verdict JSON block"
    return json.loads(blocks[0])


@pytest.mark.parametrize("name", sorted(TEMPLATES))
def test_template_verdict_example_is_valid_for_the_aggregator(agg, library, name):
    """The template's schema is the aggregator's: its example must validate and use every field."""
    pairwise = TEMPLATES[name]
    example = _example_verdict(name)
    fields = agg.PAIRWISE_FIELDS if pairwise else agg.VERDICT_FIELDS
    assert tuple(example) == fields
    prof = loader().load_profile(PROFILES_DIR / "editorial-talk.json", library)
    agg.validate_verdict(copy.deepcopy(example), library, prof, pairwise=pairwise)


@pytest.mark.parametrize("name", sorted(TEMPLATES))
def test_template_isolates_the_judge_and_allows_insufficient_evidence(agg, name):
    low = _template(name).lower()
    assert agg.INSUFFICIENT in low
    assert "overthink" in low
    assert re.search(r"(never|do not|don't)[^.]*builder", low)
    assert re.search(r"(≤|at most|no more than) ?(~ ?)?3 sentences|three sentences", low)
    for field in (agg.PAIRWISE_FIELDS if TEMPLATES[name] else agg.VERDICT_FIELDS):
        assert f"`{field}`" in _template(name), field


def test_output_and_process_examples_cover_both_locator_kinds():
    out_ev = _example_verdict("output-judge.md")["evidence"][0]
    proc_ev = _example_verdict("process-judge.md")["evidence"][0]
    assert {"slide", "step"} <= set(out_ev)
    assert {"file", "commit"} & set(proc_ev)


def test_process_template_verifies_claims_against_diffs_and_tests():
    low = _template("process-judge.md").lower()
    assert "diff" in low and "test" in low
    assert re.search(r"commit message[^.]*(claim|not evidence)", low)
    assert re.search(r"transcript", low)


def test_pairwise_template_hides_version_identity():
    low = _template("pairwise-judge.md").lower()
    assert "both orders" in low or "order" in low
    assert re.search(r"(never|not)[^.]*(which version|version names|labels)", low)
