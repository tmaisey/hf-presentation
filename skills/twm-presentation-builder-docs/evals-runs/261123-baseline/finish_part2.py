# /// script
# requires-python = ">=3.12"
# ///
"""Close part 2 of the 261123 baseline without further judges.

Records a reason for every in-scope criterion that has no verdict in each cold-build run
(`not_judged`), fixes the run's `.gitignore` regenerate line, and writes the baseline suite
manifest. Run from the repo root: `uv run <this file>`.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

RUN = Path(__file__).resolve().parent
SKILL = RUN.parents[2] / "twm-presentation-builder"
DECKS = {"pitch-solar-coop": "builds/pitch-solar-coop/deck/deck.html",
         "data-review-bus-reliability": "builds/data-review-bus-reliability/drafts/bus-reliability-q3.html"}
SPEND = ("not run: the account's spend limit was reached mid-run (261123); the prompt is filled "
         "in prompts/ and listed in dispatch.tsv, ready to re-dispatch with the presenter's OK")
BUDGET = "judge budget (part 2 cap 120): not sampled in this run"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    """Write `not_judged` reasons, the `.gitignore` line and the suite manifest."""
    crit = _load(SKILL / "evals" / "criteria.py", "baseline_criteria")
    library, profiles = crit.load_library(), crit.load_profiles()
    for target, deck in DECKS.items():
        d = RUN / target
        m = json.loads((d / "manifest.json").read_text())
        profile = profiles[m["profile"]]
        judged = {json.loads(f.read_text())["criterion"] for f in (d / "verdicts").glob("*.json")}
        dispatched = (d / "dispatch.tsv").read_text()
        reasons = {}
        for cid in profile["weights"]:
            c = library[cid]
            if c["concern"] not in m["concerns"] or c["evidence"] == "D" or cid in judged:
                continue
            if cid == "PX-06":
                reasons[cid] = "no PPTX renderer: LibreOffice (soffice) is not on PATH"
            elif f"{cid}_" in dispatched or c["concern"] == "process":
                reasons[cid] = SPEND
            else:
                reasons[cid] = BUDGET
        m["not_judged"] = reasons
        (d / "manifest.json").write_text(json.dumps(m, indent=1, ensure_ascii=False) + "\n")
        gi = d / ".gitignore"
        lines = gi.read_text().splitlines()
        lines[0] = (f"# Screenshots, contact sheets and worktrees are regenerable (from the skill folder): "
                    f"uv run scripts/shoot.py <run>/{deck} <this>/evidence --sizes 1920x1080,1288x598 "
                    f"--notes --contact 1920x1080; uv run evals/extract.py <run>/{deck} <this>/evidence/text")
        gi.write_text("\n".join(lines) + "\n")
        print(target, "not_judged:", len(reasons))
    suite = {"label": "baseline", "date": "261123",
             "runs": ["hf-subset", "hf-subset-bright", "anchors", *DECKS]}
    (RUN / "manifest.json").write_text(json.dumps(suite, indent=1) + "\n")


if __name__ == "__main__":
    main()
