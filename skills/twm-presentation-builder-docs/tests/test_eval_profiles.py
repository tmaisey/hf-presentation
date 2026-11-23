"""Spec: PB-016

Deck-type profiles (`evals/profiles/*.json`) adapt the one criterion library to editorial talks,
pitches, data reviews and internal updates by selecting and weighting criteria by id, declaring
gates and adding only profile-specific criteria.

Coverage: happy (four profiles, schema, known ids, weights, gates, concern coverage, profiles
differ, loader resolves each) · edge (profile-only criteria owned by exactly one profile, every
generic criterion used somewhere, params only for selected ids) · negative (no handout profile,
loader rejects unknown ids, unselected or graded gates, bad weights, borrowed profile-only
criteria; no incident terms).
"""

import json

import pytest

from helper_eval import (EVAL_DIR, INCIDENT_TERMS, PROFILE_IDS, PROFILE_ORDER, PROFILES_DIR,
                         copy_eval, loader, read_criteria, read_profiles)


@pytest.fixture(scope="module")
def library():
    return {c["id"]: c for c in read_criteria()}


@pytest.fixture(scope="module")
def profiles():
    return read_profiles()


def test_exactly_the_four_deck_type_profiles_ship(profiles):
    """Handout is a non-goal of PB-016."""
    assert set(profiles) == PROFILE_IDS


def test_profile_fields_in_order_and_id_matches_filename(profiles):
    for stem, p in profiles.items():
        assert tuple(p) in (PROFILE_ORDER, PROFILE_ORDER[:-1]), stem
        assert p["id"] == stem
        assert p["description"].strip(), stem


def test_profiles_reference_only_known_criteria(profiles, library):
    for stem, p in profiles.items():
        assert set(p["weights"]) - set(library) == set(), stem
        assert set(p["gates"]) - set(library) == set(), stem


def test_weights_are_integers_one_to_three(profiles):
    for stem, p in profiles.items():
        assert p["weights"], stem
        for cid, w in p["weights"].items():
            assert type(w) is int and 1 <= w <= 3, f"{stem}:{cid}={w!r}"


def test_gates_are_selected_binary_criteria(profiles, library):
    """A gate is pass/fail outside the weighted mean, so it must be selected and binary."""
    for stem, p in profiles.items():
        assert p["gates"], stem
        assert len(p["gates"]) == len(set(p["gates"])), stem
        assert set(p["gates"]) <= set(p["weights"]), stem
        assert all(library[g]["form"]["type"] == "binary" for g in p["gates"]), stem


def test_profile_flag_names_a_shipped_profile(library):
    assert {c["profile"] for c in library.values()} - {None} <= PROFILE_IDS


def test_profile_only_criteria_are_selected_by_their_profile_alone(profiles, library):
    for cid, c in library.items():
        if c["profile"] is None:
            continue
        owners = {stem for stem, p in profiles.items() if cid in p["weights"]}
        assert owners == {c["profile"]}, cid


def test_every_profile_adds_at_least_one_profile_only_criterion(library):
    assert {c["profile"] for c in library.values()} - {None} == PROFILE_IDS


def test_every_generic_criterion_is_selected_by_some_profile(profiles, library):
    selected = set().union(*(p["weights"] for p in profiles.values()))
    unused = {cid for cid, c in library.items() if c["profile"] is None} - selected
    assert unused == set()


def test_every_profile_covers_every_concern(profiles, library):
    """The run-time scope prompt narrows concerns; profiles themselves stay complete."""
    concerns = {c["concern"] for c in library.values()}
    for stem, p in profiles.items():
        assert {library[cid]["concern"] for cid in p["weights"]} == concerns, stem


def test_profiles_genuinely_differ(profiles):
    seen = [json.dumps(p["weights"], sort_keys=True) for p in profiles.values()]
    assert len(set(seen)) == len(seen)


def test_params_only_tune_selected_criteria(profiles):
    for stem, p in profiles.items():
        params = p.get("params", {})
        assert isinstance(params, dict), stem
        assert set(params) <= set(p["weights"]), stem
        assert all(isinstance(v, dict) and v for v in params.values()), stem


def test_profiles_never_name_the_reference_incident(profiles):
    for stem, p in profiles.items():
        assert INCIDENT_TERMS.findall(json.dumps(p)) == [], stem


# --- loader contract ------------------------------------------------------------------------


def test_loader_resolves_each_profile_to_weighted_criteria():
    mod = loader()
    lib = mod.load_library(EVAL_DIR)
    for stem in PROFILE_IDS:
        prof = mod.load_profile(PROFILES_DIR / f"{stem}.json", lib)
        rows = mod.resolve(prof, lib)
        assert {r["id"] for r in rows} == set(prof["weights"])
        for r in rows:
            assert r["weight"] == prof["weights"][r["id"]]
            assert r["gate"] == (r["id"] in prof["gates"])
            assert r["question"] == lib[r["id"]]["question"], "resolve carries the full criterion"


def test_loader_checks_every_shipped_profile():
    mod = loader()
    assert set(mod.load_profiles(EVAL_DIR)) == PROFILE_IDS


def _bad_profile(tmp_path, mutate):
    d = copy_eval(tmp_path)
    path = d / "profiles" / "pitch.json"
    p = json.loads(path.read_text(encoding="utf-8"))
    mutate(p)
    path.write_text(json.dumps(p), encoding="utf-8")
    return d, path


def _foreign_criterion(p):
    lib = {c["id"]: c for c in read_criteria()}
    return next(cid for cid, c in lib.items() if c["profile"] not in (None, p["id"]))


def _graded(p):
    lib = {c["id"]: c for c in read_criteria()}
    return next(cid for cid in p["weights"] if lib[cid]["form"]["type"] == "scale")


@pytest.mark.parametrize("name,mutate", [
    ("unknown id", lambda p: p["weights"].__setitem__("ZZ-99", 2)),
    ("unknown gate id", lambda p: p["gates"].append("ZZ-98")),
    ("gate not selected", lambda p: p["gates"].append(
        next(c["id"] for c in read_criteria() if c["id"] not in p["weights"]
             and c["form"]["type"] == "binary" and c["profile"] is None))),
    ("graded gate", lambda p: p["gates"].append(_graded(p))),
    ("weight zero", lambda p: p["weights"].__setitem__(next(iter(p["weights"])), 0)),
    ("weight float", lambda p: p["weights"].__setitem__(next(iter(p["weights"])), 1.5)),
    ("borrowed profile-only criterion", lambda p: p["weights"].__setitem__(_foreign_criterion(p), 1)),
    ("params for unselected id", lambda p: p.__setitem__("params", {"ZZ-97": {"x": 1}})),
])
def test_loader_rejects_a_malformed_profile(tmp_path, name, mutate):
    mod = loader()
    d, path = _bad_profile(tmp_path, mutate)
    lib = mod.load_library(d)
    with pytest.raises(mod.EvalFormatError):
        mod.load_profile(path, lib)


def test_unknown_id_error_names_the_id(tmp_path):
    mod = loader()
    d, path = _bad_profile(tmp_path, lambda p: p["weights"].__setitem__("ZZ-99", 2))
    with pytest.raises(mod.EvalFormatError, match="ZZ-99"):
        mod.load_profile(path, mod.load_library(d))
