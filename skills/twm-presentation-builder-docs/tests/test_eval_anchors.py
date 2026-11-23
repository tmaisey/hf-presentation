"""Spec: PB-020

Flawed anchor decks: small self-contained decks under ``evals/anchors/``, each carrying one or a few
deliberate flaws and labelled in ``anchors.json`` with the criteria it must fail and a few it must
still pass, so a lenient judge or a broken gate is caught without a presenter-scored calibration set.

Coverage: happy (label schema, every id and tag resolves through the loader, files exist, single-file,
offline and small; a clean control) · edge (a collision present only at the short-wide size; the
required flaw kinds are all covered; labels agree with the criteria's own flaw tags) · negative (each
labelled flaw a code check can see is measurably present when rendered in Chrome, and each listed
must-pass check finds nothing; no incident terms outside reference-verdict anchors; no label leaks
into the deck a judge sees; slides carry no styling).
"""

from __future__ import annotations

import json
import re

import pytest
from playwright.sync_api import sync_playwright

from helper_engine import REVIEW_SIZES, block, open_deck, settle
from helper_eval import EVAL_DIR, INCIDENT_TERMS, ORIGINS, loader

ANCHOR_DIR = EVAL_DIR / "anchors"
LABELS = ANCHOR_DIR / "anchors.json"
ANCHOR_FIELDS = ("id", "file", "name", "flaws", "must_fail", "must_pass", "where", "provenance",
                 "description")
MAX_BYTES = 150_000
SHORT_WIDE = (1288, 598)
SHORT_WIDE_ANCHOR = "AN-01"  # the collision that only the short-wide window shows
# flaw kinds PB-020 must cover (brief + kernel): collisions, contrast, voice-rejected titles,
# sourcing, the first-draft faults, accent as text, ambient motion on a diagram, a sourceless note
REQUIRED_FLAWS = {"occluded-content", "insufficient-contrast", "hook-title", "title-form",
                  "unsourced-claim", "altered-quote", "restated-steps", "cluttered-layout",
                  "sparse-layout", "distant-annotation", "role-misuse", "distracting-animation",
                  "broken-link"}
# words that would tell a judge what it is looking at
LEAKS = re.compile(r"\banchor|\bflaw|deliberate|must[_ ]fail|must[_ ]pass|\bcontrol\b|"
                   r"\b(?:CN|RS|VC|DL|DP|DS|AR|PX|PR)-\d\d\b", re.I)
STEP_WORDS = 40  # CN-04 default word budget


# ---------- labels ----------

@pytest.fixture(scope="module")
def labels():
    assert LABELS.is_file(), "evals/anchors/anchors.json missing"
    return json.loads(LABELS.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def anchors(labels):
    return labels["anchors"]


@pytest.fixture(scope="module")
def library():
    return loader().load_library(EVAL_DIR)


@pytest.fixture(scope="module")
def flaw_tags():
    return loader().load_flaws(EVAL_DIR)


def _html(a) -> str:
    return (ANCHOR_DIR / a["file"]).read_text(encoding="utf-8")


def test_label_file_states_how_to_read_a_label(labels):
    assert set(labels) == {"about", "verdict_rule", "anchors"}
    assert labels["about"].strip()
    rule = labels["verdict_rule"]
    assert set(rule) == {"must_fail", "must_pass"}
    assert all("scale" in rule[k] and "binary" in rule[k] for k in rule), "both forms covered"


def test_anchors_are_unique_and_fields_in_order(anchors):
    assert len(anchors) >= 10
    assert [tuple(a) for a in anchors] == [ANCHOR_FIELDS] * len(anchors)
    ids = [a["id"] for a in anchors]
    assert len(set(ids)) == len(ids) and all(re.fullmatch(r"AN-\d\d", i) for i in ids)
    files = [a["file"] for a in anchors]
    assert len(set(files)) == len(files)


def test_file_names_do_not_name_the_flaw(anchors):
    """A judge may see the path; a name like 'low-contrast.html' would hand it the verdict."""
    assert all(re.fullmatch(r"an-\d\d\.html", a["file"]) for a in anchors)


def test_every_label_resolves_in_the_library(anchors, library, flaw_tags):
    for a in anchors:
        assert set(a["must_fail"]) <= set(library), a["id"]
        assert set(a["must_pass"]) <= set(library), a["id"]
        assert set(a["flaws"]) <= set(flaw_tags), a["id"]
        assert not set(a["must_fail"]) & set(a["must_pass"]), a["id"]
        assert a["must_pass"], f"{a['id']}: a few passes keep judges from failing everything"
        assert len(set(a["must_fail"])) == len(a["must_fail"]) and len(set(a["must_pass"])) == len(a["must_pass"])


def test_each_failed_criterion_names_one_of_the_anchors_flaws(anchors, library):
    """Labels agree with the library: a criterion only fails an anchor for a flaw it is defined to catch."""
    for a in anchors:
        for cid in a["must_fail"]:
            assert set(library[cid]["flaws"]) & set(a["flaws"]), f"{a['id']} {cid}"
        for tag in a["flaws"]:
            assert any(tag in library[c]["flaws"] for c in a["must_fail"]), f"{a['id']} {tag} unexplained"


def test_one_clean_control_and_every_other_anchor_is_flawed(anchors):
    clean = [a for a in anchors if not a["flaws"]]
    assert len(clean) == 1 and clean[0]["must_fail"] == []
    assert len(clean[0]["must_pass"]) >= 10, "the control is checked against most of the gates"
    assert all(a["flaws"] and a["must_fail"] for a in anchors if a is not clean[0])
    assert all(len(a["flaws"]) <= 4 for a in anchors), "one or a few flaws per anchor"


def test_anchors_cover_the_required_flaw_kinds(anchors):
    assert REQUIRED_FLAWS <= {t for a in anchors for t in a["flaws"]}


def test_provenance_is_synthetic_or_cites_a_recorded_verdict(anchors):
    origins = set()
    for a in anchors:
        p = a["provenance"]
        assert p["origin"] in ORIGINS - {"reference-deck"}, a["id"]
        origins.add(p["origin"])
        if p["origin"] == "reference-verdict":
            assert str(p.get("cite", "")).strip(), f"{a['id']} must cite where the verdict is recorded"
    assert origins == {"synthetic", "reference-verdict"}


def test_where_and_description_say_where_the_flaw_is(anchors):
    for a in anchors:
        assert a["where"].strip() and len(a["description"].split()) >= 8, a["id"]


# ---------- files ----------

def test_every_file_exists_is_one_html_file_within_budget(anchors):
    for a in anchors:
        path = ANCHOR_DIR / a["file"]
        assert path.is_file(), a["file"]
        src = path.read_text(encoding="utf-8")
        assert src.lstrip().lower().startswith("<!doctype html>")
        assert src.count("<script") == 1, "modules and engine in one script"
        assert path.stat().st_size < MAX_BYTES, f"{a['file']}: {path.stat().st_size} bytes"
        assert "@font-face" not in src, "no embedded fonts: anchors stay small"


def test_only_anchor_files_and_labels_live_in_the_folder(anchors):
    expected = {a["file"] for a in anchors} | {"anchors.json"}
    assert {p.name for p in ANCHOR_DIR.iterdir()} == expected


def test_files_reference_nothing_remote(anchors):
    for a in anchors:
        src = _html(a)
        remote = re.findall(r"""(?:src|href)\s*=\s*["']?(?:https?:)?//[^"'\s>]+""", src)
        cites = re.findall(r"""<a class="src" href="https://[^"]+""", src)
        assert len(remote) == len(cites), f"{a['file']}: remote reference outside a citation"
        assert not re.search(r"@import|url\(\s*['\"]?(?:https?:)?//", src), a["file"]


def test_slides_carry_no_styling_or_scripts(anchors):
    """Flaws live in copy, markup or the deck layer, never in per-slide styling (AR-04 holds everywhere)."""
    for a in anchors:
        slides = block(_html(a), "SLIDES").group(1)
        assert slides.strip(), a["file"]
        assert not re.search(r"<style|<script|\sstyle\s*=", slides, re.I), a["file"]
        assert not re.search(r"#[0-9a-f]{3,8}\b(?![-\w])|rgba?\(", slides, re.I), a["file"]


def test_theme_blocks_are_the_generated_paper_green_editorial_theme(anchors):
    for a in anchors:
        src = _html(a)
        pal, sty = block(src, "PALETTE").group(1), block(src, "STYLE").group(1)
        assert "@layer palette" in pal and "--sys-color-accent:" in pal, a["file"]
        assert "@layer style" in sty and "--sys-type-title-size:" in sty, a["file"]
        assert "@layer components" in block(src, "COMPONENTS").group(1), a["file"]


def test_no_incident_terms_outside_reference_verdict_anchors(anchors):
    for a in anchors:
        if a["provenance"]["origin"] == "reference-verdict":
            continue
        text = _html(a) + json.dumps({k: v for k, v in a.items() if k != "provenance"})
        hit = INCIDENT_TERMS.search(text)
        assert not hit, f"{a['id']}: {hit.group(0)!r}"


def test_label_file_prose_is_generic_outside_reference_cites(labels):
    hit = INCIDENT_TERMS.search(labels["about"] + json.dumps(labels["verdict_rule"]))
    assert not hit, hit and hit.group(0)


def test_decks_do_not_leak_their_labels(anchors):
    for a in anchors:
        src = _html(a)
        for name in ("SLIDES", "DECK", "COMPONENTS"):
            hit = LEAKS.search(block(src, name).group(1))
            assert not hit, f"{a['file']} {name}: {hit.group(0)!r}"
        assert not LEAKS.search(re.search(r"<title>(.*?)</title>", src).group(1)), a["file"]


# ---------- rendered checks ----------

# Runs in the page on the active slide: tight text-line boxes, tiles and annotation boxes, every visible
# text run with its colour and composited background, and the slide's static facts.
PROBE = r"""() => {
  const s = document.querySelector('.slide.is-active');
  const cv = document.createElement('canvas'); cv.width = cv.height = 1;
  const cx = cv.getContext('2d', { willReadFrequently: true });
  const rgba = c => { if (!c || c === 'none') return [0, 0, 0, 0]; cx.clearRect(0, 0, 1, 1);
    cx.fillStyle = 'rgba(0,0,0,0)'; cx.fillStyle = c; cx.fillRect(0, 0, 1, 1);
    const d = cx.getImageData(0, 0, 1, 1).data; return [d[0], d[1], d[2], d[3] / 255]; };
  const over = (top, bot) => { const a = top[3]; return [0, 1, 2].map(i => top[i] * a + bot[i] * (1 - a)).concat(1); };
  const hidden = e => { for (let n = e; n && n !== document.documentElement; n = n.parentElement) {
      const cs = getComputedStyle(n); if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity < .05) return true; }
    return false; };
  const alpha = e => { let a = 1; for (let n = e; n && n !== document.documentElement; n = n.parentElement) a *= +getComputedStyle(n).opacity; return a; };
  const out = e => e.closest('aside.note, .ambient');
  const label = e => (e.id ? '#' + e.id : e.tagName.toLowerCase() + '.' + [...e.classList].join('.')) + ' «' + e.textContent.trim().slice(0, 28) + '»';
  const R = r => ({ l: r.left, t: r.top, r: r.right, b: r.bottom });
  const lines = e => { const rg = document.createRange(); rg.selectNodeContents(e);
    return [...rg.getClientRects()].filter(r => r.width > 1 && r.height > 1).map(R); };
  // layout boxes: outermost text blocks (tight line boxes), tiles, annotation tiles, fixed chrome
  const BLOCKS = 'h2, h3, p, li, blockquote, figcaption, .narr-tile, .quote, g.tile';
  const cands = [...s.querySelectorAll(BLOCKS)].filter(e => !out(e) && !hidden(e));
  const top = cands.filter(e => !cands.some(o => o !== e && o.contains(e)));
  const boxes = top.map(e => ({ who: label(e), solid: e.matches('.narr-tile, .quote, g.tile'),
    rects: e.matches('.narr-tile, .quote, g.tile') ? [R(e.getBoundingClientRect())] : lines(e) }))
    .concat(['.bar', '.notes-btn'].map(q => document.querySelector(q)).filter(Boolean)
      .map(e => ({ who: label(e), solid: true, chrome: true, rects: [R(e.getBoundingClientRect())] })));
  // text runs with fg/bg
  const bodyBg = rgba(getComputedStyle(document.body).backgroundColor);
  const bgOf = e => { const layers = [];
    const tile = e instanceof SVGElement && e.closest('g.tile');
    if (tile) layers.push(rgba(getComputedStyle(tile.querySelector('rect')).fill));
    for (let n = e; n && n !== document.documentElement; n = n.parentElement) {
      const c = rgba(getComputedStyle(n).backgroundColor); if (c[3] > 0) layers.push(c); if (c[3] >= 1) break; }
    return layers.reverse().reduce((bot, l) => over(l, bot), bodyBg); };
  const accent = (() => { const p = document.createElement('span'); p.style.color = 'var(--sys-color-accent)';
    document.body.append(p); const c = rgba(getComputedStyle(p).color); p.remove(); return c; })();
  const runs = [...s.querySelectorAll('*')].filter(e => !out(e) && !hidden(e)
      && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()))
    .map(e => { const cs = getComputedStyle(e), svg = e instanceof SVGElement;
      const fg = rgba(svg ? cs.fill : cs.color);
      return { who: label(e), text: [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join(' ').trim(),
        fg: over([fg[0], fg[1], fg[2], fg[3] * alpha(e)], bgOf(e)), bg: bgOf(e), px: parseFloat(cs.fontSize),
        weight: +cs.fontWeight, accent: [0, 1, 2].every(i => Math.abs(fg[i] - accent[i]) <= 2),
        kicker: !!e.closest('.kicker') }; });
  // annotations and the diagram parts revealed at the same step
  const tiles = [...s.querySelectorAll('svg.diagram g.tile[data-show-at]')].filter(e => !hidden(e));
  const titles = [...s.querySelectorAll('.title')].filter(e => !hidden(e)).flatMap(lines);
  const notes = [...s.querySelectorAll('aside.note')];
  const notesText = notes.map(n => n.textContent).join(' ');
  const annotations = [...s.querySelectorAll('.narr-tile, .quote')].filter(e => !hidden(e)).map(e => {
    const n = e.dataset.at || e.dataset.showAt, b = R(e.getBoundingClientRect());
    const refs = tiles.filter(t => t.dataset.showAt === n).map(t => R(t.getBoundingClientRect()));
    const gap = r => Math.max(0, r.l - b.r, b.l - r.r, r.t - b.b, b.t - r.b);
    return { who: label(e), gap: refs.length ? Math.min(...refs.map(gap)) / innerWidth : null,
      overTitle: titles.some(t => t.l < b.r - 2 && b.l < t.r - 2 && t.t < b.b - 2 && b.t < t.b - 2) }; });
  return {
    vw: innerWidth, vh: innerHeight, boxes, runs, annotations,
    lead: s.classList.contains('slide--lead'),
    titles: [...s.querySelectorAll('.title')].map(t => ({ text: t.textContent.trim(), em: t.querySelectorAll('em, i').length })),
    steps: [...s.querySelectorAll('ol.steps > li')].map(li => li.textContent.trim()),
    tileTitles: [...s.querySelectorAll('svg.diagram .tile-title')].map(t => t.textContent.trim()),
    quotes: [...s.querySelectorAll('blockquote')].filter(q => !out(q)).map(q => q.textContent.trim()),
    notes: notes.map(n => ({ text: n.textContent, srcs: [...n.querySelectorAll('a.src')].map(a => a.getAttribute('href')) })),
    notesText,
    ambient: !!s.querySelector(':scope > .ambient'),
    builds: !!s.querySelector('svg.diagram, [data-show-at], [data-at]'),
  };
}"""

WELL_FORMED = re.compile(r"^https://[a-z0-9-]+(?:\.[a-z0-9-]+)+/\S+$")
CITATION_TEXT = re.compile(r"\bsources?\s*:", re.I)
QUOTE_MARKS = str.maketrans("", "", "“”\"‘’'")


def _lum(c):
    v = [x / 255 for x in c[:3]]
    v = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]


def contrast(fg, bg) -> float:
    """WCAG 2 ratio of two opaque RGB colours, never rounded."""
    a, b = sorted((_lum(fg), _lum(bg)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def _norm(text: str) -> str:
    return " ".join(text.translate(QUOTE_MARKS).split()).lower()


def collisions(m) -> list[str]:
    """Overlapping or off-canvas boxes in one probe (DL-01)."""
    hits, boxes = [], m["boxes"]
    for i, a in enumerate(boxes):
        for r in a["rects"]:
            if not a.get("chrome") and (r["l"] < -1 or r["t"] < -1 or r["r"] > m["vw"] + 1 or r["b"] > m["vh"] + 1):
                hits.append(f"off-canvas {a['who']}")
        for b in boxes[i + 1:]:
            if a.get("chrome") and b.get("chrome"):
                continue
            if any(min(r["r"], q["r"]) - max(r["l"], q["l"]) > 2 and min(r["b"], q["b"]) - max(r["t"], q["t"]) > 2
                   for r in a["rects"] for q in b["rects"]):
                hits.append(f"{a['who']} × {b['who']}")
    return hits


def low_contrast(m) -> list[str]:
    """Text runs below their WCAG threshold (DP-01)."""
    out = []
    for r in m["runs"]:
        large = r["px"] >= 24 or (r["px"] >= 18.5 and r["weight"] >= 700)
        ratio = contrast(r["fg"], r["bg"])
        if ratio < (3.0 if large else 4.5):
            out.append(f"{r['who']} {ratio:.2f}:1 at {r['px']:.0f}px")
    return out


def words(m) -> int:
    """Visible words on the slide, reader notes excluded (CN-04)."""
    return sum(len([w for w in r["text"].split() if re.search(r"\w", w)]) for r in m["runs"])


def static_checks(m) -> dict[str, list[str]]:
    """Checks that read one slide's markup facts, independent of size and step."""
    out: dict[str, list[str]] = {}
    bad_titles = [t["text"] for t in m["titles"] if t["text"].endswith(".") or t["em"] > 1
                  or re.search(r"[.!?]\s+\S", t["text"])]
    out["VC-03"] = bad_titles
    out["VC-01"] = [t["text"] for t in m["titles"] if t["text"].endswith("?")]
    out["CN-08"] = [] if m["lead"] or m["notes"] else ["content slide without a reader note"]
    out["RS-05"] = [s for n in m["notes"] for s in n["srcs"] if not WELL_FORMED.match(s or "")] + [
        n["text"].strip()[:60] for n in m["notes"] if not n["srcs"] and CITATION_TEXT.search(n["text"])]
    out["DS-03"] = ["ambient layer on a slide that builds or holds a diagram"] if m["ambient"] and m["builds"] else []
    out["CN-05"] = [s for s in m["steps"] if any(t.lower() in s.lower() for t in m["tileTitles"] if t)]
    notes = _norm(m["notesText"])
    out["RS-03"] = [f for q in m["quotes"] for f in re.split(r"\[(?:…|\.\.\.)\]", q)
                    if len(_norm(f)) > 3 and _norm(f).strip(" ,.;:—-") not in notes]
    linked = any(WELL_FORMED.match(s or "") for n in m["notes"] for s in n["srcs"])
    figures = [r["text"] for r in m["runs"] if not r["kicker"] and re.search(r"\d", r["text"])]
    out["RS-01"] = figures if figures and not linked else []
    return out


def step_checks(m) -> dict[str, list[str]]:
    """Checks that read one rendered state (a slide at a step and size)."""
    return {
        "DL-01": collisions(m),
        "DP-01": low_contrast(m),
        "DP-04": [r["who"] for r in m["runs"] if r["accent"]],
        "DL-07": [a["who"] for a in m["annotations"] if a["overTitle"] or (a["gap"] is not None and a["gap"] > 0.25)],
        "CN-04": [f"{words(m)} words"] if words(m) > STEP_WORDS else [],
    }


# criteria whose flaw these probes can see; every other labelled criterion is a judge's call
CHECKED = {"DL-01", "DP-01", "DP-04", "DL-07", "CN-04", "VC-03", "VC-01", "CN-08", "RS-05", "DS-03",
           "CN-05", "RS-03", "RS-01"}


@pytest.fixture(scope="module")
def browser():
    """System Chrome, once per module (no conftest: other suites share this folder)."""
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        yield b
        b.close()


def _goto(page, sid, k):
    page.evaluate("([s, k]) => deck.goto(s, k)", [sid, k])
    page.wait_for_function("([s, k]) => deck.state().slide === s && deck.state().step === k", arg=[sid, k])
    settle(page)


def _measure(browser, a) -> dict:
    """Render one anchor at every review size, slide and step; return findings per check and size."""
    found: dict[str, dict[str, list[str]]] = {c: {} for c in CHECKED}
    for w, h in REVIEW_SIZES:
        ctx = browser.new_context(viewport={"width": w, "height": h})
        page = ctx.new_page()
        open_deck(page, ANCHOR_DIR / a["file"])
        size = f"{w}x{h}"
        for sid, last in page.evaluate("deck.plan()"):
            for k in range(last + 1):
                _goto(page, sid, k)
                m = page.evaluate(PROBE)
                checks = step_checks(m) | (static_checks(m) if size == "1280x720" else {})
                for cid, hits in checks.items():
                    found[cid].setdefault(size, []).extend(f"{sid}:{k} {x}" for x in hits)
        ctx.close()
    return found


@pytest.fixture(scope="module")
def measured(browser, anchors):
    return {a["id"]: _measure(browser, a) for a in anchors}


def _hits(found, cid, size=None):
    sizes = found[cid]
    return [x for s, v in sizes.items() if size in (None, s) for x in v]


def test_every_failed_deterministic_criterion_has_a_check(anchors, library):
    """A D-criterion an anchor must fail is proved present here, never only asserted in the label."""
    for a in anchors:
        for cid in a["must_fail"]:
            if library[cid]["evidence"] == "D":
                assert cid in CHECKED, f"{a['id']} {cid}"


def test_labelled_flaws_are_present_when_rendered(anchors, measured):
    missing = [f"{a['id']} {cid}" for a in anchors for cid in a["must_fail"]
               if cid in CHECKED and not _hits(measured[a["id"]], cid)]
    assert missing == []


def test_must_pass_checks_find_nothing(anchors, measured):
    """Anchors fail only where labelled, so a judge that fails everything is caught too."""
    found = {f"{a['id']} {cid}": _hits(measured[a["id"]], cid)[:3]
             for a in anchors for cid in a["must_pass"] if cid in CHECKED and _hits(measured[a["id"]], cid)}
    assert found == {}


def test_control_shows_no_flaw_any_check_can_see(anchors, measured):
    control = next(a for a in anchors if not a["flaws"])
    found = {cid: _hits(measured[control["id"]], cid)[:3] for cid in CHECKED if _hits(measured[control["id"]], cid)}
    assert found == {}
    assert CHECKED - {"VC-01"} <= set(control["must_pass"]), "the control lists what it is checked for"


def test_collision_shows_only_in_the_short_wide_window(measured):
    found = measured[SHORT_WIDE_ANCHOR]
    assert _hits(found, "DL-01", "1288x598"), "overlap expected at 1288×598"
    assert _hits(found, "DL-01", "1920x1080") == [] and _hits(found, "DL-01", "1280x720") == []


def test_low_contrast_is_below_threshold_not_just_near_it(anchors, measured):
    """The contrast anchor is a clear fail (< 4.5:1 on small body text), not a rounding question."""
    for a in anchors:
        if "insufficient-contrast" in a["flaws"]:
            ratios = [float(re.search(r" (\d+\.\d+):1", x).group(1)) for x in _hits(measured[a["id"]], "DP-01")]
            assert ratios and min(ratios) < 4.0, a["id"]


def test_ambient_motion_drifts_on_the_diagram_slide(browser, anchors):
    """The flaw is motion, not just markup: the orbs behind the diagram really move while it is shown."""
    for a in (x for x in anchors if "DS-03" in x["must_fail"]):
        ctx = browser.new_context(viewport={"width": 1280, "height": 720})
        page = ctx.new_page()
        open_deck(page, ANCHOR_DIR / a["file"])
        sid = page.evaluate("document.querySelector('.slide[data-ambient]:has(svg.diagram)').id")
        _goto(page, sid, 0)
        t0 = page.evaluate("s => document.querySelector('#' + s + ' .ambient .orb').style.transform", sid)
        page.wait_for_function("([s, t]) => document.querySelector('#' + s + ' .ambient .orb').style.transform !== t",
                               arg=[sid, t0], timeout=5000)
        ctx.close()


def test_anchors_render_offline_without_errors(browser, anchors):
    for a in anchors:
        ctx = browser.new_context(viewport={"width": 1280, "height": 720})
        page = ctx.new_page()
        requests, errors = [], []
        page.route("**/*", lambda r: r.continue_() if r.request.url.startswith("file:") else
                   (requests.append(r.request.url), r.abort()))
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda msg: msg.type == "error" and errors.append(msg.text))
        open_deck(page, ANCHOR_DIR / a["file"])
        for sid, last in page.evaluate("deck.plan()"):
            _goto(page, sid, last)
        ctx.close()
        assert requests == [] and errors == [], a["id"]
