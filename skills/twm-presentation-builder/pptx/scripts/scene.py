# /// script
# requires-python = ">=3.12"
# dependencies = ["playwright>=1.49"]
# ///
"""PPTX scene extraction (PB-023): interface stub, built in the next commit."""

from __future__ import annotations

from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "scene.schema.json"


class SceneError(Exception):
    """A refusal: not a skill deck, or the engine did not start."""


def extract(deck, browser=None, size=(1920, 1080)) -> dict:
    """Stub: returns an empty scene."""
    return {"slides": [], "size": {}, "palette": {}}


def validate(doc, schema) -> list[str]:
    """Stub: accepts everything."""
    return []


def normalise_path(d: str) -> list[tuple]:
    """Stub: no segments."""
    return []


def main(argv=None) -> int:
    """Stub CLI."""
    return 0
