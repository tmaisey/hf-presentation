"""Spec: S-032

Incident world: one persistent diagram shared by world slides (s-3 onward), plus pop-over cards.
Coverage: happy (world shows on a world slide between timeline and narration under the title, with
a run key; builds with steps; pop-over softens the world then sharpens it; notes spotlight world parts) · edge (going back to a
non-world slide hides it; re-entering resets to that step) · negative (world never on a non-world
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


def test_world_key_shows_an_agent_run_dot(page):
    open_deck(page)
    goto_slide(page, page.evaluate(FIRST_WORLD), 0)
    key = page.evaluate("""() => { const k = document.querySelector('.world .world-key');
      return k && {text: k.innerText.trim().toLowerCase(), dot: !!k.querySelector('.run'),
                   shown: k.getBoundingClientRect().height > 0}; }""")
    assert key == {"text": "agent run", "dot": True, "shown": True}


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
