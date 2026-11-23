# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Score gates and judges against the anchor labels: the lenient-judge / broken-gate check.

Reads ``anchors/anchors.json`` (labels and verdict rule) and each anchor run's aggregated report
(``anchors/an-NN/<date>-<label>.json``). For every labelled (anchor, criterion) it applies the
verdict rule to the aggregated unit outcomes: ``must_fail`` holds when any unit fails (binary) or
scores ≤ 2 (scale); ``must_pass`` when every unit passes (binary) or scores ≥ 3 (scale). A label
with no aggregated unit is ``not-run``.

Usage (from the repo root)::

    uv run skills/twm-presentation-builder-docs/evals-runs/261123-baseline/accuracy.py

Writes ``anchors/accuracy.json`` and ``anchors/accuracy.md``.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANCHORS = HERE.parents[2] / "twm-presentation-builder" / "evals" / "anchors" / "anchors.json"


def _holds(label: str, crit: dict) -> tuple[str, str]:
    """Return (match status, observed outcome summary) for one label on one criterion report."""
    units = crit.get("units") or {}
    outs = {u: v["outcome"] for u, v in units.items()}
    if not outs or all(o == "insufficient-evidence" for o in outs.values()):
        return ("not-run" if not outs else "insufficient", "–")
    scale = crit["form"] == "scale"
    bad = [u for u, o in outs.items() if (o <= 2 if scale and isinstance(o, (int, float)) else o == "fail")]
    if scale:
        seen = ", ".join(f"{u}: {o}" for u, o in sorted(outs.items()))
    else:
        seen = f"{len(bad)}/{len(outs)} unit(s) fail" + (f" ({', '.join(sorted(bad)[:4])})" if bad else "")
        k = [v for v in units.values() if v.get("k", 1) > 1]
        if k:
            seen += " · repeats " + "; ".join("/".join(map(str, v["results"])) for v in k)
    ok = bool(bad) if label == "must_fail" else not bad
    return ("match" if ok else "MISMATCH", seen)


def main() -> None:
    """Build the accuracy table for gates (D) and judges (S/T) separately."""
    spec = json.loads(ANCHORS.read_text())
    rows = []
    for a in spec["anchors"]:
        run = HERE / "anchors" / a["id"].lower()
        reports = sorted(run.glob("2*-*.json"))
        rep = json.loads(reports[-1].read_text()) if reports else {"criteria": {}}
        for label in ("must_fail", "must_pass"):
            for cid in a[label]:
                crit = rep["criteria"].get(cid)
                kind = "gate" if crit and crit["evidence"] == "D" else "judge"
                status, seen = _holds(label, crit) if crit else ("not-run", "–")
                rows.append({"anchor": a["id"], "criterion": cid, "kind": kind, "label": label,
                             "status": status, "observed": seen})
    (HERE / "anchors" / "accuracy.json").write_text(json.dumps(rows, indent=1) + "\n")
    lines = ["# Anchor accuracy (261123 baseline)", ""]
    for kind in ("judge", "gate"):
        sub = [r for r in rows if r["kind"] == kind]
        n = sum(r["status"] == "match" for r in sub)
        lines += [f"## {kind.title()}s: {n}/{len(sub)} labels matched", "",
                  "| Anchor | Criterion | Label | Result | Observed |", "| --- | --- | --- | --- | --- |"]
        lines += [f"| {r['anchor']} | {r['criterion']} | {r['label']} | {r['status']} | {r['observed']} |"
                  for r in sub]
        lines.append("")
    (HERE / "anchors" / "accuracy.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
