"""Spec: S-019

v2 concepts slide (s-2): the approved "incomplete proxy" title, two plain statements on the left and a
step-built boxes-and-arrows reward loop on the right (storyboard s-2): one AI model → a stack of test
environments (many rollouts) → an automated scorer; three scored attempts, one a verified success
(bold green, tick at the scorer); the reward flows back to the model with an annotation; then a red
reward-hack path replaces it with its own annotation and the second statement; a closing Insight.
Coverage: happy (shell and approved copy; five states; per-step tiles, arrows, colours, tick and
annotations; Insight verbatim at step 4; sourced notes) · edge (arrowheads match their arrow's colour;
statement 2 waits for step 3; step 2's annotation dissolves at step 3; annotation and statements
never overlap the drawn diagram at three sizes) · negative (none of the first draft's
Action/Loophole/Weights tiles; no narration tiles; no reward arrow before step 2; no red before
step 3; no forbidden wording).
"""

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
]
ANNOT_REWARD = ("The model is rewarded only for successes the scorer verifies, so those behaviours are "
                "reinforced.")
ANNOT_HACK = ("Agents can find loopholes in their environment to 'reward hack' (cheat) the task. If "
              "undetected, the cheat is rewarded and reinforced.")
INSIGHT = ("Alignment of AI agents during reinforcement learning is unsolved. It is practically impossible to "
           "assure agents won't cheat, and efforts to constrain cheating can have unintended consequences, "
           "like subversion or more sophisticated cheating.")
TR = "https://cdn.openai.com/pdf/67869394-cb91-4c12-888c-5cbd85c7814c/"
SIZES = [(1920, 1080), (1280, 720), (1288, 598)]

# On-screen state of the s-2 diagram: shown tiles (by title; every box of the test stack counts as
# "Test environments"), shown edges (by the tile their ends touch, colour, width, arrowhead fill),
# shown tick badges, visible text in the slide. Read from rendered geometry, not markup.
STATE = """sid => {
  const s = document.getElementById(sid), svg = s.querySelector('svg.diagram');
  const op = e => { let o = 1; for (let n = e; n && n.nodeType === 1; n = n.parentElement) o *= +getComputedStyle(n).opacity; return o; };
  const shown = e => op(e) > 0.5;
  const title = t => [...t.querySelectorAll('.tile-title')].map(x => x.textContent.trim()).join(' ').trim();
  const tiles = [...svg.querySelectorAll('.tile')].filter(shown).map(t => {
    const r = t.querySelector('rect'), b = { x: +r.getAttribute('x'), y: +r.getAttribute('y'),
      w: +r.getAttribute('width'), h: +r.getAttribute('height') };
    return { title: title(t), b }; });
  // overlapping boxes form one stack, named by the titles it carries (a cascade of test environments)
  const ov = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
  const grp = tiles.map((_, i) => i), root = i => grp[i] === i ? i : (grp[i] = root(grp[i]));
  tiles.forEach((a, i) => tiles.forEach((b, j) => { if (i < j && ov(a.b, b.b)) grp[root(j)] = root(i); }));
  const named = tiles.map((t, i) => ({ title: tiles.filter((_, j) => root(j) === root(i)).map(u => u.title)
    .filter(Boolean).join(' '), b: t.b }));
  const near = p => {   // the tile whose box (plus the edge gap) the point lies in; ties → the one painted last
    let best = null;
    named.forEach(t => { const { x, y, w, h } = t.b;
      if (p.x >= x - 26 && p.x <= x + w + 26 && p.y >= y - 26 && p.y <= y + h + 26) best = t.title; });
    return best; };
  const markerFill = e => { const m = (e.getAttribute('marker-end') || '').match(/url\\(#([^)]+)\\)/);
    const p = m && document.querySelector('#' + m[1] + ' path'); return p ? getComputedStyle(p).fill : null; };
  const edges = [...svg.querySelectorAll('.edge')].filter(shown).map(e => {
    const L = e.getTotalLength(), a = e.getPointAtLength(0), z = e.getPointAtLength(L);
    return { from: near(a), to: near(z), end: [z.x, z.y], stroke: getComputedStyle(e).stroke,
      width: parseFloat(getComputedStyle(e).strokeWidth), head: markerFill(e) }; });
  const ticks = [...svg.querySelectorAll('.tick-badge')].filter(shown).map(g => {
    const b = g.getBBox(), m = g.getCTM(), sm = svg.getCTM().inverse().multiply(m);
    const c = new DOMPoint(b.x + b.width / 2, b.y + b.height / 2).matrixTransform(sm);
    return [c.x, c.y]; });
  const text = [...s.querySelectorAll('.body p, .overlay p')].filter(shown).map(p => p.textContent.replace(/\\s+/g, ' ').trim());
  const insight = [...s.querySelectorAll('.overlay--insight.is-shown p')].map(p => p.textContent.replace(/\\s+/g, ' ').trim());
  const cs = getComputedStyle(document.documentElement);
  const rgb = v => { const d = document.createElement('i'); d.style.color = v; document.body.appendChild(d);
    const c = getComputedStyle(d).color; d.remove(); return c; };
  return { tiles: named.map(t => t.title), edges, ticks, text, insight,
    accent: rgb(cs.getPropertyValue('--accent')), loss: rgb(cs.getPropertyValue('--loss')),
    ink3: rgb(cs.getPropertyValue('--ink-3')) };
}"""

MODEL, TESTS, SCORER = "AI model", "Test environments", "Automated scorer"


def _norm(s):
    return " ".join(s.replace("’", "'").replace("‘", "'").split())


def _section_src():
    m = re.search(r'<section[^>]*id="s-2".*?</section>', slides_source(), re.S)
    assert m, "s-2 not built"
    return m.group(0)


def _state(page, k):
    goto_slide(page, SID, k)
    st = page.evaluate(STATE, SID)
    st["text"] = [_norm(t) for t in st["text"]]
    st["insight"] = [_norm(t) for t in st["insight"]]
    return st


def _between(st, a, b, colour=None):
    return [e for e in st["edges"] if (e["from"], e["to"]) == (a, b) and (colour is None or e["stroke"] == colour)]


def test_concepts_slide_follows_the_title_slide_with_approved_title():
    slides = parse_slides()
    assert [s["attrs"]["id"] for s in slides[:2]] == ["s-1", SID]
    s = slides[1]
    assert s["attrs"].get("data-chapter") == "Concepts"
    assert _norm(s["title"]) == TITLE
    kicker = re.search(r'<p class="kicker">(.*?)</p>', _section_src()).group(1)
    assert re.fullmatch(r"0\d · Concepts", kicker), kicker


def test_slide_has_five_states(page):
    assert open_deck(page) == []
    assert dict(page.evaluate("() => window.deck.plan()"))[SID] == 4


def test_step_zero_shows_model_into_a_stack_of_tests_and_a_lone_scorer(page):
    open_deck(page)
    st = _state(page, 0)
    assert st["tiles"].count(MODEL) == 1, "a single model is trained"
    assert st["tiles"].count(TESTS) >= 3, "overlapping test boxes read as many rollouts"
    assert st["tiles"].count(SCORER) == 1
    assert _between(st, MODEL, TESTS), "the model goes into the tests"
    assert not [e for e in st["edges"] if SCORER in (e["from"], e["to"])], "the scorer waits for step 1"
    assert st["text"] == [STATEMENTS[0]], "statement 1 only"


def test_step_one_scores_three_attempts_and_one_verified_success(page):
    open_deck(page)
    st = _state(page, 1)
    scored = _between(st, TESTS, SCORER)
    assert len(scored) == 3
    green = [e for e in scored if e["stroke"] == st["accent"]]
    grey = [e for e in scored if e["stroke"] == st["ink3"]]
    assert len(green) == 1 and len(grey) == 2
    assert green[0]["width"] >= 1.8 * max(e["width"] for e in grey), "the success is bold"
    assert len({tuple(round(v) for v in e["end"]) for e in scored}) == 3, "three distinct arrows"
    assert len(st["ticks"]) == 1, "one round tick"
    tx, ty = st["ticks"][0]
    ex, ey = green[0]["end"]
    assert abs(ty - ey) < 30 and 0 <= ex - tx < 110, "the tick sits on the green arrow at the scorer end"
    assert not _between(st, SCORER, MODEL), "no reward yet"


def test_step_two_rewards_the_model_and_annotates_it(page):
    open_deck(page)
    st = _state(page, 2)
    back = _between(st, SCORER, MODEL, st["accent"])
    assert len(back) == 1, "green reward arrow closes the loop"
    assert ANNOT_REWARD in st["text"]
    assert STATEMENTS[1] not in st["text"]
    assert not [e for e in st["edges"] if e["stroke"] == st["loss"]], "no red before step 3"


def test_step_three_adds_the_red_reward_hack_path_and_statement_two(page):
    open_deck(page)
    st = _state(page, 3)
    red_in = _between(st, TESTS, SCORER, st["loss"])
    red_back = _between(st, SCORER, MODEL, st["loss"])
    assert len(red_in) == 1 and len(red_back) == 1
    assert ANNOT_HACK in st["text"]
    assert ANNOT_REWARD not in st["text"], "step 2's annotation dissolves"
    assert st["text"][:2] == STATEMENTS
    assert len(_between(st, TESTS, SCORER)) == 3, "still three attempts: one turned red"


def test_coloured_arrows_carry_heads_in_their_own_colour(page):
    open_deck(page)
    st = _state(page, 3)
    coloured = [e for e in st["edges"] if e["stroke"] in (st["accent"], st["loss"])]
    assert len(coloured) == 4
    assert all(e["head"] == e["stroke"] for e in coloured), coloured


def test_step_four_is_the_insight_verbatim_and_only_there(page):
    open_deck(page)
    assert _state(page, 3)["insight"] == []
    assert _state(page, 4)["insight"] == [INSIGHT]


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
    body_ids = re.findall(r'<p id="([\w-]+)"', src)[:2]
    assert set(body_ids) <= {t for t, _ in notes}, "both statements carry a note"


def test_forbidden_wording_absent():
    text = re.sub(r"<[^>]+>", " ", _section_src()).lower()
    assert "suicide" not in text and "openai's agent swarm" not in text
    assert not re.search(r",\s+not\s+(the|a|an)\b", text)


@pytest.mark.parametrize("vw,vh", SIZES)
def test_annotations_and_statements_never_cover_the_drawn_diagram(page, vw, vh):
    """The annotation box sits beside the loop, never over a tile, arrow or tick; statements stay left."""
    assert open_deck(page, vw, vh) == []
    bad = []
    for k in range(4):
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
