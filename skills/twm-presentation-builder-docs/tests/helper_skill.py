"""Shared helpers for skill tests: locating the shipped skill and checking its structure."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[3]
SKILL_NAME = "twm-presentation-builder"
SKILL_DIR = REPO / "skills" / SKILL_NAME
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
TEXT_SUFFIXES = {".md", ".py", ".js", ".css", ".html", ".json", ".jsonl", ".txt", ".yaml", ".yml"}


def frontmatter(skill_md: Path) -> dict:
    """Parse the YAML frontmatter of a ``SKILL.md``.

    Args:
        skill_md: Path to the file.

    Returns:
        The frontmatter mapping, or an empty dict when the file has none.
    """
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return (yaml.safe_load(m.group(1)) or {}) if m else {}


def local_links(md: Path) -> list[str]:
    """Return the relative link targets in a markdown file (URLs and anchors excluded).

    Args:
        md: Markdown file to scan.

    Returns:
        Link targets without any ``#fragment``.
    """
    out = []
    for target in LINK_RE.findall(md.read_text(encoding="utf-8")):
        if re.match(r"^[a-z]+:", target) or target.startswith("#"):
            continue
        out.append(target.split("#", 1)[0])
    return out


def broken_links(skill_dir: Path) -> list[str]:
    """List links in ``SKILL.md`` whose target does not exist inside the skill.

    Args:
        skill_dir: The skill folder.

    Returns:
        One ``target`` string per broken link.
    """
    return [t for t in local_links(skill_dir / "SKILL.md") if not (skill_dir / t).exists()]


def unrouted_parts(skill_dir: Path) -> list[str]:
    """List markdown parts not linked directly from ``SKILL.md`` (the one-hop rule).

    Files under ``examples/`` and ``assets/`` are content, not parts, so they are exempt.

    Args:
        skill_dir: The skill folder.

    Returns:
        Relative paths of markdown files that ``SKILL.md`` does not link.
    """
    linked = {str(Path(t)) for t in local_links(skill_dir / "SKILL.md")}
    parts = []
    for md in skill_dir.rglob("*.md"):
        rel = md.relative_to(skill_dir)
        if rel.name == "SKILL.md" or rel.parts[0] in {"examples", "assets"}:
            continue
        if str(rel) not in linked:
            parts.append(str(rel))
    return parts


def escaping_paths(skill_dir: Path) -> list[str]:
    """Find references that point outside the skill folder.

    Flags ``../`` path segments and absolute home/user paths in any text file.

    Args:
        skill_dir: The skill folder.

    Returns:
        ``file: match`` strings, one per offending reference.
    """
    bad = []
    pat = re.compile(r"(?<![\w.])\.\./|/Users/|/home/|~/")
    for f in skill_dir.rglob("*"):
        if f.is_file() and f.suffix in TEXT_SUFFIXES:
            for m in pat.finditer(f.read_text(encoding="utf-8", errors="ignore")):
                bad.append(f"{f.relative_to(skill_dir)}: {m.group(0)}")
    return bad
