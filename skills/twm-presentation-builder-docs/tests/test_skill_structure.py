"""Spec: PB-001

The shipped skill folder is a valid, discoverable, self-contained skill whose SKILL.md routes
to every part in one hop.

Coverage: happy (frontmatter, trigger, size, routing, symlink) · edge (name rules, length caps)
· negative (checkers catch broken links, unrouted parts and escaping paths on bad fixtures).
"""

import re

from helper_skill import (REPO, SKILL_DIR, SKILL_NAME, broken_links, escaping_paths, frontmatter,
                          unrouted_parts)

SKILL_MD = SKILL_DIR / "SKILL.md"


def test_skill_md_has_name_matching_folder():
    fm = frontmatter(SKILL_MD)
    assert fm.get("name") == SKILL_NAME
    assert re.fullmatch(r"[a-z0-9-]{1,64}", fm["name"])
    assert "claude" not in fm["name"] and "anthropic" not in fm["name"]


def test_description_triggers_on_html_slide_requests():
    """The description is what the harness matches requests against, so it must name the trigger."""
    desc = frontmatter(SKILL_MD).get("description", "")
    assert 0 < len(desc) <= 1024
    low = desc.lower()
    assert "html" in low
    assert any(w in low for w in ("slides", "slide deck", "deck", "presentation"))
    assert not re.match(r"^(i|you|we)\b", low), "description is written in the third person"


def test_skill_md_stays_a_lean_router():
    assert len(SKILL_MD.read_text(encoding="utf-8").splitlines()) <= 250


def test_every_link_in_skill_md_resolves():
    assert broken_links(SKILL_DIR) == []


def test_every_part_is_one_hop_from_skill_md():
    assert unrouted_parts(SKILL_DIR) == []


def test_no_reference_leaves_the_skill_folder():
    """Self-contained so the folder can move to its own repo (PRD Requirements)."""
    assert SKILL_DIR.is_dir()
    assert escaping_paths(SKILL_DIR) == []


def test_local_trial_symlink_resolves_to_skill():
    link = REPO / ".claude" / "skills" / SKILL_NAME
    assert link.is_symlink(), "root skills/ is not a discovery path, so a symlink exposes it"
    assert link.resolve() == SKILL_DIR.resolve()
    assert not link.readlink().is_absolute(), "relative, so the repo works when cloned elsewhere"


def _fake_skill(tmp_path, body, files=()):
    d = tmp_path / SKILL_NAME
    d.mkdir()
    (d / "SKILL.md").write_text(f"---\nname: {SKILL_NAME}\ndescription: x\n---\n{body}\n")
    for rel, text in files:
        (d / rel).parent.mkdir(parents=True, exist_ok=True)
        (d / rel).write_text(text)
    return d


def test_checker_flags_a_broken_link(tmp_path):
    d = _fake_skill(tmp_path, "Read [voice](voice/VOICE.md).")
    assert broken_links(d) == ["voice/VOICE.md"]


def test_checker_flags_a_part_reached_only_through_another_part(tmp_path):
    d = _fake_skill(tmp_path, "Read [a](a/A.md).",
                    files=[("a/A.md", "See [b](../b/B.md)."), ("b/B.md", "deep")])
    assert unrouted_parts(d) == ["b/B.md"]


def test_checker_flags_paths_that_escape_the_folder(tmp_path):
    d = _fake_skill(tmp_path, "See ../../deck/deck-v2.html and /Users/someone/x.")
    assert {hit.split(": ", 1)[1] for hit in escaping_paths(d)} == {"../", "/Users/"}


def test_checker_ignores_examples_and_urls(tmp_path):
    d = _fake_skill(tmp_path, "See [docs](https://example.com/a.md).",
                    files=[("examples/hf/NOTE.md", "an excerpt")])
    assert unrouted_parts(d) == [] and broken_links(d) == []
