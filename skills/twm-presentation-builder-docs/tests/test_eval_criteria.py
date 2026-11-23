"""Spec: PB-015

The eval criterion library (`evals/criteria.jsonl` + `evals/flaws.json`) defines every criterion
once in a machine-readable, runner-agnostic schema that later gates, judges and profiles consume.

Coverage: happy (schema, field order, enums, forms, anchors, concern and PRD-item coverage,
sources, taxonomy, loader accepts the library) · edge (every scale level, anchor levels fit the
form, reference anchors cite a verdict) · negative (no incident terms outside reference anchors,
no self-reported logs, loader rejects duplicate ids, bad order, missing levels, unanchored judged
criteria, unknown flaw tags).
"""

import re

import pytest

from helper_eval import (ANCHOR_ORDER, CONCERN_PREFIX, EVIDENCE, FIELD_ORDER, INCIDENT_TERMS,
                         ORIGINS, SCOPES, TARGETS, copy_eval, generic_text, loader, read_criteria,
                         read_flaws, research_source_numbers, write_criteria)

SOURCE_RE = re.compile(r"^(?:(llm-judge|deck-rubrics)\[(\d+)\]|PRD: .+|reference: .+)$")


@pytest.fixture(scope="module")
def criteria():
    return read_criteria()


def test_library_has_one_criterion_object_per_line(criteria):
    assert len(criteria) >= 40
    assert all(isinstance(c, dict) for c in criteria)


def test_fields_appear_in_canonical_order(criteria):
    """Verbose fields last so a reader scanning lines sees id/concern/evidence first."""
    bad = [c.get("id") for c in criteria if tuple(c) != FIELD_ORDER]
    assert bad == []


def test_ids_are_unique_stable_and_concern_prefixed(criteria):
    ids = [c["id"] for c in criteria]
    assert len(ids) == len(set(ids))
    for c in criteria:
        assert re.fullmatch(r"[A-Z]{2}-\d{2}", c["id"]), c["id"]
        assert c["id"][:2] == CONCERN_PREFIX[c["concern"]], c["id"]


def test_enumerated_fields_take_allowed_values(criteria):
    for c in criteria:
        assert c["concern"] in CONCERN_PREFIX, c["id"]
        assert c["target"] in TARGETS, c["id"]
        assert c["scope"] in SCOPES, c["id"]
        assert c["evidence"] in EVIDENCE, c["id"]
        assert c["profile"] is None or re.fullmatch(r"[a-z]+(-[a-z]+)*", c["profile"]), c["id"]
        assert isinstance(c["question"], str) and c["question"].endswith("?"), c["id"]


def test_spec_scope_only_for_repo_targets(criteria):
    """`spec` scope means one verdict per feature in the repo history; it has no deck meaning."""
    assert all(c["target"] == "repo" for c in criteria if c["scope"] == "spec")


def test_binary_items_describe_pass_and_fail(criteria):
    for c in criteria:
        f = c["form"]
        if f["type"] == "binary":
            assert set(f) == {"type", "pass", "fail"}, c["id"]
            assert f["pass"].strip() and f["fail"].strip() and f["pass"] != f["fail"], c["id"]


def test_every_scale_level_zero_to_five_is_described(criteria):
    scales = [c for c in criteria if c["form"]["type"] == "scale"]
    assert scales, "graded criteria exist where a checklist can't decompose the judgement"
    for c in scales:
        levels = c["form"]["levels"]
        assert set(c["form"]) == {"type", "levels"}, c["id"]
        assert list(levels) == [str(n) for n in range(6)], c["id"]
        texts = [levels[k].strip() for k in levels]
        assert all(texts) and len(set(texts)) == 6, c["id"]


def test_forms_are_binary_or_scale_and_deterministic_items_are_binary(criteria):
    """Code checks return pass/fail; graded scales are for judges only."""
    for c in criteria:
        assert c["form"]["type"] in {"binary", "scale"}, c["id"]
        if c["evidence"] == "D":
            assert c["form"]["type"] == "binary", c["id"]


def test_every_judged_criterion_has_pass_side_and_fail_side_anchors(criteria):
    for c in criteria:
        if c["evidence"] == "D":
            continue
        levels = [a["level"] for a in c["anchors"]]
        if c["form"]["type"] == "binary":
            assert "pass" in levels and "fail" in levels, c["id"]
        else:
            assert any(lv >= 4 for lv in levels) and any(lv <= 1 for lv in levels), c["id"]


def test_anchors_are_well_formed_and_fit_the_form(criteria):
    for c in criteria:
        assert isinstance(c["anchors"], list), c["id"]
        for a in c["anchors"]:
            assert tuple(a) in (ANCHOR_ORDER, ANCHOR_ORDER[:-1]), c["id"]
            assert a["origin"] in ORIGINS, c["id"]
            assert a["example"].strip() and a["why"].strip(), c["id"]
            if c["form"]["type"] == "binary":
                assert a["level"] in {"pass", "fail"}, c["id"]
            else:
                assert isinstance(a["level"], int) and 0 <= a["level"] <= 5, c["id"]


def test_reference_verdict_anchors_cite_the_verdict(criteria):
    """Anchors from recorded presenter verdicts say where the verdict is recorded."""
    refs = [a for c in criteria for a in c["anchors"] if a["origin"] == "reference-verdict"]
    assert len(refs) >= 10, "presenter verdicts are the main anchor source (PRD Calibration)"
    assert all(a.get("cite", "").strip() for a in refs)


def test_every_prd_concern_has_generic_criteria(criteria):
    generic = {c["concern"] for c in criteria if c["profile"] is None}
    assert generic == set(CONCERN_PREFIX)


def test_all_evidence_types_and_targets_are_used(criteria):
    assert {c["evidence"] for c in criteria} == EVIDENCE
    assert {c["target"] for c in criteria} == TARGETS


# (concern, evidence, pattern over the question): items the PRD or a consuming spec names.
REQUIRED_ITEMS = [
    ("design-layout", "D", r"overlap"),
    ("design-palette", "D", r"contrast"),
    ("architecture", "D", r"offline|network"),
    ("architecture", "D", r"endpoint"),
    ("architecture", "D", r"unique.*title|title.*unique"),
    ("architecture", "D", r"alt text|accessible name"),
    ("architecture", "D", r"reachable"),
    ("content", "D", r"word"),
    ("pptx", "D", r"native.*text|editable text"),
    ("pptx", "D", r"placeholder"),
    ("pptx", "D", r"theme colou?r"),
    ("pptx", "D", r"animation"),
    ("pptx", "D", r"native, approximated or lost"),
    ("pptx", "S", r"wrap"),
    ("process", "D", r"red commit"),
    ("process", "D", r"fail.*red|red.*fail"),
    ("process", "D", r"index row|docs?.*same commit"),
    ("process", "D", r"screenshot"),
    ("process", "T", r"one question at a time"),
    ("process", "T", r"consent"),
    ("process", "T", r"done.*claim|claim.*done"),
    ("research", "T", r"source"),
    ("voice", "T", r"hook|teaser"),
]


@pytest.mark.parametrize("concern,evidence,pattern", REQUIRED_ITEMS)
def test_prd_required_item_has_a_criterion(criteria, concern, evidence, pattern):
    hits = [c["id"] for c in criteria if c["concern"] == concern and c["evidence"] == evidence
            and re.search(pattern, c["question"], re.I)]
    assert hits, f"no {evidence} {concern} criterion asks about /{pattern}/"


def test_flaw_tags_exist_and_every_tag_is_used(criteria):
    taxonomy = read_flaws()
    used = set()
    for c in criteria:
        assert c["flaws"], c["id"]
        unknown = set(c["flaws"]) - set(taxonomy)
        assert not unknown, f"{c['id']}: {unknown}"
        used |= set(c["flaws"])
    assert set(taxonomy) - used == set(), "a dead tag misleads judges reading the taxonomy"


def test_taxonomy_entries_name_a_group_and_describe_the_flaw():
    for tag, entry in read_flaws().items():
        assert re.fullmatch(r"[a-z]+(-[a-z]+)*", tag), tag
        assert set(entry) == {"group", "description"}, tag
        assert entry["group"].strip() and entry["description"].strip(), tag


def test_sources_cite_real_research_entries(criteria):
    known = {n: research_source_numbers(n) for n in ("llm-judge", "deck-rubrics")}
    for c in criteria:
        assert c["source"], c["id"]
        for s in c["source"]:
            m = SOURCE_RE.match(s)
            assert m, f"{c['id']}: {s}"
            if m.group(1):
                assert int(m.group(2)) in known[m.group(1)], f"{c['id']}: {s}"


def test_generic_text_never_names_the_reference_incident(criteria):
    """HF material may appear only as labelled reference anchors (task brief, PRD self-contained)."""
    hits = {c["id"]: INCIDENT_TERMS.findall(generic_text(c)) for c in criteria}
    assert {k: v for k, v in hits.items() if v} == {}


def test_incident_term_checker_catches_a_leak():
    leaky = {"id": "XX-01", "question": "Does the swarm diagram read?", "anchors": []}
    assert INCIDENT_TERMS.findall(generic_text(leaky)) == ["swarm"]


def test_process_criteria_never_rely_on_a_self_reported_log(criteria):
    """PRD: process evidence is repo artefacts; the skill NEVER makes the agent keep a process log."""
    for c in criteria:
        if c["concern"] == "process":
            text = c["question"] + c["form"].get("pass", "")
            assert not re.search(r"process log|self-report", text, re.I), c["id"]


# --- loader contract ------------------------------------------------------------------------


def test_loader_accepts_the_shipped_library():
    mod = loader()
    from helper_eval import EVAL_DIR
    lib = mod.load_library(EVAL_DIR)
    assert set(lib) == {c["id"] for c in read_criteria()}


def _mutated(tmp_path, mutate):
    d = copy_eval(tmp_path)
    crit = read_criteria(d / "criteria.jsonl")
    mutate(crit)
    write_criteria(d / "criteria.jsonl", crit)
    return d


def _judged(crit, form_type):
    return next(c for c in crit if c["evidence"] != "D" and c["form"]["type"] == form_type)


@pytest.mark.parametrize("name,mutate", [
    ("duplicate id", lambda crit: crit.append(dict(crit[0]))),
    ("field order", lambda crit: crit.__setitem__(0, dict(reversed(list(crit[0].items()))))),
    ("missing scale level", lambda crit: _judged(crit, "scale")["form"]["levels"].pop("3")),
    ("unanchored judge", lambda crit: _judged(crit, "binary").__setitem__("anchors", [])),
    ("unknown flaw", lambda crit: crit[0]["flaws"].append("not-a-flaw")),
    ("bad concern", lambda crit: crit[0].__setitem__("concern", "vibes")),
])
def test_loader_rejects_a_malformed_library(tmp_path, name, mutate):
    mod = loader()
    d = _mutated(tmp_path, mutate)
    with pytest.raises(mod.EvalFormatError):
        mod.load_library(d)
