# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Fill judge prompts for a run from a judge plan: one prompt per (criterion, unit, repeat).

The plan says which criteria to judge on which units and which evidence files each judge may
open; this tool fills the right template (``judges/output-judge.md`` for a ``deck``/``pptx``
criterion, ``judges/process-judge.md`` for a ``repo`` one) with the criterion's resolved JSON
(profile params merged), its flaw tags, the unit, the repeat and the verdict path, for every
repeat ``1..k`` (``k`` from the run's ``manifest.json``). Pairwise A/B prompts are filled by
hand (``judges/pairwise-judge.md``).

Plan file (JSON list)::

    [{"criterion": "CN-01", "unit": "s-4", "evidence": ["evidence/s-4-0-1920x1080.png", ...]},
     {"criterion": "PR-05", "unit": "S-003", "evidence": [...], "repo_path": ".", "transcripts": "none"}]

Evidence paths are written as given: make them relative to the folder judges work in (the
project root), as the verdict paths are (``<run-dir as given>/verdicts/<criterion>_<unit>_r<k>.json``,
unit slugged as ``gates.py`` does).

Usage::

    uv run evals/prompts.py <run-dir> <plan.json>

Writes ``<run-dir>/prompts/<criterion>_<unit>_r<k>.md`` and prints ``prompt-path<TAB>verdict-path``
per prompt, ready for dispatch. Exit codes: 0 written, 1 bad plan or run, 2 usage.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
TEMPLATES = {"deck": "output-judge.md", "pptx": "output-judge.md", "repo": "process-judge.md"}


class PlanError(ValueError):
    """Raised when a judge plan or its run cannot produce prompts."""


def _criteria_module():
    spec = importlib.util.spec_from_file_location("skill_eval_criteria_for_prompts", EVAL_DIR / "criteria.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def slug(unit: str) -> str:
    """A unit as it appears in a file name (the gate runner's rule)."""
    return re.sub(r"[^A-Za-z0-9-]+", "-", unit).strip("-")


def _template(name: str, eval_dir: Path) -> str:
    """The judge-facing part of a template (below its first ``---`` rule)."""
    return (eval_dir / "judges" / name).read_text(encoding="utf-8").split("\n---\n", 1)[1].lstrip()


def build(run_dir: Path, plan: list[dict], eval_dir: Path = EVAL_DIR) -> list[tuple[Path, Path]]:
    """Write every prompt the plan asks for.

    Args:
        run_dir: The run folder (its ``manifest.json`` gives profile and ``k``).
        plan: Plan items (``criterion``, ``unit``, ``evidence``; ``repo_path``/``transcripts`` for
            repo criteria).
        eval_dir: Eval folder holding the library, profiles and templates.

    Returns:
        ``(prompt path, verdict path)`` per written prompt, in plan order then repeat order.

    Raises:
        PlanError: On a missing manifest, an unknown or unselected or deterministic criterion, a
            deck-scoped criterion on a non-deck unit (or the reverse), or an unfilled placeholder.
    """
    run_dir = Path(run_dir)
    try:
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise PlanError(f"{run_dir}: unreadable manifest.json ({e})") from e
    crit_mod = _criteria_module()
    library = crit_mod.load_library(eval_dir)
    profile = crit_mod.load_profile(Path(eval_dir) / "profiles" / f"{manifest['profile']}.json", library)
    resolved = {c["id"]: c for c in crit_mod.resolve(profile, library)}
    flaws = crit_mod.load_flaws(eval_dir)
    k = int(manifest.get("k", 1))
    out = []
    for item in plan:
        cid, unit = item.get("criterion"), str(item.get("unit", ""))
        if cid not in resolved:
            raise PlanError(f"{cid}: unknown, or not selected by profile {manifest['profile']!r}")
        crit = resolved[cid]
        if crit["evidence"] == "D":
            raise PlanError(f"{cid}: deterministic criteria are gated (gates.py), never judged")
        if (crit["scope"] == "deck") != (unit == "deck"):
            raise PlanError(f"{cid}@{unit}: unit must be 'deck' exactly when the criterion's scope is deck")
        template = _template(TEMPLATES[crit["target"]], eval_dir)
        flaw_txt = "\n".join(f"- `{t}`: {flaws[t]['description']}" for t in crit["flaws"])
        files = "\n".join(f"- `{f}`" for f in item.get("evidence", [])) or "- (none)"
        for r in range(1, k + 1):
            name = f"{cid}_{slug(unit)}_r{r}"
            verdict = run_dir / "verdicts" / f"{name}.json"
            text = (template
                    .replace("{{criterion_json}}", "```json\n" + json.dumps(crit, indent=1, ensure_ascii=False) + "\n```")
                    .replace("{{flaws}}", flaw_txt)
                    .replace("{{unit}}", unit).replace("{{repeat}}", str(r))
                    .replace("{{evidence_files}}", files)
                    .replace("{{repo_path}}", str(item.get("repo_path", ".")))
                    .replace("{{transcripts}}", str(item.get("transcripts", "none (not approved for this run)")))
                    .replace("{{verdict_path}}", verdict.as_posix()))
            left = sorted(set(re.findall(r"\{\{[a-z_]+\}\}", text)) - {"{{placeholder}}"})
            if left:
                raise PlanError(f"{cid}@{unit}: unfilled {', '.join(left)}")
            path = run_dir / "prompts" / f"{name}.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            out.append((path, verdict))
    return out


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: ``<run-dir> <plan.json>``.

    Args:
        argv: Arguments (defaults to ``sys.argv[1:]``).

    Returns:
        0 written, 1 bad plan or run, 2 usage.
    """
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        plan = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        if not isinstance(plan, list):
            raise PlanError("the plan must be a JSON list of items")
        made = build(Path(argv[0]), plan)
    except (ValueError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    for prompt, verdict in made:
        print(f"{prompt.as_posix()}\t{verdict.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
