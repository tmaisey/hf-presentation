"""Spec: PB-019

Bundled test briefs under ``evals/briefs/<id>/``: four fixed briefs (the HF subset with its gold
reference, the same subset re-themed in the second palette, a synthetic pitch and a synthetic data
review), each a machine-readable ``brief.json`` plus a small fixed research pack, so the skill can be
iterated on against the same inputs every time.

Coverage: happy (exactly four briefs, schema and field order, profiles resolve through the shipped
loader, theme names shipped token files, gold references exist inside the skill, research packs hold
3–6 sourced notes with an index, a disputed flag and a verbatim quote; index routed from SKILL.md and
named in EVAL.md) · edge (the bright brief re-themes the HF gold deck in place; HF verbatim quotes
match the gold markup; the routing exemption covers brief folders only) · negative (no real
organisation or incident term in synthetic briefs, no brand anywhere, synthetic sources only on
reserved example domains, no gold reference for synthetic briefs; a bare ``.md`` elsewhere in
``evals/`` is still flagged as unrouted).
"""

from __future__ import annotations

import html
import re
from urllib.parse import urlparse

import pytest

from helper_briefs import (BRANDS, BRIEF_ORDER, BRIEFS_DIR, BRIEFS_INDEX, CONCERNS, FEATURE_ID,
                           REAL_ORGS, TARGET_MODES, URL_RE, brief_dirs, pack_notes, pack_text,
                           quote_rows, read_briefs, research_pack)
from helper_eval import EVAL_MD, INCIDENT_TERMS, loader
from helper_skill import SKILL_DIR, SKILL_NAME, escaping_paths, skill_links, unrouted_parts

TOKENS = SKILL_DIR / "assets" / "tokens"
GOLD_SLIDES = SKILL_DIR / "examples" / "hf-incident" / "slides.html"
EXPECTED_PROFILE = {"hf-subset": "editorial-talk", "hf-subset-bright": "editorial-talk",
                    "pitch": "pitch", "data-review": "data-review"}


def _kind(brief_id: str) -> str:
    """Map a brief id to its kind: the HF ids are fixed; the synthetic ones carry a topic suffix."""
    if brief_id in ("hf-subset", "hf-subset-bright"):
        return brief_id
    return brief_id.split("-", 2)[0] if brief_id.startswith("pitch-") else "data-review"


@pytest.fixture(scope="module")
def briefs():
    return read_briefs()


def test_exactly_the_four_bundled_briefs_ship(briefs):
    ids = sorted(briefs)
    assert len(ids) == 4, ids
    assert {"hf-subset", "hf-subset-bright"} <= set(ids)
    assert sum(re.fullmatch(r"pitch-[a-z0-9-]+", i) is not None for i in ids) == 1
    assert sum(re.fullmatch(r"data-review-[a-z0-9-]+", i) is not None for i in ids) == 1


def test_brief_fields_in_order_and_id_matches_folder(briefs):
    for folder, b in briefs.items():
        assert tuple(b) == BRIEF_ORDER, folder
        assert b["id"] == folder


def test_brief_field_types(briefs):
    for bid, b in briefs.items():
        assert isinstance(b["title"], str) and b["title"], bid
        assert isinstance(b["synthetic"], bool), bid
        assert isinstance(b["audience"], str) and len(b["audience"]) > 20, bid
        assert isinstance(b["length"]["minutes"], int) and b["length"]["minutes"] > 0, bid
        assert isinstance(b["length"]["slides"], int) and 3 <= b["length"]["slides"] <= 15, bid
        codes = [m["code"] for m in b["core_message"]]
        assert codes and all(re.fullmatch(r"M\d", c) for c in codes), bid
        assert len(set(codes)) == len(codes), bid
        assert all(len(m["text"]) > 20 for m in b["core_message"]), bid
        assert b["constraints"] and all(isinstance(c, str) and c for c in b["constraints"]), bid
        assert b["concerns"] and set(b["concerns"]) <= CONCERNS, bid
        assert len(set(b["concerns"])) == len(b["concerns"]), bid
        assert b["features"] and all(FEATURE_ID.fullmatch(f) for f in b["features"]), bid
        assert len(set(b["features"])) == len(b["features"]), bid


def test_profiles_exist_and_resolve_through_the_shipped_loader(briefs):
    mod = loader()
    library = mod.load_library()
    profiles = mod.load_profiles()
    for bid, b in briefs.items():
        assert b["profile"] == EXPECTED_PROFILE[_kind(bid)], bid
        assert b["profile"] in profiles, bid
        assert mod.resolve(profiles[b["profile"]], library), bid


def test_theme_names_shipped_palette_and_style(briefs):
    for bid, b in briefs.items():
        assert tuple(b["theme"]) == ("palette", "style"), bid
        assert (TOKENS / "palettes" / f"{b['theme']['palette']}.tokens.json").is_file(), bid
        assert (TOKENS / "styles" / f"{b['theme']['style']}.tokens.json").is_file(), bid


def _inside_skill(rel: str) -> bool:
    return not rel.startswith(("/", "~")) and ".." not in rel.split("/")


def test_targets_are_well_formed(briefs):
    for bid, b in briefs.items():
        t = b["target"]
        assert t["mode"] in TARGET_MODES, bid
        if t["mode"] == "existing-deck":
            assert tuple(t) == ("mode", "deck", "task"), bid
            assert _inside_skill(t["deck"]) and (SKILL_DIR / t["deck"]).is_file(), bid
            assert len(t["task"]) > 20, bid
        else:
            assert tuple(t) == ("mode",), bid


def test_gold_references_exist_inside_the_skill(briefs):
    for bid, b in briefs.items():
        gold = b["gold_reference"]
        assert isinstance(gold, list), bid
        if b["synthetic"]:
            assert gold == [], f"{bid}: a synthetic brief has no gold reference"
            continue
        assert gold, bid
        for rel in gold:
            assert _inside_skill(rel), (bid, rel)
            assert (SKILL_DIR / rel).is_file(), (bid, rel)


def test_hf_briefs_are_real_and_the_others_synthetic(briefs):
    for bid, b in briefs.items():
        assert b["synthetic"] is (_kind(bid) in ("pitch", "data-review")), bid


def test_bright_brief_rethemes_the_hf_gold_deck_in_place(briefs):
    """Same subset, second palette: only the palette differs, so the start is the HF gold deck."""
    hf, bright = briefs["hf-subset"], briefs["hf-subset-bright"]
    assert bright["target"]["mode"] == "existing-deck"
    assert bright["target"]["deck"] in hf["gold_reference"]
    assert bright["theme"]["style"] == hf["theme"]["style"]
    assert bright["theme"]["palette"] != hf["theme"]["palette"]
    assert bright["research"] == hf["research"], "one subset, one research pack (DRY)"
    assert any(p.endswith("deck-bright.html") for p in bright["gold_reference"])
    assert bright["core_message"] == hf["core_message"]


def test_research_packs_have_three_to_six_sourced_notes_and_an_index(briefs):
    for bid, b in briefs.items():
        pack = research_pack(b)
        assert _inside_skill(b["research"]) and b["research"].startswith("evals/briefs/"), bid
        assert pack.is_dir(), bid
        notes = pack_notes(pack)
        assert 3 <= len(notes) <= 6, (bid, [n.name for n in notes])
        index = (pack / "RESEARCH.md").read_text(encoding="utf-8")
        for note in notes:
            text = note.read_text(encoding="utf-8")
            assert note.name in index, (bid, note.name, "index must list every note")
            assert URL_RE.search(text), (bid, note.name, "every note cites a URL")
            assert re.search(r"\*\*\[(primary|secondary|weak)\]\*\*|\[(FOR|AGAINST)\]\[(primary|secondary|weak)\]",
                             text), (bid, note.name, "sources carry quality tags")


def test_research_packs_flag_a_disputed_claim(briefs):
    for bid, b in briefs.items():
        text = "\n".join(n.read_text(encoding="utf-8") for n in pack_notes(research_pack(b)))
        assert re.search(r"\bdisputed:", text, re.I), bid
        assert "[AGAINST]" in text, f"{bid}: mixed evidence shows as [AGAINST]"


def test_research_packs_carry_a_verbatim_quote(briefs):
    for bid, b in briefs.items():
        rows = quote_rows(research_pack(b))
        verbatim = [r for r in rows if r[-1].startswith("verbatim")]
        assert verbatim, bid
        for r in verbatim:
            assert re.fullmatch(r"[\"“].+[\"”]", r[2]), (bid, r)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def test_hf_verbatim_quotes_match_the_gold_markup(briefs):
    """The HF pack is drawn from the gold deck's cited notes, so its quotes must read identically."""
    gold = _norm(re.sub(r"<[^>]+>", "", GOLD_SLIDES.read_text(encoding="utf-8")))
    for r in quote_rows(research_pack(briefs["hf-subset"])):
        if r[-1].startswith("verbatim"):
            q = _norm(r[2].strip("\"“”"))
            assert all(seg.strip() in gold for seg in q.split("[…]")), r


def test_synthetic_packs_are_marked_and_use_reserved_domains(briefs):
    for bid, b in briefs.items():
        if not b["synthetic"]:
            continue
        for note in [*pack_notes(research_pack(b)), research_pack(b) / "RESEARCH.md"]:
            text = note.read_text(encoding="utf-8")
            assert re.search(r"^> \*\*Synthetic\*\*", text, re.M), (bid, note.name)
            for url in URL_RE.findall(text):
                host = urlparse(url).hostname or ""
                assert host == "example.org" or host.endswith(".example.org"), (bid, url)


def test_synthetic_briefs_name_no_real_organisation_or_incident_term():
    for folder in brief_dirs():
        b = read_briefs()[folder.name]
        if not b["synthetic"]:
            continue
        text = pack_text(folder, b)
        assert not REAL_ORGS.findall(text), (folder.name, REAL_ORGS.findall(text))
        assert not INCIDENT_TERMS.findall(text), (folder.name, INCIDENT_TERMS.findall(text))


def test_no_brief_names_a_brand():
    """The second palette is never tied to an organisation (PRD Decisions); nor is any brief."""
    for folder in brief_dirs():
        text = pack_text(folder, read_briefs()[folder.name])
        assert not BRANDS.findall(text), (folder.name, BRANDS.findall(text))


def test_briefs_never_point_outside_the_skill():
    assert [hit for hit in escaping_paths(SKILL_DIR) if hit.startswith("evals/briefs/")] == []


def test_briefs_index_is_routed_and_lists_every_brief(briefs):
    assert "evals/briefs/BRIEFS.md" in skill_links()
    index = BRIEFS_INDEX.read_text(encoding="utf-8")
    for bid in briefs:
        assert f"`{bid}`" in index, bid
    assert "evals/briefs/BRIEFS.md" in EVAL_MD.read_text(encoding="utf-8")


def _fake_skill(tmp_path, files):
    d = tmp_path / SKILL_NAME
    d.mkdir()
    (d / "SKILL.md").write_text(f"---\nname: {SKILL_NAME}\ndescription: x\n---\nRead [b](evals/briefs/BRIEFS.md).\n")
    for rel in files:
        (d / rel).parent.mkdir(parents=True, exist_ok=True)
        (d / rel).write_text("x")
    return d


def test_routing_exemption_covers_brief_folders_only(tmp_path):
    """Brief folders are inputs for a build, not instructions: exempt. Everything else stays routed."""
    d = _fake_skill(tmp_path, [
        "evals/briefs/BRIEFS.md",
        "evals/briefs/demo/research/RESEARCH.md",
        "evals/briefs/demo/research/strand.md",
        "evals/briefs/demo/project/AGENTS.md",
        "evals/briefs/LOOSE.md",
        "evals/NEW.md",
        "evals/briefs-old/demo/NOTE.md",
    ])
    assert sorted(unrouted_parts(d)) == ["evals/NEW.md", "evals/briefs-old/demo/NOTE.md",
                                         "evals/briefs/LOOSE.md"]


def test_briefs_folder_holds_only_the_index_and_brief_folders():
    loose = [p.name for p in BRIEFS_DIR.iterdir() if p.is_file() and p.name != "BRIEFS.md"]
    assert loose == []
    assert {p.name for p in BRIEFS_DIR.iterdir() if p.is_dir()} == {d.name for d in brief_dirs()}
