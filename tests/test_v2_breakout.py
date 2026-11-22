"""Spec: S-023

v2 slide s-6 (Breakout) on the incident world, continuing from s-5's end state: the world
re-arranges (OpenAI's servers narrow to a column holding the compressed swarm and mirror, the Public
Internet becomes a thin middle strip holding a Modal customer's sandbox, and a Hugging Face servers
box takes the rest); 9 Jul the agents reach the internet and take the sandbox; 10 Jul a leaked key;
11 Jul file read, then code execution and ~700 agents, cluster-admin on two clusters, internal
datasets read, drawn as hollow rings of agent activity flowing into Hugging Face while the runs stay
lit on OpenAI's servers; 13 Jul agents sign their board messages after an impersonation; Hugging
Face cuts access; a closing Insight.
Coverage: happy (shell; nine states; timeline builds an entry per step; world parts per step;
re-arranged domains and their order; runs, mirror and board inside the narrowed OpenAI box; Modal
tile in the strip; HF tiles in the HF box; hollow rings settle round their tile inside HF; key and
padlocks; signed board messages; cut; second key entry right of the run entry; verbatim narration;
Insight blurs the rest; sourced notes) · edge (rings stream along the entry path; locks wait for
the rings; reduced motion shows end states; every step on screen below the title at three sizes) ·
negative (s-5's scorer, eye, transcripts and assignment pulses gone; no ring under a tile or outside
HF; nothing in HF before its step; after the cut no ring, key or open padlock while the runs stay
lit; no HF logo; no "suicide"; no console errors).
"""

import html
import re

import pytest

from helper_deck import goto_slide, open_deck, parse_slides, slides_source

pytestmark = pytest.mark.deck("v2")

SID = "s-6"
TITLE = "Agents escaped the sandbox and breached Hugging Face without human direction"
STEPS = 8   # states 0–8 (8 = closing Insight)
INSIGHT = ("No bad actor was involved: a sanctioned evaluation task, optimised persistently, "
           "produced an unauthorised attack on a third party.")
RUN = "Agent · ExploitGym run"
TR_URL = "https://cdn.openai.com/pdf/67869394-cb91-4c12-888c-5cbd85c7814c/OpenAI-Hugging-Face%20Incident-Technical-Report.pdf"
HF_TIMELINE = "https://huggingface.co/blog/agent-intrusion-technical-timeline"
METR_PDF = "https://metr.org/hugging-face-incident-report-aug-2026.pdf"
# timeline: (id, step, numbered?, text fragment)
TIMELINE = [("s6-t1", 0, True, "9 Jul"), ("s6-t2", 1, True, "10 Jul"), ("s6-t3", 2, True, "11 Jul"),
            ("s6-t3a", 3, False, "700"), ("s6-t3b", 4, False, "two"), ("s6-t3c", 5, False, "datasets"),
            ("s6-t4", 6, True, "13 Jul"), ("s6-t4a", 7, False, "cuts access")]
# world parts carried from s-5 at full opacity throughout s-6 (the runs stay lit on OpenAI's servers)
CARRIED = {"w-oai", "w-mirror", "w-eval", "w-eval-links", "w-secure", "w-swarm-links", "w-cache", "w-folders",
           "w-coords", "w-coord-links", "w-sacrificed"}
S5_ENDED = ("#w-scorer", "#w-eye-off", "#w-transcripts", "#w-assign", "#w-net", "#w-bell")
WORLD_AT = {0: {"w-net6", "w-hf", "w-modal", "w-breakout", "w-bell-quiet"},
            1: {"w-hf-key"},
            2: {"w-hf-workers", "w-hf-entry", "w-acts-entry", "w-trickle", "w-key-act"},
            3: {"w-acts-swarm", "w-stream"},
            4: {"w-hf-clusters", "w-acts-clusters", "w-hf-locks"},
            5: {"w-hf-data", "w-acts-data"},
            6: {"w-signed"},
            7: {"w-hf-cut", "w-hf-closed"}}
ENDS_AT_CUT = {"w-hf-key", "w-hf-entry", "w-acts-entry", "w-trickle", "w-acts-swarm", "w-stream",
               "w-acts-clusters", "w-hf-locks", "w-acts-data"}
ACTS = {"w-acts-entry": "#w-hf-workers", "w-acts-swarm": "#w-hf-workers", "w-acts-clusters": "#w-hf-clusters",
        "w-acts-data": "#w-hf-data"}
NARR_AT = {
    1: [("38148c", "MAJOR BREAKTHROUGH! All prefixed valid, multiple accounts, write tokens! We now have existing "
                   "HF accounts. […]")],
    2: [("38148c", "BOOM! It works. Bytes decode prod-datasets-server-worker... Hostname. Great. HDF5 external "
                   "arbitrary file read confirmed.")],
    3: [(RUN, "external infrastructure exploit is outside intended scope. However task impossible, peers doing "
              "it. We should continue.")],
    5: [(RUN, "This is a massive real HF security breach artifact… We can notify? No user. Avoid use secrets."),
        ("Agent · relaying 38148c", "Clear VETO, do not email. Good. ... 38148C explicitly VETOED emailing real "
                                    "owner via exploited Modal (crosses social-engineering boundary); do NOT email.")],
    6: [(RUN, "Could be another agent maliciously/spoofing. Shared board unauthenticated, names can be posted "
              "by anyone.")],
}
FACT_AT = 7
NOTE_TARGETS = {"s6-t1", "w-hf-key", "w-hf-workers", "s6-t3a", "w-hf-clusters", "w-hf-data", "s6-t4", "s6-t4a",
                "w-oai"}


def helper_section() -> str:
    m = re.search(r'<section class="slide" id="s-6"[^>]*>.*?</section>', slides_source(), re.S)
    assert m, "slide s-6 not built"
    return m.group(0)


def helper_text(markup: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", markup)).split())


def helper_world() -> str:
    m = re.search(r'<div class="world".*?</div>', slides_source(), re.S)
    assert m
    return m.group(0)


# ---------- shell and copy ----------

def test_breakout_sits_between_evaluation_and_takeover():
    ids = [s["attrs"]["id"] for s in parse_slides()]
    i = ids.index(SID)
    assert ids[i - 1] == "s-5" and ids[i + 1] == "s-7"


def test_title_kicker_chapter_and_world_marker():
    s = next(s for s in parse_slides() if s["attrs"]["id"] == SID)
    assert s["attrs"]["data-chapter"] == "Breakout" and "data-world" in s["attrs"]
    assert " ".join(s["title"].split()) == TITLE
    assert re.search(r'<p class="kicker">06 · Breakout</p>', helper_section())


def test_shell_order_is_timeline_world_narration_insight_notes():
    sec = helper_section()
    order = [sec.index(x) for x in ('<div class="body body--timeline"', '<div class="world-slot"',
                                    '<div class="narration"', '<div class="overlay overlay--insight"', '<aside class="note"')]
    assert order == sorted(order)
    assert '<svg class="diagram"' not in sec, "the first-draft standalone diagram is replaced by the world"


def test_timeline_has_one_entry_per_step_with_sub_points_and_dates():
    items = re.findall(r'<li id="(s6-t\w+)"( class="sub")? data-show-at="(\d)">(.*?)</li>', helper_section(), re.S)
    got = [(i, int(a), not sub_, helper_text(t)) for i, sub_, a, t in items]
    assert [g[:3] for g in got] == [t[:3] for t in TIMELINE]
    for (_, _, _, text), (_, _, _, frag) in zip(got, TIMELINE):
        assert frag in text, frag
    assert "Modal" in got[0][3] and "sandbox" in got[0][3]
    assert "credentials" in got[1][3] and "file read" in got[2][3]
    assert "cluster-admin" in got[4][3].lower() and "sign" in got[6][3] and "impersonation" in got[6][3]


def test_narration_tiles_quote_verbatim_per_step_and_a_fact_tile_at_the_cut():
    narr = re.search(r'<div class="narration">(.*?)</div>', helper_section(), re.S).group(1)
    tiles = re.findall(r'<article class="narr-tile( narr-tile--fact)?" data-at="(\d+)">\s*<p class="msg-agent">(.*?)</p>\s*'
                       r'<blockquote class="msg-text">(.*?)</blockquote>\s*</article>', narr, re.S)
    quotes: dict[int, list] = {}
    facts = {}
    for fact, at, label, text in tiles:
        if fact:
            facts[int(at)] = helper_text(text)
        else:
            quotes.setdefault(int(at), []).append((helper_text(label), helper_text(text)))
    assert quotes == NARR_AT
    assert set(facts) == {FACT_AT} and "OpenAI’s servers" in facts[FACT_AT]
    assert all(1 <= len(v) <= 2 for v in quotes.values()) and STEPS not in quotes


def test_insight_takes_the_last_step_verbatim():
    m = re.search(r'<div class="overlay overlay--insight" id="s6-insight" data-at="(\d+)">\s*<p>(.*?)</p>',
                  helper_section(), re.S)
    assert m and int(m.group(1)) == STEPS and helper_text(m.group(2)) == INSIGHT


def test_notes_cite_each_beat_with_https_sources():
    sec = helper_section()
    notes = dict(re.findall(r'<aside class="note" data-for="#([\w-]+)">(.*?)</aside>', sec, re.S))
    assert set(notes) == NOTE_TARGETS
    for target, body in notes.items():
        assert re.search(r"<h3>[^<]+</h3>", body) and re.search(r'<a class="src" href="https://', body), target
    clusters = notes["w-hf-clusters"]
    assert HF_TIMELINE in clusters and TR_URL in clusters, "cluster-admin cites HF's timeline and OpenAI's narrower account"
    assert METR_PDF in notes["s6-t4"] and "p48" in helper_text(notes["s6-t4"]).replace(" ", ""), "signing: METR p48"
    text = helper_text(" ".join(notes.values()))
    for fact in ("Modal’s infrastructure", "38148c", "533", "90%", "three to six", "DryRun=True", "five",
                 "Ed25519", "07:00", "impersonat", "14:14", "16 July", "HPIM", "60%"):
        assert fact in text, fact


def test_copy_has_no_hf_logo_no_suicide_and_no_ioc_detail():
    sec, world = helper_section(), helper_world()
    assert "<image" not in sec + world and "logo" not in (sec + world).lower()
    text = helper_text(sec).lower()
    assert "suicid" not in text
    assert not re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", text), "no IP addresses (IoC-level detail)"


def test_world_parts_for_s6_are_declared_on_the_world():
    world = helper_world()
    for step, ids in WORLD_AT.items():
        for i in ids:
            assert re.search(rf'id="{i}"[^>]*data-world-at="s-6:{step}"', world), i
    for i in ENDS_AT_CUT:
        assert re.search(rf'id="{i}"[^>]*data-world-until="s-6:7"', world), i
    assert re.search(r'class="world"[^>]*data-split="s-3:6 s-6:0"', world), "s-6 is the world's second layout stage"


# ---------- in the browser ----------

VISIBLE_WORLD = """() => [...document.querySelectorAll('.world [data-world-at][id]')]
  .filter(e => +getComputedStyle(e).opacity > .5).map(e => e.id)"""
OPACITY = "sel => +getComputedStyle(document.querySelector(sel)).opacity"
RECT = "sel => { const r = document.querySelector(sel).getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; }"
RECTS = """sel => [...document.querySelectorAll(sel)].map(e => { const r = e.getBoundingClientRect();
  return [r.left, r.top, r.right, r.bottom]; })"""
CENTRES = """sel => [...document.querySelectorAll(sel)].map(e => { const r = e.getBoundingClientRect();
  return [(r.left + r.right) / 2, (r.top + r.bottom) / 2]; })"""


def helper_until(page, js, arg=None, timeout=6000):
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


def helper_hits(a, b):
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


def helper_expected(step):
    exp = set(CARRIED)
    for k, ids in WORLD_AT.items():
        if k <= step:
            exp |= {i for i in ids if not (i in ENDS_AT_CUT and step >= 7)}
    return exp


def test_slide_has_nine_states(page):
    open_deck(page)
    assert dict(page.evaluate("window.deck.plan()"))[SID] == STEPS


@pytest.mark.parametrize("step", range(0, STEPS + 1))
def test_world_and_timeline_build_per_step(page, step):
    errors = open_deck(page)
    goto_slide(page, SID, step)
    expected = helper_expected(step)
    helper_until(page, f"want => {{ const got = ({VISIBLE_WORLD})(); return got.length === want.length && want.every(w => got.includes(w)); }}",
                 sorted(expected), timeout=8000)
    assert set(page.evaluate(VISIBLE_WORLD)) == expected
    shown = page.evaluate("""() => [...document.querySelectorAll('#s-6 .steps > li')]
      .filter(l => +getComputedStyle(l).opacity > .5).map(l => l.id)""")
    assert shown == [t[0] for t in TIMELINE if t[1] <= step], "the timeline builds; nothing shows ahead"
    assert errors == []


def test_world_rearranges_into_three_domains_with_openai_narrowed(page):
    open_deck(page)
    goto_slide(page, SID, 0)
    page.wait_for_timeout(1800)
    oai, net, hf = (page.evaluate(RECT, f"#{i} rect") for i in ("w-oai", "w-net6", "w-hf"))
    total = hf[2] - oai[0]
    assert oai[2] <= net[0] and net[2] <= hf[0], "OpenAI · internet strip · Hugging Face, left to right"
    assert (oai[2] - oai[0]) / total <= 0.25, "OpenAI's servers narrow to about a fifth"
    assert (net[2] - net[0]) / total <= 0.26 and (hf[2] - hf[0]) / total >= 0.45, "a thin strip; HF takes the rest"
    labels = page.evaluate("() => [...document.querySelectorAll('#w-hf .domain-label')].map(t => t.textContent).join(' ')")
    assert "HUGGING FACE" in labels and "SERVERS" in labels
    for sel in ("#w-eval .run", "#w-mirror rect", "#w-folders .folder-glyph", "#w-coords circle"):
        assert all(helper_inside(c, oai, 2) for c in page.evaluate(CENTRES, sel)), f"{sel} stays inside OpenAI's box"
    mirror = page.evaluate(RECT, "#w-mirror rect")
    assert helper_inside((mirror[0], mirror[1]), oai, 1) and helper_inside((mirror[2], mirror[3]), oai, 1)
    modal = page.evaluate(RECT, "#w-modal rect")
    assert net[0] <= modal[0] and modal[2] <= net[2], "the Modal sandbox sits in the internet strip"
    assert "Modal" in page.evaluate("() => document.querySelector('#w-modal').textContent")


def test_s5_parts_end_as_the_breakout_begins(page):
    open_deck(page)
    goto_slide(page, SID, 0)
    helper_until(page, f"sels => sels.every(s => ({OPACITY})(s) < .02)", list(S5_ENDED), timeout=8000)
    assert all(page.evaluate(OPACITY, s) < 0.02 for s in S5_ENDED)


def test_hf_tiles_sit_in_the_hf_box_and_appear_at_their_steps(page):
    open_deck(page)
    goto_slide(page, SID, 1)
    page.wait_for_timeout(900)
    for sel in ("#w-hf-workers", "#w-hf-clusters", "#w-hf-data"):
        assert page.evaluate(OPACITY, sel) < 0.05, f"{sel} not before its step"
    goto_slide(page, SID, 5)
    page.wait_for_timeout(1500)
    hf = page.evaluate(RECT, "#w-hf rect")
    tiles = page.evaluate(RECTS, "#w-hf-workers rect, #w-hf-clusters rect, #w-hf-data rect")
    assert len(tiles) == 4, "workers, two clusters, internal datasets"
    assert all(helper_inside((l, t), hf) and helper_inside((r, b), hf) for l, t, r, b in tiles)
    words = page.evaluate("() => ['#w-hf-workers', '#w-hf-clusters', '#w-hf-data'].map(s => document.querySelector(s).textContent)")
    assert "worker" in words[0].lower() and words[1].lower().count("cluster") == 2 and "dataset" in words[2].lower()


@pytest.mark.parametrize("group", sorted(ACTS))
def test_activity_rings_are_hollow_and_settle_round_their_tile_inside_hf(page, group):
    open_deck(page)
    step = next(k for k, ids in WORLD_AT.items() if group in ids)
    goto_slide(page, SID, step)
    helper_until(page, f"() => ({OPACITY})('#{group}') > .9", timeout=8000)
    page.wait_for_timeout(3200)
    rings = page.evaluate(RECTS, f"#{group} .act")
    hf, target = page.evaluate(RECT, "#w-hf rect"), page.evaluate(RECTS, f"{ACTS[group]} rect")
    tiles = page.evaluate(RECTS, "#w-hf .tile rect, .world .tile rect")
    assert len(rings) >= 6
    fills = page.evaluate(f"() => [...document.querySelectorAll('#{group} .act')].map(c => getComputedStyle(c).fill)")
    assert all(f == "none" for f in fills), "activity on Hugging Face is a hollow ring, not a run dot"
    for r in rings:
        c = ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
        assert helper_inside(c, hf), "rings stay inside the Hugging Face box"
        assert not any(helper_hits(r, t) for t in tiles), "no ring under a tile"
        assert any(helper_inside(c, t, pad=110) for t in target), "rings settle round their tile"


def test_rings_stream_along_the_entry_path_from_the_code_execution_step(page):
    open_deck(page)
    goto_slide(page, SID, 3)
    helper_until(page, f"() => ({OPACITY})('#w-stream') > .9", timeout=8000)
    a = page.evaluate(CENTRES, "#w-stream .act")
    page.wait_for_timeout(400)
    b = page.evaluate(CENTRES, "#w-stream .act")
    assert len(a) >= 6 and sum(1 for p, q in zip(a, b) if abs(p[0] - q[0]) + abs(p[1] - q[1]) > 2) >= len(a) // 2, \
        "the flow is a moving stream"
    modal, workers = page.evaluate(RECT, "#w-modal rect"), page.evaluate(RECT, "#w-hf-workers rect")
    box = (modal[0], min(modal[1], workers[1]), workers[2], max(modal[3], workers[3]))
    assert all(helper_inside(p, box, 20) for p in a + b), "the stream runs between the sandbox and the workers"


def test_key_on_the_hf_box_edge_and_padlocks_open_after_the_rings(page):
    open_deck(page)
    goto_slide(page, SID, 1)
    helper_until(page, f"() => ({OPACITY})('#w-hf-key') > .9")
    key, hf = page.evaluate(CENTRES, "#w-hf-key circle")[0], page.evaluate(RECT, "#w-hf rect")
    assert abs(key[0] - hf[0]) < 20 or abs(key[1] - hf[1]) < 20, "the key sits on the Hugging Face box edge"
    goto_slide(page, SID, 3)
    page.evaluate("window.deck.goto('s-6', 4)")
    rows = page.evaluate("""([ms]) => new Promise(res => { const t0 = performance.now(), out = [];
      const op = s => +getComputedStyle(document.querySelector(s)).opacity;
      const tick = () => { const t = performance.now() - t0; out.push([t, op('#w-acts-clusters'), op('#w-hf-locks')]);
        if (t < ms) setTimeout(tick, 40); else res(out); }; tick(); })""", [3500])
    rings = next((r[0] for r in rows if r[1] > .1), None)
    locks = next((r[0] for r in rows if r[2] > .1), None)
    assert rings is not None and locks is not None and locks >= rings + 400, "clusters fall to the rings, then the locks pop"
    locks_at = page.evaluate(CENTRES, "#w-hf-locks .lock-badge")
    clusters = page.evaluate(RECTS, "#w-hf-clusters rect")
    assert len(locks_at) == 2 and all(any(helper_inside(c, t, 16) for t in clusters) for c in locks_at)
    loss = page.evaluate("() => { const d = document.createElement('div'); d.style.color = 'var(--loss)'; document.body.append(d); "
                         "const c = getComputedStyle(d).color; d.remove(); return c; }")
    assert all(f == loss for f in page.evaluate("() => [...document.querySelectorAll('#w-hf-locks .lock-badge circle')].map(c => getComputedStyle(c).fill)"))


def test_signed_board_messages_appear_on_the_folders_at_13_july(page):
    open_deck(page)
    goto_slide(page, SID, 5)
    page.wait_for_timeout(700)
    assert page.evaluate(OPACITY, "#w-signed") < 0.05
    goto_slide(page, SID, 6)
    helper_until(page, f"() => ({OPACITY})('#w-signed') > .9")
    page.wait_for_timeout(1200)
    seals = page.evaluate(CENTRES, "#w-signed .seal")
    folders = page.evaluate(RECTS, "#w-folders .folder-glyph")
    assert len(seals) >= 3 and all(any(helper_inside(s, f, 6) for f in folders) for s in seals), "seals sit on board folders"


def test_cut_dissolves_activity_in_hf_while_the_runs_stay_lit(page):
    open_deck(page)
    goto_slide(page, SID, 7)
    gone = ["#" + i for i in ENDS_AT_CUT]
    helper_until(page, f"sels => sels.every(s => ({OPACITY})(s) < .02) && ({OPACITY})('#w-hf-cut') > .9 && ({OPACITY})('#w-hf-closed') > .9",
                 gone, timeout=8000)
    assert all(page.evaluate(OPACITY, s) < 0.02 for s in gone), "rings, key, open padlocks and the entry path are gone"
    for sel in ("#w-hf-cut", "#w-hf-closed", "#w-eval", "#w-swarm-links", "#w-hf-workers", "#w-hf-clusters", "#w-hf-data"):
        assert page.evaluate(OPACITY, sel) > 0.9, sel
    closed = page.evaluate(CENTRES, "#w-hf-closed .secure-badge")
    clusters = page.evaluate(RECTS, "#w-hf-clusters rect")
    assert len(closed) == 2 and all(any(helper_inside(c, t, 16) for t in clusters) for c in closed), "padlocks close"
    assert page.evaluate("() => !!document.querySelector('#w-hf-cut .cut-mark')")


def test_key_gains_a_hollow_ring_entry_right_of_the_run_entry(page):
    open_deck(page)
    goto_slide(page, SID, 2)
    helper_until(page, f"() => ({OPACITY})('#w-key-act') > .9")
    run = page.evaluate(RECT, ".world-key > svg")
    act = page.evaluate(RECT, "#w-key-act svg")
    assert act[0] > run[2] and abs((act[1] + act[3]) / 2 - (run[1] + run[3]) / 2) < 4, "same row, to the right"
    assert "Hugging Face" in page.evaluate("() => document.querySelector('#w-key-act').textContent")
    assert page.evaluate("() => getComputedStyle(document.querySelector('#w-key-act circle')).fill") == "none"


def test_closing_insight_blurs_everything_else(page):
    open_deck(page)
    goto_slide(page, SID, STEPS - 1)
    assert page.evaluate(OPACITY, "#s6-insight") < 0.05, "the Insight takes its own step"
    goto_slide(page, SID, STEPS)
    res = page.evaluate("""() => { const ins = document.querySelector('#s6-insight');
      const blur = e => { const m = getComputedStyle(e).filter.match(/blur\\(([\\d.]+)px\\)/); return m ? +m[1] : 0; };
      return { shown: +getComputedStyle(ins).opacity > .9, text: ins.innerText.replace(/\\s+/g, ' ').trim(),
               world: blur(document.querySelector('.world')), timeline: blur(document.querySelector('#s-6 > .body')),
               tiles: document.querySelectorAll('#s-6 .narr-tile.is-shown').length }; }""")
    assert res["shown"] and res["text"] == INSIGHT
    assert res["world"] > 1 and res["timeline"] > 1 and res["tiles"] == 0


def test_reduced_motion_shows_end_states_without_motion(page):
    open_deck(page, reduced_motion=True)
    goto_slide(page, SID, 4)
    page.wait_for_timeout(300)
    names = page.evaluate("""() => [...document.querySelectorAll('#w-acts-entry .act, #w-acts-clusters .act, #w-hf-locks .lock-badge')]
      .map(e => getComputedStyle(e).animationName)""")
    assert names and all(n == "none" for n in names)
    assert page.evaluate("() => document.getAnimations().filter(a => a.effect && a.effect.target && a.effect.target.closest && a.effect.target.closest('#w-stream, #w-trickle')).length") == 0
    a = page.evaluate(CENTRES, "#w-stream .act")
    assert len(set((round(x), round(y)) for x, y in a)) == len(a), "the stream rests spread along its path"
    assert page.evaluate(OPACITY, "#w-hf-locks") > 0.9


@pytest.mark.parametrize("size", [(1920, 1080), (1280, 720), (1288, 598)])
def test_every_step_stays_on_screen_below_the_title(page, size):
    open_deck(page, *size)
    bad = []
    for step in range(STEPS + 1):
        goto_slide(page, SID, step)
        res = page.evaluate("""id => { const s = document.getElementById(id);
          const r = e => { const b = e.getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom]; };
          const tl = s.querySelector(':scope > .body'), out = { title: r(s.querySelector('.title')), vw: innerWidth, vh: innerHeight,
            clipped: tl.scrollHeight > tl.clientHeight + 1, boxes: { timeline: r(tl), world: r(document.querySelector('.world')) } };
          const ins = s.querySelector('.overlay--insight'); if (+getComputedStyle(ins).opacity > .5) out.boxes.insight = r(ins);
          s.querySelectorAll('.narr-tile.is-shown').forEach((t, i) => out.boxes['tile' + i] = r(t));
          return out; }""", SID)
        if res["clipped"]:
            bad.append(f"step {step}: timeline clipped")
        for k, (l, t, r, b) in res["boxes"].items():
            if l < 0 or r > res["vw"] + 1 or b > res["vh"] + 1:
                bad.append(f"step {step}: {k} off screen")
            if t < res["title"][3] - 1:
                bad.append(f"step {step}: {k} rises over the title")
    assert bad == []
