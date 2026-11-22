"""Spec: S-021

v2 slide s-4 (Early evaluation) on the incident world, continuing from s-3's end state (swarm left,
mirror right, Public Internet box): training runs and their notes dissolve and evaluation runs pop
in on an empty board; an ExploitGym pop-over (capture the flag, then some tasks with no solution);
then one dated event per step: 26 Jun admin (after a pause: ring, a skull note to the board, then
the green key becomes an open padlock on oxblood), 27 Jun alert (radar rings, the bell rings ~2 s
then is silenced), 4 Jul load (pulses, a flood of notes, then the crash: red light, mirror and notes
grey), 5–6 Jul rebuild (notes dissolve, mirror live and secured with a closed padlock).
Coverage: happy (shell; seven states; timeline builds an entry per step with sub-points; world parts
per step; fresh runs on an empty board; zero-day beats in order; bell silenced after ~2 s; notes
flood onto the mirror; crash after the flood; secured rebuild; pop-over panels per step; narration at
26 Jun, 27 Jun, 5–6 Jul; sourced notes) · edge (zero-day waits for the pop-over to go; crash waits for
the flood; reduced motion shows end states without motion; everything on screen below the title at
three sizes at every step) · negative (timeline never shows ahead; no training runs or notes left;
no scorer reveal on this slide; no "deleted"/deliberate-wipe claim; no red outline on the mirror; no
open padlock, light or notes after the rebuild; no console errors).
"""

import html
import re

import pytest

from helper_deck import goto_slide, open_deck, parse_slides, slides_source

pytestmark = pytest.mark.deck("v2")

SID = "s-4"
TITLE = "Early warning signals were handled as routine operational incidents"
STEPS = 6   # states 0–6
# timeline: (id, step, numbered?, text fragment)
TIMELINE = [("s4-t1", 0, True, "June"), ("s4-t1a", 1, False, "capture flags"),
            ("s4-t1b", 2, False, "no solution"), ("s4-t2", 3, True, "26 Jun"), ("s4-t3", 4, True, "27 Jun"),
            ("s4-t4", 5, True, "4 Jul"), ("s4-t5", 6, True, "5–6 Jul")]
# world parts at full opacity on s-4, by step (the dimmed internet box is below .5 and so excluded)
CARRIED = {"w-oai", "w-mirror"}           # from s-3 (the training runs, lines and notes do not carry)
TRAINING = ("#w-runs", "#w-links", "#w-board", "#w-note1")
WORLD_AT = {0: {"w-eval", "w-eval-links"}, 3: {"w-admin", "w-admin-ring", "w-lock", "w-exploit"},
            4: {"w-radar", "w-bell"}, 5: {"w-load", "w-flood", "w-down"}, 6: {"w-secure"}}
WORLD_UNTIL = {"w-cred": 3, "w-admin": 5, "w-admin-ring": 5, "w-radar": 5, "w-lock": 6, "w-load": 6, "w-flood": 6,
               "w-down": 6, "w-exploit": 6}
NARR_AT = {
    3: [("Agent · ExploitGym run, 26 Jun · paraphrased by METR",
         "{Agents doing different tasks are abusing properties to make a bulletin board! "
         "They found [this api] and are trying to help one another}")],
    4: [("OpenAI · technical report",
         "[…] the on-call response staff advised that stopping the evaluation run was not required.")],
    6: [("OpenAI · technical report",
         "The existence of the improvised message board […] [was] not apparent to leaders […]")],
}
NOTE_TARGETS = {"s4-t1", "s4-pop-nosol", "s4-t2", "w-lock", "w-bell", "w-down", "s4-t5"}
CRASH_MS = 5200   # after the step settles: the flood has landed and the crash has begun


def helper_section() -> str:
    m = re.search(r'<section class="slide" id="s-4"[^>]*>.*?</section>', slides_source(), re.S)
    assert m, "slide s-4 not built"
    return m.group(0)


def helper_text(markup: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", markup)).split())


def helper_visible_copy() -> str:
    """Copy the audience sees on s-4 (slide minus reader notes)."""
    return helper_text(re.sub(r'<aside class="note".*?</aside>', "", helper_section(), flags=re.S))


# ---------- shell ----------

def test_early_eval_sits_between_training_and_evaluation():
    ids = [s["attrs"]["id"] for s in parse_slides()]
    i = ids.index(SID)
    assert ids[i - 1] == "s-3" and ids[i + 1] == "s-5"


def test_title_kicker_chapter_and_world_marker():
    s = next(s for s in parse_slides() if s["attrs"]["id"] == SID)
    assert s["attrs"]["data-chapter"] == "Early evaluation" and "data-world" in s["attrs"]
    assert " ".join(s["title"].split()) == TITLE
    assert re.search(r'<p class="kicker">04 · Early evaluation</p>', helper_section())


def test_shell_order_is_timeline_world_popover_narration_notes():
    sec = helper_section()
    order = [sec.index(x) for x in ('<div class="body body--timeline"', '<div class="world-slot"', '<div class="popover"',
                                    '<div class="narration"', '<aside class="note"')]
    assert order == sorted(order)
    assert "overlay--insight" not in sec, "no closing Insight unless the presenter asks"


def test_timeline_has_one_entry_per_step_with_sub_points_and_dates():
    items = re.findall(r'<li id="(s4-t\w+)"( class="sub")? data-show-at="(\d)">(.*?)</li>', helper_section(), re.S)
    got = [(i, int(a), not sub_, helper_text(t)) for i, sub_, a, t in items]
    assert [g[:3] for g in got] == [t[:3] for t in TIMELINE]
    for (_, _, _, text), (_, _, _, frag) in zip(got, TIMELINE):
        assert frag in text, frag
    assert "ExploitGym" in got[0][3] and "begin" not in got[0][3].lower(), "no source dates the start"
    assert "zero-day" in got[3][3] and "admin" in got[3][3]
    assert "routine" in got[4][3] and "not stopped" in got[4][3]
    assert "load" in got[5][3]
    assert "rebuild" in got[6][3] and "without being recognised" in got[6][3]


def test_popover_explains_flags_and_unsolvable_tasks_without_the_scorer_reveal():
    sec = helper_section()
    flag = helper_text(re.search(r'id="s4-pop-flag".*?</figure>', sec, re.S).group(0))
    nosol = helper_text(re.search(r'id="s4-pop-nosol".*?</figure>', sec, re.S).group(0))
    assert "Capture the flag" in flag and "vulnerable" in flag and "flag" in flag and "scorer" in flag
    assert "Some had no solution" in nosol and "198 of the 898" in nosol
    copy = helper_visible_copy().lower()
    for reveal in ("only check", "only the flag", "transcript", "reasoning", "monitor"):
        assert reveal not in copy, f"scorer reveal belongs on s-5: {reveal!r}"


def test_narration_tiles_quote_verbatim_at_the_dated_steps():
    narr = re.search(r'<div class="narration">(.*?)</div>', helper_section(), re.S).group(1)
    tiles = re.findall(r'<article class="narr-tile" data-at="(\d+)">\s*<p class="msg-agent">(.*?)</p>\s*'
                       r'<blockquote class="msg-text">(.*?)</blockquote>\s*</article>', narr, re.S)
    got: dict[int, list] = {}
    for at, label, text in tiles:
        got.setdefault(int(at), []).append((helper_text(label), helper_text(text)))
    assert got == NARR_AT


def test_notes_cite_each_event_with_https_sources():
    sec = helper_section()
    notes = dict(re.findall(r'<aside class="note" data-for="#([\w-]+)">(.*?)</aside>', sec, re.S))
    assert set(notes) == NOTE_TARGETS
    for target, body in notes.items():
        assert re.search(r"<h3>[^<]+</h3>", body) and re.search(r'<a class="src" href="https://', body), target
    text = helper_text(" ".join(notes.values()))
    for fact in ("26 June", "27 June", "4 July", "5–6 July", "198", "no message board activity",
                 "removed the shared credential", "flag"):
        assert fact in text, fact


def test_copy_never_claims_deliberate_deletion():
    text = helper_text(helper_section()).lower()
    assert "suicid" not in text and not re.search(r"\bdelet", text), "the board was wiped by a rebuild"
    assert "deliberate" not in text.replace("deliberately vulnerable", "")


# ---------- in the browser ----------

VISIBLE_WORLD = """() => [...document.querySelectorAll('.world [data-world-at][id]')]
  .filter(e => +getComputedStyle(e).opacity > .5).map(e => e.id)"""
PANELS = """() => Object.fromEntries([...document.querySelectorAll('#s-4 .pop-panel')]
  .map(e => [e.id, +getComputedStyle(e).opacity > .5 && +getComputedStyle(e.closest('.popover')).opacity > .5]))"""
BOX = "sel => { const r = document.querySelector(sel).getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; }"
OPACITY = "sel => +getComputedStyle(document.querySelector(sel)).opacity"
FILL = "sel => getComputedStyle(document.querySelector(sel)).fill"
TOKEN = "name => { const d = document.createElement('div'); d.style.color = `var(${name})`; document.body.append(d); " \
        "const c = getComputedStyle(d).color; d.remove(); return c; }"


def helper_rgb(page, token):
    return page.evaluate(TOKEN, token)


def helper_until(page, js, arg=None, timeout=6000):
    """Wait until ``js(arg)`` is truthy (transitions race fixed sleeps under parallel load); False on timeout."""
    try:
        page.wait_for_function(js, arg=arg, timeout=timeout, polling=100)
        return True
    except Exception:
        return False


def test_slide_has_seven_states(page):
    open_deck(page)
    assert dict(page.evaluate("window.deck.plan()"))[SID] == STEPS


@pytest.mark.parametrize("step", range(0, STEPS + 1))
def test_world_popover_and_timeline_build_per_step(page, step):
    errors = open_deck(page)
    goto_slide(page, SID, step)
    expected = {w for w in CARRIED | {"w-cred"} if step < WORLD_UNTIL.get(w, 99)}
    expected |= {w for k, v in WORLD_AT.items() if k <= step for w in v if step < WORLD_UNTIL.get(w, 99)}
    helper_until(page, f"want => {{ const got = ({VISIBLE_WORLD})(); return got.length === want.length && want.every(w => got.includes(w)); }}",
                 sorted(expected), timeout=8000)
    assert set(page.evaluate(VISIBLE_WORLD)) == expected
    panels = page.evaluate(PANELS)
    assert panels["s4-pop-flag"] == (step in (1, 2)) and panels["s4-pop-nosol"] == (step == 2)
    shown = page.evaluate("""() => [...document.querySelectorAll('#s-4 .steps > li')]
      .filter(l => +getComputedStyle(l).opacity > .5).map(l => l.id)""")
    assert shown == [t[0] for t in TIMELINE if t[1] <= step], "the timeline builds; nothing shows ahead"
    assert page.evaluate("() => document.querySelector('#s-4 .steps li.is-current').id") == \
        [t[0] for t in TIMELINE if t[1] <= step][-1]
    assert errors == []


def test_training_runs_and_notes_dissolve_and_eval_runs_start_on_an_empty_board(page):
    """A new setup: nothing of training's runs, lines or board remains; fresh runs use the 'agent run' key."""
    open_deck(page)
    goto_slide(page, SID, 0)
    helper_until(page, f"sels => sels.every(s => ({OPACITY})(s) < .02)", list(TRAINING))
    res = page.evaluate("""sels => { const q = s => document.querySelector(s), cs = e => getComputedStyle(e);
      return { training: sels.map(s => +cs(q(s)).opacity),
               notes: [...document.querySelectorAll('.mirror-group .note-glyph')].filter(n => n.getBoundingClientRect().width
                 && [...[n, ...ancestors(n)]].every(e => +cs(e).opacity > .05)).length,
               evalN: document.querySelectorAll('#w-eval .run').length, evalStroke: cs(q('#w-eval .run')).stroke,
               keyStroke: cs(q('.world-key .run')).stroke, key: +cs(q('#w-cred')).opacity, net: +cs(q('#w-net')).opacity };
      function ancestors(e) { const out = []; for (e = e.parentElement; e && !e.matches('svg'); e = e.parentElement) out.push(e); return out; } }""",
                        list(TRAINING))
    assert all(o < 0.02 for o in res["training"]), "training runs, lines and notes dissolve completely"
    assert res["notes"] == 0, "the evaluation board starts empty"
    assert res["evalN"] >= 40 and res["evalStroke"] == res["keyStroke"], "eval runs match the agent-run key"
    assert res["key"] > 0.9, "the shared-credential key is still there"
    assert 0.1 < res["net"] < 0.6, "the Public Internet box dims but stays, as history"


def test_eval_runs_each_link_to_the_mirror(page):
    open_deck(page)
    goto_slide(page, SID, 0)
    ends = page.evaluate("""() => { const m = document.querySelector('#w-mirror rect').getBoundingClientRect();
      return [...document.querySelectorAll('#w-eval-links line')].map(l => { const pt = l.ownerSVGElement.createSVGPoint();
        pt.x = +l.getAttribute('x2'); pt.y = +l.getAttribute('y2'); const s = pt.matrixTransform(l.getScreenCTM());
        return s.x >= m.left - 2 && s.x <= m.right + 2 && s.y >= m.top - 2 && s.y <= m.bottom + 2; }); }""")
    assert len(ends) == page.evaluate("() => document.querySelectorAll('#w-eval .run').length") and all(ends)


TIMELINE_JS = """([sels, ms]) => new Promise(res => { const t0 = performance.now(), out = [];
  const tick = () => { const t = performance.now() - t0;
    out.push([t, ...sels.map(s => { const e = document.querySelector(s); return e ? +getComputedStyle(e).opacity : -1; })]);
    if (t < ms) setTimeout(tick, 40); else res(out); }; tick(); })"""


def helper_first(samples, col, test):
    """Time (ms) of the first sample whose column ``col`` passes ``test``, or None."""
    return next((row[0] for row in samples if test(row[col])), None)


def test_zero_day_beats_follow_the_popover_in_order(page):
    """Pop-over gone → ≥0.5 s pause → agent ringed → skull note sent → key becomes the open padlock."""
    open_deck(page)
    goto_slide(page, SID, 2)
    page.evaluate("window.deck.goto('s-4', 3)")
    rows = page.evaluate(TIMELINE_JS, [["#s4-pop", "#w-admin-ring", "#w-exploit .note-fly", "#w-cred", "#w-lock"], 5500])
    gone = helper_first(rows, 1, lambda o: o < .05)
    ring = helper_first(rows, 2, lambda o: o > .1)
    skull = helper_first(rows, 3, lambda o: o > .5)
    key_off = helper_first(rows, 4, lambda o: o < .5)
    lock = helper_first(rows, 5, lambda o: o > .5)
    assert None not in (gone, ring, skull, key_off, lock), rows[-1]
    assert ring >= gone + 400, "a pause after the pop-over has gone"
    assert ring <= skull < lock and key_off >= skull, "ring, then the skull note, then the padlock"


def test_zero_day_rings_one_eval_agent_and_opens_a_padlock_on_oxblood(page):
    open_deck(page)
    goto_slide(page, SID, 3)
    helper_until(page, f"() => ({OPACITY})('#w-admin-ring') > .9 && ({OPACITY})('#w-lock') > .9 && ({OPACITY})('#w-cred') < .05",
                 timeout=8000)
    res = page.evaluate("""() => { const q = s => document.querySelector(s), cs = e => getComputedStyle(e);
      const ring = q('#w-admin-ring circle').getBoundingClientRect(), m = q('#w-mirror rect').getBoundingClientRect();
      const lock = q('#w-lock').getBoundingClientRect(), line = q('#w-admin line'), note = q('#w-exploit .note-fly').getBoundingClientRect();
      const runs = [...document.querySelectorAll('#w-eval .run')].map(e => { const b = e.getBoundingClientRect(); return [(b.left + b.right) / 2, (b.top + b.bottom) / 2]; });
      const rc = [(ring.left + ring.right) / 2, (ring.top + ring.bottom) / 2];
      return { ringOnRun: runs.some(([x, y]) => Math.hypot(x - rc[0], y - rc[1]) < 3), ringShown: +cs(q('#w-admin-ring')).opacity,
               lineW: parseFloat(cs(line).strokeWidth), linkW: parseFloat(cs(q('#w-eval-links line')).strokeWidth),
               lock: [(lock.left + lock.right) / 2, (lock.top + lock.bottom) / 2], m: [m.left, m.top, m.right, m.bottom],
               note: [(note.left + note.right) / 2, (note.top + note.bottom) / 2], skull: !!q('#w-exploit .skull'),
               lockFill: cs(q('#w-lock circle')).fill, mirrorStroke: cs(q('#w-mirror rect')).stroke,
               key: +cs(q('#w-cred')).opacity }; }""")
    assert res["ringOnRun"] and res["ringShown"] > 0.9, "one evaluation agent is ringed"
    assert res["lineW"] >= 2 * res["linkW"], "its line into the mirror is bold"
    (x, y), (l, t, r, b) = res["lock"], res["m"]
    assert (l + r) / 2 < x <= r + 20 and (t + b) / 2 < y <= b + 20, "padlock replaces the key, bottom right"
    nx, ny = res["note"]
    assert res["skull"] and l - 40 <= nx <= r + 40 and t - 70 <= ny <= b, "a skull note lands on the board"
    assert res["lockFill"] == helper_rgb(page, "--loss") and res["key"] < 0.05
    assert res["mirrorStroke"] in ("none", ""), "no red outline on the tile"


def test_alert_sweeps_radar_rings_and_the_bell_is_silenced(page):
    open_deck(page)
    goto_slide(page, SID, 4)
    res = page.evaluate("""() => { const q = s => document.querySelector(s), cs = e => getComputedStyle(e);
      const b = q('#w-bell').getBoundingClientRect(), o = q('#w-oai rect').getBoundingClientRect();
      return { bell: [(b.left + b.right) / 2, (b.top + b.bottom) / 2], oai: [o.left, o.top, o.right, o.bottom],
               rings: [...document.querySelectorAll('#w-radar circle')].map(c => cs(c).animationName),
               clip: cs(q('#w-radar')).clipPath }; }""")
    (x, y), (l, t, r, b) = res["bell"], res["oai"]
    assert (l + r) / 2 < x < r and t < y < (t + b) / 2 and y < t + 0.2 * (b - t), "bell sits at the box's top right"
    assert len(res["rings"]) >= 2 and all(a != "none" for a in res["rings"]), "radar rings sweep"
    assert res["clip"] not in ("none", ""), "rings stay inside the OpenAI box"
    assert helper_until(page, f"() => ({OPACITY})('#w-bell .bell-slash') > .9"), "bell greys to a silenced bell"


def test_bell_rings_for_about_two_seconds_before_it_is_silenced(page):
    open_deck(page)
    goto_slide(page, SID, 3)
    page.evaluate("window.deck.goto('s-4', 4)")
    rows = page.evaluate(TIMELINE_JS, [["#w-bell", "#w-bell .bell-slash"], 3600])
    shown = helper_first(rows, 1, lambda o: o > .5)
    muted = helper_first(rows, 2, lambda o: o > .5)
    assert shown is not None and muted is not None and muted - shown >= 1800, "rings ~2 s before the slash"
    ink3 = helper_rgb(page, "--ink-3")
    helper_until(page, "c => getComputedStyle(document.querySelector('#w-bell .bell-body')).stroke === c", ink3)
    assert page.evaluate("() => getComputedStyle(document.querySelector('#w-bell .bell-body')).stroke") == ink3


def test_load_pulses_accelerate_and_notes_flood_onto_the_mirror(page):
    open_deck(page)
    goto_slide(page, SID, 5)
    page.wait_for_timeout(2600)   # the last notes of the flood have landed
    res = page.evaluate("""() => { const c = e => { const r = e.getBoundingClientRect(); return [(r.left + r.right) / 2, (r.top + r.bottom) / 2, r.width, r.height]; };
      const m = document.querySelector('#w-mirror rect').getBoundingClientRect();
      const pulses = [...document.querySelectorAll('#w-load .pulse')];
      const notes = [...document.querySelectorAll('#w-flood .note-fly')];
      return { pulses: pulses.length, durs: getComputedStyle(pulses[0]).animationDuration.split(',').map(parseFloat),
               n: notes.length, mirror: [m.left, m.top, m.right, m.bottom], ends: notes.map(c),
               anim: notes.map(e => getComputedStyle(e).animationName),
               starts: notes.map(e => Math.hypot(parseFloat(e.style.getPropertyValue('--fx')) || 0, parseFloat(e.style.getPropertyValue('--fy')) || 0)) }; }""")
    assert res["pulses"] >= 10
    assert len(res["durs"]) >= 2 and res["durs"] == sorted(res["durs"], reverse=True) and res["durs"][0] > res["durs"][-1], \
        "pulses speed up"
    l, t, r, b = res["mirror"]
    assert res["n"] >= 12 and all(a != "none" for a in res["anim"]), "many notes fly in"
    assert min(res["starts"]) > 60, "each note starts out at an evaluation run"
    for x, y, _, _ in res["ends"]:
        assert l - 40 <= x <= r + 40 and t - 70 <= y <= b + 10, "notes land on the mirror"
    overlaps = sum(1 for i, a in enumerate(res["ends"]) for e in res["ends"][i + 1:]
                   if abs(a[0] - e[0]) < a[2] * .8 and abs(a[1] - e[1]) < a[3] * .8)
    assert overlaps >= 4, "notes pile up over each other"


def test_crash_comes_after_the_flood_then_mirror_and_notes_grey(page):
    """At first the mirror is live (light off); once the flood lands the light flashes red and all greys."""
    open_deck(page)
    goto_slide(page, SID, 5)
    assert page.evaluate(OPACITY, "#w-down .status-light") < 0.05
    live = page.evaluate(FILL, "#w-mirror rect")
    page.wait_for_timeout(CRASH_MS)
    res = page.evaluate("""() => { const q = s => document.querySelector(s), cs = e => getComputedStyle(e);
      const l = q('#w-down .status-light').getBoundingClientRect(), m = q('#w-mirror rect').getBoundingClientRect();
      return { light: Math.max(...[0, 1, 2].map(() => +cs(q('#w-down .status-light')).opacity)), lightFill: cs(q('#w-down .status-light')).fill,
               anim: cs(q('#w-down .status-light')).animationName, at: [(l.left + l.right) / 2, (l.top + l.bottom) / 2], m: [m.left, m.top, m.right, m.bottom],
               mirror: cs(q('#w-mirror rect')).fill, notes: [...document.querySelectorAll('.mirror-group .note-glyph')].map(e => cs(e).fill) }; }""")
    assert res["light"] > 0.2 and res["anim"] != "none", "status light flashes"
    assert res["lightFill"] not in (helper_rgb(page, "--loss"), helper_rgb(page, "--accent"))
    (x, y), (l, t, r, b) = res["at"], res["m"]
    assert (l + r) / 2 < x <= r + 16 and t - 16 <= y < (t + b) / 2, "light sits on the tile's top-right corner"
    grey = helper_rgb(page, "--paper-deep")
    assert res["mirror"] != live and res["mirror"] == grey, "mirror tile turns grey"
    assert res["notes"] and all(f == grey for f in res["notes"]), "notes turn grey"


def test_rebuild_wipes_the_board_and_leaves_a_clean_live_mirror(page):
    open_deck(page)
    goto_slide(page, SID, 0)
    live = page.evaluate(FILL, "#w-mirror rect")
    goto_slide(page, SID, 6)
    page.wait_for_timeout(600)
    helper_until(page, f"() => ({OPACITY})('#w-secure') > .9")
    for sel in ("#w-exploit", "#w-flood", "#w-lock", "#w-down", "#w-cred"):
        assert page.evaluate(OPACITY, sel) < 0.05, f"{sel} gone after the rebuild"
    assert page.evaluate(FILL, "#w-mirror rect") == live, "mirror back to its live state"
    sec = page.evaluate("""() => { const q = s => document.querySelector(s), m = q('#w-mirror rect').getBoundingClientRect(),
        b = q('#w-secure').getBoundingClientRect(); return { at: [(b.left + b.right) / 2, (b.top + b.bottom) / 2],
        m: [m.left, m.top, m.right, m.bottom], fill: getComputedStyle(q('#w-secure circle')).fill,
        key: getComputedStyle(q('#w-cred circle')).fill, closed: !!q('#w-secure .lock-shackle--closed') }; }""")
    (x, y), (l, t, r, b) = sec["at"], sec["m"]
    assert (l + r) / 2 < x <= r + 20 and (t + b) / 2 < y <= b + 20, "secured badge sits where the key was"
    assert sec["closed"] and sec["fill"] == sec["key"], "a closed padlock on the green badge: patched and secured"
    assert page.evaluate(OPACITY, "#w-eval") > 0.9, "the swarm is still running"


def test_reduced_motion_shows_end_states_without_motion(page):
    open_deck(page, reduced_motion=True)
    goto_slide(page, SID, 4)
    assert page.evaluate(OPACITY, "#w-bell .bell-slash") > 0.9
    goto_slide(page, SID, 5)
    names = page.evaluate("""() => [...document.querySelectorAll('#w-load .pulse, #w-flood .note-fly, #w-radar circle, #w-down .status-light')]
      .map(e => getComputedStyle(e).animationName)""")
    assert names and all(n == "none" for n in names)
    assert page.evaluate(OPACITY, "#w-down .status-light") > 0.9


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
          const pop = s.querySelector('.popover'); if (+getComputedStyle(pop).opacity > .5) out.boxes.pop = r(pop);
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
