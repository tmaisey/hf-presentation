"""Spec: PB-011

The content part teaches the storyboard method and ships a fill-in template that is generic
(topic-free), so content can be swapped without touching design.

Coverage: happy (routed from SKILL.md, method covers codes/chapters/timings/approval marks,
template carries every per-slide field and a timing total) · edge (contents list once long)
· negative (no incident-specific terms in the template).
"""

import re

from helper_skill import INCIDENT_TERMS, fenced_blocks, read_part, section, skill_links

PART = "content/STORYBOARD.md"


def _template() -> str:
    blocks = fenced_blocks(section(read_part(PART), r"^template$"))
    assert blocks, "a '## Template' section holds the fill-in template in a fenced block"
    return "\n".join(blocks)


def test_storyboard_part_is_routed_from_skill_md():
    assert PART in skill_links()


def test_method_defines_core_message_codes_chapters_timings_and_approval_marks():
    method = read_part(PART)
    assert re.search(r"\bM1\b", method), "core-message codes M1, M2…"
    for word in ("core message", "chapter", "timing", "approv"):
        assert word in method.lower(), word
    # title approval marks: approved / pending / new each have a distinct glyph
    assert all(mark in method for mark in ("✓", "◇", "✎"))


def test_template_carries_every_per_slide_field():
    tpl = _template().lower()
    for field in ("title", "visual", "overlay", "source", "serves", "time", "notes"):
        assert field in tpl, field
    assert re.search(r"\bm1\b", tpl), "template lists the core-message codes to fill in"


def test_template_has_a_running_order_with_a_total_time():
    tpl = _template()
    assert re.search(r"\|\s*#\s*\|", tpl), "running-order table with a slide-number column"
    assert "total" in tpl.lower()


def test_template_is_topic_free():
    """The template must not leak the HF incident: content is swapped per talk."""
    tpl = _template()
    leaked = [t for t in INCIDENT_TERMS if t.lower() in tpl.lower()]
    assert leaked == []


def test_long_part_has_a_contents_list():
    text = read_part(PART)
    if len(text.splitlines()) > 100:
        assert section(text, r"^contents$"), "parts over 100 lines open with a contents list"
