"""Shared test helpers: the deck's path and the presentation-builder skill's shipped tools.

Set ``DECK`` to the deck path the project's ``AGENTS.md`` index names (house rules win over the
default). The skill is found from ``PRESENTATION_SKILL_DIR``, else the project's or the user's
``.claude/skills/<skill>/`` folder.
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
from functools import cache
from pathlib import Path

SKILL_NAME = "twm-presentation-builder"
ROOT = Path(__file__).resolve().parents[1]
DECK = ROOT / "deck" / "deck.html"
REVIEW_SIZES = ((1920, 1080), (1280, 720), (1288, 598))


def skill_dir() -> Path:
    """Locate the installed skill folder.

    Returns:
        The folder holding the skill's ``scripts/``.

    Raises:
        RuntimeError: When no candidate holds ``scripts/layout_guard.py``.
    """
    env = os.environ.get("PRESENTATION_SKILL_DIR")
    tries = ([Path(env)] if env else []) + [ROOT / ".claude" / "skills" / SKILL_NAME,
                                            Path.home() / ".claude" / "skills" / SKILL_NAME]
    for d in tries:
        if (d / "scripts" / "layout_guard.py").is_file():
            return d
    raise RuntimeError(f"skill {SKILL_NAME} not found: set PRESENTATION_SKILL_DIR (tried {', '.join(map(str, tries))})")


@cache
def tool(name: str):
    """Import one of the skill's scripts by path (``scripts/`` is not a package).

    Args:
        name: Script name without ``.py``, e.g. ``"layout_guard"``.

    Returns:
        The imported module.
    """
    spec = importlib.util.spec_from_file_location(f"skill_{name}", skill_dir() / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def slide_ids(deck: Path = DECK) -> list[str]:
    """Slide ids in deck order, read from the markup (so tests can be parameterised at collection).

    Args:
        deck: Deck HTML file.

    Returns:
        Ids of every ``section.slide``; empty when the deck does not exist yet.
    """
    if not deck.is_file():
        return []
    return re.findall(r'<section\b[^>]*\bclass="slide\b[^"]*"[^>]*\bid="([\w-]+)"', deck.read_text(encoding="utf-8"))
