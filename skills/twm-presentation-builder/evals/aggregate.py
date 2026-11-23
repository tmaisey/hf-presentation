# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Validate judge and gate verdicts and aggregate a run into a dated, gated, weighted report.

A run folder holds ``manifest.json`` (the scope-prompt answers) and ``verdicts/*.json`` (one
verdict per judge call or gate check). Aggregation, per (criterion, unit):

* pointwise binary: majority of the decided repeats; a tie fails with flag ``tie``;
* pointwise scale: median of the decided repeats (even k: mean of the middle two);
* insufficient evidence: its own outcome when more than half the repeats say so, else the
  decided repeats decide and the unit is flagged ``partial-evidence``; never a pass;
* ``high-spread``: scale max − min ≥ ``SCALE_SPREAD_FLAG``, or a binary minority share ≥
  ``BINARY_SPLIT_FLAG``: send to the presenter;
* pairwise (A/B, each repeat judged in both orders): a version wins a repeat only when both orders
  pick it, else tie (``order-inconsistent`` when they pick opposite versions); the plurality of
  repeats decides, a tie at the top is a tie.

Per criterion, a unit score is 1/0 (binary) or median/5 (scale); the criterion score is the mean
over decided units. Concern and overall scores are weight-averaged over decided criteria; coverage
is the decided share of the expected weight. Any failed gate fails the deck whatever the score; a
gate that is missing or insufficient makes it ``incomplete``, and the report lists each such gate
with the reason it has no decided verdict (``incomplete``), so "incomplete" never reads as a pass
or a failure. A criterion with no verdict carries a ``reason``: the manifest's ``not_judged``
entry, else the gate runner's (``evidence/gates.json``: ``judge_inputs``, e.g. PX-06 without a
PPTX renderer, or a gate's ``missing``), else "no verdict in this run".

**Several targets in one run (a suite).** Each target is its own sub-run folder (its own
``manifest.json``, ``evidence/`` and ``verdicts/``, so verdict names never collide). The suite
folder's ``manifest.json`` holds only ``label``, ``date`` and ``runs`` (sub-folder names; a
sub-run may itself be a suite). Aggregating the suite aggregates every sub-run (each writes its
own report) and writes a roll-up ``<yymmdd>-<label>.json``/``.md`` beside them: each target's
outcome, failed and undecided gates and overall score. The suite fails when any target fails, is
incomplete when any is incomplete, else passes (pairwise sub-runs are listed, not counted).

Usage::

    uv run evals/aggregate.py <run-dir>     # writes <run-dir>/<yymmdd>-<label>.json and .md
"""

from __future__ import annotations

import importlib.util
import json
import re
import statistics
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
INSUFFICIENT = "insufficient-evidence"
VERDICT_FIELDS = ("criterion", "unit", "repeat", "evidence", "rationale", "flaws", "result")
PAIRWISE_FIELDS = ("criterion", "unit", "repeat", "order", "evidence", "rationale", "flaws",
                   "result")
LOCATORS = ("candidate", "slide", "step", "size", "region", "file", "commit", "line")
PAIR_RESULTS = ("first", "second", "tie")
ORDERS = {"AB": {"first": "A", "second": "B"}, "BA": {"first": "B", "second": "A"}}
MANIFEST_FIELDS = ("label", "date", "target", "profile", "concerns", "depth", "k", "transcripts",
                   "mode")
SUITE_FIELDS = ("label", "date", "runs")
OUTCOME_RANK = {"pass": 0, "incomplete": 1, "fail": 2}
DEPTHS = {"gates", "judges"}
RATIONALE_MAX_CHARS = 600
SCALE_SPREAD_FLAG = 2
BINARY_SPLIT_FLAG = 1 / 3
CALIBRATION_LINE = ("Calibration: agreement with the presenter is unmeasured until a "
                    "calibration set exists.")


class VerdictError(ValueError):
    """Raised when a verdict, a set of verdicts or a run manifest breaks the protocol."""


def _criteria_module():
    spec = importlib.util.spec_from_file_location("skill_eval_criteria_for_aggregate",
                                                  EVAL_DIR / "criteria.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fail(where: str, msg: str) -> None:
    raise VerdictError(f"{where}: {msg}")


def validate_verdict(verdict: dict, library: dict[str, dict], profile: dict,
                     pairwise: bool = False) -> dict:
    """Check one verdict against the schema, the library and the profile.

    Args:
        verdict: Parsed verdict JSON.
        library: Output of ``criteria.load_library``.
        profile: Output of ``criteria.load_profile``.
        pairwise: True for an A/B verdict (``PAIRWISE_FIELDS``), else pointwise.

    Returns:
        The verdict, unchanged.

    Raises:
        VerdictError: On wrong fields or order, an unknown or unselected criterion, a result that
            does not fit the criterion's form, missing or unlocated evidence, an over-long
            rationale or an unknown flaw tag.
    """
    fields = PAIRWISE_FIELDS if pairwise else VERDICT_FIELDS
    where = f"verdict {verdict.get('criterion', '?')}@{verdict.get('unit', '?')}"
    if not isinstance(verdict, dict) or tuple(verdict) != fields:
        _fail(where, f"fields must be exactly, in order: {fields}")
    cid = verdict["criterion"]
    if cid not in library:
        _fail(where, f"unknown criterion id {cid}")
    if cid not in profile["weights"]:
        _fail(where, f"criterion {cid} is not selected by profile {profile['id']!r}")
    crit = library[cid]
    unit = verdict["unit"]
    if not isinstance(unit, str) or not unit.strip():
        _fail(where, "unit must be a non-empty string")
    if (crit["scope"] == "deck") != (unit == "deck"):
        _fail(where, f"unit must be 'deck' exactly when {cid}'s scope is deck")
    if type(verdict["repeat"]) is not int or verdict["repeat"] < 1:
        _fail(where, "repeat must be an integer ≥ 1")
    result = verdict["result"]
    if pairwise:
        if verdict["order"] not in ORDERS:
            _fail(where, f"order must be one of {sorted(ORDERS)}")
        ok = result in PAIR_RESULTS or result == INSUFFICIENT
    elif crit["form"]["type"] == "binary":
        ok = result in ("pass", "fail", INSUFFICIENT)
    else:
        ok = result == INSUFFICIENT or (type(result) is int and 0 <= result <= 5)
    if not ok:
        _fail(where, f"result {result!r} does not fit {cid}'s form")
    evidence = verdict["evidence"]
    if not isinstance(evidence, list) or (result != INSUFFICIENT and not evidence):
        _fail(where, "a decided verdict needs at least one evidence item")
    for item in evidence:
        if (not isinstance(item, dict) or not str(item.get("note", "")).strip()
                or not set(item) - {"note"} or set(item) - {"note", *LOCATORS}):
            _fail(where, f"evidence items need a 'note' and at least one locator of {LOCATORS}")
    rationale = verdict["rationale"]
    if not isinstance(rationale, str) or not rationale.strip() or len(rationale) > RATIONALE_MAX_CHARS:
        _fail(where, f"rationale must be non-empty and ≤ {RATIONALE_MAX_CHARS} characters")
    flaws = verdict["flaws"]
    if not isinstance(flaws, list) or set(flaws) - set(crit["flaws"]):
        _fail(where, f"flaws must be tags from {cid}'s taxonomy {crit['flaws']}")
    return verdict


def _check_manifest(manifest: dict) -> None:
    missing = [f for f in MANIFEST_FIELDS if f not in manifest]
    if missing:
        _fail("manifest", f"missing field(s): {', '.join(missing)}")
    if not re.fullmatch(r"\d{6}", str(manifest["date"])):
        _fail("manifest", "date must be yymmdd")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", str(manifest["label"])):
        _fail("manifest", "label must be kebab-case")
    if manifest["depth"] not in DEPTHS:
        _fail("manifest", f"depth must be one of {sorted(DEPTHS)}")
    if manifest["mode"] not in {"pointwise", "pairwise"}:
        _fail("manifest", "mode must be pointwise or pairwise")
    if manifest["mode"] == "pairwise" and set(manifest.get("versions", {})) != {"A", "B"}:
        _fail("manifest", "pairwise runs name versions A and B")


def is_suite(manifest: dict) -> bool:
    """True when a manifest describes a suite of sub-runs (several targets), not a single run.

    Args:
        manifest: A parsed ``manifest.json``.

    Returns:
        Whether it carries ``runs``.
    """
    return isinstance(manifest, dict) and "runs" in manifest


def _check_suite(manifest: dict, run_dir: Path) -> None:
    missing = [f for f in SUITE_FIELDS if f not in manifest]
    if missing:
        _fail("suite manifest", f"missing field(s): {', '.join(missing)}")
    if not re.fullmatch(r"\d{6}", str(manifest["date"])):
        _fail("suite manifest", "date must be yymmdd")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", str(manifest["label"])):
        _fail("suite manifest", "label must be kebab-case")
    runs = manifest["runs"]
    if not isinstance(runs, list) or not runs or len(set(map(str, runs))) != len(runs):
        _fail("suite manifest", "runs must be a non-empty list of distinct sub-folder names")
    for name in runs:
        bad = not isinstance(name, str) or Path(name).is_absolute() or ".." in Path(name).parts
        if bad or not (run_dir / name / "manifest.json").is_file():
            _fail("suite manifest", f"run {name!r} is not a sub-folder holding a manifest.json")


def _expected(manifest: dict, library: dict, profile: dict) -> dict[str, dict]:
    resolve = _criteria_module().resolve
    out = {}
    for c in resolve(profile, library):
        if c["concern"] not in manifest["concerns"]:
            continue
        if manifest["depth"] == "gates" and c["evidence"] != "D":
            continue
        if manifest["mode"] == "pairwise" and c["evidence"] == "D":
            continue
        out[c["id"]] = c
    return out


def _unit_pointwise(results: list, form_type: str) -> dict:
    k = len(results)
    decided = [r for r in results if r != INSUFFICIENT]
    if (k - len(decided)) * 2 > k:
        return {"outcome": INSUFFICIENT, "score": None, "k": k, "results": results,
                "flags": [INSUFFICIENT]}
    flags = ["partial-evidence"] if len(decided) < k else []
    if form_type == "binary":
        passes = decided.count("pass")
        fails = len(decided) - passes
        if passes == fails:
            outcome = "fail"
            flags.append("tie")
        else:
            outcome = "pass" if passes > fails else "fail"
        if min(passes, fails) / len(decided) >= BINARY_SPLIT_FLAG:
            flags.append("high-spread")
        score = 1.0 if outcome == "pass" else 0.0
    else:
        outcome = statistics.median(decided)
        if max(decided) - min(decided) >= SCALE_SPREAD_FLAG:
            flags.append("high-spread")
        score = outcome / 5
    return {"outcome": outcome, "score": score, "k": k, "results": results, "flags": flags}


def _unit_pairwise(verdicts: list[dict], where: str) -> dict:
    by_repeat: dict[int, dict] = {}
    for v in verdicts:
        by_repeat.setdefault(v["repeat"], {})[v["order"]] = v["result"]
    flags, outcomes = [], []
    for r, orders in sorted(by_repeat.items()):
        if set(orders) != set(ORDERS):
            _fail(where, f"repeat {r} must be judged in both orders (AB and BA)")
        if INSUFFICIENT in orders.values():
            outcomes.append(INSUFFICIENT)
            continue
        picks = {ORDERS[o].get(res, "tie") for o, res in orders.items()}
        if len(picks) == 1:
            outcomes.append(picks.pop())
        else:
            outcomes.append("tie")
            if picks == {"A", "B"} and "order-inconsistent" not in flags:
                flags.append("order-inconsistent")
    k = len(outcomes)
    decided = [o for o in outcomes if o != INSUFFICIENT]
    if (k - len(decided)) * 2 > k:
        return {"outcome": INSUFFICIENT, "k": k, "results": outcomes, "flags": [INSUFFICIENT]}
    if len(decided) < k:
        flags.append("partial-evidence")
    counts = {o: decided.count(o) for o in ("A", "B", "tie")}
    top = max(counts.values())
    leaders = [o for o, n in counts.items() if n == top]
    outcome = leaders[0] if len(leaders) == 1 else "tie"
    if len(set(decided)) > 1:
        flags.append("high-spread")
    return {"outcome": outcome, "k": k, "results": outcomes, "flags": flags}


def _weighted(rows: list[tuple[int, float | None]], key: str) -> dict:
    total = sum(w for w, _ in rows)
    decided = [(w, s) for w, s in rows if s is not None]
    dw = sum(w for w, _ in decided)
    return {key: (sum(w * s for w, s in decided) / dw) if dw else None,
            "coverage": (dw / total) if total else None}


def aggregate(verdicts: list[dict], manifest: dict, library: dict[str, dict],
              profile: dict, reasons: dict[str, str] | None = None) -> dict:
    """Aggregate a run's verdicts into a report.

    Args:
        verdicts: Parsed verdicts (pointwise, or pairwise when ``manifest['mode']`` is pairwise).
        manifest: The run's scope-prompt answers (``MANIFEST_FIELDS``).
        library: Output of ``criteria.load_library``.
        profile: Output of ``criteria.load_profile`` for ``manifest['profile']``.
        reasons: Why a criterion has no verdict, by id (e.g. from the gate log); the manifest's
            ``not_judged`` entries take precedence.

    Returns:
        The report: run manifest, calibration line, deck outcome, the undecided gates behind an
        ``incomplete`` outcome with their reasons, per-criterion statuses with per-unit outcomes
        (and a ``reason`` when missing), concern and overall scores (pointwise) or preferences
        (pairwise), and every flagged unit.

    Raises:
        VerdictError: On a malformed verdict or manifest, a verdict outside the run's scope, a
            duplicated repeat, or a pairwise repeat missing an order.
    """
    _check_manifest(manifest)
    pairwise = manifest["mode"] == "pairwise"
    expected = _expected(manifest, library, profile)
    grouped: dict[str, dict[str, list[dict]]] = {}
    seen = set()
    for v in verdicts:
        validate_verdict(v, library, profile, pairwise=pairwise)
        cid = v["criterion"]
        if cid not in expected:
            _fail(f"verdict {cid}@{v['unit']}",
                  f"{cid} is outside this run's scope (concerns, depth or mode)")
        key = (cid, v["unit"], v["repeat"], v.get("order"))
        if key in seen:
            _fail(f"verdict {cid}@{v['unit']}", f"repeat {v['repeat']} given twice")
        seen.add(key)
        grouped.setdefault(cid, {}).setdefault(v["unit"], []).append(v)

    criteria, flagged = {}, []
    for cid, crit in expected.items():
        units = {}
        for unit, vs in grouped.get(cid, {}).items():
            if pairwise:
                units[unit] = _unit_pairwise(vs, f"verdict {cid}@{unit}")
            else:
                vs = sorted(vs, key=lambda x: x["repeat"])
                units[unit] = _unit_pointwise([x["result"] for x in vs], crit["form"]["type"])
            if units[unit]["flags"]:
                flagged.append({"criterion": cid, "unit": unit, "flags": units[unit]["flags"]})
        entry = {"concern": crit["concern"], "weight": crit["weight"], "gate": crit["gate"],
                 "evidence": crit["evidence"], "form": crit["form"]["type"]}
        decided = {u: x for u, x in units.items() if x["outcome"] != INSUFFICIENT}
        if not units:
            status, score = "missing", None
        elif not decided:
            status, score = INSUFFICIENT, None
        elif pairwise:
            vals = [{"A": 1, "B": -1, "tie": 0}[x["outcome"]] for x in decided.values()]
            score = sum(vals) / len(vals)
            status = "A" if score > 0 else "B" if score < 0 else "tie"
        else:
            score = statistics.fmean(x["score"] for x in decided.values())
            if crit["form"]["type"] == "binary":
                status = ("fail" if any(x["outcome"] == "fail" for x in decided.values())
                          else INSUFFICIENT if len(decided) < len(units) else "pass")
            else:
                status = "scored"
        entry.update(status=status, score=score, units=units)
        if status == "missing":
            entry["reason"] = _reason(cid, crit, manifest, reasons or {})
        criteria[cid] = entry

    key = "preference" if pairwise else "score"
    concerns = {}
    for concern in dict.fromkeys(c["concern"] for c in expected.values()):
        rows = [(c["weight"], c["score"]) for c in criteria.values() if c["concern"] == concern]
        concerns[concern] = _weighted(rows, key)
    overall = _weighted([(c["weight"], c["score"]) for c in criteria.values()], key)

    if pairwise:
        outcome = ("A" if (overall[key] or 0) > 0 else "B" if (overall[key] or 0) < 0 else "tie")
        gates = []
    else:
        gates = [{"criterion": cid, "status": c["status"]} for cid, c in criteria.items() if c["gate"]]
        statuses = {g["status"] for g in gates}
        outcome = ("fail" if "fail" in statuses
                   else "incomplete" if statuses - {"pass"} else "pass")
    undecided = [{"criterion": g["criterion"], "status": g["status"],
                  "reason": criteria[g["criterion"]].get("reason")
                  or "judged, but more than half the repeats found the evidence insufficient"}
                 for g in gates if g["status"] not in ("pass", "fail")]
    return {"run": manifest, "calibration": CALIBRATION_LINE, "outcome": outcome, "gates": gates,
            "incomplete": undecided if outcome == "incomplete" else [],
            "concerns": concerns, "overall": overall, "criteria": criteria, "flags": flagged}


def _reason(cid: str, crit: dict, manifest: dict, reasons: dict[str, str]) -> str:
    """Why a criterion has no verdict: the manifest's ``not_judged``, the gate log, or a default."""
    given = manifest.get("not_judged") if isinstance(manifest.get("not_judged"), dict) else {}
    if given.get(cid):
        return str(given[cid])
    if reasons.get(cid):
        return reasons[cid]
    if crit["evidence"] == "D":
        return "no gate verdict in this run (gates.py was not given the target this criterion checks)"
    return "no judge verdict in this run (not dispatched)"


def _fmt(x) -> str:
    if x is None:
        return "–"
    return f"{x:.2f}" if isinstance(x, float) else str(x)


def render_markdown(report: dict) -> str:
    """Render a report as the markdown the presenter reads.

    Args:
        report: Output of ``aggregate``.

    Returns:
        Markdown text, always including ``CALIBRATION_LINE``.
    """
    run = report["run"]
    pairwise = run["mode"] == "pairwise"
    key = "preference" if pairwise else "score"
    out = [f"# Eval report: {run['label']} ({run['date']})", "",
           f"**{CALIBRATION_LINE}**", "",
           f"- Target: `{run['target']}` · profile `{run['profile']}` · mode {run['mode']}"
           f" · depth {run['depth']} · k = {run['k']}",
           f"- Concerns: {', '.join(run['concerns'])} · transcripts read: "
           f"{'yes (approved for this run)' if run['transcripts'] else 'no'}",
           f"- **Outcome: {report['outcome']}** · overall {key} {_fmt(report['overall'][key])}"
           f" (coverage {_fmt(report['overall']['coverage'])})", ""]
    if report.get("incomplete"):
        out += ["Outcome incomplete: no gate failed, but these gates have no decided verdict, so the deck "
                "is neither passed nor failed. Gate or judge them to settle it:", ""]
        out += [f"- {g['criterion']} ({g['status']}): {g['reason']}" for g in report["incomplete"]] + [""]
    if pairwise:
        out += [f"Versions: A = `{run['versions']['A']}`, B = `{run['versions']['B']}`; "
                "preference runs from −1 (B) to +1 (A).", ""]
    if report["gates"]:
        out += ["## Gates", "", "| Gate | Status |", "| --- | --- |"]
        out += [f"| {g['criterion']} | {g['status']} |" for g in report["gates"]] + [""]
    out += ["## Concerns", "", f"| Concern | {key.title()} | Coverage |", "| --- | --- | --- |"]
    out += [f"| {c} | {_fmt(x[key])} | {_fmt(x['coverage'])} |"
            for c, x in report["concerns"].items()] + [""]
    out += ["## Criteria", "", f"| Criterion | Concern | Weight | Gate | Status | {key.title()} |",
            "| --- | --- | --- | --- | --- | --- |"]
    out += [f"| {cid} | {c['concern']} | {c['weight']} | {'yes' if c['gate'] else ''} "
            f"| {c['status']} | {_fmt(c['score'])} |" for cid, c in report["criteria"].items()]
    missing = [(cid, c) for cid, c in report["criteria"].items() if c["status"] == "missing"]
    if missing:
        out += ["", "## Missing criteria", ""]
        out += [f"- {cid}{' (gate)' if c['gate'] else ''}: {c.get('reason', 'no verdict')}"
                for cid, c in missing]
    out += ["", "## Flagged for the presenter", ""]
    out += ([f"- {f['criterion']} @ {f['unit']}: {', '.join(f['flags'])}" for f in report["flags"]]
            or ["- none"])
    return "\n".join(out) + "\n"


def _gate_reasons(run_dir: Path) -> dict[str, str]:
    """Missing reasons the gate runner logged (``evidence/gates.json``), by criterion id."""
    path = run_dir / "evidence" / "gates.json"
    if not path.is_file():
        return {}
    try:
        log = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    out = {cid: c["missing"] for cid, c in (log.get("criteria") or {}).items() if c.get("missing")}
    out |= {cid: c["missing"] for cid, c in (log.get("judge_inputs") or {}).items() if c.get("missing")}
    return out


def load_run(run_dir: Path, eval_dir: Path = EVAL_DIR) -> dict:
    """Validate and aggregate one run folder in memory, writing nothing.

    Args:
        run_dir: Folder with ``manifest.json`` (a single run, not a suite) and ``verdicts/*.json``.
        eval_dir: The eval folder whose library and ``profiles/`` the run uses.

    Returns:
        The report, as ``aggregate`` returns it (missing reasons from the manifest and gate log).

    Raises:
        VerdictError: On any protocol breach; the message names the offending verdict file.
        criteria.EvalFormatError: If the library or the named profile is invalid or unknown.
    """
    run_dir, eval_dir = Path(run_dir), Path(eval_dir)
    crit = _criteria_module()
    library = crit.load_library(eval_dir)
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    _check_manifest(manifest)
    profile_path = eval_dir / "profiles" / f"{manifest['profile']}.json"
    if not profile_path.is_file():
        raise crit.EvalFormatError(f"manifest: unknown profile {manifest['profile']!r}")
    profile = crit.load_profile(profile_path, library)
    verdicts = []
    pairwise = manifest["mode"] == "pairwise"
    for path in sorted((run_dir / "verdicts").glob("*.json")):
        try:
            v = json.loads(path.read_text(encoding="utf-8"))
            validate_verdict(v, library, profile, pairwise=pairwise)
        except (json.JSONDecodeError, VerdictError) as e:
            raise VerdictError(f"{path.name}: {e}") from e
        verdicts.append(v)
    return aggregate(verdicts, manifest, library, profile, _gate_reasons(run_dir))


def _write(run_dir: Path, manifest: dict, report: dict, markdown: str) -> tuple[Path, Path]:
    stem = f"{manifest['date']}-{manifest['label']}"
    json_path, md_path = run_dir / f"{stem}.json", run_dir / f"{stem}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8")
    return json_path, md_path


def _rollup_row(name: str, sub: Path, report: dict, report_path: Path, suite_dir: Path) -> dict:
    rel = report_path.relative_to(suite_dir).as_posix()
    if report.get("tool") == "aggregate-suite":
        return {"run": name, "label": report["label"], "target": None, "outcome": report["outcome"],
                "gates_failed": [], "gates_undecided": [], "overall": None, "flags": None, "report": rel,
                "runs": report["runs"]}
    return {"run": name, "label": report["run"]["label"], "target": report["run"]["target"],
            "outcome": report["outcome"],
            "gates_failed": [g["criterion"] for g in report["gates"] if g["status"] == "fail"],
            "gates_undecided": [g["criterion"] for g in report.get("incomplete", [])],
            "overall": report["overall"], "flags": len(report["flags"]), "report": rel}


def render_suite_markdown(rollup: dict) -> str:
    """Render a suite roll-up as markdown: one row per target, worst outcome first in the headline.

    Args:
        rollup: Output of ``run_suite`` (the roll-up JSON).

    Returns:
        Markdown text, always including ``CALIBRATION_LINE``.
    """
    out = [f"# Eval roll-up: {rollup['label']} ({rollup['date']})", "", f"**{CALIBRATION_LINE}**", "",
           f"- **Outcome: {rollup['outcome']}** over {len(rollup['runs'])} run(s); each target's own report "
           "holds its detail.", "",
           "| Run | Target | Outcome | Gates failed | Gates undecided | Overall (coverage) | Flags |",
           "| --- | --- | --- | --- | --- | --- | --- |"]

    def rows(entries, prefix=""):
        for r in entries:
            path = f"{prefix}{r['run']}"
            if r.get("runs") is not None:
                out.append(f"| {path} | (suite) | {r['outcome']} | | | | |")
                rows(r["runs"], path + "/")
                continue
            ov = r["overall"] or {}
            key = "score" if "score" in ov else "preference"
            out.append(f"| {path} | `{r['target']}` | {r['outcome']} | {', '.join(r['gates_failed']) or '–'} "
                       f"| {', '.join(r['gates_undecided']) or '–'} | {_fmt(ov.get(key))} ({_fmt(ov.get('coverage'))}) "
                       f"| {r['flags']} |")

    rows(rollup["runs"])
    return "\n".join(out) + "\n"


def run_suite(suite_dir: Path, eval_dir: Path = EVAL_DIR) -> tuple[Path, Path]:
    """Aggregate every sub-run of a suite (several targets) and write the dated roll-up.

    Args:
        suite_dir: Folder whose ``manifest.json`` names ``label``, ``date`` and ``runs``.
        eval_dir: The eval folder whose library and profiles the sub-runs use.

    Returns:
        Paths of the written roll-up ``<yymmdd>-<label>.json`` and ``.md``.

    Raises:
        VerdictError: On a malformed suite manifest or any sub-run's protocol breach (named).
    """
    suite_dir = Path(suite_dir)
    manifest = json.loads((suite_dir / "manifest.json").read_text(encoding="utf-8"))
    _check_suite(manifest, suite_dir)
    rows = []
    for name in manifest["runs"]:
        sub = suite_dir / name
        try:
            json_path, _ = run(sub, eval_dir)
        except VerdictError as e:
            raise VerdictError(f"{name}/{e}") from e
        rows.append(_rollup_row(name, sub, json.loads(json_path.read_text(encoding="utf-8")), json_path, suite_dir))
    ranked = [r["outcome"] for r in rows if r["outcome"] in OUTCOME_RANK]
    outcome = max(ranked, key=OUTCOME_RANK.get) if ranked else "–"
    rollup = {"tool": "aggregate-suite", "label": manifest["label"], "date": manifest["date"],
              "calibration": CALIBRATION_LINE, "outcome": outcome, "runs": rows}
    return _write(suite_dir, manifest, rollup, render_suite_markdown(rollup))


def run(run_dir: Path, eval_dir: Path = EVAL_DIR) -> tuple[Path, Path]:
    """Aggregate a run folder (or a suite of sub-runs) and write its dated report files.

    Args:
        run_dir: Folder with ``manifest.json`` and ``verdicts/*.json``, or a suite folder whose
            ``manifest.json`` names its sub-runs (``runs``).
        eval_dir: The eval folder whose library and ``profiles/`` the run uses.

    Returns:
        Paths of the written ``<yymmdd>-<label>.json`` and ``.md`` (the roll-up for a suite).

    Raises:
        VerdictError: On any protocol breach; the message names the offending verdict file.
        criteria.EvalFormatError: If the library or the named profile is invalid or unknown.
    """
    run_dir = Path(run_dir)
    mpath = run_dir / "manifest.json"
    if not mpath.is_file():
        raise VerdictError(f"{run_dir}: no manifest.json (a run, or a suite naming its runs)")
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    if is_suite(manifest):
        return run_suite(run_dir, eval_dir)
    report = load_run(run_dir, eval_dir)
    return _write(run_dir, manifest, report, render_markdown(report))


def main(argv: list[str]) -> int:
    """CLI entry point: ``<run-dir>``.

    Args:
        argv: Arguments after the script name.

    Returns:
        Process exit code: 0 written, 1 protocol or format error, 2 usage.
    """
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        json_path, md_path = run(Path(argv[0]))
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"wrote {json_path} and {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
