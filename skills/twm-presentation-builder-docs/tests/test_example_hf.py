"""Spec: PB-014

The HF incident worked example: ``examples/hf-incident/EXAMPLE.md`` is linked from SKILL.md and maps
each skill part to a short cited excerpt from the HF deck project (PRD core message, storyboard rows,
voice pairs, design decisions, ADR-001, spec lines with their commit pattern, the v2 first-draft
failure), with before/after screenshots of the failure kept small.

Coverage: happy (entry linked; every excerpt in the table exists, is linked, names a real part and a
source; quoted text is verbatim from the HF deck's docs; commits cited exist with their subjects;
images are PNGs under budget) · edge (quotes cut with ``[…]`` match segment by segment; whitespace
re-wrapped) · negative (the verbatim checker rejects a paraphrase; the first-draft section must name
every recorded cause and rule, not just some).
"""

from __future__ import annotations

import re
import shutil
import subprocess

import pytest

from helper_skill import REPO, SKILL_DIR, escaping_paths, section, skill_links, table_rows

EX_DIR = SKILL_DIR / "examples" / "hf-incident"
ENTRY = EX_DIR / "EXAMPLE.md"
IMAGE_BUDGET = 2 * 1024 * 1024
SOURCE_RE = re.compile(r"\b((?:docs|design)/[\w./-]+\.(?:md|jsonl)|AGENTS\.md|README\.md)"
                       r"(?: at commit ([0-9a-f]{7,40}))?")
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _excerpt_files() -> list[str]:
    """Excerpt files named in the entry's table (second column, backticked or linked)."""
    files = []
    for row in table_rows(ENTRY.read_text(encoding="utf-8")):
        cells = [c.strip() for c in row.strip("|").split("|")]
        m = re.search(r"\(([\w./-]+\.md)\)", cells[1]) if len(cells) > 1 else None
        if m:
            files.append(m.group(1))
    return files


def _sources(text: str) -> list[tuple[str, str | None]]:
    """Source paths (and optional commits) named on an excerpt's ``Source:`` line(s)."""
    out = []
    for line in re.findall(r"^\*\*Sources?:\*\*(.*)$", text, re.M):
        out += SOURCE_RE.findall(line)
    return out


def _read_source(path: str, commit: str | None) -> str:
    if commit:
        if not shutil.which("git"):
            pytest.skip("git unavailable to read a historical source")
        return subprocess.run(["git", "show", f"{commit}:{path}"], cwd=REPO, capture_output=True,
                              text=True, check=True).stdout
    return (REPO / path).read_text(encoding="utf-8")


def _quotes(text: str) -> list[str]:
    """Blockquote paragraphs and fenced-block lines: the parts claimed to be verbatim."""
    quotes, para = [], []
    in_fence = False
    for line in text.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            if line.strip():
                quotes.append(line)
            continue
        if line.startswith(">"):
            body = line[1:].strip()
            if body:
                para.append(body)
            elif para:
                quotes.append(" ".join(para))
                para = []
        elif para:
            quotes.append(" ".join(para))
            para = []
    if para:
        quotes.append(" ".join(para))
    return quotes


def unquoted(quotes: list[str], source: str) -> list[str]:
    """Return the quotes (or their ``[…]``-separated segments) not found verbatim in ``source``.

    Args:
        quotes: Quoted text; ``[…]`` marks our cuts.
        source: The source text the quotes claim to come from.

    Returns:
        Each missing segment, collapsed to single spaces.
    """
    hay = _collapse(source)
    missing = []
    for q in quotes:
        for seg in q.split("[…]"):
            seg = _collapse(seg)
            if seg and seg not in hay:
                missing.append(seg)
    return missing


def _part(name: str) -> str:
    return (EX_DIR / name).read_text(encoding="utf-8")


def test_entry_is_linked_from_skill_md():
    assert "examples/hf-incident/EXAMPLE.md" in skill_links()
    assert ENTRY.is_file()


def test_entry_table_lists_the_promised_excerpts():
    files = _excerpt_files()
    assert len(files) >= 7, files
    for f in files:
        assert (EX_DIR / f).is_file(), f"{f} named in EXAMPLE.md but missing"


def test_entry_links_the_gold_deck_built_with_the_skill():
    text = ENTRY.read_text(encoding="utf-8")
    assert "(deck.html)" in text and "(slides.html)" in text


@pytest.mark.parametrize("name", [
    "prd-core-message.md", "storyboard-rows.md", "voice-pairs.md", "design-decisions.md",
    "adr-001.md", "spec-commits.md", "first-draft-failure.md"])
def test_excerpt_names_a_real_part_and_a_source(name):
    assert name in _excerpt_files(), f"{name} is not in the EXAMPLE.md table"
    text = _part(name)
    m = re.search(r"^\*\*Illustrates:\*\*(.*)$", text, re.M)
    assert m, "excerpt must say which skill part it illustrates"
    parts = re.findall(r"`([\w/.-]+\.md)`", m.group(1))
    assert parts and all(p in skill_links() for p in parts), parts
    srcs = _sources(text)
    assert srcs, "excerpt must cite a source"
    assert re.search(r"\d{1,2} Nov", re.search(r"^\*\*Sources?:\*\*.*$", text, re.M).group(0))


@pytest.mark.parametrize("name", [
    "prd-core-message.md", "storyboard-rows.md", "voice-pairs.md", "design-decisions.md",
    "adr-001.md", "spec-commits.md", "first-draft-failure.md"])
def test_quoted_text_is_verbatim_from_its_sources(name):
    text = _part(name)
    source = "\n".join(_read_source(p, c) for p, c in _sources(text))
    quotes = _quotes(text)
    assert quotes, "an excerpt quotes its source"
    assert unquoted(quotes, source) == []


def test_voice_pairs_are_verbatim_rejected_and_approved_copy():
    source = (REPO / "docs" / "VOICE.md").read_text(encoding="utf-8")
    pairs = []
    for row in table_rows(_part("voice-pairs.md")):
        cells = [c.strip() for c in row.strip("|").split("|")]
        pairs.append((cells[0], cells[1]))
    assert 4 <= len(pairs) <= 6, pairs
    for rejected, approved in pairs:
        assert unquoted([rejected, approved], source) == [], (rejected, approved)


def test_storyboard_rows_are_verbatim_table_rows():
    lines = {ln.strip() for ln in (REPO / "docs" / "STORYBOARD.md").read_text(encoding="utf-8")
             .splitlines()}
    rows = [r for r in table_rows(_part("storyboard-rows.md")) if re.match(r"\|\s*s-\d+", r)]
    assert 3 <= len(rows) <= 4, rows
    assert all(r in lines for r in rows), [r for r in rows if r not in lines]


def test_spec_commits_exist_with_their_subjects():
    if not shutil.which("git"):
        pytest.skip("git unavailable")
    rows = table_rows(_part("spec-commits.md"))
    shas = []
    for row in rows:
        m = re.search(r"`([0-9a-f]{7})`[^|]*\|\s*(.+?)\s*\|", row)
        if m:
            shas.append(m.groups())
    specs = set(re.findall(r'"id": "(S-0\d\d)"', _part("spec-commits.md")))
    assert len(specs) == 3, specs
    assert len(shas) >= 6, shas
    assert any(s.startswith("Red:") for _, s in shas), "the red-commit pattern is shown"
    for sha, subject in shas:
        real = subprocess.run(["git", "log", "-1", "--format=%s", sha], cwd=REPO,
                              capture_output=True, text=True)
        assert real.returncode == 0, f"{sha} not in history"
        assert _collapse(subject.strip("`")) in real.stdout, (sha, subject)


CAUSES = {
    "layout tests switched off": r"layout (tests?|guard)[^.\n]*(switched |turned )?off",
    "per-slide screenshots only": r"per-slide|component screenshots",
    "no prototypes": r"no prototype",
    "briefs led by merge-safety": r"merge-safety",
    "16:9-only tests": r"16:9",
}
RULES = {
    "always-on layout guard": r"layout guard",
    "look at assembled screenshots": r"assembled",
    "prototype first": r"prototype",
    "briefs lead with quality": r"briefs? lead",
}


def _missing(body: str, wanted: dict[str, str]) -> list[str]:
    return [name for name, pat in wanted.items() if not re.search(pat, body, re.I)]


def test_first_draft_names_every_recorded_cause_and_rule():
    text = _part("first-draft-failure.md")
    assert _missing(section(text, r"^Causes"), CAUSES) == []
    assert _missing(section(text, r"^Rules"), RULES) == []


def test_first_draft_shows_before_and_after_screenshots():
    text = _part("first-draft-failure.md")
    imgs = re.findall(r"!\[[^\]]*\]\(([^)]+\.png)\)", text)
    assert any("before" in i for i in imgs) and any("after" in i for i in imgs), imgs
    for i in imgs:
        assert (EX_DIR / i).is_file(), i


def test_images_are_png_and_under_budget():
    imgs = sorted((EX_DIR / "images").glob("*"))
    assert imgs, "the example carries screenshots"
    for p in imgs:
        assert p.suffix == ".png" and p.read_bytes()[:8] == PNG_MAGIC, p.name
    assert sum(p.stat().st_size for p in imgs) < IMAGE_BUDGET


def test_example_points_nowhere_outside_the_skill():
    assert [h for h in escaping_paths(SKILL_DIR) if h.startswith("examples/")] == []


def test_checker_rejects_a_paraphrase_but_accepts_marked_cuts():
    source = "Reward is an incomplete proxy for actual desired behaviour, as the deck says."
    assert unquoted(["Reward is an incomplete proxy for actual\n desired behaviour"], source) == []
    assert unquoted(["Reward is an incomplete […] desired behaviour"], source) == []
    assert unquoted(["Reward is a partial proxy for desired behaviour"], source) != []


def test_checker_flags_a_missing_cause():
    body = "The layout guard was switched off. No prototypes. 16:9 only."
    assert set(_missing(body, CAUSES)) == {"per-slide screenshots only", "briefs led by merge-safety"}
