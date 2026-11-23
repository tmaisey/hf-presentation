"""Spec: PB-009

The shipped, deck-agnostic tools in ``scripts/``: ``shoot.py`` screenshots any assembled deck at every
slide × step × review size (optionally every reader note) into ``<slide>-<step>-<w>x<h>.png`` files plus a
``shots.json`` index; ``layout_guard.py`` checks every slide × step × size for overlap, overflow,
off-canvas and occlusion faults, exits 1 with a readable list and has a stable JSON report for the gate
runner. Both are PEP 723 scripts run with ``uv run``; fonts stay with ``assemble.py``.

Coverage: happy (exact file set and names for the core fixture at every review size, non-blank images,
index entries match files, notes-mode shots, guard clean on the core and module fixtures, ``--help``,
uv run for each) · edge (``--slides`` filter, a re-run drops only the files its previous index listed,
``--settle`` extra wait accepted) · negative (planted overlap and off-canvas element are reported with
their slide, step, size and kind; exit 1 on faults, 2 on a bad deck or size).
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageStat

from helper_engine import FIXTURE_SLIDES, MODULE_SLIDES, REVIEW_SIZES, load_assemble
from helper_skill import SKILL_DIR

SCRIPTS = SKILL_DIR / "scripts"
SHOOT = SCRIPTS / "shoot.py"
GUARD = SCRIPTS / "layout_guard.py"
CORE_IDS = re.findall(r'<section class="[^"]*" id="([\w-]+)"', FIXTURE_SLIDES)
CORE_STEPS = {"s-1": 0, "s-2": 3, "s-3": 2, "s-4": 0}
CORE_NOTES = {"s-1": 1, "s-2": 2, "s-3": 1, "s-4": 0}
SIZE_IDS = [f"{w}x{h}" for w, h in REVIEW_SIZES]
REPORT_KEYS = {"tool", "version", "deck", "sizes", "states", "ok", "faults"}
FAULT_KEYS = {"slide", "step", "size", "kind", "check", "target"}
KINDS = {"overlap", "overflow", "off-canvas", "occlusion"}


# ---------- helpers and fixtures ----------

def _load(path: Path, name: str):
    """Import a shipped script by path (``scripts/`` is not a package)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run(script: Path, *args, uv=False):
    """Run a shipped CLI (with the test interpreter, or through ``uv run`` to prove PEP 723)."""
    cmd = [shutil.which("uv"), "run", "--quiet", str(script)] if uv else [sys.executable, str(script)]
    return subprocess.run(cmd + [str(a) for a in args], capture_output=True, text=True, timeout=600)


def _deck(path: Path, slides: str, deck_css: str = "") -> Path:
    """Assemble a fixture deck with the shipped assembler (default theme), planting optional DECK CSS."""
    asm = load_assemble()
    asm.new(path, "Tool Fixture", "Generic tools", slides=slides)
    if deck_css:
        path.write_text(asm.fill(path.read_text(encoding="utf-8"), {"DECK": deck_css}), encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def shoot():
    return _load(SHOOT, "pb_shoot")


@pytest.fixture(scope="module")
def guard():
    return _load(GUARD, "pb_layout_guard")


@pytest.fixture(scope="module")
def core_deck(tmp_path_factory):
    return _deck(tmp_path_factory.mktemp("core") / "core.html", FIXTURE_SLIDES)


@pytest.fixture(scope="module")
def module_deck(tmp_path_factory):
    return _deck(tmp_path_factory.mktemp("mod") / "modules.html", MODULE_SLIDES)


@pytest.fixture(scope="module")
def faulty_deck(tmp_path_factory):
    """A body pushed over its title (s-2) and a paragraph pushed past the right edge (s-4)."""
    css = ("@layer deck { #s-2 > .body { translate: 0 -30vh; } "
           "#s-4 .body p { translate: 120vw 0; } }")
    return _deck(tmp_path_factory.mktemp("bad") / "faulty.html", FIXTURE_SLIDES, css)


@pytest.fixture(scope="module")
def core_shots(shoot, core_deck, tmp_path_factory):
    out = tmp_path_factory.mktemp("shots")
    index = shoot.shoot(core_deck, out, REVIEW_SIZES)
    return out, index


def _blank(png: Path) -> bool:
    """True when every channel of the image is a single value (nothing drawn)."""
    with Image.open(png) as im:
        return all(lo == hi for lo, hi in im.convert("RGB").getextrema())


# ---------- shoot ----------

def test_shoot_writes_one_file_per_slide_step_and_size_with_evidence_names(core_shots):
    out, _ = core_shots
    want = {f"{s}-{k}-{w}x{h}.png" for s, n in CORE_STEPS.items() for k in range(n + 1) for w, h in REVIEW_SIZES}
    assert {p.name for p in out.glob("*.png")} == want


def test_shoot_images_are_at_the_viewport_size_and_not_blank(core_shots):
    out, _ = core_shots
    for p in sorted(out.glob("*.png")):
        w, h = (int(v) for v in p.stem.rsplit("-", 1)[1].split("x"))
        with Image.open(p) as im:
            assert im.size == (w, h), p.name
        assert not _blank(p), p.name


def test_shoot_steps_differ_where_the_slide_builds(core_shots):
    """A shot taken before the step's reveal landed would match the previous step."""
    out, _ = core_shots
    a, b = (Image.open(out / f"s-2-{k}-1920x1080.png").convert("RGB") for k in (0, 1))
    from PIL import ImageChops
    assert ImageChops.difference(a, b).getbbox() is not None


def test_shoot_index_lists_every_file_with_slide_step_and_size(core_shots):
    out, index = core_shots
    on_disk = json.loads((out / "shots.json").read_text(encoding="utf-8"))
    assert on_disk == index
    assert on_disk["sizes"] == SIZE_IDS
    assert on_disk["slides"] == [{"id": s, "steps": CORE_STEPS[s]} for s in CORE_IDS]
    assert {e["file"] for e in on_disk["shots"]} == {p.name for p in out.glob("*.png")}
    for e in on_disk["shots"]:
        assert e["mode"] == "step" and e["file"] == f"{e['slide']}-{e['step']}-{e['size']}.png"


def test_shoot_notes_mode_adds_one_shot_per_reader_note(shoot, core_deck, tmp_path):
    index = shoot.shoot(core_deck, tmp_path, [(1280, 720)], notes=True)
    notes = [e for e in index["shots"] if e["mode"] == "notes"]
    want = {f"{s}-n{i}-1280x720.png" for s, n in CORE_NOTES.items() for i in range(1, n + 1)}
    assert {e["file"] for e in notes} == want
    assert all((tmp_path / f).exists() and not _blank(tmp_path / f) for f in want)
    a, b = (Image.open(tmp_path / f"s-2-n{i}-1280x720.png").convert("RGB") for i in (1, 2))
    from PIL import ImageChops
    assert ImageChops.difference(a, b).getbbox() is not None, "each note shot focuses its own note"


def test_shoot_slides_filter_via_uv_writes_only_those_slides_and_drops_stale_indexed_files(module_deck, tmp_path):
    """Stale shots from an earlier run would be mistaken for the current deck; other files stay."""
    (tmp_path / "x-9-1x1.png").write_bytes(b"stale")
    (tmp_path / "keep.txt").write_text("mine")
    (tmp_path / "shots.json").write_text(json.dumps({"shots": [{"file": "x-9-1x1.png"}]}))
    r = run(SHOOT, module_deck, tmp_path, "--slides", "m-2,m-5", "--sizes", "1288x598", "--settle", "50", uv=True)
    assert r.returncode == 0, r.stderr
    assert {p.name for p in tmp_path.glob("*.png")} == {f"m-2-{k}-1288x598.png" for k in range(4)} | {
        "m-5-0-1288x598.png"}
    assert (tmp_path / "keep.txt").exists()
    index = json.loads((tmp_path / "shots.json").read_text())
    assert [s["id"] for s in index["slides"]] == ["m-2", "m-5"] and index["settle_ms"] == 50


def test_shoot_refuses_an_unknown_slide_or_bad_size(shoot, core_deck, tmp_path):
    assert shoot.main([str(core_deck), str(tmp_path), "--slides", "nope"]) == 2
    assert shoot.main([str(core_deck), str(tmp_path), "--sizes", "wide"]) == 2
    assert not list(tmp_path.glob("*.png"))


# ---------- layout guard ----------

def test_guard_finds_no_fault_on_the_core_fixture_at_every_review_size(guard, core_deck):
    report = guard.guard(core_deck, REVIEW_SIZES)
    assert report["faults"] == [] and report["ok"] is True
    assert report["states"] == sum(n + 1 for n in CORE_STEPS.values()) * len(REVIEW_SIZES)


def test_guard_via_uv_is_clean_on_the_module_fixture_with_a_stable_json_report(module_deck):
    r = run(GUARD, module_deck, "--json", uv=True)
    assert r.returncode == 0, r.stdout + r.stderr
    report = json.loads(r.stdout)
    assert set(report) == REPORT_KEYS
    assert (report["tool"], report["version"], report["ok"], report["faults"]) == ("layout_guard", 1, True, [])
    assert report["sizes"] == SIZE_IDS and report["deck"] == str(module_deck)


@pytest.fixture(scope="module")
def faulty_report(guard, faulty_deck):
    return guard.guard(faulty_deck, [(1280, 720)])


def test_guard_reports_a_planted_overlap_with_slide_step_size_and_kind(faulty_report):
    hits = [f for f in faulty_report["faults"] if f["slide"] == "s-2" and f["check"] == "covers title"]
    assert hits, faulty_report["faults"]
    assert all(f["kind"] == "overlap" and f["size"] == "1280x720" for f in hits)
    assert {f["step"] for f in hits} == {0, 1, 2, 3}


def test_guard_reports_a_planted_off_canvas_element(faulty_report):
    hits = [f for f in faulty_report["faults"] if f["slide"] == "s-4" and f["kind"] == "off-canvas"]
    assert hits and hits[0]["step"] == 0 and '"No steps here."' in hits[0]["target"], faulty_report["faults"]
    assert not [f for f in faulty_report["faults"] if f["slide"] in ("s-1", "s-3")], "faults stay on their slides"


def test_guard_fault_records_have_a_fixed_schema(faulty_report):
    assert set(faulty_report) == REPORT_KEYS and faulty_report["ok"] is False
    for f in faulty_report["faults"]:
        assert set(f) == FAULT_KEYS and f["kind"] in KINDS, f


def test_guard_cli_exits_1_with_a_readable_fault_list(guard, faulty_deck, capsys):
    assert guard.main([str(faulty_deck), "--sizes", "1280x720", "--slides", "s-2,s-4"]) == 1
    out = capsys.readouterr().out
    assert re.search(r"^FAIL s-2@0 1280x720 overlap: covers title: ", out, re.M), out
    assert re.search(r"^FAIL s-4@0 1280x720 off-canvas: ", out, re.M), out


def test_guard_cli_exits_2_on_a_missing_deck_or_bad_size(guard, core_deck, tmp_path):
    assert guard.main([str(tmp_path / "missing.html")]) == 2
    assert guard.main([str(core_deck), "--sizes", "1280"]) == 2


def test_guard_needs_no_page_chrome_to_run(guard, tmp_path):
    """Deck-agnostic: a deck without the bar or notes button is checked, not crashed on."""
    src = load_assemble().new(tmp_path / "d.html", "T", slides=FIXTURE_SLIDES).read_text(encoding="utf-8")
    bare = re.sub(r'<button [^>]*class="notes-btn".*?</button>', "", src, flags=re.S)
    (tmp_path / "bare.html").write_text(bare, encoding="utf-8")
    assert guard.guard(tmp_path / "bare.html", [(1280, 720)], slides=["s-2"])["ok"] is True


# ---------- both CLIs ----------

@pytest.mark.parametrize("script", [SHOOT, GUARD], ids=["shoot", "layout_guard"])
def test_cli_help_names_its_options(script):
    r = run(script, "--help")
    assert r.returncode == 0
    for opt in ("--sizes", "--slides") + (("--settle", "--notes") if script == SHOOT else ("--json",)):
        assert opt in r.stdout, opt


@pytest.mark.parametrize("script", [SHOOT, GUARD], ids=["shoot", "layout_guard"])
def test_cli_is_a_pep723_script_depending_on_playwright(script):
    head = re.match(r"# /// script\n(.*?)# ///\n", script.read_text(encoding="utf-8"), re.S)
    assert head and "playwright" in head.group(1)

