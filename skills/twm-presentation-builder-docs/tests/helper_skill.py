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


INCIDENT_TERMS = ("Hugging Face", "OpenAI", "METR", "ExploitGym", "Artifactory", "swarm",
                  "mirror", "scorer", "zero-day")


def read_part(rel: str) -> str:
    """Read a shipped part of the skill.

    Args:
        rel: Path relative to the skill folder, e.g. ``voice/VOICE.md``.

    Returns:
        The file text.
    """
    return (SKILL_DIR / rel).read_text(encoding="utf-8")


def section(text: str, heading_re: str) -> str:
    """Return the body under the first markdown heading matching a pattern.

    The body runs to the next heading of the same or a higher level. Lines inside fenced code
    blocks are never headings, so a template's own ``#`` lines stay in its section.

    Args:
        text: Markdown text.
        heading_re: Case-insensitive regex matched against the heading text.

    Returns:
        The section body, or ``""`` when no heading matches.
    """
    lines, fenced, in_fence = text.splitlines(), [], False
    for line in lines:
        if line.startswith("```"):
            in_fence = not in_fence
            fenced.append(True)
        else:
            fenced.append(in_fence)
    for i, line in enumerate(lines):
        m = None if fenced[i] else re.match(r"^(#+)\s+(.*)$", line)
        if m and re.search(heading_re, m.group(2), re.I):
            level, body = len(m.group(1)), []
            for j in range(i + 1, len(lines)):
                h = None if fenced[j] else re.match(r"^(#+)\s", lines[j])
                if h and len(h.group(1)) <= level:
                    break
                body.append(lines[j])
            return "\n".join(body)
    return ""


def fenced_blocks(text: str) -> list[str]:
    """Return the contents of every fenced code block in markdown text.

    Args:
        text: Markdown text.

    Returns:
        One string per fenced block, fences excluded.
    """
    return re.findall(r"^```[^\n]*\n(.*?)^```", text, re.S | re.M)


def table_rows(text: str) -> list[str]:
    """Return markdown table data rows (header and separator rows excluded).

    Args:
        text: Markdown text.

    Returns:
        Each data row's line, stripped.
    """
    rows = []
    lines = [ln.strip() for ln in text.splitlines()]
    for i, line in enumerate(lines):
        is_row = line.startswith("|")
        if is_row and not re.fullmatch(r"\|[\s:|-]+\|", line):
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            is_header = re.fullmatch(r"\|[\s:|-]+\|", nxt) is not None
            if not is_header:
                rows.append(line)
    return rows


def skill_links() -> set[str]:
    """Return the set of local link targets in ``SKILL.md``."""
    return set(local_links(SKILL_DIR / "SKILL.md"))
