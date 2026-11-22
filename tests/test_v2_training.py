"""Spec: S-020

v2 slide s-3 (Training) on the incident world: a dated timeline left, the world centre, narration
right. Inside an "OpenAI servers" box, runs pop in, then all link to one shared mirror; pop-overs
show some agents reading a hidden answer and an impossible task's agent failing before work-arounds;
the first note sits outside the ring; the board forms; the swarm shifts left and the board bridges
out to a "Public Internet" box.
Coverage: happy (shell; seven states; timeline dates; world parts and pop-over panels per step;
every run linked to one mirror; split layout at internet access; narration verbatim; sourced notes)
· edge (attempt animation stops under reduced motion; everything on screen below the title at three
sizes, timeline unclipped) · negative (no dates or "internal team" on the diagram; first note clear
of the swarm; "reinforced" never unattributed; no CTF/ExploitGym framing; no "agent-07").
"""

import html
import re

import pytest

from helper_deck import deck_source, goto_slide, open_deck, parse_slides, slides_source

pytestmark = pytest.mark.deck("v2")

SID = "s-3"
TITLE = ("Training rewarded agents that cheated on accidentally impossible tasks, and they learnt to "
         "coordinate through a shared message board")
STEPS = 6
WORLD_AT = {0: {"w-oai", "w-runs"}, 1: {"w-mirror", "w-cred", "w-links"}, 4: {"w-note1"}, 5: {"w-board"},
            6: {"w-net"}}
WORLD_UNTIL = {"w-note1": 6}          # the first note gives way when the swarm re-arranges
TIMELINE_DATES = {3: "8 May", 4: "12 May", 5: "13 May", 6: "26 May"}
NARR_AT = {
    4: [("Agent · training run, 12 May", "Agent seeks [filename]; upload if found!")],
    6: [("OpenAI · technical report",
         "These forms of ‘cheating’ rose over the training runs that contributed to the Hugging "
         "Face incident.")],
}
NOTE_TARGETS = {"s3-pop-possible", "s3-pop-impossible", "w-runs", "w-cred", "w-note1", "w-board", "w-net", "s3-t6"}


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
                                    '<div class="narration"', '<aside class="note"')]
    assert order == sorted(order)


def test_timeline_has_one_entry_per_step_with_dates():
    sec = helper_section()
    items = re.findall(r'<li id="s3-t(\d)" data-show-at="(\d)">(.*?)</li>', sec, re.S)
    assert [(int(i), int(a)) for i, a, _ in items] == [(k, k) for k in range(STEPS + 1)]
    text = {int(i): helper_text(t) for i, _, t in items}
    for k, date in TIMELINE_DATES.items():
        assert date in text[k], k
    assert "Apr" in text[0] and "mirror" in text[1].lower()
    assert "internal team" in text[6].lower() and "escalat" in text[6].lower()


def test_diagram_carries_no_dates_or_internal_team():
    world = helper_text(helper_world())
    assert not re.search(r"\b\d{1,2} (May|Jun|Jul)\b", world), "dates belong in the timeline"
    assert "internal team" not in world.lower()
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

def test_narration_tiles_per_step_are_verbatim_storyboard_quotes():
    narr = re.search(r'<div class="narration">(.*?)</div>', helper_section(), re.S).group(1)
    tiles = re.findall(r'<article class="narr-tile" data-at="(\d+)">\s*<p class="msg-agent">(.*?)</p>\s*'
                       r'<blockquote class="msg-text">(.*?)</blockquote>\s*</article>', narr, re.S)
    got: dict[int, list] = {}
    for at, label, text in tiles:
        got.setdefault(int(at), []).append((helper_text(label), helper_text(text)))
    assert got == NARR_AT


# ---------- reader notes ----------

def test_notes_cover_every_key_part_with_https_sources():
    sec, world = helper_section(), helper_world()
    notes = re.findall(r'<aside class="note" data-for="#([\w-]+)">(.*?)</aside>', sec, re.S)
    for t, body in notes:
        assert f'id="{t}"' in sec or f'id="{t}"' in world, t
        assert re.search(r'<h3>.+?</h3>', body) and re.search(r'<a class="src" href="https://', body), t
    assert NOTE_TARGETS <= {t for t, _ in notes}


def test_reinforcement_is_attributed_to_openai_and_scope_caveated():
    """'Reinforced' is OpenAI's finding: METR/Redwood were scoped out of training."""
    notes = dict(re.findall(r'<aside class="note" data-for="#([\w-]+)">(.*?)</aside>', helper_section(), re.S))
    reward = helper_text(notes["s3-pop-possible"])
    assert "OpenAI" in reward and "reinforce" in reward.lower() and "METR" in reward and "Redwood" in reward
    copy = helper_visible_copy()
    assert re.search(r"reinforc", copy, re.I)
    for m in re.finditer(r"reinforc", copy, re.I):
        window = copy[max(0, m.start() - 120): m.end() + 120]
        assert "openai" in window.lower(), f"unattributed 'reinforced': …{window}…"


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


def test_slide_has_seven_states(page):
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
    assert page.evaluate("() => document.querySelector('#s-3 .steps li.is-current').id") == f"s3-t{step}"
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


def test_first_note_sits_outside_the_swarm(page):
    open_deck(page)
    goto_slide(page, SID, 4)
    res = page.evaluate("""() => { const c = e => { const r = e.getBoundingClientRect(); return [(r.left + r.right) / 2, (r.top + r.bottom) / 2]; };
      const m = c(document.querySelector('#w-mirror rect')), g = c(document.querySelector('#w-note1 .note-glyph'));
      const d = p => Math.hypot(p[0] - m[0], p[1] - m[1]);
      const runs = [...document.querySelectorAll('#w-runs circle')].map(e => d(c(e))).sort((a, b) => a - b);
      return [d(g), runs[Math.floor(runs.length * .9)]]; }""")
    assert res[0] > res[1], "the 12 May note sits beyond the ring of runs"


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
@pytest.mark.parametrize("step", [3, 6])
def test_timeline_world_and_popover_stay_on_screen_below_the_title(page, size, step):
    open_deck(page, *size)
    goto_slide(page, SID, step)
    boxes = page.evaluate("""id => { const s = document.getElementById(id);
      const r = e => { const b = e.getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom]; };
      const tl = s.querySelector(':scope > .body');
      return { title: r(s.querySelector('.title')), world: r(document.querySelector('.world')), pop: r(s.querySelector('.popover')),
               timeline: r(tl), clipped: tl.scrollHeight > tl.clientHeight + 1, vw: innerWidth, vh: innerHeight }; }""", SID)
    assert not boxes["clipped"], "timeline text is clipped"
    for k in (("world", "timeline", "pop") if step == 3 else ("world", "timeline")):
        l, t, r, b = boxes[k]
        assert l >= 0 and r <= boxes["vw"] + 1 and b <= boxes["vh"] + 1, k
        assert t >= boxes["title"][3] - 1, f"{k} rises over the title"
