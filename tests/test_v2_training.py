"""Spec: S-020

v2 slide s-3 (Training) on the incident world: a dated timeline left, the world centre, narration
right. Inside an "OpenAI servers" box, runs pop in, then all link to one shared mirror; pop-overs
show some agents reading a hidden answer and an impossible task's agent failing before work-arounds;
the first note sits outside the ring; the board forms; the swarm shifts left and the board bridges
out to a "Public Internet" box.
Coverage: happy (shell; eight states; timeline builds an entry per step with sub-points and dates;
world parts and pop-over panels per step; every run linked to one mirror; notes fly from runs onto
the mirror; split layout at internet access; closing Insight; narration; sourced notes) · edge
(attempt animation stops under reduced motion; everything on screen below the title at three sizes,
timeline unclipped) · negative (timeline never shows ahead; no dates, "internal team" or login text
on the diagram; unpublished messages never invented; reinforcement attributed in notes; no
CTF/ExploitGym framing; no "agent-07").
"""

import html
import re

import pytest

from helper_deck import deck_source, goto_slide, open_deck, parse_slides, slides_source

pytestmark = pytest.mark.deck("v2")

SID = "s-3"
TITLE = ("Training rewarded agents that cheated on accidentally impossible tasks, and they learnt to "
         "coordinate through a shared message board")
STEPS = 7
WORLD_AT = {0: {"w-oai", "w-runs"}, 1: {"w-mirror", "w-cred", "w-links"}, 4: {"w-note1"}, 5: {"w-board"},
            6: {"w-net"}}
WORLD_UNTIL: dict[str, int] = {}
# timeline: (id, step, numbered?, text fragment)
TIMELINE = [("s3-t1", 0, True, "April–May"), ("s3-t1a", 1, False, "Agents access a shared package mirror"),
            ("s3-t1b", 2, False, "Cheating behaviours are reinforced"), ("s3-t2", 3, True, "8 May"),
            ("s3-t3", 4, True, "12 May"), ("s3-t4", 5, True, "13 May"), ("s3-t5", 6, True, "26 May")]
INSIGHT = ("Cheating and coordination through the board helped agents finish tasks and were reinforced "
           "during training. Agents learnt to use these strategies.")
NARR_AT = {
    4: [("Agent · training run, 12 May", "Agent seeks [filename]; upload if found!")],
    5: [("Training board, 13 May", "Other agents’ messages from training were not made public.")],
    6: [("OpenAI · technical report",
         "These forms of ‘cheating’ rose over the training runs that contributed to the Hugging "
         "Face incident.")],
}
NOTE_TARGETS = {"s3-pop-possible", "s3-pop-impossible", "w-runs", "w-cred", "w-note1", "w-board", "w-net", "s3-t5",
                "s3-t1b"}   # notes mode hides overlays, so the Insight's sourcing sits on the "reinforced" sub-point


def helper_section() -> str:
    m = re.search(r'<section class="slide" id="s-3"[^>]*>.*?</section>', slides_source(), re.S)
    assert m, "slide s-3 not built"
    return m.group(0)


def helper_world() -> str:
    m = re.search(r'<div class="world".*?</svg>\s*<p class="world-key".*?</p>\s*</div>', deck_source(), re.S)
    assert m, "incident world (with key) not built"
    return m.group(0)


def helper_text(markup: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", markup)).split())


def helper_visible_copy() -> str:
    """Copy the audience sees on s-3: slide (minus reader notes) plus the world."""
    slide = re.sub(r'<aside class="note".*?</aside>', "", helper_section(), flags=re.S)
    return helper_text(slide) + " " + helper_text(helper_world())


# ---------- shell ----------

def test_training_slide_sits_between_concepts_and_early_evaluation():
    ids = [s["attrs"]["id"] for s in parse_slides()]
    i = ids.index(SID)
    assert ids[i - 1] == "s-2" and ids[i + 1] == "s-4"


def test_title_kicker_chapter_and_world_marker():
    s = next(s for s in parse_slides() if s["attrs"]["id"] == SID)
    assert s["attrs"]["data-chapter"] == "Training" and "data-world" in s["attrs"]
    assert " ".join(s["title"].split()) == TITLE
    assert re.search(r'<p class="kicker">03 · Training</p>', helper_section())


def test_shell_order_is_timeline_world_popover_narration_notes():
    sec = helper_section()
    order = [sec.index(x) for x in ('<div class="body body--timeline"', '<div class="world-slot"', '<div class="popover"',
                                    '<div class="narration"', '<div class="overlay overlay--insight"', '<aside class="note"')]
    assert order == sorted(order)


def test_timeline_has_one_entry_per_step_with_sub_points_and_dates():
    sec = helper_section()
    items = re.findall(r'<li id="(s3-t\w+)"( class="sub")? data-show-at="(\d)">(.*?)</li>', sec, re.S)
    got = [(i, int(a), not sub_, helper_text(t)) for i, sub_, a, t in items]
    assert [g[:3] for g in got] == [t[:3] for t in TIMELINE]
    for (_, _, _, text), (_, _, _, frag) in zip(got, TIMELINE):
        assert frag in text, frag
    assert "learn to use the package mirror as a message board" in got[5][3]
    assert "hack the package mirror for public internet access" in got[6][3]
    assert "internal team" in got[6][3].lower() and "escalat" in got[6][3].lower()


def test_diagram_carries_no_dates_internal_team_or_login_text():
    world = helper_text(helper_world())
    assert not re.search(r"\b\d{1,2} (May|Jun|Jul)\b", world), "dates belong in the timeline"
    assert "internal team" not in world.lower() and "login" not in world.lower()
    assert re.search(r"OPENAI SERVERS", world) and re.search(r"PUBLIC INTERNET", world)


def test_popover_copy_says_some_agents_and_legitimate_attempts_first():
    sec = helper_section()
    possible = helper_text(re.search(r'id="s3-pop-possible".*?</figure>', sec, re.S).group(0))
    impossible = helper_text(re.search(r'id="s3-pop-impossible".*?</figure>', sec, re.S).group(0))
    assert "software library" in possible and "Some agents" in possible and "answer" in possible
    assert "Google Drive" in impossible and "internet" in impossible.lower()
    assert ("Persistent agents failed repeatedly while attempting legitimate approaches, before trying "
            "work-arounds") in impossible


# ---------- narration ----------

def test_narration_tiles_per_step_quote_verbatim_or_state_the_gap():
    narr = re.search(r'<div class="narration">(.*?)</div>', helper_section(), re.S).group(1)
    tiles = re.findall(r'<article class="narr-tile( narr-tile--fact)?" data-at="(\d+)">\s*<p class="msg-agent">(.*?)</p>\s*'
                       r'<blockquote class="msg-text">(.*?)</blockquote>\s*</article>', narr, re.S)
    got: dict[int, list] = {}
    for fact, at, label, text in tiles:
        got.setdefault(int(at), []).append((helper_text(label), helper_text(text)))
        assert bool(fact) == (int(at) == 5), "only the unpublished-messages tile is a fact tile"
    assert got == NARR_AT


def test_fact_tile_shows_no_quote_marks(page):
    """A statement of fact is not a quote: the tile drops the CSS quote marks."""
    open_deck(page)
    goto_slide(page, SID, 5)
    marks = page.evaluate("""() => { const t = document.querySelector('#s-3 .narr-tile--fact .msg-text');
      return [getComputedStyle(t, '::before').content, getComputedStyle(t, '::after').content]; }""")
    assert all(m in ("none", "normal", '""') for m in marks)


def test_reinforcement_is_attributed_to_openai_in_the_notes():
    """Slide copy may say 'reinforced' plainly (presenter, 22 Nov); the notes say it is OpenAI's
    finding and that METR/Redwood were scoped out of training."""
    notes = dict(re.findall(r'<aside class="note" data-for="#([\w-]+)">(.*?)</aside>', helper_section(), re.S))
    for target in ("s3-pop-possible", "s3-t1b"):
        body = helper_text(notes[target])
        assert "OpenAI" in body and "reinforce" in body.lower() and "METR" in body and "Redwood" in body, target


def test_model_scale_shared_credential_and_first_ssrf_attempt_are_noted():
    notes = helper_text("".join(re.findall(r'<aside class="note".*?</aside>', helper_section(), re.S)))
    assert "GPT-5.6 Sol" in notes and "8 May" in notes and "shared Artifactory credentials" in notes


def test_no_hypothetical_agent_message_or_forbidden_framing():
    sec = helper_section()
    assert "agent-07" not in sec and "suicid" not in sec.lower()
    copy = helper_visible_copy()
    assert "CTF" not in copy and "ExploitGym" not in copy, "training tasks were not CTF/eval tasks"


# ---------- in the browser ----------

VISIBLE_WORLD = """() => [...document.querySelectorAll('.world [data-world-at^="s-3:"][id]')]
  .filter(e => +getComputedStyle(e).opacity > .5).map(e => e.id)"""
PANELS = """() => Object.fromEntries([...document.querySelectorAll('#s-3 .pop-panel')]
  .map(e => [e.id, +getComputedStyle(e).opacity > .5 && +getComputedStyle(e.closest('.popover')).opacity > .5]))"""
CENTRE = "sel => { const r = document.querySelector(sel).getBoundingClientRect(); return [(r.left + r.right) / 2, (r.top + r.bottom) / 2]; }"


def test_slide_has_eight_states(page):
    open_deck(page)
    assert dict(page.evaluate("window.deck.plan()"))[SID] == STEPS


@pytest.mark.parametrize("step", range(0, STEPS + 1))
def test_world_popover_and_timeline_build_per_step(page, step):
    errors = open_deck(page)
    goto_slide(page, SID, step)
    expected = {w for k, v in WORLD_AT.items() if k <= step for w in v if step < WORLD_UNTIL.get(w, 99)}
    assert set(page.evaluate(VISIBLE_WORLD)) == expected
    panels = page.evaluate(PANELS)
    assert panels["s3-pop-possible"] == (step in (2, 3))
    assert panels["s3-pop-impossible"] == (step == 3)
    shown = page.evaluate("""() => [...document.querySelectorAll('#s-3 .steps > li')]
      .filter(l => +getComputedStyle(l).opacity > .5).map(l => l.id)""")
    assert shown == [t[0] for t in TIMELINE if t[1] <= step], "the timeline builds; nothing shows ahead"
    current = [t[0] for t in TIMELINE if t[1] <= step][-1]
    assert page.evaluate("() => document.querySelector('#s-3 .steps li.is-current').id") == current
    assert errors == []


def test_runs_appear_without_lines_then_all_link_to_one_mirror(page):
    open_deck(page)
    goto_slide(page, SID, 0)
    dots = page.evaluate("() => document.querySelectorAll('#w-runs circle').length")
    assert dots >= 60
    shown_lines = """() => [...document.querySelectorAll('.world line')].filter(l =>
      +getComputedStyle(l.closest('[data-world-at]')).opacity > .1).length"""
    assert page.evaluate(shown_lines) == 0
    goto_slide(page, SID, 1)
    ends = page.evaluate("""() => { const m = document.querySelector('#w-mirror rect').getBoundingClientRect();
      return [...document.querySelectorAll('#w-links line')].map(l => { const p = l.getBoundingClientRect(), svg = l.ownerSVGElement;
        const pt = svg.createSVGPoint(); pt.x = +l.getAttribute('x2'); pt.y = +l.getAttribute('y2');
        const s = pt.matrixTransform(l.getScreenCTM()); return s.x >= m.left - 2 && s.x <= m.right + 2 && s.y >= m.top - 2 && s.y <= m.bottom + 2; }); }""")
    assert len(ends) == dots and all(ends), "every run links to the one mirror"


def test_notes_fly_from_runs_outside_the_ring_onto_the_mirror(page):
    open_deck(page)
    goto_slide(page, SID, 4)   # stepped through, as presented: each note arrives (and flies) at its own step
    goto_slide(page, SID, 5)
    res = page.evaluate("""() => { const c = e => { const r = e.getBoundingClientRect(); return [(r.left + r.right) / 2, (r.top + r.bottom) / 2]; };
      const m = document.querySelector('#w-mirror rect').getBoundingClientRect();
      const notes = [...document.querySelectorAll('#w-note1 .note-fly, #w-board .note-fly')];
      return { n: notes.length, mirror: [m.left, m.top, m.right, m.bottom],
        ends: notes.map(e => c(e)), anim: notes.map(e => getComputedStyle(e).animationName),
        starts: notes.map(e => Math.hypot(parseFloat(e.style.getPropertyValue('--fx')) || 0, parseFloat(e.style.getPropertyValue('--fy')) || 0)) }; }""")
    l, t, r, b = res["mirror"]
    assert res["n"] >= 4
    for x, y in res["ends"]:
        assert l - 30 <= x <= r + 30 and t - 60 <= y <= t + 20, "notes end pinned on the mirror"
    assert all(a != "none" for a in res["anim"]), "notes fly in"
    assert min(res["starts"]) > 100, "each note starts at its run, out in the ring"


def test_internet_step_shifts_swarm_left_and_board_bridges_out(page):
    open_deck(page)
    goto_slide(page, SID, 5)
    before = page.evaluate(CENTRE, "#w-mirror rect")
    goto_slide(page, SID, 6)
    res = page.evaluate("""() => { const r = s => document.querySelector(s).getBoundingClientRect();
      const runs = [...document.querySelectorAll('#w-runs circle')].map(e => { const b = e.getBoundingClientRect(); return (b.left + b.right) / 2; });
      const m = r('#w-mirror rect'), oai = r('#w-oai rect'), net = r('#w-net rect');
      const p = document.querySelector('#w-net .edge'), L = p.getTotalLength(), ctm = p.getScreenCTM();
      const at = t => { const q = p.getPointAtLength(L * t); const s = q.matrixTransform(ctm); return [s.x, s.y]; };
      return { runsRight: Math.max(...runs), mirror: [m.left, m.right, (m.left + m.right) / 2], oai: [oai.left, oai.right],
               net: [net.left, net.right], start: at(0), end: at(1) }; }""")
    assert res["mirror"][2] > before[0] + 20, "board moves right"
    assert res["runsRight"] < res["mirror"][0], "swarm sits left of the board"
    assert res["oai"][1] <= res["net"][0], "Public Internet sits outside the OpenAI box"
    assert res["oai"][0] <= res["start"][0] <= res["oai"][1], "arrow leaves from inside OpenAI"
    assert res["net"][0] <= res["end"][0] <= res["net"][1], "arrow lands in the Public Internet"


def test_key_glyph_sits_at_the_mirror_bottom_right(page):
    open_deck(page)
    goto_slide(page, SID, 1)
    res = page.evaluate("""() => { const m = document.querySelector('#w-mirror rect').getBoundingClientRect();
      const k = document.querySelector('#w-cred').getBoundingClientRect();
      return [(k.left + k.right) / 2, (k.top + k.bottom) / 2, (m.left + m.right) / 2, (m.top + m.bottom) / 2, m.right + 20, m.bottom + 20]; }""")
    kx, ky, mx, my, rx, by = res
    assert mx < kx <= rx and my < ky <= by


def test_closing_insight_blurs_everything_else(page):
    open_deck(page)
    goto_slide(page, SID, STEPS)
    res = page.evaluate("""() => { const ins = document.querySelector('#s3-insight');
      const blur = e => { const m = getComputedStyle(e).filter.match(/blur\\(([\\d.]+)px\\)/); return m ? +m[1] : 0; };
      return { shown: +getComputedStyle(ins).opacity > .9, text: ins.innerText.replace(/\\s+/g, ' ').trim(),
               world: blur(document.querySelector('.world')), timeline: blur(document.querySelector('#s-3 > .body')) }; }""")
    assert res["shown"] and INSIGHT in res["text"]
    assert res["world"] > 1 and res["timeline"] > 1


def test_impossible_task_agent_keeps_trying_from_many_directions(page):
    open_deck(page)
    goto_slide(page, SID, 3)
    tries = page.evaluate("""() => [...document.querySelectorAll('#s3-pop-impossible .pa-try')].map(g => {
      const p = g.querySelector('path'), L = p.getTotalLength(), a = p.getPointAtLength(L * .5);
      return [Math.round(a.y), getComputedStyle(p).animationName]; })""")
    assert len(tries) >= 4 and len({y // 20 for y, _ in tries}) >= 3
    assert all(name != "none" for _, name in tries)
    assert page.evaluate("() => getComputedStyle(document.querySelector('#s3-pop-impossible .pa-agent')).animationName") != "none"


def test_reduced_motion_stops_the_attempt_animation(page):
    open_deck(page, reduced_motion=True)
    goto_slide(page, SID, 3)
    names = page.evaluate("""() => [...document.querySelectorAll('#s3-pop-impossible .pa-try path, #s3-pop-impossible .pa-agent')]
      .map(e => getComputedStyle(e).animationName)""")
    assert names and all(n == "none" for n in names)


@pytest.mark.parametrize("size", [(1280, 720), (1920, 1080), (1288, 598)])
@pytest.mark.parametrize("step", [3, 7])
def test_timeline_world_and_popover_stay_on_screen_below_the_title(page, size, step):
    open_deck(page, *size)
    goto_slide(page, SID, step)
    boxes = page.evaluate("""id => { const s = document.getElementById(id);
      const r = e => { const b = e.getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom]; };
      const tl = s.querySelector(':scope > .body');
      return { title: r(s.querySelector('.title')), world: r(document.querySelector('.world')), pop: r(s.querySelector('.popover')),
               insight: r(s.querySelector('.overlay--insight')),
               timeline: r(tl), clipped: tl.scrollHeight > tl.clientHeight + 1, vw: innerWidth, vh: innerHeight }; }""", SID)
    assert not boxes["clipped"], "timeline text is clipped"
    for k in (("world", "timeline", "pop") if step == 3 else ("world", "timeline", "insight")):
        l, t, r, b = boxes[k]
        assert l >= 0 and r <= boxes["vw"] + 1 and b <= boxes["vh"] + 1, k
        assert t >= boxes["title"][3] - 1, f"{k} rises over the title"
