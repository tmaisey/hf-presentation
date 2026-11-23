# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Load and validate the eval criterion library and deck-type profiles.

Runner-agnostic: any runner (generic subagents now, an API later) calls ``resolve`` to get the
weighted, gated criteria for a profile, each carrying its full definition.

Usage::

    uv run eval/criteria.py check              # validate library, taxonomy and every profile
    uv run eval/criteria.py resolve pitch      # print a profile's resolved criteria as JSON
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
FIELD_ORDER = ("id", "concern", "target", "scope", "evidence", "profile", "question", "form",
               "anchors", "flaws", "source")
ANCHOR_FIELDS = ("level", "example", "why", "origin", "cite")
PROFILE_FIELDS = ("id", "description", "weights", "gates", "params")
CONCERN_PREFIX = {
    "content": "CN", "research": "RS", "voice": "VC", "design-layout": "DL",
    "design-palette": "DP", "design-style": "DS", "architecture": "AR", "pptx": "PX",
    "process": "PR",
}
TARGETS = {"deck", "pptx", "repo"}
SCOPES = {"step", "slide", "deck", "spec"}
EVIDENCE = {"D", "S", "T"}
ORIGINS = {"reference-verdict", "reference-deck", "synthetic"}
SCALE_LEVELS = [str(n) for n in range(6)]


class EvalFormatError(ValueError):
    """Raised when the library, taxonomy or a profile breaks the documented format."""


def _fail(where: str, msg: str) -> None:
    raise EvalFormatError(f"{where}: {msg}")


def _check_form(cid: str, crit: dict) -> None:
    form = crit["form"]
    if not isinstance(form, dict) or form.get("type") not in {"binary", "scale"}:
        _fail(cid, "form.type must be 'binary' or 'scale'")
    if form["type"] == "binary":
        if set(form) != {"type", "pass", "fail"} or not all(
                isinstance(form[k], str) and form[k].strip() for k in ("pass", "fail")):
            _fail(cid, "binary form needs non-empty 'pass' and 'fail' descriptors")
    else:
        if crit["evidence"] == "D":
            _fail(cid, "deterministic criteria are binary")
        levels = form.get("levels")
        if set(form) != {"type", "levels"} or not isinstance(levels, dict) or list(levels) != SCALE_LEVELS:
            _fail(cid, "scale form needs 'levels' keyed '0'..'5' in order")
        texts = [str(v).strip() for v in levels.values()]
        if not all(texts) or len(set(texts)) != 6:
            _fail(cid, "every scale level needs its own descriptor")


def _check_anchors(cid: str, crit: dict) -> None:
    anchors = crit["anchors"]
    if not isinstance(anchors, list):
        _fail(cid, "anchors must be a list")
    binary = crit["form"]["type"] == "binary"
    for a in anchors:
        if tuple(a) not in (ANCHOR_FIELDS, ANCHOR_FIELDS[:-1]):
            _fail(cid, f"anchor fields must be {ANCHOR_FIELDS} (cite optional)")
        if a["origin"] not in ORIGINS:
            _fail(cid, f"anchor origin {a['origin']!r} unknown")
        if a["origin"] == "reference-verdict" and not str(a.get("cite", "")).strip():
            _fail(cid, "a reference-verdict anchor must cite where the verdict is recorded")
        ok = a["level"] in {"pass", "fail"} if binary else (
            type(a["level"]) is int and 0 <= a["level"] <= 5)
        if not ok:
            _fail(cid, f"anchor level {a['level']!r} does not fit the form")
    if crit["evidence"] != "D":
        levels = [a["level"] for a in anchors]
        if binary and not {"pass", "fail"} <= set(levels):
            _fail(cid, "judged binary criteria need a pass and a fail anchor")
        if not binary and not (any(lv >= 4 for lv in levels) and any(lv <= 1 for lv in levels)):
            _fail(cid, "judged scale criteria need a high (≥4) and a low (≤1) anchor")


def load_flaws(eval_dir: Path = EVAL_DIR) -> dict:
    """Load the flaw taxonomy.

    Args:
        eval_dir: Folder holding ``flaws.json``.

    Returns:
        Mapping of flaw tag to ``{group, description}``.

    Raises:
        EvalFormatError: If an entry lacks a group or description.
    """
    flaws = json.loads((Path(eval_dir) / "flaws.json").read_text(encoding="utf-8"))
    for tag, entry in flaws.items():
        if not re.fullmatch(r"[a-z]+(-[a-z]+)*", tag) or set(entry) != {"group", "description"}:
            _fail(f"flaws.json:{tag}", "tag must be kebab-case with exactly group + description")
    return flaws


def load_library(eval_dir: Path = EVAL_DIR) -> dict[str, dict]:
    """Load and validate ``criteria.jsonl`` against the flaw taxonomy.

    Args:
        eval_dir: Folder holding ``criteria.jsonl`` and ``flaws.json``.

    Returns:
        Criteria keyed by id, in file order.

    Raises:
        EvalFormatError: On any schema breach (field order, enums, forms, anchors, flaws, ids).
    """
    eval_dir = Path(eval_dir)
    flaws = load_flaws(eval_dir)
    lib: dict[str, dict] = {}
    lines = (eval_dir / "criteria.jsonl").read_text(encoding="utf-8").splitlines()
    for n, line in enumerate(lines, 1):
        if not line.strip():
            continue
        where = f"criteria.jsonl:{n}"
        try:
            crit = json.loads(line)
        except json.JSONDecodeError as e:
            raise EvalFormatError(f"{where}: invalid JSON ({e})") from e
        if tuple(crit) != FIELD_ORDER:
            _fail(where, f"fields must be exactly, in order: {FIELD_ORDER}")
        cid = crit["id"]
        if cid in lib:
            _fail(where, f"duplicate id {cid}")
        if crit["concern"] not in CONCERN_PREFIX:
            _fail(cid, f"unknown concern {crit['concern']!r}")
        if not re.fullmatch(rf"{CONCERN_PREFIX[crit['concern']]}-\d\d", cid):
            _fail(cid, f"id must be {CONCERN_PREFIX[crit['concern']]}-NN for its concern")
        for field, allowed in (("target", TARGETS), ("scope", SCOPES), ("evidence", EVIDENCE)):
            if crit[field] not in allowed:
                _fail(cid, f"{field} {crit[field]!r} not in {sorted(allowed)}")
        if crit["scope"] == "spec" and crit["target"] != "repo":
            _fail(cid, "scope 'spec' applies only to repo targets")
        if crit["profile"] is not None and not re.fullmatch(r"[a-z]+(-[a-z]+)*", str(crit["profile"])):
            _fail(cid, "profile must be null or a profile id")
        if not str(crit["question"]).strip().endswith("?"):
            _fail(cid, "question must be a question")
        _check_form(cid, crit)
        _check_anchors(cid, crit)
        if not crit["flaws"] or set(crit["flaws"]) - set(flaws):
            _fail(cid, f"flaws must be known tags; unknown: {sorted(set(crit['flaws']) - set(flaws))}")
        if not crit["source"]:
            _fail(cid, "source must cite at least one reference")
        lib[cid] = crit
    return lib


def load_profile(path: Path, library: dict[str, dict]) -> dict:
    """Load and validate one profile against the library.

    Args:
        path: The profile's JSON file (stem = profile id).
        library: Output of ``load_library``.

    Returns:
        The profile mapping.

    Raises:
        EvalFormatError: On an unknown id, a bad weight, a gate that is unselected or graded, a
            borrowed profile-only criterion, or params for an unselected criterion.
    """
    path = Path(path)
    prof = json.loads(path.read_text(encoding="utf-8"))
    where = path.name
    if tuple(prof) not in (PROFILE_FIELDS, PROFILE_FIELDS[:-1]):
        _fail(where, f"fields must be, in order: {PROFILE_FIELDS} (params optional)")
    if prof["id"] != path.stem:
        _fail(where, "id must match the file name")
    weights, gates, params = prof["weights"], prof["gates"], prof.get("params", {})
    unknown = sorted((set(weights) | set(gates) | set(params)) - set(library))
    if unknown:
        _fail(where, f"unknown criterion id(s): {', '.join(unknown)}")
    for cid, w in weights.items():
        if type(w) is not int or not 1 <= w <= 3:
            _fail(where, f"{cid} weight {w!r} must be an integer 1–3")
        owner = library[cid]["profile"]
        if owner not in (None, prof["id"]):
            _fail(where, f"{cid} belongs to profile {owner!r}")
    if len(gates) != len(set(gates)):
        _fail(where, "duplicate gate")
    for g in gates:
        if g not in weights:
            _fail(where, f"gate {g} is not selected")
        if library[g]["form"]["type"] != "binary":
            _fail(where, f"gate {g} must be a binary criterion")
    for cid, p in params.items():
        if cid not in weights or not isinstance(p, dict) or not p:
            _fail(where, f"params for {cid} must be a non-empty object on a selected criterion")
    return prof


def load_profiles(eval_dir: Path = EVAL_DIR) -> dict[str, dict]:
    """Load every profile and check each profile-only criterion is selected by its owner.

    Args:
        eval_dir: Folder holding ``criteria.jsonl``, ``flaws.json`` and ``profiles/``.

    Returns:
        Profiles keyed by id.

    Raises:
        EvalFormatError: On any profile error or an orphaned profile-only criterion.
    """
    eval_dir = Path(eval_dir)
    lib = load_library(eval_dir)
    profs = {p.stem: load_profile(p, lib) for p in sorted((eval_dir / "profiles").glob("*.json"))}
    for cid, c in lib.items():
        if c["profile"] is not None and cid not in profs.get(c["profile"], {}).get("weights", {}):
            _fail(cid, f"profile-only criterion not selected by profile {c['profile']!r}")
    return profs


def resolve(profile: dict, library: dict[str, dict]) -> list[dict]:
    """Expand a profile into the criteria a runner judges.

    Args:
        profile: Output of ``load_profile``.
        library: Output of ``load_library``.

    Returns:
        One dict per selected criterion: the full definition plus ``weight``, ``gate`` and
        ``params`` (empty dict when the profile sets none), in library order.
    """
    return [dict(c, weight=profile["weights"][cid], gate=cid in profile["gates"],
                 params=profile.get("params", {}).get(cid, {}))
            for cid, c in library.items() if cid in profile["weights"]]


def main(argv: list[str]) -> int:
    """CLI entry point: ``check`` or ``resolve <profile>``.

    Args:
        argv: Arguments after the script name.

    Returns:
        Process exit code.
    """
    try:
        if argv[:1] == ["check"]:
            profs = load_profiles()
            print(f"ok: {len(load_library())} criteria, {len(profs)} profiles")
            return 0
        if argv[:1] == ["resolve"] and len(argv) == 2:
            lib = load_library()
            prof = load_profile(EVAL_DIR / "profiles" / f"{argv[1]}.json", lib)
            print(json.dumps(resolve(prof, lib), ensure_ascii=False, indent=1))
            return 0
    except EvalFormatError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
