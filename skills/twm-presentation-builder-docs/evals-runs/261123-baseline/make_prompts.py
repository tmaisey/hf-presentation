# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Fill ``judges/output-judge.md`` for every planned (criterion, unit, repeat) of this baseline run.

The judge plan (which criteria, which units, which evidence) is fixed below and recorded in each
run's manifest. Writes ``<run>/prompts/<criterion>_<unit>_r<k>.md`` and prints one line per prompt
(``prompt-path<TAB>verdict-path``), all relative to the repo root, which judges use as their cwd.

Usage (from the repo root)::

    uv run skills/twm-presentation-builder-docs/evals-runs/261123-baseline/make_prompts.py
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
SKILL = REPO / "skills" / "twm-presentation-builder"
K = 3
RESEARCH = sorted((SKILL / "evals/briefs/hf-subset/research").glob("*.md"))
VOICE = [SKILL / "voice/profiles/twm.md"]

# (run dir, criterion, unit, evidence kind); kinds: steps = the unit's step shots at both sizes,
# deck1920 = every step shot at 1920x1080, text = the unit's text extract + its 1920 shots,
# alltext = every slide's text extract (+ extra files).
PLAN = [
    # anchors: only each anchor's labelled S/T criteria, one unit = the slide its label is about
    ("anchors/an-00", "DP-04", "a0-2", "steps"), ("anchors/an-00", "DL-07", "a0-2", "steps"),
    ("anchors/an-00", "CN-05", "a0-2", "steps"), ("anchors/an-00", "VC-01", "a0-2", "text"),
    ("anchors/an-00", "RS-01", "a0-2", "text"), ("anchors/an-00", "RS-03", "a0-3", "text"),
    ("anchors/an-02", "DS-04", "a2-1", "steps"),
    ("anchors/an-03", "VC-01", "a3-1", "text"),
    ("anchors/an-04", "RS-01", "a4-1", "text"), ("anchors/an-04", "RS-03", "a4-2", "text"),
    ("anchors/an-05", "CN-05", "a5-1", "steps"), ("anchors/an-05", "CN-03", "a5-1", "steps"),
    ("anchors/an-05", "CN-01", "a5-1", "steps"), ("anchors/an-05", "DL-05", "a5-1", "steps"),
    ("anchors/an-05", "DL-06", "a5-1", "steps"), ("anchors/an-05", "DS-06", "deck", "steps"),
    ("anchors/an-05", "RS-03", "a5-1", "text"),
    ("anchors/an-06", "DL-07", "a6-1", "steps"), ("anchors/an-06", "RS-03", "a6-1", "text"),
    ("anchors/an-07", "DP-04", "a7-1", "steps"),
    ("anchors/an-09", "RS-01", "a9-1", "text"),
    # hf-subset: weight-3 and gate criteria first, sampled on the slide that tests them hardest
    ("hf-subset", "CN-01", "s-4", "steps"), ("hf-subset", "CN-03", "s-2", "steps"),
    ("hf-subset", "CN-05", "s-4", "steps"), ("hf-subset", "CN-06", "deck", "alltext"),
    ("hf-subset", "CN-10", "deck", "deck1920"), ("hf-subset", "RS-01", "s-4", "text"),
    ("hf-subset", "RS-02", "s-4", "text+research"), ("hf-subset", "RS-04", "s-9", "text"),
    ("hf-subset", "VC-08", "deck", "alltext+voice"), ("hf-subset", "DL-05", "s-4", "steps"),
    ("hf-subset", "DL-07", "s-4", "steps"), ("hf-subset", "DS-02", "s-5", "steps"),
    ("hf-subset", "DS-04", "s-4", "steps"), ("hf-subset", "DS-06", "deck", "deck1920"),
    # hf-subset-bright: palette and style screenshot criteria (PX-06 needs PPTX renders: none)
    ("hf-subset-bright", "DP-04", "s-4", "steps"), ("hf-subset-bright", "DP-06", "deck", "deck1920"),
    ("hf-subset-bright", "DS-04", "s-4", "steps"), ("hf-subset-bright", "DS-05", "s-9", "steps"),
    ("hf-subset-bright", "DS-06", "deck", "deck1920"),
]


def _rel(p: Path) -> str:
    return p.resolve().relative_to(REPO).as_posix()


def _step_shots(ev: Path, slide: str | None, sizes=("1920x1080", "1288x598")) -> list[Path]:
    shots = json.loads((ev / "shots.json").read_text())["shots"]
    return [ev / s["file"] for s in shots
            if s["mode"] == "step" and s["size"] in sizes and (slide is None or s["slide"] == slide)]


def evidence(run: str, unit: str, kind: str) -> list[str]:
    """Return the evidence file paths (repo-relative) one judge of ``unit`` may open."""
    ev = HERE / run / "evidence"
    slide = None if unit == "deck" else unit
    files: list[Path] = []
    if kind == "steps":
        files = _step_shots(ev, slide)
    elif kind == "deck1920":
        files = _step_shots(ev, None, ("1920x1080",))
    elif kind.startswith("text"):
        files = [ev / "text" / f"{unit}.txt"] + _step_shots(ev, slide, ("1920x1080",))
        if kind.endswith("+research"):
            files += RESEARCH
    elif kind.startswith("alltext"):
        files = sorted((ev / "text").glob("*.txt"))
        if kind.endswith("+voice"):
            files += VOICE
    return [_rel(f) for f in files]


def main() -> None:
    """Write every prompt and print its prompt and verdict paths."""
    template = (SKILL / "evals/judges/output-judge.md").read_text().split("\n---\n", 1)[1].lstrip()
    resolved = json.loads(subprocess.run(
        ["uv", "run", "-q", str(SKILL / "evals/criteria.py"), "resolve", "editorial-talk"],
        check=True, capture_output=True, text=True).stdout)
    crits = {c["id"]: c for c in resolved}
    flaws = json.loads((SKILL / "evals/flaws.json").read_text())
    for run, cid, unit, kind in PLAN:
        crit = crits[cid]
        flaw_txt = "\n".join(f"- `{t}`: {flaws[t]['description']}" for t in crit["flaws"])
        files = evidence(run, unit, kind)
        for r in range(1, K + 1):
            verdict = HERE / run / "verdicts" / f"{cid}_{unit}_r{r}.json"
            text = (template
                    .replace("{{criterion_json}}", "```json\n" + json.dumps(crit, indent=1, ensure_ascii=False) + "\n```")
                    .replace("{{flaws}}", flaw_txt)
                    .replace("{{unit}}", unit).replace("{{repeat}}", str(r))
                    .replace("{{evidence_files}}", "\n".join(f"- `{f}`" for f in files))
                    .replace("{{verdict_path}}", _rel(verdict)))
            assert "{{" not in text, (cid, unit)
            out = HERE / run / "prompts" / f"{cid}_{unit}_r{r}.md"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
            print(f"{_rel(out)}\t{_rel(verdict)}")


if __name__ == "__main__":
    main()
