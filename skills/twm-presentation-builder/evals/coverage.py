# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Feature coverage check: every skill feature is exercised by a bundled brief and judged there.

Reads ``features.json`` (feature id → the criteria that judge it), ``criteria.jsonl``,
``profiles/*.json`` and ``briefs/<id>/brief.json`` (each brief claims the features it exercises).
A feature is **covered** when at least one brief claims it whose profile selects one of the
feature's criteria in a concern the brief scopes; otherwise nothing in an eval run would judge it.

Faults (one ``FAIL`` line each): a feature with no criterion, an unknown criterion id, a feature
no brief claims, a feature claimed but judged by no claiming brief, a brief claiming an unknown
feature, a brief whose id is not its folder name (an unknown brief), a brief with an unknown
profile or concern, a duplicate feature id.

Usage (from the skill folder)::

    uv run evals/coverage.py [--evals DIR] [--list]

Exit 0 when covered (prints a summary line, and with ``--list`` each feature's briefs), 1 with
``FAIL`` lines otherwise.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def load(eval_dir: Path = EVAL_DIR) -> tuple[list[dict], dict[str, dict], dict[str, dict], dict[str, dict]]:
    """Load the feature list, criterion library, profiles and briefs.

    Args:
        eval_dir: The ``evals/`` folder.

    Returns:
        ``(features, criteria by id, profiles by file stem, briefs by folder name)``.
    """
    features = json.loads((eval_dir / "features.json").read_text(encoding="utf-8"))["features"]
    criteria = {c["id"]: c for c in _read_jsonl(eval_dir / "criteria.jsonl")}
    profiles = {p.stem: json.loads(p.read_text(encoding="utf-8"))
                for p in sorted((eval_dir / "profiles").glob("*.json"))}
    briefs = {p.parent.name: json.loads(p.read_text(encoding="utf-8"))
              for p in sorted((eval_dir / "briefs").glob("*/brief.json"))}
    return features, criteria, profiles, briefs


def coverage(eval_dir: Path = EVAL_DIR) -> dict[str, dict]:
    """Map each feature to the briefs that claim it and the (brief, criterion) pairs that judge it.

    Args:
        eval_dir: The ``evals/`` folder.

    Returns:
        ``{feature id: {"briefs": [...], "judged_by": [[brief, criterion], ...]}}``.
    """
    features, criteria, profiles, briefs = load(eval_dir)
    out = {}
    for f in features:
        claim = [bid for bid, b in briefs.items() if f["id"] in b.get("features", [])]
        judged = []
        for bid in claim:
            b = briefs[bid]
            weights = profiles.get(b.get("profile"), {}).get("weights", {})
            for cid in f.get("criteria", []):
                c = criteria.get(cid)
                if c and cid in weights and c["concern"] in b.get("concerns", []):
                    judged.append([bid, cid])
        out[f["id"]] = {"briefs": claim, "judged_by": judged}
    return out


def check(eval_dir: Path = EVAL_DIR) -> list[str]:
    """Return every coverage fault as a human-readable line (empty when covered).

    Args:
        eval_dir: The ``evals/`` folder.

    Returns:
        Fault descriptions, each naming the feature, criterion or brief at fault.
    """
    features, criteria, profiles, briefs = load(eval_dir)
    concerns = {c["concern"] for c in criteria.values()}
    errs: list[str] = []
    ids = [f["id"] for f in features]
    errs += [f"feature {i}: duplicate id" for i in sorted({i for i in ids if ids.count(i) > 1})]
    known = set(ids)
    for folder, b in briefs.items():
        if b.get("id") != folder:
            errs.append(f"brief {b.get('id')!r} in folder {folder}: unknown brief id (id must equal its folder)")
        if b.get("profile") not in profiles:
            errs.append(f"brief {folder}: unknown profile {b.get('profile')!r}")
        errs += [f"brief {folder}: unknown concern {c!r}" for c in b.get("concerns", []) if c not in concerns]
        errs += [f"brief {folder}: claims unknown feature {fid}" for fid in b.get("features", [])
                 if fid not in known]
    cov = coverage(eval_dir)
    for f in features:
        fid = f["id"]
        if not f.get("criteria"):
            errs.append(f"feature {fid}: no criterion judges it")
        errs += [f"feature {fid}: unknown criterion {cid}" for cid in f.get("criteria", [])
                 if cid not in criteria]
        if not cov[fid]["briefs"]:
            errs.append(f"feature {fid}: no brief exercises it")
        elif f.get("criteria") and not cov[fid]["judged_by"]:
            errs.append(f"feature {fid}: not judged by any brief that claims it (no claiming brief's "
                        f"profile selects {', '.join(f['criteria'])} in a concern it scopes)")
    return errs


def main(argv: list[str]) -> int:
    """CLI entry point.

    Args:
        argv: Command-line arguments (without the program name).

    Returns:
        Process exit code: 0 covered, 1 faults found.
    """
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--evals", type=Path, default=EVAL_DIR, help="the evals/ folder (default: this one)")
    ap.add_argument("--list", action="store_true", help="print each feature's claiming briefs")
    args = ap.parse_args(argv)
    errs = check(args.evals)
    for e in errs:
        print(f"FAIL {e}")
    if errs:
        return 1
    features, _, _, briefs = load(args.evals)
    if args.list:
        for fid, row in coverage(args.evals).items():
            print(f"{fid}: {', '.join(row['briefs'])}")
    print(f"ok: {len(features)} features covered by {len(briefs)} briefs")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
