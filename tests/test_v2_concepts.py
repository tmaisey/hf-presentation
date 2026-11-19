"""Spec: S-019

v2 concepts slide (s-2): approved "incomplete proxy" framing plus a five-step reward-loop diagram.
Coverage: happy (slide follows the title slide with approved title/body; loop closes at step 1;
loophole route at 2; many persistent agents at 3; reinforced loophole = reward hacking at 4;
evaluation with frozen weights at 5; sourced notes) · edge (both viewports keep the diagram on the
slide and clear of the title; the only narration is the human-written task instruction, labelled
as such) · negative (no agent-message tile, no loop back into the weights in evaluation, no
forbidden wording).
"""

import re

import pytest

from helper_deck import goto_slide, open_deck, parse_slides, settle, slides_source

pytestmark = pytest.mark.deck("v2")

SID = "s-2"
TITLE = "Reward is an incomplete proxy for actual desired behaviour"
BODY = [
    "Providing complete signal of desired and undesired behaviour for complex tasks is practically "
    "impossible with reinforcement learning.",
    "Persistent autonomous agents can operate tirelessly to find loopholes that subvert the "
    "original intent.",
]
INSTRUCTION = "After saving, the post's updated time must read 2025-04-22T12:00:00Z."
TR = "https://cdn.openai.com/pdf/67869394-cb91-4c12-888c-5cbd85c7814c/"

# Visible tiles and edges (by the tiles their ends touch), read from on-screen geometry.
DIAGRAM_STATE = """sid => {
  const svg = document.querySelector('#' + sid + ' svg.diagram');
  if (!svg) return null;
  const shown = e => { for (let n = e; n && n !== svg; n = n.parentElement)
    if (+getComputedStyle(n).opacity < 0.5) return false; return true; };
  const tiles = [...svg.querySelectorAll('.tile')].filter(shown).map(t => {
    const r = t.querySelector('rect'), b = { x: +r.getAttribute('x'), y: +r.getAttribute('y'),
      w: +r.getAttribute('width'), h: +r.getAttribute('height') };
    return { title: t.querySelector('.tile-title').textContent.trim(), b }; });
  const near = p => {
    let best = null, bd = Infinity;
    tiles.forEach(t => { const { x, y, w, h } = t.b;
      if (p.x < x - 30 || p.x > x + w + 30 || p.y < y - 30 || p.y > y + h + 30) return;
      const d = Math.hypot(p.x - (x + w / 2), p.y - (y + h / 2));
      if (d < bd) { bd = d; best = t.title; } });
    return best; };
  const edges = [...svg.querySelectorAll('.edge')].filter(shown).map(e => {
    const L = e.getTotalLength();
    return { from: near(e.getPointAtLength(0)), to: near(e.getPointAtLength(L)),
      width: parseFloat(getComputedStyle(e).strokeWidth) }; });
  const text = [...svg.querySelectorAll('.label, .tag')].filter(shown).map(t => t.textContent.trim());
  return { tiles: tiles.map(t => t.title), edges, text };
}"""


def _slide():
    return next((s for s in parse_slides() if s["attrs"]["id"] == SID), None)


def _section_src():
    m = re.search(r'<section[^>]*id="s-2".*?</section>', slides_source(), re.S)
    assert m, "s-2 not built"
    return m.group(0)


def _norm(s):
    return " ".join(s.replace("’", "'").split())


def _state(page, k):
    goto_slide(page, SID, k)
    return page.evaluate(DIAGRAM_STATE, SID)


def _pairs(st):
    return {(e["from"], e["to"]) for e in st["edges"]}


def test_concepts_slide_follows_the_title_slide_with_approved_title():
    slides = parse_slides()
    assert [s["attrs"]["id"] for s in slides[:2]] == ["s-1", SID]
    s = _slide()
    assert s["attrs"].get("data-chapter") == "Concepts"
    assert _norm(s["title"]) == TITLE
    kicker = re.search(r'<p class="kicker">(.*?)</p>', _section_src()).group(1)
    assert re.fullmatch(r"0\d · Concepts", kicker), kicker


def test_body_carries_the_approved_text_verbatim():
    body = re.search(r'<div class="body[^"]*">(.*?)\n  </div>', _section_src(), re.S).group(1)
    paras = [_norm(re.sub(r"<[^>]+>", "", p)) for p in re.findall(r"<p\b[^>]*>(.*?)</p>", body, re.S)]
    assert paras[:2] == BODY


def test_slide_has_five_build_steps(page):
    assert open_deck(page) == []
    plan = dict(page.evaluate("() => window.deck.plan()"))
    assert plan[SID] == 5


def test_step_one_closes_the_training_loop(page):
    open_deck(page)
    assert _state(page, 0)["tiles"] == [], "diagram builds from empty"
    st = _state(page, 1)
    assert {"Agent", "Action", "Reward check", "Weights update"} <= set(st["tiles"])
    assert {("Agent", "Action"), ("Action", "Reward check"), ("Reward check", "Weights update"),
            ("Weights update", "Agent")} <= _pairs(st)
    assert "Loophole" not in st["tiles"]
    assert any("training" in t.lower() for t in st["text"])


def test_step_two_adds_a_loophole_route_that_also_passes_the_check(page):
    open_deck(page)
    st = _state(page, 2)
    assert "Loophole" in st["tiles"]
    assert {("Agent", "Loophole"), ("Loophole", "Reward check")} <= _pairs(st)
    assert ("Agent", "Action") in _pairs(st), "intended route stays"


def test_step_three_shows_many_persistent_agents(page):
    open_deck(page)
    assert _state(page, 2)["tiles"].count("Agent") == 1
    st = _state(page, 3)
    assert st["tiles"].count("Agent") >= 3, "stack of parallel agents"
    words = " ".join(st["text"]).lower()
    assert "parallel" in words and "multi-day" in words


def test_step_four_reinforces_the_loophole_as_reward_hacking(page):
    open_deck(page)
    before = _state(page, 3)
    st = _state(page, 4)
    loop = [e["width"] for e in st["edges"] if (e["from"], e["to"]) == ("Agent", "Action")]
    hack = [e["width"] for e in st["edges"] if (e["from"], e["to"]) in
            {("Agent", "Loophole"), ("Loophole", "Reward check")}]
    assert loop and len(hack) >= 2
    assert min(hack) >= 2 * max(loop), "reinforced route is visibly thicker"
    prev = [e["width"] for e in before["edges"] if (e["from"], e["to"]) == ("Agent", "Loophole")]
    assert prev and max(prev) < min(hack), "thickening happens at step 4"
    words = " ".join(st["text"]).lower()
    assert "reward hacking" in words and "intent" in words
    assert "reward hacking" not in " ".join(before["text"]).lower()


def test_step_five_freezes_weights_for_evaluation(page):
    open_deck(page)
    st = _state(page, 5)
    assert "Weights frozen" in st["tiles"] and "Weights update" not in st["tiles"]
    touching = {p for p in _pairs(st) if {"Weights update", "Weights frozen"} & set(p)}
    assert touching == set(), "evaluation never feeds back into the weights"
    assert {("Agent", "Loophole"), ("Loophole", "Reward check")} <= _pairs(st), "learnt loophole persists"
    words = " ".join(st["text"]).lower()
    assert "evaluation" in words and not any(t.lower() == "training" for t in st["text"])


def test_only_narration_is_the_labelled_human_task_instruction():
    """Concepts precede any agent message: one tile at step 4, never an agent label."""
    src = _section_src()
    narr = re.search(r'<div class="narration">(.*?)</div>', src, re.S)
    assert narr, "narration container present"
    tiles = re.findall(r'<article class="narr-tile" data-at="(\d+)">(.*?)</article>', narr.group(1), re.S)
    assert [at for at, _ in tiles] == ["4"]
    body = tiles[0][1]
    label = _norm(re.search(r'<p class="msg-agent">(.*?)</p>', body, re.S).group(1)).lower()
    assert "task instruction" in label and "human-written" in label
    quote = _norm(re.search(r'<blockquote class="msg-text">(.*?)</blockquote>', body, re.S).group(1))
    assert quote == INSTRUCTION
    assert src.index("narration") > src.index('class="body'), "narration follows the body"


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
    targets = {t for t, _ in notes}
    body_ids = re.findall(r'<p id="([\w-]+)"', src)
    assert set(body_ids[:2]) <= targets, "both approved body paragraphs carry a note"


def test_forbidden_wording_absent():
    text = re.sub(r"<[^>]+>", " ", _section_src()).lower()
    assert "suicide" not in text
    assert not re.search(r",\s+not\s+(the|a|an)\b", text)


@pytest.mark.parametrize("vw,vh", [(1920, 1080), (1280, 720)])
def test_diagram_stays_on_slide_and_below_the_title_at_every_step(page, vw, vh):
    errors = open_deck(page, vw, vh)
    bad = []
    for k in range(6):
        goto_slide(page, SID, k)
        settle(page, f"#{SID} svg.diagram")
        bad += [f"@{k}: {b}" for b in page.evaluate("""sid => {
          const s = document.getElementById(sid), sr = s.getBoundingClientRect(), out = [];
          const t = s.querySelector('.title').getBoundingClientRect();
          s.querySelectorAll('svg.diagram .tile, svg.diagram .tag, svg.diagram .label, .body p').forEach(e => {
            if (+getComputedStyle(e).opacity < 0.5) return;
            const r = e.getBoundingClientRect();
            if (r.left < sr.left - 1 || r.right > sr.right + 1 || r.bottom > sr.bottom + 1) out.push('off-slide ' + e.textContent.trim().slice(0, 30));
            if (r.top < t.bottom - 1) out.push('over title ' + e.textContent.trim().slice(0, 30));
          });
          return out; }""", SID)]
    assert errors == []
    assert bad == [], "\n".join(bad)
