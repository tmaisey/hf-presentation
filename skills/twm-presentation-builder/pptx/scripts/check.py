# /// script
# requires-python = ">=3.12"
# dependencies = ["python-pptx>=1.0.2", "lxml>=5"]
# ///
"""PPTX checks (PB-024): interface stub for the red commit."""

from __future__ import annotations

import sys

CRITERIA: tuple[str, ...] = ()


def verdicts(pptx, scene=None, report=None) -> list[dict]:
    """Stub: no verdicts."""
    return []


def validate_package(path) -> list[str]:
    """Stub: always reports one problem."""
    return ["not implemented"]


def reflow(pptx, out, template=None):
    """Stub: returns the input unchanged."""
    return pptx


def resolve_colour(slide, run, slot=None):
    """Stub."""
    return None


def resolve_font(slide, run):
    """Stub."""
    return None


def main(argv=None) -> int:
    print("check: not implemented", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
