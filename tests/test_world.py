"""Spec: S-032

Incident world: one persistent diagram shared by world slides (s-3 onward), plus pop-over cards.
Coverage: happy (world shows on a world slide between timeline and narration under the title, with
a run key on one row (presenter's short labels, text shrunk to the world column, hidden entries
holding their space); it holds one place and scale from one world slide to the next; builds with steps; pop-over softens the world then sharpens it; notes spotlight world parts) · edge (going back to a
non-world slide hides it; re-entering resets to that step; a jump to a later step shows board glyphs
from earlier steps already at rest on the mirror's board) · negative (world never on a non-world
slide; world never over the title; pop-over exit is a rack focus, not a cut).
"""

import pytest

from helper_deck import goto_slide, open_deck

pytestmark = pytest.mark.deck("v2")

WORLD_ON = "() => { const w = document.querySelector('.world'); return !!w && +getComputedStyle(w).opacity > .5 " \
           "&& getComputedStyle(w).visibility !== 'hidden'; }"
VISIBLE_WORLD_IDS = """() => [...document.querySelectorAll('.world [data-world-at][id]')]
  .filter(e => +getComputedStyle(e).opacity > .5).map(e => e.id)"""
WORLD_BLUR = """() => { const f = getComputedStyle(document.querySelector('.world')).filter;
  const m = f.match(/blur\\(([\\d.]+)px\\)/); return m ? +m[1] : 0; }"""
FIRST_WORLD = "() => document.querySelector('section.slide[data-world]').id"
POP_SLIDE = "() => { const p = document.querySelector('section.slide .popover'); return p && [p.closest('section').id, +p.dataset.showAt, +p.dataset.hideAt]; }"


def test_world_shows_only_on_world_slides(page):
    open_deck(page)
    sid = page.evaluate(FIRST_WORLD)
    goto_slide(page, "s-2", 0)
    assert not page.evaluate(WORLD_ON)
    goto_slide(page, sid, 0)
    assert page.evaluate(WORLD_ON)
    goto_slide(page, "s-1", 0)
    assert not page.evaluate(WORLD_ON)


@pytest.mark.parametrize("w,h", [(1920, 1080), (1280, 720), (1288, 598)])
def test_world_sits_between_timeline_and_narration_below_the_title(page, w, h):
    """World slides read left to right: timeline (~30%) · world (~40%) · narration (~30%)."""
    open_deck(page, w, h)
    sid = page.evaluate(FIRST_WORLD)
    goto_slide(page, sid, 0)
    box = page.evaluate("""id => { const s = document.getElementById(id), r = e => { const b = e.getBoundingClientRect();
        return [b.left, b.top, b.right, b.bottom]; };
      return {w: r(document.querySelector('.world')), tl: r(s.querySelector(':scope > .body')),
              nr: r(s.querySelector(':scope > .narration')), tb: s.querySelector('.title').getBoundingClientRect().bottom,
              vw: innerWidth, vh: innerHeight}; }""", sid)
    (l, t, r, b), tl, nr = box["w"], box["tl"], box["nr"]
    assert r - l > 200 and b - t > 150, "world has real size"
    assert t >= box["tb"] - 1 and tl[1] >= box["tb"] - 1, "world and timeline stay below the title"
    assert tl[2] <= l + 1 and r <= nr[0] + 1, "timeline · world · narration, no overlap"
    widths = [tl[2] - tl[0], r - l, nr[2] - nr[0]]
    assert widths[1] > widths[0] and widths[1] > widths[2], "the world gets the widest column"
    assert r <= box["vw"] and b <= box["vh"]


@pytest.mark.parametrize("w,h", [(1920, 1080), (1280, 720), (1288, 598)])
def test_world_holds_its_place_and_scale_between_world_slides(page, w, h):
    """Titles of different lengths must not move or rescale the world: shared parts stay put."""
    open_deck(page, w, h)
    ids = page.evaluate("() => [...document.querySelectorAll('section.slide[data-world]')].map(s => s.id)")
    assert len(ids) >= 2
    boxes = []
    for sid in ids:
        steps = dict(page.evaluate("window.deck.plan()"))[sid]
        goto_slide(page, sid, 0)
        boxes.append(page.evaluate("""() => { const r = e => { const b = e.getBoundingClientRect();
          return [b.left, b.top, b.width, b.height].map(Math.round); };
          return [r(document.querySelector('.world')), r(document.querySelector('#w-oai rect'))]; }"""))
    assert all(b[0] == boxes[0][0] for b in boxes), f"world box moves between world slides: {boxes}"


def test_world_key_shows_an_agent_run_dot(page):
    open_deck(page)
    goto_slide(page, page.evaluate(FIRST_WORLD), 0)
    key = page.evaluate("""() => { const k = document.querySelector('.world .world-key');
      const own = [...k.childNodes].filter(n => !(n.classList && n.classList.contains('world-key-item')));
      return k && {text: own.map(n => n.textContent).join('').trim().toLowerCase(), dot: !!k.querySelector('.run'),
                   shown: k.getBoundingClientRect().height > 0,
                   later: [...k.querySelectorAll('.world-key-item')].every(e => +getComputedStyle(e).opacity < .05)}; }""")
    # later entries (e.g. s-6's hollow ring) join the same row at their slide, never before (DESIGN §10)
    assert key == {"text": "agent run", "dot": True, "shown": True, "later": True}


def test_world_builds_with_steps_and_resets_on_reentry(page):
    open_deck(page)
    sid = page.evaluate(FIRST_WORLD)
    steps = dict(page.evaluate("window.deck.plan()"))[sid]
    goto_slide(page, sid, 0)
    first = set(page.evaluate(VISIBLE_WORLD_IDS))
    goto_slide(page, sid, steps)
    last = set(page.evaluate(VISIBLE_WORLD_IDS))
    assert first < last, "later steps add to the world, keeping what came before"
    goto_slide(page, "s-2", 0)
    goto_slide(page, sid, 0)
    assert set(page.evaluate(VISIBLE_WORLD_IDS)) == first


def test_popover_softens_the_world_then_racks_focus_out(page):
    open_deck(page)
    sid, at, until = page.evaluate(POP_SLIDE)
    goto_slide(page, sid, at - 1)
    assert page.evaluate(WORLD_BLUR) == 0
    goto_slide(page, sid, at)
    assert page.evaluate(WORLD_BLUR) > 1
    assert page.evaluate(f"() => +getComputedStyle(document.querySelector('#{sid} .popover')).opacity") > .9
    page.evaluate(f"() => window.deck.goto('{sid}', {until})")
    page.wait_for_timeout(250)
    mid = page.evaluate(f"""() => {{ const f = getComputedStyle(document.querySelector('#{sid} .popover')).filter;
      const m = f.match(/blur\\(([\\d.]+)px\\)/); return m ? +m[1] : 0; }}""")
    assert mid > 1, "pop-over should defocus before it vanishes"
    page.wait_for_timeout(1200)
    assert page.evaluate(f"() => +getComputedStyle(document.querySelector('#{sid} .popover')).opacity") < .05
    assert page.evaluate(WORLD_BLUR) == 0


def test_reader_notes_spotlight_world_parts(page):
    open_deck(page)
    sid = page.evaluate(FIRST_WORLD)
    goto_slide(page, sid, 0)
    page.keyboard.press("n")
    page.wait_for_timeout(700)
    hits = []
    for _ in range(page.evaluate(f"() => document.querySelectorAll('#{sid} aside.note').length")):
        hits.append(page.evaluate("""() => { const ring = document.querySelector('.ring').getBoundingClientRect();
          const t = [...document.querySelectorAll('.world [id]')].find(e => { const r = e.getBoundingClientRect();
            return r.width && Math.abs(r.left - 14 - ring.left) < 3 && Math.abs(r.top - 14 - ring.top) < 3; });
          return t ? t.id : null; }"""))
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(700)
    assert any(hits), "no note spotlighted a world element"


KEY_ENTRIES = """() => { const k = document.querySelector('.world .world-key'), w = document.querySelector('.world').getBoundingClientRect();
  const boxes = [k.querySelector(':scope > svg'), ...k.querySelectorAll('.world-key-item')].map(e => { const r = e.getBoundingClientRect();
    return [r.left, r.top, r.right, r.bottom]; });
  const kr = k.getBoundingClientRect();
  return {boxes, key: [kr.left, kr.top, kr.right, kr.bottom], world: [w.left, w.right], scroll: k.scrollWidth - k.clientWidth,
          labels: [[...k.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim(),
                   ...[...k.querySelectorAll('.world-key-item')].map(e => e.textContent.trim())]}; }"""


@pytest.mark.parametrize("w,h", [(1920, 1080), (1280, 720), (1288, 598)])
def test_world_key_stays_on_one_row_at_one_height_on_every_world_slide(page, w, h):
    """Presenter, 22 Nov (DESIGN §10): every entry, shown or still hidden, sits on one row inside the world
    column, clear of its neighbours, and the key's height never changes between world slides (so the world
    above it never resizes). Catches the old wrap to two rows once s-5's run roles joined the key."""
    open_deck(page, w, h)
    plan = dict(page.evaluate("window.deck.plan()"))
    worlds = page.evaluate("() => [...document.querySelectorAll('section.slide[data-world]')]"
                           ".filter(s => s.dataset.world !== 'backdrop').map(s => s.id)")
    heights = {}
    for sid in worlds:
        goto_slide(page, sid, plan[sid])
        k = page.evaluate(KEY_ENTRIES)
        assert k["labels"] == ["Agent Run", "Coordinator", "Sacrificed", "HF activity"], "presenter's short labels"
        mids = [(b[1] + b[3]) / 2 for b in k["boxes"]]
        assert max(mids) - min(mids) < 3, f"{sid}: key entries on one row: {k['boxes']}"
        assert all(a[2] <= b[0] + 0.5 for a, b in zip(k["boxes"], k["boxes"][1:])), f"{sid}: entries overlap"
        assert k["scroll"] <= 1 and k["key"][2] <= k["world"][1] + 1, f"{sid}: key overflows the world column"
        assert all(b[0] >= k["world"][0] - 1 and b[2] <= k["world"][1] + 1 for b in k["boxes"]), f"{sid}: entry outside the world"
        heights[sid] = round(k["key"][3] - k["key"][1], 1)
    assert len(set(heights.values())) == 1, f"key height changes between world slides: {heights}"


BOARD_GLYPHS = """() => { const m = document.querySelector('#w-mirror rect').getBoundingClientRect();
  return [...document.querySelectorAll('.world .mirror-group .w-board .note-fly')].filter(n => {
      const h = n.closest('[data-world-at]'); return h.classList.contains('is-visible'); })
    .map(n => { const r = n.getBoundingClientRect(), h = n.closest('[data-world-at]');
      return {id: h.id + ' ' + n.dataset.noteFor, at: h.dataset.worldAt, x: (r.left + r.right) / 2, y: (r.top + r.bottom) / 2, o: +getComputedStyle(n).opacity}; })
    .concat([{mirror: [m.left, m.top, m.right, m.bottom]}]); }"""


def test_board_glyphs_from_earlier_steps_rest_on_the_board_after_a_jump(page):
    """Every board glyph (notes, folders) shown at a world step after s-5:0 that arrived at an earlier step sits
    on the mirror's board, whichever layout stage the mirror is in, straight after a jump there: a carried-over
    part never replays its fly-in from a stale start (the stray folder left of the mirror on s-6/s-7)."""
    open_deck(page)
    plan = dict(page.evaluate("window.deck.plan()"))
    order = page.evaluate("() => [...document.querySelectorAll('section.slide[data-world]')].map(s => s.id)")
    points = [(sid, k) for sid in order[order.index("s-5"):] for k in range(plan[sid] + 1) if (sid, k) != ("s-5", 0)]
    bad = []
    for sid, k in points:
        page.evaluate("() => window.deck.goto('s-3', 0)")   # a world point before every s-5 part: a real jump from there
        page.wait_for_timeout(100)
        page.evaluate("([id, s]) => window.deck.goto(id, s)", [sid, k])
        page.wait_for_timeout(250)
        *glyphs, mirror = page.evaluate(BOARD_GLYPHS)
        l, t, r, b = mirror["mirror"]
        mw, mh = r - l, b - t
        for g in glyphs:
            if g["at"] == f"{sid}:{k}":
                continue   # arriving at this very step: its fly-in is the point
            if not (l - .3 * mw <= g["x"] <= r + .3 * mw and t - 1.6 * mh <= g["y"] <= b):
                bad.append(f"{sid}:{k} {g['id']} at ({g['x']:.0f}, {g['y']:.0f}) off the board {mirror['mirror']}")
            elif g["o"] < .9:
                bad.append(f"{sid}:{k} {g['id']} not yet shown (opacity {g['o']:.2f}): still waiting to fly in")
    assert bad == []
