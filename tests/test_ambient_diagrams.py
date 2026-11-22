"""Spec: S-007, S-008

Ambient bokeh only where declared; diagram kit honours shared defs and layer order; swarm
module builds with the slide's steps.
Coverage: happy (orbs on ambient slides, swarm renders, key tiles tinted) · edge (reduced motion
freezes drift; small diagrams keep text/edge/arrowhead floors; row titles share a baseline) ·
negative (no orbs on detail slides; no animated dashes; key nodes never below ordinary ones).
"""

import re

import pytest

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


@pytest.mark.deck("v1")
def test_swarm_builds_with_steps_and_coordinators_paint_on_top(page):
    """Engine stages follow steps 1–5 by default; an optional data-stages list remaps step → stage.

    v1 only: v2 has no standalone swarm diagram since s-5 moved onto the incident world (S-022).
    """
    open_deck(page)
    sid, stages = page.evaluate("""() => { const svg = document.querySelector('.diagram[data-diagram=swarm]');
      return [svg.closest('section').id, svg.dataset.stages || '']; }""")
    smap = [int(x) for x in stages.split(",") if x]
    at = (lambda stage: 1 + next(i for i, v in enumerate(smap) if v >= stage)) if smap else (lambda stage: stage)
    goto_slide(page, sid, 0)
    assert page.evaluate(f"() => document.querySelectorAll('#{sid} .agent.is-visible').length") == 0
    goto_slide(page, sid, at(4))
    res = page.evaluate(f"""() => {{
      const svg = document.querySelector('#{sid} .diagram');
      const all = [...svg.querySelectorAll('circle')];
      const hubIdx = all.findIndex(c => c.classList.contains('hub'));
      const lastAgent = all.map(c => c.classList.contains('agent') && !c.classList.contains('hub')).lastIndexOf(true);
      return {{ hubs: svg.querySelectorAll('.hub').length, gone: svg.querySelectorAll('.agent.gone').length,
               hubIdx, lastAgent }}; }}""")
    assert res["hubs"] >= 2 and res["hubIdx"] > res["lastAgent"] and res["gone"] == 0
    goto_slide(page, sid, at(5))
    assert page.evaluate(f"() => document.querySelectorAll('#{sid} .agent.gone').length") > 0


DIAGRAM_METRICS = """() => {
  const out = { text: [], edges: [], marker: null };
  const m = document.querySelector('#arr');
  out.marker = { units: m.getAttribute('markerUnits') || 'strokeWidth', w: +m.getAttribute('markerWidth') };
  document.querySelectorAll('section.slide svg.diagram').forEach(svg => {
    const sc = svg.getScreenCTM().a, sid = svg.closest('section').id;
    svg.querySelectorAll('.tile-title, .tile-sub, .label, .tag').forEach(t => out.text.push(
      [sid, t.getAttribute('class'), t.textContent, parseFloat(getComputedStyle(t).fontSize) * sc]));
    svg.querySelectorAll('.edge').forEach(e => out.edges.push([sid, parseFloat(getComputedStyle(e).strokeWidth), sc]));
  });
  return out;
}"""


@pytest.mark.parametrize("vw,vh,floor", [(1280, 720, 15), (1920, 1080, 20)])
def test_diagram_text_strokes_and_arrowheads_stay_legible_on_screen(page, vw, vh, floor):
    """Diagrams shrink to fit their column; text, edges and heads must still clear the floor."""
    open_deck(page, vw, vh)
    page.wait_for_timeout(300)
    m = page.evaluate(DIAGRAM_METRICS)
    small = [f"{sid} {cls} '{txt}' {px:.1f}px" for sid, cls, txt, px in m["text"] if px < floor - 0.05]
    assert not small, "\n".join(small)
    thin = [f"{sid} {sw * sc:.2f}px" for sid, sw, sc in m["edges"] if sw * sc < 1.75]
    assert not thin, thin
    for sid, sw, sc in m["edges"]:
        head = m["marker"]["w"] * (sw if m["marker"]["units"] == "strokeWidth" else 1) * sc
        assert head >= 12, f"{sid}: arrowhead {head:.1f}px"


def test_key_tiles_are_tinted_and_keep_ink_text(page):
    """tile--key marks the slide's most important objects without borders or accent text."""
    open_deck(page)
    res = page.evaluate("""() => {
      const keys = [...document.querySelectorAll('.diagram .tile.tile--key')];
      const plain = document.querySelector('.diagram .tile:not(.tile--key) rect');
      const ink = getComputedStyle(document.querySelector('.diagram .tile:not(.tile--key) .tile-title')).fill;
      return { n: keys.length, slides: new Set(keys.map(k => (k.closest('section') || k.closest('.world')).id || 'world')).size,
        plainFill: getComputedStyle(plain).fill,
        keys: keys.map(k => [getComputedStyle(k.querySelector('rect')).fill, getComputedStyle(k.querySelector('rect')).stroke,
                             getComputedStyle(k.querySelector('.tile-title')).fill, ink]) }; }""")
    assert res["n"] >= 1, "the deck uses key tiles"  # counts were first-draft content, not the promise
    for fill, stroke, title, ink in res["keys"]:
        assert fill != res["plainFill"], "key tile must be visibly tinted"
        assert stroke == "none" and title == ink


def test_tiles_in_one_row_share_a_title_baseline(page):
    """Timeline tiles with different line counts must not jitter their titles."""
    open_deck(page)
    page.wait_for_timeout(300)
    rows = page.evaluate("""() => {
      const out = {};
      document.querySelectorAll('section.slide svg.diagram .tile').forEach(t => {
        const r = t.querySelector('rect'), svg = t.closest('svg');
        const key = svg.closest('section').id + ':' + r.getAttribute('y') + ':' + r.getAttribute('height');
        (out[key] ||= []).push(+t.querySelector('.tile-title').getAttribute('y'));
      });
      return out; }""")
    jitter = {k: v for k, v in rows.items() if len(v) > 1 and max(v) - min(v) > 0.5}
    assert not jitter, jitter
