"""Spec: S-032

Incident world: one persistent diagram shared by world slides (s-3 onward), plus pop-over cards.
Coverage: happy (world shows on a world slide, fits its body under the title, builds with steps;
pop-over softens the world then sharpens it; notes spotlight world parts) · edge (going back to a
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
def test_world_fits_its_slide_body_below_the_title(page, w, h):
    open_deck(page, w, h)
    sid = page.evaluate(FIRST_WORLD)
    goto_slide(page, sid, 0)
    box = page.evaluate("""id => { const s = document.getElementById(id), r = e => e.getBoundingClientRect();
      const w = r(document.querySelector('.world')), b = r(s.querySelector('.body')), t = r(s.querySelector('.title'));
      return {w: [w.left, w.top, w.right, w.bottom], b: [b.left, b.top, b.right, b.bottom], tb: t.bottom, vw: innerWidth, vh: innerHeight}; }""", sid)
    l, t, r, b = box["w"]
    assert r - l > 200 and b - t > 150, "world has real size"
    assert t >= box["tb"] - 1, "world rises over the title"
    assert l >= box["b"][0] - 1 and r <= box["b"][2] + 1 and b <= box["b"][3] + 1, "world stays inside the body"
    assert r <= box["vw"] and b <= box["vh"]


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
