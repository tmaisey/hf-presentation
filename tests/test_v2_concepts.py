"""Spec: S-019

v2 concepts slide (s-2): the approved "incomplete proxy" title, three plain statements on the left and a
step-built triangle reward loop on the right (storyboard s-2): Test environments (an overlapping stack, the
many rollouts) at the apex, AI model bottom-left, Automated scorer bottom-right; model → tests up the left
side; three scored attempts down the right side, one a verified success (bold green, its tick on the scorer
edge); a green reward back along the base with an "Aligned reinforcement:" annotation; then a red attempt
that also passes (its own tick) and a red return inside the green one, with a "Misaligned reinforcement:"
annotation; statement 3; a closing Insight.
Coverage: happy (shell and approved copy; six states; triangle geometry; per-step arrows, colours, ticks,
annotations with run-in labels; statement 3 at step 4; Insight verbatim at step 5; sourced notes) · edge
(arrowheads match their arrow's colour; ticks sit on the scorer box edge; red return inside the green;
annotation centred under the base; box text a size below body; nothing overlaps the drawn diagram at three
sizes) · negative (no first-draft tiles; no narration tiles; no reward before step 2; no red before step 3;
no coloured side bar on the annotation cards; no forbidden wording).
"""

import math
import re

import pytest

from helper_deck import goto_slide, open_deck, parse_slides, slides_source

pytestmark = pytest.mark.deck("v2")

SID = "s-2"
TITLE = "Reward is an incomplete proxy for actual desired behaviour"
STATEMENTS = [
    "In training, one model attempts thousands of tasks and is rewarded only when an automated check says "
    "it succeeded.",
    "If an agent finds a loophole that passes the check without doing the task, the cheat is rewarded too, "
    "and the model learns to cheat.",
    "Learnt misaligned behaviours persist in production models if undetected, leading to unintended and "
    "potentially harmful behaviours at scale.",
]
LEAD_OK, LEAD_LOSS = "Aligned reinforcement:", "Misaligned reinforcement:"
ANNOT_REWARD = (f"{LEAD_OK} the model is rewarded only for successes the scorer verifies, so those behaviours "
                "are reinforced.")
ANNOT_HACK = (f"{LEAD_LOSS} agents can find loopholes in their environment to 'reward hack' (cheat) the task. "
              "If undetected, the cheat is rewarded and reinforced.")
INSIGHT = ("Alignment of AI agents during reinforcement learning is unsolved. It's practically impossible to "
           "assure that agents won't cheat without unintended consequences.")   # shortened, presenter 22 Nov
TR = "https://cdn.openai.com/pdf/67869394-cb91-4c12-888c-5cbd85c7814c/"
SIZES = [(1920, 1080), (1280, 720), (1288, 598)]

# On-screen state of the s-2 diagram, read from rendered geometry (SVG user units), not markup: shown tiles
# (by title; every box of the test stack counts as "Test environments") with their boxes; shown edges (by
# the tile their ends touch, end points, colour, width, arrowhead fill); shown tick badges; visible text;
# the shown annotation cards (text, run-in label and its colour/weight, border widths, screen rect).
STATE = """sid => {
  const s = document.getElementById(sid), svg = s.querySelector('svg.diagram');
  const op = e => { let o = 1; for (let n = e; n && n.nodeType === 1; n = n.parentElement) o *= +getComputedStyle(n).opacity; return o; };
  const shown = e => op(e) > 0.5;
  const title = t => [...t.querySelectorAll('.tile-title')].map(x => x.textContent.trim()).join(' ').trim();
  const tiles = [...svg.querySelectorAll('.tile')].filter(shown).map(t => {
    const r = t.querySelector('rect'), b = { x: +r.getAttribute('x'), y: +r.getAttribute('y'),
      w: +r.getAttribute('width'), h: +r.getAttribute('height') };
    return { title: title(t), b, front: !!title(t) }; });
  // overlapping boxes form one stack, named by the titles it carries (a cascade of test environments)
  const ov = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
  const grp = tiles.map((_, i) => i), root = i => grp[i] === i ? i : (grp[i] = root(grp[i]));
  tiles.forEach((a, i) => tiles.forEach((b, j) => { if (i < j && ov(a.b, b.b)) grp[root(j)] = root(i); }));
  const named = tiles.map((t, i) => ({ title: tiles.filter((_, j) => root(j) === root(i)).map(u => u.title)
    .filter(Boolean).join(' '), b: t.b, front: t.front }));
  const near = p => {   // the tile whose box (plus the edge gap and a badge) the point lies in
    let best = null;
    named.forEach(t => { const { x, y, w, h } = t.b;
      if (p.x >= x - 40 && p.x <= x + w + 40 && p.y >= y - 40 && p.y <= y + h + 40) best = t.title; });
    return best; };
  const markerFill = e => { const m = (e.getAttribute('marker-end') || '').match(/url\\(#([^)]+)\\)/);
    const p = m && document.querySelector('#' + m[1] + ' path'); return p ? getComputedStyle(p).fill : null; };
  const headW = e => { const m = (e.getAttribute('marker-end') || '').match(/url\\(#([^)]+)\\)/), mk = m && document.getElementById(m[1]);
    return mk ? mk.markerWidth.baseVal.value * (mk.markerUnits.baseVal === 2 ? parseFloat(getComputedStyle(e).strokeWidth) : 1) : 0; };
  const edges = [...svg.querySelectorAll('.edge')].filter(shown).map(e => {
    const L = e.getTotalLength(), a = e.getPointAtLength(0), z = e.getPointAtLength(L);
    return { from: near(a), to: near(z), start: [a.x, a.y], end: [z.x, z.y], stroke: getComputedStyle(e).stroke,
      width: parseFloat(getComputedStyle(e).strokeWidth), head: markerFill(e), headw: headW(e) }; });
  const ticks = [...svg.querySelectorAll('.tick-badge')].filter(shown).map(g => {
    const b = g.getBBox(), m = g.getCTM(), sm = svg.getCTM().inverse().multiply(m);
    const c = new DOMPoint(b.x + b.width / 2, b.y + b.height / 2).matrixTransform(sm);
    return [c.x, c.y]; });
  const text = [...s.querySelectorAll('.body p, .overlay p')].filter(shown).map(p => p.textContent.replace(/\\s+/g, ' ').trim());
  const insight = [...s.querySelectorAll('.overlay--insight.is-shown p')].map(p => p.textContent.replace(/\\s+/g, ' ').trim());
  const annots = [...s.querySelectorAll('.fig-notes > *')].filter(shown).map(a => {
    const cs = getComputedStyle(a), lead = a.querySelector('strong'), r = a.getBoundingClientRect();
    return { text: a.textContent.replace(/\\s+/g, ' ').trim(), lead: lead && lead.textContent.trim(),
      leadColor: lead && getComputedStyle(lead).color, leadWeight: lead && +getComputedStyle(lead).fontWeight,
      borders: ['Left', 'Right', 'Top', 'Bottom'].map(k => parseFloat(cs['border' + k + 'Width'])),
      shadow: cs.boxShadow, rect: [r.left, r.top, r.right, r.bottom] }; });
  const box = t => { const r = [...svg.querySelectorAll('.tile')].find(x => title(x) === t);
    const b = r && r.querySelector('rect').getBoundingClientRect(); return b && [b.left, b.top, b.right, b.bottom]; };
  const tt = svg.querySelector('.tile-title');
  const cs = getComputedStyle(document.documentElement);
  const rgb = v => { const d = document.createElement('i'); d.style.color = v; document.body.appendChild(d);
    const c = getComputedStyle(d).color; d.remove(); return c; };
  return { tiles: named.map(t => t.title), boxes: named, edges, ticks, text, insight, annots,
    screen: { model: box('AI model'), scorer: box('Automated scorer') },
    tileFont: parseFloat(getComputedStyle(tt).fontSize) * svg.getScreenCTM().a,
    bodyFont: parseFloat(getComputedStyle(s.querySelector('.body p')).fontSize),
    accent: rgb(cs.getPropertyValue('--accent')), accentInk: rgb(cs.getPropertyValue('--accent-ink')),
    loss: rgb(cs.getPropertyValue('--loss')), ink3: rgb(cs.getPropertyValue('--ink-3')) };
}"""

MODEL, TESTS, SCORER = "AI model", "Test environments", "Automated scorer"


def _norm(s):
    return " ".join(s.replace("’", "'").replace("‘", "'").split())


def _section_src():
    m = re.search(r'<section[^>]*id="s-2".*?</section>', slides_source(), re.S)
    assert m, "s-2 not built"
    return m.group(0)


def _settle(page):
    """Wait until the slide's finite transitions/animations have finished (robust under parallel load)."""
    page.wait_for_function("""sid => { const s = document.getElementById(sid);
      return document.getAnimations().every(a => a.playState !== 'running' || !(a.effect && a.effect.target
        && s.contains(a.effect.target)) || a.effect.getComputedTiming().endTime === Infinity); }""",
                           arg=SID, timeout=10000)


def _state(page, k):
    goto_slide(page, SID, k)
    _settle(page)
    st = page.evaluate(STATE, SID)
    st["text"] = [_norm(t) for t in st["text"]]
    st["insight"] = [_norm(t) for t in st["insight"]]
    for a in st["annots"]:
        a["text"] = _norm(a["text"])
    return st


def _between(st, a, b, colour=None):
    return [e for e in st["edges"] if (e["from"], e["to"]) == (a, b) and (colour is None or e["stroke"] == colour)]


def _centre(st, name):
    """Centre of the named tile; for the test stack, the front (titled) box."""
    b = next(t["b"] for t in st["boxes"] if t["title"] == name and t["front"])
    return b["x"] + b["w"] / 2, b["y"] + b["h"] / 2


def _on_scorer_edge(st, pt, tol=6):
    """True when a point lies on the scorer box's outline (within tol units)."""
    b = next(t["b"] for t in st["boxes"] if t["title"] == SCORER)
    x, y = pt
    in_x, in_y = b["x"] - tol <= x <= b["x"] + b["w"] + tol, b["y"] - tol <= y <= b["y"] + b["h"] + tol
    on_h = in_x and min(abs(y - b["y"]), abs(y - b["y"] - b["h"])) <= tol
    on_v = in_y and min(abs(x - b["x"]), abs(x - b["x"] - b["w"])) <= tol
    return on_h or on_v


def test_concepts_slide_follows_the_title_slide_with_approved_title():
    slides = parse_slides()
    assert [s["attrs"]["id"] for s in slides[:2]] == ["s-1", SID]
    s = slides[1]
    assert s["attrs"].get("data-chapter") == "Concepts"
    assert _norm(s["title"]) == TITLE
    kicker = re.search(r'<p class="kicker">(.*?)</p>', _section_src()).group(1)
    assert re.fullmatch(r"0\d · Concepts", kicker), kicker


def test_slide_has_six_states(page):
    assert open_deck(page) == []
    assert dict(page.evaluate("() => window.deck.plan()"))[SID] == 5


def test_step_zero_is_an_equilateral_triangle_with_tests_at_the_apex(page):
    open_deck(page)
    st = _state(page, 0)
    assert st["tiles"].count(MODEL) == 1, "a single model is trained"
    assert st["tiles"].count(TESTS) >= 3, "overlapping test boxes read as many rollouts"
    assert st["tiles"].count(SCORER) == 1
    (mx, my), (tx, ty), (sx, sy) = (_centre(st, n) for n in (MODEL, TESTS, SCORER))
    assert abs(my - sy) < 4 and mx < tx < sx and ty < my, "tests at the apex, model left and scorer right"
    sides = [math.dist((mx, my), (tx, ty)), math.dist((tx, ty), (sx, sy)), math.dist((mx, my), (sx, sy))]
    assert max(sides) / min(sides) < 1.05, f"equilateral: {sides}"
    up = _between(st, MODEL, TESTS)
    assert len(up) == 1, "the model goes into the tests"
    (ax, ay), (bx, by) = up[0]["start"], up[0]["end"]
    assert ax < bx and ay > by, "up the left side, from the model to the tests"
    assert not [e for e in st["edges"] if SCORER in (e["from"], e["to"])], "the scorer waits for step 1"
    assert st["text"] == [STATEMENTS[0]], "statement 1 only"


def test_step_one_scores_three_attempts_with_the_success_ticked_on_the_scorer_edge(page):
    open_deck(page)
    st = _state(page, 1)
    scored = _between(st, TESTS, SCORER)
    assert len(scored) == 3
    green = [e for e in scored if e["stroke"] == st["accent"]]
    grey = [e for e in scored if e["stroke"] == st["ink3"]]
    assert len(green) == 1 and len(grey) == 2
    gw, kw = green[0]["width"], max(e["width"] for e in grey)
    # presenter, 22 Nov: the first build (2x grey, heads scaled with it) read blocky
    assert 1.2 * kw <= gw <= 1.6 * kw, f"the success stands out without being heavy ({gw} vs {kw})"
    assert abs(green[0]["headw"] - grey[0]["headw"]) <= 1, "coloured heads match the grey heads' size"
    for e in scored:
        (ax, ay), (bx, by) = e["start"], e["end"]
        assert bx > ax and by > ay, "attempts run down the right side"
    assert len({tuple(round(v) for v in e["end"]) for e in scored}) == 3, "three distinct arrows"
    assert len(st["ticks"]) == 1, "one round tick"
    assert _on_scorer_edge(st, st["ticks"][0]), "the tick sits on the scorer box edge"
    assert math.dist(st["ticks"][0], green[0]["end"]) < 45, "where the green arrow lands"
    assert not _between(st, SCORER, MODEL), "no reward yet"
    assert st["annots"] == []


def test_step_two_rewards_the_model_along_the_base_and_annotates_it(page):
    open_deck(page)
    st = _state(page, 2)
    back = _between(st, SCORER, MODEL, st["accent"])
    assert len(back) == 1, "green reward arrow closes the loop"
    (ax, ay), (bx, by) = back[0]["start"], back[0]["end"]
    assert bx < ax and abs(ay - by) < 4, "along the base, scorer to model"
    assert [a["text"] for a in st["annots"]] == [ANNOT_REWARD]
    a = st["annots"][0]
    assert a["lead"] == LEAD_OK and a["leadColor"] == st["accentInk"] and a["leadWeight"] >= 600
    assert STATEMENTS[1] not in st["text"]
    assert not [e for e in st["edges"] if e["stroke"] == st["loss"]], "no red before step 3"


def test_step_three_adds_a_passing_red_attempt_and_a_red_return_inside_the_green(page):
    open_deck(page)
    st = _state(page, 3)
    red_in = _between(st, TESTS, SCORER, st["loss"])
    red_back = _between(st, SCORER, MODEL, st["loss"])
    green_back = _between(st, SCORER, MODEL, st["accent"])
    assert len(red_in) == 1 and len(red_back) == 1 and len(green_back) == 1
    assert len(_between(st, TESTS, SCORER)) == 3, "still three attempts: one turned red"
    assert len(st["ticks"]) == 2 and all(_on_scorer_edge(st, t) for t in st["ticks"])
    assert min(math.dist(t, red_in[0]["end"]) for t in st["ticks"]) < 45, "the cheat passes the check too"
    _, ty = _centre(st, TESTS)
    ry, gy = red_back[0]["end"][1], green_back[0]["end"][1]
    assert ty < ry < gy and gy - ry < 80, "the red return runs just inside the green one"
    assert [a["text"] for a in st["annots"]] == [ANNOT_HACK], "step 2's annotation dissolves"
    a = st["annots"][0]
    assert a["lead"] == LEAD_LOSS and a["leadColor"] == st["loss"] and a["leadWeight"] >= 600
    assert st["text"][:2] == STATEMENTS[:2] and STATEMENTS[2] not in st["text"]


def test_step_four_adds_statement_three(page):
    open_deck(page)
    st = _state(page, 4)
    assert st["text"][:3] == STATEMENTS
    assert st["insight"] == []


def test_coloured_arrows_carry_heads_in_their_own_colour(page):
    open_deck(page)
    st = _state(page, 3)
    coloured = [e for e in st["edges"] if e["stroke"] in (st["accent"], st["loss"])]
    assert len(coloured) == 4
    assert all(e["head"] == e["stroke"] for e in coloured), coloured


def test_step_five_is_the_insight_verbatim_and_only_there(page):
    open_deck(page)
    assert _state(page, 4)["insight"] == []
    assert _state(page, 5)["insight"] == [INSIGHT]


def test_annotation_cards_are_plain_with_no_coloured_side_bar(page):
    """NEVER a coloured side bar or border stripe (DESIGN §10): a plain card with the lift shadow."""
    open_deck(page)
    for k in (2, 3):
        for a in _state(page, k)["annots"]:
            assert a["borders"] == [0, 0, 0, 0], a
            assert a["shadow"] != "none"


@pytest.mark.parametrize("vw,vh", SIZES)
def test_annotation_sits_centred_under_the_base_and_box_text_is_a_size_below_body(page, vw, vh):
    open_deck(page, vw, vh)
    for k in (2, 3):
        st = _state(page, k)
        (l, t, r, b), m, s = st["annots"][0]["rect"], st["screen"]["model"], st["screen"]["scorer"]
        assert t >= max(m[3], s[3]) - 1, "under the base"
        assert abs((l + r) / 2 - (m[0] + s[2]) / 2) < 0.06 * (s[2] - m[0]), "centred under model and scorer"
        assert b <= vh, "on screen"
    assert st["tileFont"] < st["bodyFont"] - 1, "box text is smaller than the statements"


def test_first_draft_loop_and_narration_are_gone():
    src = _section_src()
    titles = " ".join(re.findall(r'<text class="tile-title">([^<]*)</text>', src))
    for old in ("Action", "Loophole", "Weights", "Reward check", "Agent"):
        assert not re.search(rf"\b{old}\b", titles), old
    assert "narr-tile" not in src and 'class="narration"' not in src


def test_notes_target_slide_elements_and_cite_primary_sources():
    src = _section_src()
    notes = re.findall(r'<aside class="note" data-for="#([\w-]+)">(.*?)</aside>', src, re.S)
    assert len(notes) >= 4
    for target, body in notes:
        assert re.search(rf'id="{target}"', src), target
        assert re.search(r'<a class="src" href="https://', body), target
    joined = " ".join(b for _, b in notes)
    assert "hidden efficiencies and shortcuts" in joined, "storyboard note: boundary hard to draw"
    assert TR in joined
    body_ids = re.findall(r'<p id="([\w-]+)"', src)[:3]
    assert len(body_ids) == 3 and set(body_ids) <= {t for t, _ in notes}, "every statement carries a note"


def test_forbidden_wording_absent():
    text = re.sub(r"<[^>]+>", " ", _section_src()).lower()
    assert "suicide" not in text and "openai's agent swarm" not in text
    assert not re.search(r",\s+not\s+(the|a|an)\b", text)


@pytest.mark.parametrize("vw,vh", SIZES)
def test_annotations_and_statements_never_cover_the_drawn_diagram(page, vw, vh):
    """Annotation cards and statements never sit over a tile, arrow or tick at any built step."""
    assert open_deck(page, vw, vh) == []
    bad = []
    for k in range(5):
        goto_slide(page, SID, k)
        bad += [f"@{k}: {b}" for b in page.evaluate("""sid => {
          const s = document.getElementById(sid), out = [];
          const op = e => { let o = 1; for (let n = e; n && n.nodeType === 1; n = n.parentElement) o *= +getComputedStyle(n).opacity; return o; };
          const hit = (a, b) => a.left < b.right - 1 && a.right > b.left + 1 && a.top < b.bottom - 1 && a.bottom > b.top + 1;
          const drawn = [...s.querySelectorAll('svg.diagram .tile rect, svg.diagram .edge, svg.diagram .tick-badge')]
            .filter(e => op(e) > 0.05).map(e => e.getBoundingClientRect());
          s.querySelectorAll('.body p').forEach(p => { if (op(p) < 0.05) return;
            const r = p.getBoundingClientRect();
            if (drawn.some(d => hit(r, d))) out.push('covers diagram: ' + p.textContent.trim().slice(0, 40)); });
          return out; }""", SID)]
    assert bad == [], "\n".join(bad)
