"""Spec: S-025

v2 slide s-7 (Takeover) on the incident world, continuing from s-6's end state (Hugging Face cut
access, 13 Jul): at 19 Jul a third layout stage widens OpenAI's box (Hugging Face and the internet
strip dissolve); a separate evaluation's runs of a different, Astra-family model join the shared
mirror; agents read cloud secrets and root a node running the mirror; that model's agents take
cluster-admin on the OpenAI cluster running the mirror (the open padlock of s-6's clusters).
Coverage: happy (shell; four states; timeline builds an entry per step; world parts per step; the
OpenAI box widens and holds every new part; the new runs sit apart from the HF-phase swarm and link
into the mirror; the secrets tile; the mirror's padlock opens; the cluster is a key tile whose
padlock pops after it appears, with bold lines from the new runs; verbatim source tiles; sourced
notes) · edge (step 0 is s-6's end state exactly; going back to step 0 narrows OpenAI again; reduced
motion shows end states; no tile, run or tag overlaps) · negative (Hugging Face parts gone from step
1; no padlock change or new parts before their step; no "same agents", "eval cluster", Aug 15, Sep
DNS escape or post-scope compromises in the slide body; credential reuse only in a note; no
standalone diagram; no console errors).
"""

import html
import re

import pytest

from helper_deck import goto_slide, open_deck, parse_slides, slides_source

pytestmark = pytest.mark.deck("v2")

SID = "s-7"
TITLE = "After Hugging Face cut access, a second model’s agents took control of an OpenAI cluster"
STEPS = 3   # states 0–3
TR_URL = "https://cdn.openai.com/pdf/67869394-cb91-4c12-888c-5cbd85c7814c/OpenAI-Hugging-Face%20Incident-Technical-Report.pdf"
# timeline: (id, step, numbered?, text fragments)
TIMELINE = [("s7-t1", 0, True, ("13 Jul", "cuts access", "OpenAI’s servers")),
            ("s7-t2", 1, True, ("19 Jul", "separate evaluation", "Astra-family")),
            ("s7-t2a", 2, False, ("956", "cloud secrets", "root", "mirror")),
            ("s7-t2b", 3, False, ("Astra-family", "cluster-admin", "mirror"))]
# s-6 parts whose story ends at the cut: they dissolve as OpenAI's box widens at 19 Jul
HF_END = {"w-net6", "w-hf", "w-modal", "w-breakout", "w-hf-workers", "w-hf-clusters", "w-hf-data",
          "w-hf-closed", "w-hf-cut", "w-key-act"}
WORLD_AT = {1: {"w-astra", "w-astra-links", "w-astra-tag"},
            2: {"w-secrets", "w-root"},
            3: {"w-oai-cluster", "w-astra-admin", "w-oai-lock"}}
ENDS = {"w-secure": 2}   # the mirror's closed padlock gives way to the open one
NARR_AT = {
    0: [("METR investigation", "agents compromised OpenAI infrastructure between July 13th and July 19th")],
    1: [("OpenAI · technical report", "While this model is from the same family as our next model, Astra, it was "
                                      "a distinct model with different post-training")],
    3: [("OpenAI · technical report", "The agents escalated to Kubernetes cluster-admin and created a privileged "
                                      "host-mounted pod.")],
}
NOTE_TARGETS = {"s7-t1", "w-astra", "w-secrets", "w-oai-cluster", "s7-t2b"}


def helper_section() -> str:
    m = re.search(r'<section class="slide" id="s-7"[^>]*>.*?</section>', slides_source(), re.S)
    assert m, "slide s-7 not built"
    return m.group(0)


def helper_text(markup: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", markup)).split())


def helper_world() -> str:
    m = re.search(r'<div class="world".*?</div>', slides_source(), re.S)
    assert m
    return m.group(0)


def helper_body() -> str:
    """The slide's own copy without its reader notes."""
    return re.sub(r'<aside class="note".*?</aside>', "", helper_section(), flags=re.S)


# ---------- shell and copy ----------

def test_takeover_sits_between_breakout_and_investigation_as_a_world_slide():
    ids = [s["attrs"]["id"] for s in parse_slides()]
    i = ids.index(SID)
    assert ids[i - 1] == "s-6" and ids[i + 1] == "s-8"
    s = parse_slides()[i]
    assert s["attrs"]["data-chapter"] == "Takeover" and s["attrs"].get("data-world", "x") in (None, "")
    assert " ".join(s["title"].split()) == TITLE
    assert re.search(r'<p class="kicker">07 · Takeover</p>', helper_section())


def test_shell_order_is_timeline_world_narration_notes_with_no_standalone_diagram():
    sec = helper_section()
    order = [sec.index(x) for x in ('<div class="body body--timeline"', '<div class="world-slot"',
                                    '<div class="narration"', '<aside class="note"')]
    assert order == sorted(order)
    assert '<svg class="diagram"' not in sec, "the first-draft standalone diagram is replaced by the world"
    assert "overlay--insight" not in sec, "a 1:00 slide: the title carries the finding"


def test_timeline_has_one_entry_per_step_with_dates_and_sub_points():
    items = re.findall(r'<li id="(s7-t\w+)"( class="sub")? data-show-at="(\d)">(.*?)</li>', helper_section(), re.S)
    got = [(i, int(a), not sub_, helper_text(t)) for i, sub_, a, t in items]
    assert [g[:3] for g in got] == [t[:3] for t in TIMELINE]
    for (_, _, _, text), (_, _, _, frags) in zip(got, TIMELINE):
        for f in frags:
            assert f in text, (f, text)


def test_narration_is_verbatim_source_tiles_per_step():
    narr = re.search(r'<div class="narration">(.*?)</div>', helper_section(), re.S).group(1)
    tiles = re.findall(r'<article class="narr-tile" data-at="(\d+)">\s*<p class="msg-agent">(.*?)</p>\s*'
                       r'<blockquote class="msg-text">(.*?)</blockquote>\s*</article>', narr, re.S)
    got: dict[int, list] = {}
    for at, label, text in tiles:
        got.setdefault(int(at), []).append((helper_text(label), helper_text(text)))
    assert got == NARR_AT
    assert len(re.findall(r"<article", narr)) == sum(len(v) for v in NARR_AT.values())
    for v in got.values():
        for _, text in v:
            assert not re.search(r'^[“"]|[”"]$', text), "CSS adds quote marks"


def test_notes_cite_each_beat_with_https_sources():
    notes = dict(re.findall(r'<aside class="note" data-for="#([\w-]+)">(.*?)</aside>', helper_section(), re.S))
    assert set(notes) == NOTE_TARGETS
    for target, body in notes.items():
        assert re.search(r"<h3>[^<]+</h3>", body) and re.search(r'<a class="src" href="https://', body), target
    assert TR_URL in notes["w-astra"] and TR_URL in notes["w-oai-cluster"] and TR_URL in notes["w-secrets"]
    text = helper_text(" ".join(notes.values()))
    for fact in ("14:14", "between July 13th and July 19th", "after the end of the dates in scope",
                 "different post-training", "credentials left behind by earlier runs on Artifactory",
                 "956", "14:43", "15:59", "16:35", "artifactory-3", "privileged host-mounted pod",
                 "DNS", "mid-August"):
        assert fact in text, fact


def test_body_states_only_confirmed_events_in_precise_words():
    """S-024: a different model's agents on 19 Jul; Sep DNS escape, Aug 15 and post-scope claims stay in notes."""
    text = helper_text(helper_body())
    for bad in (r"same agents", r"eval(uation)? cluster", r"Aug(ust)?\.? 15|15 Aug|mid-Aug", r"\bSep(t(ember)?)?\b",
                r"DNS", r"after the end of the dates", r"suicid", r"credential", r"left behind"):
        assert not re.search(bad, text, re.I), bad
    assert "Astra-family" in text


def test_world_parts_for_s7_are_declared_on_the_world():
    world = helper_world()
    for step, ids in WORLD_AT.items():
        for i in ids:
            assert re.search(rf'id="{i}"[^>]*data-world-at="s-7:{step}"', world), i
    for i in HF_END:
        assert re.search(rf'id="{i}"[^>]*data-world-until="s-7:1"', world), i
    for i, step in ENDS.items():
        assert re.search(rf'id="{i}"[^>]*data-world-until="s-7:{step}"', world), i
    assert re.search(r'class="world"[^>]*data-split="s-3:6 s-6:0 s-7:1"', world), "s-7 is the world's third layout stage"


# ---------- in the browser ----------

VISIBLE_WORLD = """() => [...document.querySelectorAll('.world [data-world-at][id]')]
  .filter(e => +getComputedStyle(e).opacity > .5).map(e => e.id)"""
OPACITY = "sel => +getComputedStyle(document.querySelector(sel)).opacity"
RECT = "sel => { const r = document.querySelector(sel).getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; }"
RECTS = """sel => [...document.querySelectorAll(sel)].map(e => { const r = e.getBoundingClientRect();
  return [r.left, r.top, r.right, r.bottom]; })"""
CENTRES = """sel => [...document.querySelectorAll(sel)].map(e => { const r = e.getBoundingClientRect();
  return [(r.left + r.right) / 2, (r.top + r.bottom) / 2]; })"""
# a line's two ends in screen px
LINE_ENDS = """sel => [...document.querySelectorAll(sel)].map(l => { const m = l.getScreenCTM(), p = l.ownerSVGElement.createSVGPoint();
  return [['x1', 'y1'], ['x2', 'y2']].map(([a, b]) => { p.x = +l.getAttribute(a); p.y = +l.getAttribute(b);
    const q = p.matrixTransform(m); return [q.x, q.y]; }); })"""
OAI_SHARE = """() => document.querySelector('#w-oai rect').getBoundingClientRect().width
  / document.querySelector('.world svg').getBoundingClientRect().width"""
LOSS = """() => { const d = document.createElement('div'); d.style.color = 'var(--loss)'; document.body.append(d);
  const c = getComputedStyle(d).color; d.remove(); return c; }"""


def helper_until(page, js, arg=None, timeout=8000):
    """Wait until ``js(arg)`` is truthy (transitions race fixed sleeps under parallel load); False on timeout."""
    try:
        page.wait_for_function(js, arg=arg, timeout=timeout, polling=100)
        return True
    except Exception:
        return False


def helper_inside(pt, box, pad=0):
    x, y = pt
    l, t, r, b = box
    return l - pad <= x <= r + pad and t - pad <= y <= b + pad


def helper_hits(a, b, pad=0):
    return a[0] < b[2] + pad and a[2] > b[0] - pad and a[1] < b[3] + pad and a[3] > b[1] - pad


def helper_settled(page, step):
    """Go to ``step`` and wait for the layout tween and every world fade to land."""
    goto_slide(page, SID, step)
    want = OAI_SHARE + (" > .9" if step >= 1 else " < .3")
    helper_until(page, f"() => ({want})()")
    helper_until(page, "() => document.getAnimations().every(a => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity)")
    page.wait_for_timeout(300)


def test_slide_has_four_states(page):
    open_deck(page)
    assert dict(page.evaluate("window.deck.plan()"))[SID] == STEPS


def test_step_0_is_the_world_as_s6_left_it(page):
    open_deck(page)
    goto_slide(page, "s-6", dict(page.evaluate("window.deck.plan()"))["s-6"])
    helper_until(page, f"() => ({OPACITY})('#w-hf-closed') > .9")
    page.wait_for_timeout(1500)
    end6 = set(page.evaluate(VISIBLE_WORLD))
    share6 = page.evaluate(OAI_SHARE)
    goto_slide(page, SID, 0)
    page.wait_for_timeout(1200)
    assert set(page.evaluate(VISIBLE_WORLD)) == end6
    assert abs(page.evaluate(OAI_SHARE) - share6) < .01, "no re-arrangement before 19 Jul"


@pytest.mark.parametrize("step", range(0, STEPS + 1))
def test_world_and_timeline_build_per_step(page, step):
    errors = open_deck(page)
    goto_slide(page, "s-6", dict(page.evaluate("window.deck.plan()"))["s-6"])
    helper_until(page, f"() => ({OPACITY})('#w-hf-closed') > .9")
    page.wait_for_timeout(1500)
    expected = set(page.evaluate(VISIBLE_WORLD))
    if step >= 1:
        expected -= HF_END
    for k, ids in WORLD_AT.items():
        if k <= step:
            expected |= ids
    expected -= {i for i, k in ENDS.items() if k <= step}
    goto_slide(page, SID, step)
    helper_until(page, f"want => {{ const got = ({VISIBLE_WORLD})(); return got.length === want.length && want.every(w => got.includes(w)); }}",
                 sorted(expected), timeout=9000)
    assert set(page.evaluate(VISIBLE_WORLD)) == expected
    shown = page.evaluate("""() => [...document.querySelectorAll('#s-7 .steps > li')]
      .filter(l => +getComputedStyle(l).opacity > .5).map(l => l.id)""")
    assert shown == [t[0] for t in TIMELINE if t[1] <= step], "the timeline builds; nothing shows ahead"
    assert errors == []


def test_openai_widens_and_hugging_face_dissolves_at_19_july(page):
    open_deck(page)
    helper_settled(page, 1)
    assert page.evaluate(OAI_SHARE) > .9, "OpenAI's box takes the whole world again"
    assert all(page.evaluate(OPACITY, f"#{i}") < .02 for i in HF_END), "Hugging Face's story ended at the cut"
    oai = page.evaluate(RECT, "#w-oai rect")
    for sel in ("#w-eval .run", "#w-astra .run", "#w-mirror rect", "#w-folders .folder-glyph", "#w-astra-tag text"):
        assert all(helper_inside(c, oai, 1) for c in page.evaluate(CENTRES, sel)), f"{sel} sits in OpenAI's box"
    helper_settled(page, 0)
    assert page.evaluate(OAI_SHARE) < .3, "back at step 0 the world is s-6's again"


def test_new_runs_are_a_separate_group_linked_into_the_shared_mirror(page):
    open_deck(page)
    helper_settled(page, 1)
    hpim, astra = page.evaluate(RECTS, "#w-eval .run"), page.evaluate(RECTS, "#w-astra .run")
    assert 8 <= len(astra) < len(hpim), "a smaller, separate evaluation"
    box = lambda rs: (min(r[0] for r in rs), min(r[1] for r in rs), max(r[2] for r in rs), max(r[3] for r in rs))
    assert not helper_hits(box(hpim), box(astra), 20), "the two groups stand apart"
    assert box(astra)[0] > box(hpim)[2], "the new group stands right of the HF-phase swarm"
    mirror = page.evaluate(RECT, "#w-mirror rect")
    centre = ((mirror[0] + mirror[2]) / 2, (mirror[1] + mirror[3]) / 2)
    ends = page.evaluate(LINE_ENDS, "#w-astra-links line")
    assert len(ends) >= len(astra) // 2
    assert all(helper_inside(b, (centre[0], centre[1], centre[0], centre[1]), 3) for _, b in ends), "links end at the mirror"
    assert all(any(helper_inside(a, r, 2) for r in astra) for a, _ in ends), "links start at the new runs"
    hpim_ends = page.evaluate(LINE_ENDS, "#w-swarm-links line")
    assert all(helper_inside(b, (centre[0], centre[1], centre[0], centre[1]), 3) for _, b in hpim_ends), \
        "the HF-phase swarm stays attached to the moved mirror"
    tag = helper_text(page.evaluate("() => document.querySelector('#w-astra-tag').textContent"))
    assert "Astra-family" in tag


@pytest.mark.parametrize("step", [1, 2, 3])
def test_nothing_overlaps_on_the_widened_world(page, step):
    open_deck(page)
    helper_settled(page, step)
    tiles = page.evaluate("""() => [...document.querySelectorAll('.world .tile rect')].filter(r =>
      +getComputedStyle(r.closest('[data-world-at]')).opacity > .5).map(r => { const b = r.getBoundingClientRect();
      return [b.left, b.top, b.right, b.bottom]; })""")
    assert len(tiles) == 1 + (step >= 2) + (step >= 3)
    for i, a in enumerate(tiles):
        for b in tiles[i + 1:]:
            assert not helper_hits(a, b, 8), "tiles keep clear of each other"
    for sel in ("#w-astra .run", "#w-eval .run", "#w-astra-tag text"):
        for r in page.evaluate(RECTS, sel):
            assert not any(helper_hits(r, t) for t in tiles), f"{sel} never under a tile"
    tag = page.evaluate(RECTS, "#w-astra-tag text")
    for r in page.evaluate(RECTS, "#w-astra .run, #w-eval .run"):
        assert not any(helper_hits(r, t) for t in tag), "the tag keeps clear of the runs"


def test_mirror_padlock_opens_when_its_node_is_rooted(page):
    open_deck(page)
    helper_settled(page, 1)
    assert page.evaluate(OPACITY, "#w-secure") > .9 and page.evaluate(OPACITY, "#w-root") < .05
    assert page.evaluate(OPACITY, "#w-secrets") < .05, "no secrets tile before its step"
    helper_settled(page, 2)
    assert page.evaluate(OPACITY, "#w-secure") < .05 and page.evaluate(OPACITY, "#w-root") > .9
    mirror = page.evaluate(RECT, "#w-mirror rect")
    lock = page.evaluate(CENTRES, "#w-root circle")[0]
    assert helper_inside(lock, mirror, 16), "the padlock sits on the mirror"
    assert page.evaluate("() => getComputedStyle(document.querySelector('#w-root circle')).fill") == page.evaluate(LOSS)
    words = helper_text(page.evaluate("() => document.querySelector('#w-secrets').textContent"))
    assert "secrets" in words.lower() and "956" in words


def test_cluster_is_the_key_tile_taken_by_the_new_runs(page):
    open_deck(page)
    helper_settled(page, 2)
    assert page.evaluate(OPACITY, "#w-oai-cluster") < .05 and page.evaluate(OPACITY, "#w-oai-lock") < .05
    page.evaluate("window.deck.goto('s-7', 3)")
    rows = page.evaluate("""([ms]) => new Promise(res => { const t0 = performance.now(), out = [];
      const op = s => +getComputedStyle(document.querySelector(s)).opacity;
      const tick = () => { const t = performance.now() - t0; out.push([t, op('#w-oai-cluster'), op('#w-oai-lock')]);
        if (t < ms) setTimeout(tick, 40); else res(out); }; tick(); })""", [3500])
    tile = next((r[0] for r in rows if r[1] > .5), None)
    lock = next((r[0] for r in rows if r[2] > .1), None)
    assert tile is not None and lock is not None and lock >= tile + 400, "the cluster appears, then its padlock pops"
    page.wait_for_timeout(800)
    assert "tile--key" in page.evaluate("() => document.querySelector('#w-oai-cluster').getAttribute('class')")
    words = helper_text(page.evaluate("() => document.querySelector('#w-oai-cluster').textContent")).lower()
    assert "cluster" in words and "mirror" in words and "openai" in words
    cluster = page.evaluate(RECT, "#w-oai-cluster rect")
    assert helper_inside(page.evaluate(CENTRES, "#w-oai-lock circle")[0], cluster, 16)
    assert page.evaluate("() => getComputedStyle(document.querySelector('#w-oai-lock circle')).fill") == page.evaluate(LOSS)
    astra = page.evaluate(RECTS, "#w-astra .run")
    ends = page.evaluate(LINE_ENDS, "#w-astra-admin line")
    assert len(ends) >= 2
    assert all(any(helper_inside(a, r, 2) for r in astra) and helper_inside(b, cluster, 4) for a, b in ends), \
        "bold lines run from the new runs to the cluster"


def test_reduced_motion_shows_the_end_state_at_once(page):
    page.emulate_media(reduced_motion="reduce")
    open_deck(page)
    goto_slide(page, SID, 3)
    page.wait_for_timeout(900)
    for sel in ("#w-oai-cluster", "#w-oai-lock", "#w-astra", "#w-root", "#w-secrets"):
        assert page.evaluate(OPACITY, sel) > .9, sel
    assert page.evaluate(OAI_SHARE) > .9
