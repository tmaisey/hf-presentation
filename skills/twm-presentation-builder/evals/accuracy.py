# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Anchor accuracy: score the run's gates and judges against the anchor labels (lenient-judge check).

Reads ``anchors/anchors.json`` (labels and verdict rule) and an anchors run: a suite whose
``manifest.json`` names one sub-run per anchor (``runs``), or, for a folder without a suite
manifest, every sub-folder holding a ``manifest.json``. Each sub-run is matched to its anchor by
the file name of its manifest ``target`` (e.g. ``…/an-05.html``) and aggregated **in memory** from
its verdicts (``aggregate.load_run``): nothing is written into the run unless ``--out`` points
there (the default).

Per labelled (anchor, criterion), the verdict rule applies to the aggregated unit outcomes:

* ``must_fail`` holds when any unit fails (binary) or any unit's median is ≤ 2 (scale);
* ``must_pass`` holds when no unit fails (binary) and every unit's median is ≥ 3 (scale);
* a label with no unit is ``not-run``; one whose units are all insufficient evidence is
  ``insufficient``; neither counts as a match.

Gates (``D`` criteria) and judges (``S``/``T``) are tallied apart: a gate mismatch is a broken
gate, a judge ``must_fail`` mismatch a lenient judge, a judge ``must_pass`` mismatch an
over-strict one.

Usage::

    uv run evals/accuracy.py <anchors-run-dir> [--out dir] [--anchors anchors.json]

Writes ``accuracy.json`` (``{"summary": {"judge"|"gate": {"matched", "labels"}}, "rows": […]}``)
and ``accuracy.md`` into ``--out`` (default: the run folder). Exit codes: 0 written, 1 unusable
run, 2 usage.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
ANCHORS = EVAL_DIR / "anchors" / "anchors.json"
INSUFFICIENT = "insufficient-evidence"


def _aggregate_module():
    spec = importlib.util.spec_from_file_location("skill_eval_aggregate_for_accuracy", EVAL_DIR / "aggregate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def label_status(label: str, crit: dict | None) -> tuple[str, str]:
    """Apply the anchor verdict rule to one criterion's aggregated units.

    Args:
        label: ``must_fail`` or ``must_pass``.
        crit: The criterion's entry in an aggregate report (``form``, ``units``), or None when the
            run has no verdict for it.

    Returns:
        ``(status, observed)``: status is ``match``, ``MISMATCH``, ``insufficient`` or ``not-run``;
        observed summarises the unit outcomes for the table.
    """
    units = (crit or {}).get("units") or {}
    if not units:
        return "not-run", "–"
    outs = {u: v["outcome"] for u, v in units.items() if v["outcome"] != INSUFFICIENT}
    if not outs:
        return "insufficient", "all units insufficient evidence"
    form = crit["form"]["type"] if isinstance(crit["form"], dict) else crit["form"]
    if form == "scale":
        seen = ", ".join(f"{u}: {o:g}" for u, o in sorted(outs.items()))
        if label == "must_fail":
            ok = any(o <= 2 for o in outs.values())
        else:
            ok = all(o >= 3 for o in outs.values())
    else:
        bad = [u for u, o in outs.items() if o == "fail"]
        seen = f"{len(bad)}/{len(outs)} unit(s) fail" + (f" ({', '.join(sorted(bad)[:4])})" if bad else "")
        k = [v for v in units.values() if v.get("k", 1) > 1]
        if k:
            seen += " · repeats " + "; ".join("/".join(map(str, v["results"])) for v in k)
        ok = bool(bad) if label == "must_fail" else not bad
    return ("match" if ok else "MISMATCH"), seen


def anchor_runs(run_dir: Path) -> list[Path]:
    """The sub-runs of an anchors run: the suite manifest's ``runs``, else every child run folder."""
    run_dir = Path(run_dir)
    m = run_dir / "manifest.json"
    if m.is_file():
        manifest = json.loads(m.read_text(encoding="utf-8"))
        if "runs" not in manifest:
            return [run_dir]
        return [run_dir / r for r in manifest["runs"]]
    return sorted(p.parent for p in run_dir.glob("*/manifest.json"))


def accuracy(run_dir: Path, anchors: Path = ANCHORS, eval_dir: Path = EVAL_DIR) -> dict:
    """Build the accuracy table for one anchors run.

    Args:
        run_dir: The anchors run (suite or folder of sub-runs).
        anchors: The anchor labels file.
        eval_dir: Eval folder whose library and profiles the runs use.

    Returns:
        ``{"summary": {"judge": {...}, "gate": {...}}, "rows": [...]}``; rows follow the labels'
        order (anchor, then must_fail, then must_pass).

    Raises:
        ValueError: When a sub-run cannot be aggregated (the message names it).
    """
    agg = _aggregate_module()
    spec = json.loads(Path(anchors).read_text(encoding="utf-8"))
    library = agg._criteria_module().load_library(eval_dir)
    reports = {}
    for sub in anchor_runs(run_dir):
        target = json.loads((sub / "manifest.json").read_text(encoding="utf-8")).get("target", "")
        try:
            reports[Path(str(target)).name] = agg.load_run(sub, eval_dir)
        except ValueError as e:
            raise ValueError(f"{sub.name}: {e}") from e
    rows = []
    for a in spec["anchors"]:
        rep = reports.get(a["file"], {"criteria": {}})
        for label in ("must_fail", "must_pass"):
            for cid in a[label]:
                crit = rep["criteria"].get(cid)
                kind = "gate" if library.get(cid, {}).get("evidence") == "D" else "judge"
                status, seen = label_status(label, crit)
                rows.append({"anchor": a["id"], "criterion": cid, "kind": kind, "label": label,
                             "status": status, "observed": seen})
    summary = {k: {"matched": sum(r["status"] == "match" for r in rows if r["kind"] == k),
                   "labels": sum(r["kind"] == k for r in rows)} for k in ("judge", "gate")}
    return {"summary": summary, "rows": rows}


def render_markdown(result: dict, title: str = "Anchor accuracy") -> str:
    """Render the accuracy table: judges first (the lenient-judge check), then gates."""
    lines = [f"# {title}", ""]
    for kind in ("judge", "gate"):
        s = result["summary"][kind]
        lines += [f"## {kind.title()}s: {s['matched']}/{s['labels']} labels matched", "",
                  "| Anchor | Criterion | Label | Result | Observed |", "| --- | --- | --- | --- | --- |"]
        lines += [f"| {r['anchor']} | {r['criterion']} | {r['label']} | {r['status']} | {r['observed']} |"
                  for r in result["rows"] if r["kind"] == kind]
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Arguments (defaults to ``sys.argv[1:]``).

    Returns:
        0 written, 1 unusable run, 2 usage.
    """
    ap = argparse.ArgumentParser(description="Score an anchors run's gates and judges against the anchor labels.")
    ap.add_argument("run_dir", type=Path, help="anchors run: a suite of one sub-run per anchor")
    ap.add_argument("--out", type=Path, help="folder for accuracy.json and accuracy.md (default: run_dir)")
    ap.add_argument("--anchors", type=Path, default=ANCHORS, help="anchor labels (default: the shipped anchors.json)")
    args = ap.parse_args(argv)
    if not args.run_dir.is_dir():
        print(f"error: {args.run_dir}: no such folder", file=sys.stderr)
        return 2
    try:
        result = accuracy(args.run_dir, args.anchors)
    except (ValueError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    out = args.out or args.run_dir
    out.mkdir(parents=True, exist_ok=True)
    (out / "accuracy.json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    md = render_markdown(result)
    (out / "accuracy.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
