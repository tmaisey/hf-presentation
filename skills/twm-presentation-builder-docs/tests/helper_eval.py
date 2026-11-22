"""Shared helpers for the eval criterion-library and profile tests: paths, schema constants, readers."""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
from pathlib import Path

from helper_skill import REPO, SKILL_DIR

EVAL_DIR = SKILL_DIR / "eval"
CRITERIA = EVAL_DIR / "criteria.jsonl"
FLAWS = EVAL_DIR / "flaws.json"
PROFILES_DIR = EVAL_DIR / "profiles"
LOADER = EVAL_DIR / "criteria.py"
RESEARCH_DIR = REPO / "skills" / "twm-presentation-builder-docs" / "research"

FIELD_ORDER = ("id", "concern", "target", "scope", "evidence", "profile", "question", "form",
               "anchors", "flaws", "source")
ANCHOR_ORDER = ("level", "example", "why", "origin", "cite")
PROFILE_ORDER = ("id", "description", "weights", "gates", "params")
CONCERN_PREFIX = {
    "content": "CN", "research": "RS", "voice": "VC", "design-layout": "DL",
    "design-palette": "DP", "design-style": "DS", "architecture": "AR", "pptx": "PX",
    "process": "PR",
}
TARGETS = {"deck", "pptx", "repo"}
SCOPES = {"step", "slide", "deck", "spec"}
EVIDENCE = {"D", "S", "T"}
ORIGINS = {"reference-verdict", "reference-deck", "synthetic"}
PROFILE_IDS = {"editorial-talk", "pitch", "data-review", "internal-update"}

# Terms that tie text to the reference incident; allowed only in reference-* anchors.
INCIDENT_TERMS = re.compile(
    r"hugging\s*face|\bHF\b|openai|\bmetr\b|exploitgym|\bmodal\b|swarm|message board|"
    r"\bincident\b|\bs-\d+\b|deck-v2|cluster-admin|\bscorer\b",
    re.I,
)


def read_criteria(path: Path = CRITERIA) -> list[dict]:
    """Parse the criterion library, one JSON object per non-blank line, keeping key order.

    Args:
        path: The ``criteria.jsonl`` file.

    Returns:
        Criteria in file order.
    """
    assert path.is_file(), f"criterion library missing: {path.name}"
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [json.loads(ln) for ln in lines]


def read_flaws(path: Path = FLAWS) -> dict:
    """Parse the flaw taxonomy (tag → {group, description}).

    Args:
        path: The ``flaws.json`` file.

    Returns:
        The taxonomy mapping.
    """
    assert path.is_file(), f"flaw taxonomy missing: {path.name}"
    return json.loads(path.read_text(encoding="utf-8"))


def read_profiles(directory: Path = PROFILES_DIR) -> dict[str, dict]:
    """Parse every profile file, keyed by file stem.

    Args:
        directory: The ``profiles/`` folder.

    Returns:
        Profile mappings by stem.
    """
    assert directory.is_dir(), "profiles folder missing"
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(directory.glob("*.json"))}


def loader():
    """Import the shipped eval loader module by path (it is a script, not a package).

    Returns:
        The imported module.
    """
    assert LOADER.is_file(), f"eval loader missing: {LOADER.name}"
    spec = importlib.util.spec_from_file_location("skill_eval_criteria", LOADER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def copy_eval(tmp_path: Path) -> Path:
    """Copy the shipped eval folder to a scratch dir so a test can corrupt it.

    Args:
        tmp_path: pytest's temporary directory.

    Returns:
        The copied eval folder.
    """
    assert EVAL_DIR.is_dir(), "eval folder missing"
    dst = tmp_path / "eval"
    shutil.copytree(EVAL_DIR, dst)
    return dst


def write_criteria(path: Path, criteria: list[dict]) -> None:
    """Write criteria back as JSONL.

    Args:
        path: Destination ``criteria.jsonl``.
        criteria: Criteria to write, in order.
    """
    path.write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in criteria),
                    encoding="utf-8")


def research_source_numbers(note: str) -> set[int]:
    """Return the numbered entries in a research note's Sources list.

    Args:
        note: Note stem, e.g. ``llm-judge``.

    Returns:
        The source numbers the note defines.
    """
    text = (RESEARCH_DIR / f"{note}.md").read_text(encoding="utf-8")
    sources = text.split("## 4 · Sources", 1)[-1] if "## 4 · Sources" in text else text.split("## 4. Sources", 1)[-1]
    return {int(n) for n in re.findall(r"^(\d+)\. ", sources, re.M)}


def generic_text(criterion: dict) -> str:
    """Concatenate every field of a criterion that must stay free of incident terms.

    Everything except reference-* anchors counts: synthetic anchors must be generic too.

    Args:
        criterion: One criterion.

    Returns:
        The text to scan.
    """
    parts = [json.dumps({k: v for k, v in criterion.items() if k != "anchors"}, ensure_ascii=False)]
    parts += [json.dumps(a, ensure_ascii=False) for a in criterion.get("anchors", [])
              if not str(a.get("origin", "")).startswith("reference-")]
    return "\n".join(parts)
