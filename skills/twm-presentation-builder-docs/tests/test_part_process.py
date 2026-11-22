"""Spec: PB-010

The process part and the AGENTS.md template it installs carry the development approach into a
deck project, so it persists across sessions without hooks.

Coverage: happy (part routed, phases in order, template sections, CLAUDE.md pointer, templates
present) · edge (existing AGENTS.md is merged with consent, not overwritten) · negative (no
incident-specific terms or hooks in what ships).
"""

import json
import re

from helper_skill import SKILL_DIR, local_links

PROCESS = SKILL_DIR / "process" / "PROCESS.md"
TPL = SKILL_DIR / "assets" / "templates" / "project"
INCIDENT_TERMS = re.compile(r"Hugging Face|OpenAI|swarm|deck-v2|ExploitGym|METR|S-0\d\d", re.I)


def _text(p):
    return p.read_text(encoding="utf-8")


def test_process_part_is_routed_from_skill_md():
    assert "process/PROCESS.md" in local_links(SKILL_DIR / "SKILL.md")


def test_process_phases_appear_in_order():
    t = _text(PROCESS).lower()
    phases = ["prd", "interview", "research", "storyboard", "prototype", "spec", "red", "green",
              "screenshot", "done"]
    pos = [t.find(p) for p in phases]
    assert -1 not in pos, dict(zip(phases, pos))
    assert pos == sorted(pos), "phases must be introduced in workflow order"


def test_agents_template_carries_the_binding_sections():
    t = _text(TPL / "AGENTS.md")
    for heading in ("## Docs & progressive disclosure", "## Workflow", "## Spec model",
                    "## Test authoring", "## Decisions (ADR)"):
        assert heading in t, heading
    assert "Definition of done" in t
    assert re.search(r"screenshots? of the\s+\*\*assembled\*\*", t), "the look-at-the-deck rule"
    assert re.search(r"one question at a time", t, re.I)


def test_agents_template_has_a_deck_project_index():
    t = _text(TPL / "AGENTS.md")
    for path in ("docs/PRD.md", "docs/SPEC.jsonl", "docs/STORYBOARD.md", "docs/DESIGN.md",
                 "docs/VOICE.md", "docs/research/", "tests/"):
        assert f"`{path}" in t, path


def test_claude_md_template_is_a_bare_pointer():
    assert _text(TPL / "CLAUDE.md").strip() == "@AGENTS.md"


def test_prd_and_spec_templates_present():
    assert "## Core message" in _text(TPL / "docs" / "PRD.md")
    line = json.loads(_text(TPL / "docs" / "SPEC.jsonl").splitlines()[0])
    assert list(line) == ["id", "status", "name", "depends_on", "description"]


def test_existing_agents_md_is_merged_with_consent_not_overwritten():
    """A deck project may already have an AGENTS.md (e.g. from a starter template)."""
    t = _text(PROCESS).lower()
    assert "merge" in t and "overwrite" in t and "ask" in t


def test_shipped_process_material_has_no_incident_terms():
    assert PROCESS.is_file() and TPL.is_dir()
    for p in [PROCESS, *TPL.rglob("*")]:
        if p.is_file():
            assert not INCIDENT_TERMS.search(_text(p)), p.name


def test_process_is_instructed_not_hooked():
    """PRD: no hooks; compliance is measured by the eval."""
    for p in [PROCESS, TPL / "AGENTS.md"]:
        assert not re.search(r"\bhooks?:", _text(p))
