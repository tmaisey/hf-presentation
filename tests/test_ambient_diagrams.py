"""Spec: S-007, S-008

Ambient bokeh only where declared; diagram kit honours shared defs and layer order; swarm
module builds with the slide's steps.
Coverage: happy (orbs on ambient slides, swarm renders) · edge (reduced motion freezes drift)
· negative (no orbs on detail slides; no animated dashes; key nodes never below ordinary ones).
"""

import re

from helper_deck import goto_slide, open_deck, slides_source

LAYERS = ["layer-edges", "layer-nodes", "layer-key", "layer-labels"]


def test_orbs_only_on_ambient_slides(page):
    open_deck(page)
    res = page.evaluate("""() => [...document.querySelectorAll('section.slide')].map(s =>
      [s.hasAttribute('data-ambient'), s.querySelectorAll('.orb').length])""")
    assert any(a for a, _ in res)
    for ambient, orbs in res:
        assert (orbs > 0) == ambient


def test_reduced_motion_freezes_ambient_drift(page):
    open_deck(page, reduced_motion=True)
    sid = page.evaluate("() => document.querySelector('section.slide[data-ambient]').id")
    goto_slide(page, sid)
    a = page.evaluate(f"() => getComputedStyle(document.querySelector('#{sid} .orb')).transform")
    page.wait_for_timeout(800)
    b = page.evaluate(f"() => getComputedStyle(document.querySelector('#{sid} .orb')).transform")
    assert a == b


def test_diagrams_declare_layers_in_importance_order():
    svgs = re.findall(r'<svg class="diagram"(?![^>]*data-diagram=)[^>]*>(.*?)</svg>', slides_source(), re.S)
    for body in svgs:
        found = [l for l in LAYERS if f'class="{l}"' in body]
        positions = [body.index(f'class="{l}"') for l in found]
        assert positions == sorted(positions), found


def test_edges_use_shared_arrow_and_tiles_have_no_stroke(page):
    open_deck(page)
    res = page.evaluate("""() => ({
      edges: [...document.querySelectorAll('.diagram .edge[marker-end]')].map(e => e.getAttribute('marker-end')),
      tileStrokes: [...document.querySelectorAll('.diagram .tile rect')].map(r => getComputedStyle(r).stroke),
      dashes: [...document.querySelectorAll('.diagram .edge')].map(e => getComputedStyle(e).strokeDasharray) })""")
    assert all(m == "url(#arr)" for m in res["edges"])
    assert all(s == "none" for s in res["tileStrokes"])
    assert all(d == "none" for d in res["dashes"]), "never dashed edges"


def test_swarm_builds_with_steps_and_coordinators_paint_on_top(page):
    open_deck(page)
    sid = page.evaluate("() => document.querySelector('.diagram[data-diagram=swarm]').closest('section').id")
    goto_slide(page, sid, 0)
    assert page.evaluate(f"() => document.querySelectorAll('#{sid} .agent.is-visible').length") == 0
    goto_slide(page, sid, 4)
    res = page.evaluate(f"""() => {{
      const svg = document.querySelector('#{sid} .diagram');
      const all = [...svg.querySelectorAll('circle')];
      const hubIdx = all.findIndex(c => c.classList.contains('hub'));
      const lastAgent = all.map(c => c.classList.contains('agent') && !c.classList.contains('hub')).lastIndexOf(true);
      return {{ hubs: svg.querySelectorAll('.hub').length, hubIdx, lastAgent }}; }}""")
    assert res["hubs"] >= 2 and res["hubIdx"] > res["lastAgent"]
    goto_slide(page, sid, 5)
    assert page.evaluate(f"() => document.querySelectorAll('#{sid} .agent.gone').length") > 0
