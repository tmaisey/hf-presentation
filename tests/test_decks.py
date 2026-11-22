"""Spec: S-017

Two decks, one suite: v2 is a new file on the shared architecture and v1 stays frozen.
Coverage: happy (--deck selects the file under test; v2 opens on the approved title slide) ·
edge (v2 shares v1's engine contract but is its own file) · negative (v1 bytes never change).
"""

import hashlib
import os

import pytest

from helper_deck import DECK, DECK_FILES, open_deck, parse_slides

V1_SHA256 = "5fbe1007900382654573d8b8a669850ffaa7e89740f02146037411dece029466"  # v1 at S-016 close


def test_v1_deck_is_byte_unchanged():
    """v1 is frozen reference: any edit (even whitespace) is a regression."""
    assert hashlib.sha256(DECK_FILES["v1"].read_bytes()).hexdigest() == V1_SHA256


def test_suite_targets_the_selected_deck():
    assert DECK == DECK_FILES[os.environ["HF_DECK"]]


@pytest.mark.deck("v2")
def test_v2_is_its_own_file_on_the_shared_engine():
    v1, v2 = (DECK_FILES[k].read_text(encoding="utf-8") for k in ("v1", "v2"))
    assert v2 != v1
    assert "ADR: ADR-001" in v2 and "<!-- SLIDES:BEGIN -->" in v2
    engine = lambda s: s[s.index("<script>"):]  # noqa: E731
    assert "window.deck" in engine(v2)


@pytest.mark.deck("v2")
def test_v2_opens_on_the_approved_title_slide(page):
    first = parse_slides()[0]
    assert first["attrs"]["id"] == "s-1" and "data-ambient" in first["attrs"]
    assert first["title"].strip(), "approved title copy is S-034's (test_v2_title.py)"
    assert open_deck(page) == []
