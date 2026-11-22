"""Spec: PB-012

The research part makes every claim traceable: a sourcing method, research-index and note
templates, citation and flagging rules, verbatim-quote handling, and consent before research.

Coverage: happy (routed, rules for single-sourced/disputed/paraphrase, verbatim marks, consent,
both templates with their fields) · negative (templates topic-free; quotes never altered).
"""

import re

from helper_skill import INCIDENT_TERMS, fenced_blocks, read_part, section, skill_links

PART = "research/RESEARCH.md"


def _template(heading_re: str) -> str:
    blocks = fenced_blocks(section(read_part(PART), heading_re))
    assert blocks, f"a heading matching {heading_re!r} holds a fenced template"
    return "\n".join(blocks)


def test_research_part_is_routed_from_skill_md():
    assert PART in skill_links()


def test_asks_presenter_before_researching():
    low = read_part(PART).lower()
    assert re.search(r"ask[^.\n]*before[^.\n]*research", low)


def test_flagging_rules_cover_single_sourced_disputed_and_paraphrase():
    low = read_part(PART).lower()
    for flag in ("single-sourced", "disputed", "paraphrase"):
        assert flag in low, flag


def test_verbatim_quotes_mark_cuts_and_paraphrase_distinctly():
    text = read_part(PART)
    assert "verbatim" in text.lower()
    assert "[…]" in text, "our cuts are marked [...]"
    assert "{" in text and "}" in text, "paraphrase is braced, never shown as a quote"
    assert re.search(r"never[^.\n]*(alter|edit|correct|tidy)", text.lower())


def test_index_template_uses_the_four_column_row_schema():
    tpl = _template(r"index template").lower()
    for col in ("file", "description", "when to use", "when to update"):
        assert col in tpl, col


def test_note_template_records_source_quality_and_claims():
    tpl = _template(r"note template").lower()
    for field in ("question", "source", "url", "accessed", "claim", "quote", "open"):
        assert field in tpl, field
    for tag in ("[primary]", "[secondary]", "[weak]"):
        assert tag in tpl, tag


def test_templates_are_topic_free():
    text = _template(r"index template") + _template(r"note template")
    assert [t for t in INCIDENT_TERMS if t.lower() in text.lower()] == []


def test_long_part_has_a_contents_list():
    text = read_part(PART)
    if len(text.splitlines()) > 100:
        assert section(text, r"^contents$")
