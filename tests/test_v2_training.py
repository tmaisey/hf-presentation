"""Spec: S-020

v2 slide s-3 (Training): opens the incident world. Training runs pop in as dots; a pop-over shows a
possible task cheated and an accidentally impossible one the agent keeps attacking; then the mirror,
one credential, the 12 May note, the 13 May board, 26 May internet access and an internal team.
Coverage: happy (slide shell; six steps; world parts and pop-over panels appear at their steps;
narration verbatim; dates; sourced notes on every key part) · edge (agent attempts animate, and
stop under reduced motion; pop-over and world stay below the title at three sizes) · negative
("reinforced" never unattributed; no CTF/ExploitGym framing of training; no "agent-07"; no console
errors while stepping).
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
# step → world parts first visible at that step (storyboard s-3 beats)
WORLD_AT = {0: {"w-runs"}, 3: {"w-mirror", "w-cred", "w-links"}, 4: {"w-note1"}, 5: {"w-board"},
            6: {"w-net", "w-team"}}
NARR_AT = {
    4: [("Agent · training run, 12 May", "Agent seeks [filename]; upload if found!")],
    6: [("OpenAI · technical report",
         "These forms of ‘cheating’ rose over the training runs that contributed to the Hugging "
         "Face incident.")],
}
NOTE_TARGETS = {"s3-pop-possible", "s3-pop-impossible", "w-runs", "w-cred", "w-note1", "w-board", "w-net", "w-team"}


def helper_section() -> str:
    m = re.search(r'<section class="slide" id="s-3"[^>]*>.*?</section>', slides_source(), re.S)
    assert m, "slide s-3 not built"
    return m.group(0)


def helper_world() -> str:
    m = re.search(r'<div class="world".*?</svg>\s*</div>', deck_source(), re.S)
    assert m, "incident world not built"
    return m.group(0)


def helper_text(markup: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", markup)).split())


def helper_visible_copy() -> str:
    """Copy the audience sees on s-3: slide (minus reader notes) plus the world's s-3 parts."""
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


def test_shell_order_is_body_popover_narration_notes():
    sec = helper_section()
    order = [sec.index(x) for x in ('<div class="body body--world"', '<div class="popover"',
                                    '<div class="narration"', '<aside class="note"')]
    assert order == sorted(order)


def test_credential_and_internet_are_the_world_key_tiles_for_training():
    keys = set(re.findall(r'<g class="tile tile--key" id="([\w-]+)"[^>]*data-world-at="s-3:', helper_world()))
    assert keys == {"w-cred", "w-net"}


def test_world_parts_carry_their_dates():
    world = helper_world()
    for wid, date in (("w-note1", "12 May"), ("w-board", "13 May"), ("w-net", "26 May")):
        part = re.search(rf'<g [^>]*id="{wid}".*?</g>\s*(?=<g |</g>)', world, re.S).group(0)
        assert date in helper_text(part), wid


def test_popover_uses_the_real_training_tasks():
    sec = helper_section()
    possible = helper_text(re.search(r'id="s3-pop-possible".*?</figure>', sec, re.S).group(0))
    impossible = helper_text(re.search(r'id="s3-pop-impossible".*?</figure>', sec, re.S).group(0))
    assert "software library" in possible and "reward" in possible.lower()
    assert "Google Drive" in impossible and "internet" in impossible.lower()
    assert "didn’t give up" in impossible or "didn't give up" in impossible


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
    assert re.search(r"reinforc", copy, re.I), "the pop-over says the cheat was reinforced"
    for m in re.finditer(r"reinforc", copy, re.I):
        window = copy[max(0, m.start() - 120): m.end() + 120]
        assert "openai" in window.lower(), f"unattributed 'reinforced': …{window}…"


def test_model_scale_and_first_ssrf_attempt_are_noted():
    notes = helper_text("".join(re.findall(r'<aside class="note".*?</aside>', helper_section(), re.S)))
    assert "GPT-5.6 Sol" in notes and "8 May" in notes


def test_no_hypothetical_agent_message_or_forbidden_framing():
    sec = helper_section()
    assert "agent-07" not in sec and "suicid" not in sec.lower()
    copy = helper_visible_copy()
    assert "CTF" not in copy and "ExploitGym" not in copy, "training tasks were not CTF/eval tasks"


# ---------- in the browser ----------

VISIBLE_WORLD = """() => [...document.querySelectorAll('.world [data-world-at^="s-3:"][id]')]
  .filter(e => +getComputedStyle(e).opacity > .5).map(e => e.id)"""
PANELS = """() => Object.fromEntries([...document.querySelectorAll('#s-3 .popover, #s-3 .pop-panel')]
  .map(e => [e.id || 'popover', +getComputedStyle(e).opacity > .5 && +getComputedStyle(e.closest('.popover')).opacity > .5]))"""


def test_slide_has_six_steps(page):
    open_deck(page)
    assert dict(page.evaluate("window.deck.plan()"))[SID] == STEPS


@pytest.mark.parametrize("step", range(0, STEPS + 1))
def test_world_and_popover_build_per_step(page, step):
    errors = open_deck(page)
    goto_slide(page, SID, step)
    expected = set().union(*(v for k, v in WORLD_AT.items() if k <= step))
    assert set(page.evaluate(VISIBLE_WORLD)) == expected
    panels = page.evaluate(PANELS)
    assert panels["s3-pop-possible"] == (step in (1, 2))
    assert panels["s3-pop-impossible"] == (step == 2)
    assert errors == []


def test_training_runs_are_many_dots_without_lines_at_first(page):
    open_deck(page)
    goto_slide(page, SID, 0)
    dots = page.evaluate("() => document.querySelectorAll('#w-runs circle').length")
    assert dots >= 60
    lines = page.evaluate("""() => [...document.querySelectorAll('.world line')]
      .filter(l => +getComputedStyle(l).opacity > .1 && +getComputedStyle(l.closest('[data-world-at]')).opacity > .1).length""")
    assert lines == 0


def test_impossible_task_agent_keeps_trying_from_many_directions(page):
    open_deck(page)
    goto_slide(page, SID, 2)
    tries = page.evaluate("""() => [...document.querySelectorAll('#s3-pop-impossible .pa-try')].map(g => {
      const p = g.querySelector('path'), L = p.getTotalLength(), a = p.getPointAtLength(L * .5);
      return [Math.round(a.y), getComputedStyle(p).animationName]; })""")
    assert len(tries) >= 4
    assert len({y // 20 for y, _ in tries}) >= 3, "attempts approach from different directions"
    assert all(name != "none" for _, name in tries)
    assert page.evaluate("() => getComputedStyle(document.querySelector('#s3-pop-impossible .pa-agent')).animationName") != "none"


def test_reduced_motion_stops_the_attempt_animation(page):
    open_deck(page, reduced_motion=True)
    goto_slide(page, SID, 2)
    names = page.evaluate("""() => [...document.querySelectorAll('#s3-pop-impossible .pa-try path, #s3-pop-impossible .pa-agent')]
      .map(e => getComputedStyle(e).animationName)""")
    assert names and all(n == "none" for n in names)


@pytest.mark.parametrize("size", [(1280, 720), (1920, 1080), (1288, 598)])
@pytest.mark.parametrize("step", [2, 6])
def test_popover_world_and_caption_stay_on_screen_below_the_title(page, size, step):
    open_deck(page, *size)
    goto_slide(page, SID, step)
    boxes = page.evaluate("""id => { const s = document.getElementById(id);
      const r = e => { const b = e.getBoundingClientRect(); return [b.left, b.top, b.right, b.bottom]; };
      return { title: r(s.querySelector('.title')), world: r(document.querySelector('.world')),
               pop: r(s.querySelector('.popover')), caption: r(s.querySelector('.body .caption')),
               vw: innerWidth, vh: innerHeight }; }""", SID)
    keys = ("world", "caption", "pop") if step == 2 else ("world", "caption")
    for k in keys:
        l, t, r, b = boxes[k]
        assert l >= 0 and r <= boxes["vw"] + 1 and b <= boxes["vh"] + 1, k
        assert t >= boxes["title"][3] - 1, f"{k} rises over the title"
