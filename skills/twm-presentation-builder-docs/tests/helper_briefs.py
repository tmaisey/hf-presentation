"""Shared helpers for the bundled-brief and feature-coverage tests: paths, schema constants, readers."""

from __future__ import annotations

import json
import re
from pathlib import Path

from helper_skill import SKILL_DIR

BRIEFS_DIR = SKILL_DIR / "evals" / "briefs"
BRIEFS_INDEX = BRIEFS_DIR / "BRIEFS.md"
BRIEF_ORDER = ("id", "title", "synthetic", "profile", "theme", "target", "gold_reference",
               "research", "audience", "length", "core_message", "constraints", "concerns",
               "features")
CONCERNS = {"content", "research", "voice", "design-layout", "design-palette", "design-style",
            "architecture", "pptx", "process"}
TARGET_MODES = {"build-from-brief", "existing-deck"}
FEATURE_ID = re.compile(r"^[a-z]+\.[a-z0-9-]+$")
URL_RE = re.compile(r"https://[^\s)>\"]+")

# Real organisations a synthetic brief must never take as its subject, and brands no brief may
# name (the second palette is never tied to an organisation: PRD Decisions).
REAL_ORGS = re.compile(
    r"\b(google|alphabet|microsoft|apple|amazon|meta platforms|facebook|netflix|tesla|nvidia|ibm|intel|"
    r"samsung|sony|siemens|oracle|salesforce|spotify|uber|airbnb|anthropic|openai|deepmind|"
    r"hugging\s*face|metr|redwood|bbc|nhs|unicef|nasa|tfl|transport for london|"
    r"deutsche bahn|network rail|greyhound|flixbus|tesco|walmart|ikea)\b",
    re.I,
)
BRANDS = re.compile(r"\b(google|alphabet|microsoft|apple|material design|android)\b", re.I)


def brief_dirs(root: Path = BRIEFS_DIR) -> list[Path]:
    """Return every brief folder (a sub-folder holding ``brief.json``).

    Args:
        root: The ``evals/briefs/`` folder.

    Returns:
        Brief folders, sorted by name.
    """
    assert root.is_dir(), "evals/briefs/ missing"
    return sorted(p.parent for p in root.glob("*/brief.json"))


def read_brief(folder: Path) -> dict:
    """Parse a brief's ``brief.json``, keeping key order.

    Args:
        folder: The brief folder.

    Returns:
        The brief mapping.
    """
    return json.loads((folder / "brief.json").read_text(encoding="utf-8"))


def read_briefs(root: Path = BRIEFS_DIR) -> dict[str, dict]:
    """Parse every brief, keyed by folder name.

    Args:
        root: The ``evals/briefs/`` folder.

    Returns:
        Brief mappings by folder name.
    """
    return {d.name: read_brief(d) for d in brief_dirs(root)}


def research_pack(brief: dict) -> Path:
    """Resolve a brief's research pack folder (paths in a brief are relative to the skill folder).

    Args:
        brief: One brief.

    Returns:
        The research pack folder.
    """
    return SKILL_DIR / brief["research"]


def pack_notes(pack: Path) -> list[Path]:
    """Return a research pack's notes: every markdown file except its ``RESEARCH.md`` index.

    Args:
        pack: The research pack folder.

    Returns:
        Note files, sorted.
    """
    return sorted(p for p in pack.glob("*.md") if p.name != "RESEARCH.md")


def pack_text(brief_folder: Path, brief: dict) -> str:
    """Concatenate everything a builder reads for a brief: its JSON and its research pack.

    Args:
        brief_folder: The brief folder (fixtures beside ``brief.json`` count too).
        brief: The parsed brief.

    Returns:
        All the brief's text.
    """
    files = [p for p in brief_folder.rglob("*") if p.is_file()]
    files += [p for p in research_pack(brief).rglob("*") if p.is_file()]
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(set(files)))


def quote_rows(pack: Path) -> list[list[str]]:
    """Return the cells of every row of every *Quotes* table in a pack.

    Args:
        pack: The research pack folder.

    Returns:
        One list of stripped cell strings per quote row (header and separator rows excluded).
    """
    rows = []
    for note in pack_notes(pack):
        text = note.read_text(encoding="utf-8")
        body = text.split("## Quotes", 1)[1] if "## Quotes" in text else ""
        body = re.split(r"^## ", body, maxsplit=1, flags=re.M)[0]
        for line in body.splitlines():
            line = line.strip()
            if not line.startswith("|") or re.fullmatch(r"\|[\s:|-]+\|", line):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if cells and cells[0] != "#":
                rows.append(cells)
    return rows
