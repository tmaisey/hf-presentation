"""Spec: PB-013

The voice part is a small contract (apply a profile, add verdicts as example pairs, pick a
profile) plus the presenter's profile, which carries every rule and approved/rejected pair
from the HF deck's docs/VOICE.md in British spelling.

Coverage: happy (both routed, contract topics, every source table row and key rules present)
· edge (British spelling sample) · negative (contract holds no profile content; no American
spellings or health details in the profile).
"""

import re

from helper_skill import REPO, read_part, skill_links, table_rows

CONTRACT, PROFILE = "voice/VOICE.md", "voice/profiles/twm.md"
SOURCE = REPO / "docs" / "VOICE.md"


def test_contract_and_profile_are_both_routed_from_skill_md():
    """One-hop rule: the profile is a part, so SKILL.md links it directly, not via VOICE.md."""
    assert {CONTRACT, PROFILE} <= skill_links()


def test_contract_says_how_to_pick_apply_and_extend_a_profile():
    low = read_part(CONTRACT).lower()
    assert "profiles/" in low
    assert re.search(r"\bpick|\bchoos", low)
    assert re.search(r"\bappl(y|ied)", low)
    assert "verdict" in low and "pair" in low
    assert "✗" in low and "✓" in low, "pair format shown"


def test_contract_holds_no_presenter_specific_rules():
    """Swapping profiles must not require editing the contract."""
    contract = read_part(CONTRACT)
    assert len(table_rows(contract)) <= 2, "example pairs live in the profile, not the contract"
    assert "aphoris" not in contract.lower()


def test_profile_carries_every_example_pair_from_source():
    src_rows = table_rows(SOURCE.read_text(encoding="utf-8"))
    prof_rows = table_rows(read_part(PROFILE))
    assert len(src_rows) > 30
    assert len(prof_rows) >= len(src_rows)


def test_profile_keeps_key_rules_and_approved_copy_verbatim():
    prof = read_part(PROFILE)
    for phrase in ("State the finding", "No trailing full stop", "X, not Y",
                   "Reward is an incomplete proxy for actual desired behaviour",
                   "Verbatim only", "Discussion prompts", "sacrifice"):
        assert phrase in prof, phrase


def test_profile_uses_british_spelling():
    prof = read_part(PROFILE)
    assert "British spelling" in prof
    for word in ("behaviour", "organised", "learnt"):
        assert word in prof, word
    american = re.findall(r"\b(behavior|organized|color|recognize[ds]?|analyze[ds]?)\b", prof)
    assert american == []


def test_profile_records_no_health_details():
    low = read_part(PROFILE).lower()
    assert not re.search(r"\b(health|illness|diagnos|medical|medication)\w*", low)
