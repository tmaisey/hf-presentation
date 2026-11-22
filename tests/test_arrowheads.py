"""Spec: S-008, S-019

Arrowhead alignment, deck-wide (DESIGN §7, *Arrowhead alignment*): every marker-end arrow on every
slide and step sits on its line: the head's axis follows the line where the head meets it, and the
midpoint of the head's base lies on the line, never offset or skewed (curved edges end in a short
straight run so the marker can't skew).
Coverage: happy (every reachable marker-end path, measured from rendered geometry in the path's own
user space, tolerances converted from screen px) · edge (curved pop-art and world edges; coloured
heads; heads on hidden-until-later steps are measured too) · negative (a base midpoint more than
~1.5 screen px off the line, or a head axis more than ~4° off the line's direction under the head).
"""

import pytest

from helper_deck import open_deck

pytestmark = pytest.mark.deck("v2")

BASE_TOL_PX = 1.5   # head base midpoint to the line, screen px
ANGLE_TOL_DEG = 4   # head axis to the line's direction over the head's length

# For each rendered marker-end path: place the head as the browser does (orient=auto: along the end
# tangent; markerUnits=strokeWidth), find the midpoint of its base, and measure (1) its distance to the
# path and (2) the angle between the head axis and the chord of the path under the head.
MEASURE = """() => {
  const out = [];
  document.querySelectorAll('path[marker-end]').forEach((p, i) => {
    const m = (p.getAttribute('marker-end') || '').match(/url\\(#([^)]+)\\)/);
    const mk = m && document.getElementById(m[1]);
    if (!mk) return;
    let L; try { L = p.getTotalLength(); } catch (e) { return; }
    const ctm = p.getScreenCTM();
    if (!L || !ctm) return;
    const scale = Math.sqrt(Math.abs(ctm.a * ctm.d - ctm.b * ctm.c));
    if (!(scale > 0)) return;
    const sw = parseFloat(getComputedStyle(p).strokeWidth) || 1;
    const vb = mk.viewBox.baseVal, u = (+mk.getAttribute('markerWidth') || 3) * sw / vb.width;
    const refX = +mk.getAttribute('refX') || 0, refY = +mk.getAttribute('refY') || 0;
    const shape = mk.querySelector('path, polygon'), bb = shape.getBBox();
    const E = p.getPointAtLength(L), Q = p.getPointAtLength(Math.max(0, L - Math.min(0.05, L / 10)));
    const orient = mk.getAttribute('orient') || '0';
    const th = /^auto/.test(orient) ? Math.atan2(E.y - Q.y, E.x - Q.x) : (+orient) * Math.PI / 180;
    const c = Math.cos(th), s = Math.sin(th);
    const bx = (bb.x - refX) * u, by = (bb.y + bb.height / 2 - refY) * u;
    const B = { x: E.x + c * bx - s * by, y: E.y + s * bx + c * by };
    const head = Math.hypot(bx, by);
    // distance from B to the path, sampled finely over the last three head lengths
    const from = Math.max(0, L - 3 * head), N = 600;
    let dmin = Infinity;
    for (let k = 0; k <= N; k++) { const P = p.getPointAtLength(from + (L - from) * k / N);
      dmin = Math.min(dmin, Math.hypot(P.x - B.x, P.y - B.y)); }
    const H = p.getPointAtLength(Math.max(0, L - head));
    let dth = Math.abs(Math.atan2(E.y - H.y, E.x - H.x) - th) * 180 / Math.PI;
    if (dth > 180) dth = 360 - dth;
    const host = p.closest('section.slide, [id]');
    out.push({ i, where: (p.id ? '#' + p.id : '') + ' in ' + (host ? host.id : '?'),
      d: (p.getAttribute('d') || '').slice(0, 60), off_px: dmin * scale, angle: dth, len_px: L * scale });
  });
  return out;
}"""


def helper_measure_every_step(page):
    """Visit every slide and step; return one measurement per marker-end path (worst seen)."""
    worst = {}
    for sid, last in page.evaluate("() => window.deck.plan()"):
        for k in range(last + 1):
            page.evaluate("([id, s]) => window.deck.goto(id, s)", [sid, k])
            page.wait_for_timeout(60)
            for r in page.evaluate(MEASURE):
                key = r["i"]
                if key not in worst or (r["off_px"], r["angle"]) > (worst[key]["off_px"], worst[key]["angle"]):
                    worst[key] = r | {"at": f"{sid}:{k}"}
    return list(worst.values())


@pytest.mark.parametrize("vw,vh", [(1920, 1080), (1288, 598)])
def test_every_arrowhead_sits_on_its_line_along_its_end_tangent(page, vw, vh):
    assert open_deck(page, vw, vh) == []
    heads = helper_measure_every_step(page)
    assert len(heads) >= 10, "the deck's arrows were found"
    bad = [f"{h['where']} @{h['at']} d={h['d']!r}: base {h['off_px']:.2f}px off, axis {h['angle']:.1f}° off"
           for h in heads if h["len_px"] > 1 and (h["off_px"] > BASE_TOL_PX or h["angle"] > ANGLE_TOL_DEG)]
    assert bad == [], "\n".join(bad)
