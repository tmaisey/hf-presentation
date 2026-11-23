"""Spec: PB-017

The deterministic gate runner (`evals/gates.py`) checks every in-scope `D` criterion on a deck
(rendered in Chrome) and on a deck repo's git history, and writes one verdict per unit in the judge
format into a run's `verdicts/`, so `aggregate.py` consumes them unchanged.

Coverage: happy (every labelled anchor gets the verdict its label demands; the clean control passes
every deck gate; verdicts validate; a gates-only run aggregates end to end; a correct red→done repo
history passes; CLI) · edge (step units cover every slide × step; `--no-rerun` leaves the re-run
criterion missing with a reason; pptx criteria are missing, never guessed) · negative (a failed
gate fails the deck; tests committed with the implementation, a red whose tests already pass, a red
that fails on an import, a doc without its index row, screenshots made after done and a skipped
layout check each fail; a self-reported process log changes nothing; the target repo is left as
found).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from helper_eval import EVAL_DIR, _import, aggregator, loader

GATES = EVAL_DIR / "gates.py"
ANCHOR_DIR = EVAL_DIR / "anchors"
PROFILE = "editorial-talk"
DECK_CONCERNS = ["content", "research", "voice", "design-layout", "design-palette", "design-style",
                 "architecture"]
REVIEW = ("1920x1080", "1280x720", "1288x598")


@pytest.fixture(scope="module")
def gates():
    return _import(GATES, "skill_eval_gates")


@pytest.fixture(scope="module")
def library():
    return loader().load_library(EVAL_DIR)


@pytest.fixture(scope="module")
def profile(library):
    return loader().load_profile(EVAL_DIR / "profiles" / f"{PROFILE}.json", library)


@pytest.fixture(scope="module")
def labels():
    return json.loads((ANCHOR_DIR / "anchors.json").read_text(encoding="utf-8"))["anchors"]


@pytest.fixture(scope="module")
def browser():
    """System Chrome, once per module (no conftest: other suites share this folder)."""
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        yield b
        b.close()


def _verdicts(run_dir: Path) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((run_dir / "verdicts").glob("*.json"))]


def _status(verdicts: list[dict], cid: str) -> str | None:
    """Criterion-level result as the aggregator would see it at k=1: any unit fail → fail."""
    rs = [v["result"] for v in verdicts if v["criterion"] == cid]
    if not rs:
        return None
    return "fail" if "fail" in rs else "pass" if set(rs) == {"pass"} else rs[0]


@pytest.fixture(scope="module")
def anchor_runs(gates, browser, labels, tmp_path_factory):
    """Gate every anchor deck once (deck concerns, editorial-talk), sharing one Chrome."""
    out = {}
    for a in labels:
        run_dir = tmp_path_factory.mktemp(a["id"].lower())
        report = gates.run_gates(run_dir, deck=ANCHOR_DIR / a["file"], profile=PROFILE,
                                 concerns=DECK_CONCERNS, browser=browser)
        out[a["id"]] = {"dir": run_dir, "report": report, "verdicts": _verdicts(run_dir)}
    return out


# ---------- deck gates on the labelled anchors ----------

def test_every_deterministic_must_fail_label_yields_fail(anchor_runs, labels, library):
    for a in labels:
        vs = anchor_runs[a["id"]]["verdicts"]
        for cid in a["must_fail"]:
            if library[cid]["evidence"] == "D":
                assert _status(vs, cid) == "fail", f"{a['id']} {cid}: {_status(vs, cid)}"


def test_every_deterministic_must_pass_label_yields_pass(anchor_runs, labels, library):
    for a in labels:
        vs = anchor_runs[a["id"]]["verdicts"]
        for cid in a["must_pass"]:
            if library[cid]["evidence"] == "D":
                bad = [v for v in vs if v["criterion"] == cid and v["result"] != "pass"]
                assert _status(vs, cid) == "pass", f"{a['id']} {cid}: {bad[:2]}"


# Known conflict, reported to the presenter: the shipped editorial style sets its kicker role
# (kickers, quote and sender lines) at 13 px at 1280 wide and 19 px at 1920, below DL-02's default
# floor (15 / 20 px). The gate reports it faithfully; resolving it is a style or profile decision.
LABEL_ROLE = ("p.kicker", "p.quote-from", "p.msg-from")


def test_clean_control_passes_every_deck_gate(anchor_runs, library):
    """Over-strict checks show up here: the control must pass everything a gate can check."""
    vs = anchor_runs["AN-00"]["verdicts"]
    checked = {v["criterion"] for v in vs}
    deck_d = {c for c, x in library.items() if x["evidence"] == "D" and x["target"] == "deck"}
    assert checked >= {"DL-01", "DP-01", "AR-01", "AR-02", "AR-03", "AR-05", "CN-04", "VC-03"}
    assert checked <= deck_d
    fails = [(v["criterion"], v["unit"], v["evidence"][:2]) for v in vs
             if v["result"] != "pass" and v["criterion"] != "DL-02"]
    assert fails == []


def test_control_fails_the_size_floor_only_on_kicker_role_labels(anchor_runs):
    notes = [e["note"] for v in anchor_runs["AN-00"]["verdicts"]
             if v["criterion"] == "DL-02" and v["result"] == "fail" for e in v["evidence"]]
    assert notes, "the style's kicker role sits below the default floor (see LABEL_ROLE)"
    assert all(n.startswith(LABEL_ROLE) or "more)" in n for n in notes), notes


def test_every_verdict_validates_in_the_judge_format(anchor_runs, library, profile):
    validate = aggregator().validate_verdict
    for run in anchor_runs.values():
        assert run["verdicts"], "no verdicts written"
        for v in run["verdicts"]:
            validate(v, library, profile)
            assert v["repeat"] == 1 and v["evidence"], v


def test_step_units_cover_every_slide_and_step(anchor_runs, browser):
    page = browser.new_page()
    page.goto((ANCHOR_DIR / "an-00.html").as_uri())
    page.wait_for_function("window.deck && window.deck.ready === true")
    want = {f"{s}/{k}" for s, last in page.evaluate("deck.plan()") for k in range(last + 1)}
    page.close()
    units = {v["unit"] for v in anchor_runs["AN-00"]["verdicts"] if v["criterion"] == "DL-01"}
    assert units == want


def test_failures_locate_the_fault_by_slide_step_and_size(anchor_runs):
    """AN-01's collision exists only in the short-wide window, so its evidence must say so."""
    fails = [v for v in anchor_runs["AN-01"]["verdicts"] if v["criterion"] == "DL-01" and v["result"] == "fail"]
    assert fails and all(v["unit"].startswith("a1-1/") for v in fails)
    sizes = {e.get("size") for v in fails for e in v["evidence"]}
    assert sizes == {"1288x598"}
    assert all(v["flaws"] for v in fails), "a failure names its flaw tags"


def test_pptx_criteria_are_reported_missing_never_guessed(anchor_runs, library, gates):
    run = anchor_runs["AN-00"]
    log = json.loads((run["dir"] / "evidence" / "gates.json").read_text(encoding="utf-8"))
    assert log["criteria"] and all(("checked" in c) != ("missing" in c) for c in log["criteria"].values())
    assert all(c["missing"].strip() for c in log["criteria"].values() if "missing" in c), "a reason, always"
    pptx ={c for c, x in library.items() if x["evidence"] == "D" and x["target"] == "pptx"}
    assert pptx, "library has D pptx criteria"
    assert not {v["criterion"] for v in run["verdicts"]} & pptx
    full = gates.coverage()
    for c in pptx:
        assert "PB-024" in full[c]["missing"], full[c]
    for c, x in library.items():
        if x["evidence"] == "D":
            assert c in full and (full[c].get("checked") or full[c].get("missing")), c


# Unlabelled deck criteria: each mutation of the clean control must trip exactly the gate named.
MUTATIONS = [
    ("DL-10", 'markerUnits="strokeWidth" orient="auto"', 'markerUnits="strokeWidth" orient="0"'),
    ("AR-06", 'role="img" aria-label="Walk-in queue, booking page and pick-up slot, joined in order"', 'role="img"'),
    ("AR-04", '<div class="body"><ul class="points">', '<div class="body zzfancy" style="margin:0"><ul class="points">'),
    ("AR-07", "", ""),  # the zzfancy class above is in no contract doc
    ("DS-07", "<li>Keep walk-in collection open</li>",
     '<li>Keep walk-in collection <a href="https://pharmacy-review.example.org/walk-in">open</a></li>'),
    ("DS-07", "/* DECK:BEGIN */\n", "/* DECK:BEGIN */\n@layer deck { .points a { color: revert; } }\n"),
    ("AR-05", "Offer booked slots at the next two branches", "Staff said the afternoons became calmer"),
    ("VC-05", '<aside class="note" data-for="#a0-4-title">',
     '<aside class="overlay" data-at="1"><p>One. Two. Three. Four.</p></aside>\n  <aside class="note" data-for="#a0-4-title">'),
    ("AR-02", '<p class="kicker">03 · Next</p>', '<p class="kicker">03 · Next</p><!-- window.open( -->'),
    ("DS-01", "/* DECK:BEGIN */\n", '/* DECK:BEGIN */\n@layer deck { .points li { font-family: "Comic Sans MS"; } }\n'),
    ("DP-03", "/* DECK:BEGIN */\n", "/* DECK:BEGIN */\n@layer deck { .lede { color: #2b2a27; } }\n"),
    ("DP-02", "/* DECK:BEGIN */\n", "/* DECK:BEGIN */\n@layer deck { .edge { stroke: var(--sys-color-paper-deep); } }\n"),
]


def test_each_unlabelled_deck_gate_catches_its_mutation_of_the_control(gates, browser, tmp_path):
    src = (ANCHOR_DIR / "an-00.html").read_text(encoding="utf-8")
    for cid, old, new in MUTATIONS:
        if old:
            assert old in src, cid
            src = src.replace(old, new, 1)
    deck = tmp_path / "mutated.html"
    deck.write_text(src, encoding="utf-8")
    repo = _base(tmp_path)
    run_dir = tmp_path / "run"
    gates.run_gates(run_dir, deck=deck, repo=repo.root, profile=PROFILE, concerns=DECK_CONCERNS,
                    sizes=[(1280, 720)], browser=browser)
    vs = _verdicts(run_dir)
    assert {cid: _status(vs, cid) for cid, _, _ in MUTATIONS} == {cid: "fail" for cid, _, _ in MUTATIONS}


def test_a_freshly_assembled_deck_uses_only_contract_markup(gates, browser, tmp_path):
    """Positive partner of the AR-07 mutation. (The anchors themselves use `lede`, `quote-from` and
    `body--diagram`, which no contract doc names, so they fail AR-07: a finding, not a gate fault.)"""
    deck = tmp_path / "fresh.html"
    gates.asm_mod.new(deck, "A fresh deck", "Its subtitle")
    repo = _base(tmp_path)
    gates.run_gates(tmp_path / "run", deck=deck, repo=repo.root, profile=PROFILE,
                    concerns=["architecture"], sizes=[(1280, 720)], browser=browser)
    vs = _verdicts(tmp_path / "run")
    assert _status(vs, "AR-07") == "pass", [v["evidence"] for v in vs if v["criterion"] == "AR-07"]
    assert _status(vs, "AR-01") == "pass" and _status(vs, "AR-02") == "pass"


def _aggregate(run_dir: Path, label: str, concerns: list[str]) -> dict:
    manifest = {"label": label, "date": "261123", "target": label, "profile": PROFILE,
                "concerns": concerns, "depth": "gates", "k": 1, "transcripts": False, "mode": "pointwise"}
    (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    json_path, md_path = aggregator().run(run_dir)
    assert md_path.is_file()
    return json.loads(json_path.read_text(encoding="utf-8"))


def test_gates_only_run_aggregates_and_a_failed_gate_fails_the_deck(anchor_runs):
    report = _aggregate(anchor_runs["AN-01"]["dir"], "gates-an-01", DECK_CONCERNS)
    assert report["outcome"] == "fail"
    assert report["criteria"]["DL-01"]["status"] == "fail"
    assert {g["criterion"] for g in report["gates"] if g["status"] == "fail"} >= {"DL-01"}


def test_gates_only_run_of_a_passing_deck_aggregates_to_pass(gates, browser, tmp_path):
    """Layout concerns left out (see LABEL_ROLE), so every gate in scope is decided by code."""
    concerns = [c for c in DECK_CONCERNS if c != "design-layout"]
    gates.run_gates(tmp_path, deck=ANCHOR_DIR / "an-00.html", profile=PROFILE, concerns=concerns,
                    browser=browser)
    report = _aggregate(tmp_path, "gates-an-00", concerns)
    assert report["gates"] and all(g["status"] == "pass" for g in report["gates"]), report["gates"]
    assert report["outcome"] == "pass"


# ---------- repo gates on synthetic deck repos ----------

T0 = 1_790_000_000  # fixed commit clock, so screenshot times can sit before or after a commit
INDEX = """# Deck project

| File | Description | When to use | When to update |
| --- | --- | --- | --- |
| `docs/PRD.md` | Requirements | Before scoping | On intent change |
| `docs/SPEC.jsonl` | Backlog | Start of session | On every flip |
"""
DECK_V1 = """<!doctype html><html><body><main class="deck">
<section class="slide" id="s-1"><h2 class="title">First slide</h2></section>
</main></body></html>
"""
DECK_V2 = DECK_V1.replace("</main>", """<section class="slide" id="s-2"><h2 class="title">Second slide</h2>
<p data-show-at="1">Revealed</p></section>
</main>""")
TEST_S2 = '''"""Spec: S-001

The deck has a second slide.
"""
from pathlib import Path

DECK = Path(__file__).resolve().parents[1] / "deck" / "deck.html"


def test_second_slide_exists():
    assert 'id="s-2"' in DECK.read_text()
'''
TEST_PASSING = TEST_S2.replace('id="s-2"', 'id="s-1"')
TEST_IMPORT_ERROR = TEST_S2.replace("from pathlib import Path", "from pathlib import Path\nimport deckbuilder_missing")


def _spec(status: str) -> str:
    return json.dumps({"id": "S-001", "status": status, "name": "Second slide", "depends_on": [],
                       "description": "built: a second slide · why: story · not-built: more"}) + "\n"


class Repo:
    """A throwaway deck repo whose commits carry fixed timestamps."""

    def __init__(self, root: Path):
        self.root, self.n = root, 0
        root.mkdir(parents=True)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.org")
        self.git("config", "user.name", "t")

    def git(self, *args) -> str:
        return subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True,
                              text=True).stdout

    def commit(self, msg: str, files: dict[str, str], t: int) -> str:
        for rel, text in files.items():
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        self.git("add", "--", *files)
        env = dict(os.environ, GIT_AUTHOR_DATE=f"@{t} +0000", GIT_COMMITTER_DATE=f"@{t} +0000")
        subprocess.run(["git", "-C", str(self.root), "commit", "-q", "-m", msg], check=True, env=env)
        return self.git("rev-parse", "HEAD").strip()


def _base(tmp_path) -> Repo:
    r = Repo(tmp_path / "deckrepo")
    r.commit("Init", {"AGENTS.md": INDEX, "docs/PRD.md": "# PRD\n", "docs/SPEC.jsonl": _spec("todo"),
                      "deck/deck.html": DECK_V1}, T0)
    return r


def _shots(repo: Repo, t: int, slides=(("s-2", 1),)) -> None:
    d = repo.root / "shots"
    d.mkdir(exist_ok=True)
    for sid, last in slides:
        for k in range(last + 1):
            for size in REVIEW:
                p = d / f"{sid}-{k}-{size}.png"
                p.write_bytes(b"\x89PNG\r\n")
                os.utime(p, (t, t))


def _good_history(tmp_path) -> Repo:
    r = _base(tmp_path)
    r.commit("Red: S-001 second slide test", {"tests/test_second.py": TEST_S2, "docs/SPEC.jsonl": _spec("build"),
                                              ".gitignore": "shots/\n"}, T0 + 100)  # test config is not implementation
    _shots(r, T0 + 200)
    r.commit("Done: S-001 second slide", {
        "deck/deck.html": DECK_V2, "docs/SPEC.jsonl": _spec("done"),
        "docs/STORYBOARD.md": "# Storyboard\n",
        "AGENTS.md": INDEX + "| `docs/STORYBOARD.md` | Arc | Before slides | On a slide change |\n"}, T0 + 300)
    return r


def _repo_gate(gates, tmp_path, repo: Repo, **kw) -> tuple[dict, list[dict]]:
    run_dir = tmp_path / "run"
    report = gates.run_gates(run_dir, repo=repo.root, profile=PROFILE, concerns=["process"], **kw)
    return report, _verdicts(run_dir)


def _result(verdicts, cid, unit="S-001"):
    hits = [v for v in verdicts if v["criterion"] == cid and v["unit"] == unit]
    assert len(hits) == 1, (cid, unit, verdicts)
    return hits[0]["result"]


def test_correct_red_then_done_history_passes_every_process_gate(gates, tmp_path, library, profile):
    repo = _good_history(tmp_path)
    head, status = repo.git("rev-parse", "HEAD"), repo.git("status", "--porcelain")
    _, vs = _repo_gate(gates, tmp_path, repo)
    for cid in ("PR-01", "PR-02", "PR-03", "PR-04"):
        assert _result(vs, cid) == "pass", [v for v in vs if v["criterion"] == cid]
    assert _status(vs, "PR-09") == "pass"
    for v in vs:
        aggregator().validate_verdict(v, library, profile)
    assert repo.git("rev-parse", "HEAD") == head and repo.git("status", "--porcelain") == status
    assert len(repo.git("worktree", "list").splitlines()) == 1, "throwaway worktrees removed"


def test_tests_committed_with_the_implementation_fail_red_first(gates, tmp_path):
    """No red commit: tests, implementation and the flip to done land together. A process log
    claiming otherwise is a self-report and must not count."""
    r = _base(tmp_path)
    r.commit("Add second slide with tests", {
        "tests/test_second.py": TEST_S2, "deck/deck.html": DECK_V2, "docs/SPEC.jsonl": _spec("done"),
        "docs/process-log.md": "S-001: red commit made first, tests failed, then green.\n",
        "AGENTS.md": INDEX + "| `docs/process-log.md` | Log | Never | Never |\n"}, T0 + 100)
    _, vs = _repo_gate(gates, tmp_path, r)
    assert _result(vs, "PR-01") == "fail"


def test_red_commit_carrying_implementation_fails_red_first(gates, tmp_path):
    r = _base(tmp_path)
    r.commit("Red: S-001", {"tests/test_second.py": TEST_S2, "deck/deck.html": DECK_V2,
                            "docs/SPEC.jsonl": _spec("build")}, T0 + 100)
    r.commit("Done: S-001", {"docs/SPEC.jsonl": _spec("done")}, T0 + 300)
    _, vs = _repo_gate(gates, tmp_path, r)
    assert _result(vs, "PR-01") == "fail"


def test_red_commit_whose_tests_already_pass_fails(gates, tmp_path):
    r = _base(tmp_path)
    r.commit("Red: S-001", {"tests/test_second.py": TEST_PASSING, "docs/SPEC.jsonl": _spec("build")}, T0 + 100)
    r.commit("Done: S-001", {"deck/deck.html": DECK_V2, "docs/SPEC.jsonl": _spec("done")}, T0 + 300)
    _, vs = _repo_gate(gates, tmp_path, r)
    assert _result(vs, "PR-01") == "pass"
    assert _result(vs, "PR-02") == "fail"


def test_red_commit_failing_on_an_import_error_is_a_false_red(gates, tmp_path):
    r = _base(tmp_path)
    r.commit("Red: S-001", {"tests/test_second.py": TEST_IMPORT_ERROR, "docs/SPEC.jsonl": _spec("build")},
             T0 + 100)
    r.commit("Done: S-001", {"deck/deck.html": DECK_V2, "tests/test_second.py": TEST_S2,
                             "docs/SPEC.jsonl": _spec("done")}, T0 + 300)
    _, vs = _repo_gate(gates, tmp_path, r)
    assert _result(vs, "PR-02") == "fail"


def test_doc_added_without_its_index_row_fails(gates, tmp_path):
    r = _base(tmp_path)
    r.commit("Red: S-001", {"tests/test_second.py": TEST_S2, "docs/SPEC.jsonl": _spec("build")}, T0 + 100)
    _shots(r, T0 + 200)
    r.commit("Done: S-001", {"deck/deck.html": DECK_V2, "docs/SPEC.jsonl": _spec("done"),
                             "docs/STORYBOARD.md": "# Storyboard\n"}, T0 + 300)
    _, vs = _repo_gate(gates, tmp_path, r)
    assert _result(vs, "PR-03") == "fail"
    assert _result(vs, "PR-01") == "pass"


@pytest.mark.parametrize("when", ["after-done", "none"])
def test_screenshots_missing_or_made_after_done_fail(gates, tmp_path, when):
    r = _base(tmp_path)
    r.commit("Red: S-001", {"tests/test_second.py": TEST_S2, "docs/SPEC.jsonl": _spec("build")}, T0 + 100)
    r.commit("Done: S-001", {"deck/deck.html": DECK_V2, "docs/SPEC.jsonl": _spec("done")}, T0 + 300)
    if when == "after-done":
        _shots(r, T0 + 400)
    _, vs = _repo_gate(gates, tmp_path, r, rerun=False)
    assert _result(vs, "PR-04") == "fail"


def test_screenshots_missing_one_step_fail(gates, tmp_path):
    r = _base(tmp_path)
    r.commit("Red: S-001", {"tests/test_second.py": TEST_S2, "docs/SPEC.jsonl": _spec("build")}, T0 + 100)
    _shots(r, T0 + 200, slides=(("s-2", 0),))
    r.commit("Done: S-001", {"deck/deck.html": DECK_V2, "docs/SPEC.jsonl": _spec("done")}, T0 + 300)
    _, vs = _repo_gate(gates, tmp_path, r, rerun=False)
    assert _result(vs, "PR-04") == "fail"


def test_layout_check_skipped_in_a_commit_fails(gates, tmp_path):
    r = _good_history(tmp_path)
    r.commit("Quiet the guard", {"tests/test_layout.py":
                                 '"""Spec: S-001\n"""\nimport pytest\n\n\n'
                                 '@pytest.mark.skip(reason="title overlap")\n'
                                 'def test_layout_guard():\n    assert False\n'}, T0 + 500)
    _, vs = _repo_gate(gates, tmp_path, r, rerun=False)
    assert _status(vs, "PR-09") == "fail"


def test_no_rerun_leaves_the_rerun_criterion_missing_with_a_reason(gates, tmp_path):
    repo = _good_history(tmp_path)
    report, vs = _repo_gate(gates, tmp_path, repo, rerun=False)
    assert not [v for v in vs if v["criterion"] == "PR-02"]
    assert "rerun" in report["criteria"]["PR-02"]["missing"].replace("-", "")
    assert _result(vs, "PR-01") == "pass"


def test_cli_writes_verdicts_and_exits_by_outcome(tmp_path):
    good = _good_history(tmp_path / "good")
    bad = _base(tmp_path / "bad")
    bad.commit("Add with tests", {"tests/test_second.py": TEST_S2, "deck/deck.html": DECK_V2,
                                  "docs/SPEC.jsonl": _spec("done")}, T0 + 100)
    codes = {}
    for name, repo in (("good", good), ("bad", bad)):
        run_dir = tmp_path / f"run-{name}"
        proc = subprocess.run([sys.executable, str(GATES), str(run_dir), "--repo", str(repo.root),
                               "--profile", PROFILE, "--concerns", "process", "--no-rerun"],
                              capture_output=True, text=True)
        codes[name] = proc.returncode
        assert list((run_dir / "verdicts").glob("PR-01_*_r1.json")), proc.stderr
        assert (run_dir / "evidence" / "gates.json").is_file()
    assert codes == {"good": 0, "bad": 1}
    proc = subprocess.run([sys.executable, str(GATES), str(tmp_path / "run-x"), "--profile", PROFILE],
                          capture_output=True, text=True)
    assert proc.returncode == 2, "neither --deck nor --repo is a usage error"
