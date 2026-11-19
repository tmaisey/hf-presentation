"""Spec: S-001, S-009

Static checks that the deck is one DRY, offline, endpoint-safe file (ADR-001).
Coverage: happy (layers present, slides parse) · edge (hex only in tokens, fonts embedded)
· negative (no per-slide style/script, no remote scripts, no risky JS, no branding).
"""

import re

from helper_deck import DECK, deck_source, parse_slides, slides_source


def test_deck_is_a_single_html_file():
    assert DECK.exists()
    assert deck_source().lstrip().lower().startswith("<!doctype html>")


def test_adr001_layers_are_each_defined_once():
    src = deck_source()
    assert src.count(":root {") == 1, "tokens defined once on :root"
    assert src.count('id="lift"') == 1 and src.count('id="arr"') == 1, "shared SVG defs once"
    assert len(re.findall(r"<script\b", src)) == 1, "exactly one engine script"
    assert "ADR: ADR-001" in src, "implementation carries its ADR marker"


def test_slides_contain_no_styles_or_scripts():
    """Slides are semantic content + data-attributes only: styling and behaviour live once."""
    region = slides_source()
    assert "<style" not in region and "<script" not in region
    assert not re.search(r'\sstyle\s*=', region), "no inline style attributes on slide markup"


def test_colours_are_tokens_not_literals_outside_root():
    src = deck_source()
    root = re.search(r":root \{.*?\n  \}", src, re.S).group(0)
    rest = src.replace(root, "")
    rest = re.sub(r"@font-face\s*\{.*?\}", "", rest, flags=re.S)
    hexes = set(re.findall(r"#[0-9A-Fa-f]{6}\b", rest))
    assert not hexes, f"hex colours must be tokens: {sorted(hexes)}"


def test_every_slide_has_id_chapter_kicker_and_title():
    slides = parse_slides()
    assert len(slides) >= 2
    ids = [s["attrs"].get("id") for s in slides]
    assert all(ids) and len(ids) == len(set(ids))
    for s in slides:
        assert s["attrs"].get("data-chapter"), s["attrs"]["id"]
        classes = [(t, (a.get("class") or "")) for t, a in s["tags"]]
        assert any("kicker" in c.split() for _, c in classes), s["attrs"]["id"]
        assert any(t == "h2" and "title" in c.split() for t, c in classes), s["attrs"]["id"]


def test_fonts_are_embedded_for_offline_use():
    src = deck_source()
    assert "fonts.googleapis.com" not in src and "fonts.gstatic.com" not in src
    assert re.search(r"@font-face\s*\{[^}]*Newsreader[^}]*url\(data:font/woff2;base64,", src, re.S)
    assert re.search(r"@font-face\s*\{[^}]*Inter[^}]*url\(data:font/woff2;base64,", src, re.S)


def test_no_remote_scripts_or_risky_patterns():
    src = deck_source()
    assert not re.search(r"<script[^>]+src=", src)
    code = re.search(r"<script\b[^>]*>(.*?)</script>", src, re.S).group(1)
    for bad in ("eval(", "atob(", "document.write", "new Function", "innerHTML"):
        assert bad not in code, bad
    assert "<form" not in src.lower() and 'type="password"' not in src


def test_no_corporate_branding():
    assert "deloitte" not in deck_source().lower()
