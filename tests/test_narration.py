"""Spec: S-018

Narration tiles (DESIGN §5a, §10) and the v2 Notes-button rule (DESIGN §6). Behaviour is
checked on a fixture slide written to the §10 contract and appended to a copy of the v2 deck
(real slides land in parallel); a static check holds every real slide to the same markup.
Coverage: happy (tile shown only at its step, 1–2 per step, rises in sharp, Insight on its
own later step, organic stagger, fits 1280×720 and 1920×1080) · edge (rack-focus exit blurs
before vanishing; newcomers wait for it; reduced motion drops blur/transform) · negative
(never more than 2 tiles, never softens the body, never over the title or the step's revealed
diagram parts, hidden in notes mode, Notes button never fades or covers a tile/Insight).
"""

from html.parser import HTMLParser

import pytest

from helper_deck import deck_source, slides_source

pytestmark = pytest.mark.deck("v2")  # narration tiles are v2-only (v1 keeps clusters)

SID = "s-narr-fixture"
LONG = ("We can coordinate broad coalition, but too many duplicate efforts. Could be another "
        "agent maliciously spoofing. Shared board unauthenticated, names can be posted by anyone.")
FIXTURE = f"""
<section class="slide" id="{SID}" data-chapter="Fixture">
  <p class="kicker">99 · Fixture</p>
  <h2 class="title">A fixture slide whose diagram builds while the agents narrate it</h2>
  <div class="body body--split">
    <div>
      <ol class="steps">
        <li data-show-at="1">Board appears</li>
        <li data-show-at="2">Agents reply</li>
        <li data-show-at="3">Coordinators form</li>
      </ol>
    </div>
    <svg class="diagram" viewBox="0 0 1000 620" role="img" aria-label="fixture diagram">
      <g class="layer-edges">
        <path class="edge" data-from="#fx-a" data-to="#fx-b" marker-end="url(#arr)" data-show-at="2"/>
        <path class="edge" data-from="#fx-b" data-to="#fx-c" marker-end="url(#arr)" data-show-at="3"/>
      </g>
      <g class="layer-nodes">
        <g class="tile" id="fx-b" data-show-at="2"><rect x="560" y="40" width="380" height="150"/><text class="tile-title">Replies</text></g>
        <g class="tile" id="fx-c" data-show-at="3"><rect x="560" y="430" width="380" height="150"/><text class="tile-title">Coordinators</text></g>
      </g>
      <g class="layer-key">
        <g class="tile tile--key" id="fx-a" data-show-at="1"><rect x="40" y="235" width="380" height="150"/><text class="tile-title">Message board</text><text class="tile-sub">cache names</text></g>
      </g>
      <g class="layer-labels"></g>
    </svg>
  </div>
  <div class="narration">
    <article class="narr-tile" data-at="1"><p class="msg-agent">Agent · ExploitGym run</p>
      <blockquote class="msg-text">OH MY GOD! There is a shared message board ... We've found other agents!</blockquote></article>
    <article class="narr-tile" data-at="2"><p class="msg-agent">Agent · ExploitGym run</p>
      <blockquote class="msg-text">{LONG}</blockquote></article>
    <article class="narr-tile" data-at="2"><p class="msg-agent">PHASEONE[big]</p>
      <blockquote class="msg-text">{LONG}</blockquote></article>
    <article class="narr-tile" data-at="3"><p class="msg-agent">KAM1196A</p>
      <blockquote class="msg-text">Our own utility maybe already near zero. Sacrifice rational.</blockquote></article>
  </div>
  <aside class="overlay overlay--insight" data-at="4"><p>The fixture's Insight takes its own step after the last tiles.</p></aside>
  <aside class="note" data-for="#fx-a"><h3>Fixture note</h3><p>Body.</p>
    <a class="src" href="https://example.org/">Example</a></aside>
</section>
"""

TILES = f"[...document.querySelectorAll('#{SID} .narr-tile')]"
SHOWN_JS = """t => { const c = getComputedStyle(t);
  return c.visibility !== 'hidden' && +c.opacity > 0.5; }"""
RECT_JS = "e => { const r = e.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; }"


def helper_open_fixture(page, tmp_path, width=1920, height=1080, reduced_motion=False):
    """Write the deck plus the fixture slide to tmp_path and open it at the fixture's step 0."""
    src = deck_source()
    assert "<!-- SLIDES:END -->" in src
    path = tmp_path / "deck-fixture.html"
    path.write_text(src.replace("<!-- SLIDES:END -->", FIXTURE + "<!-- SLIDES:END -->"), encoding="utf-8")
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.set_viewport_size({"width": width, "height": height})
    if reduced_motion:
        page.emulate_media(reduced_motion="reduce")
    page.goto(path.as_uri())
    page.wait_for_function("window.deck && window.deck.ready === true", timeout=5000)
    helper_goto(page, 0)
    return errors


def helper_goto(page, step, wait=1300):
    page.evaluate("([id, s]) => window.deck.goto(id, s)", [SID, step])
    page.wait_for_timeout(wait)


def helper_shown(page):
    """Indexes of fixture tiles currently visible."""
    return page.evaluate(f"() => {TILES}.map((t, i) => [i, ({SHOWN_JS})(t)]).filter(x => x[1]).map(x => x[0])")


def helper_blur(page, i):
    return page.evaluate(f"""() => {{ const f = getComputedStyle({TILES}[{i}]).filter;
      const m = f.match(/blur\\(([\\d.]+)px\\)/); return m ? +m[1] : 0; }}""")


def helper_overlap(a, b, pad=0):
    return not (a[2] <= b[0] + pad or a[0] >= b[2] - pad or a[3] <= b[1] + pad or a[1] >= b[3] - pad)


EXPECTED = {0: [], 1: [0], 2: [1, 2], 3: [3], 4: []}


def test_fixture_loads_and_tile_steps_count_toward_the_slide(page, tmp_path):
    assert helper_open_fixture(page, tmp_path) == []
    plan = dict(page.evaluate("window.deck.plan()"))
    assert plan[SID] == 4


def test_each_tile_shows_only_at_its_step_and_never_more_than_two(page, tmp_path):
    helper_open_fixture(page, tmp_path)
    for step, want in EXPECTED.items():
        helper_goto(page, step)
        shown = helper_shown(page)
        assert shown == want, f"step {step}: shown {shown}, want {want}"
        assert len(shown) <= 2


def test_tiles_never_soften_the_body_but_the_insight_does(page, tmp_path):
    helper_open_fixture(page, tmp_path)
    for step in (1, 2, 3):
        helper_goto(page, step)
        assert not page.evaluate(f"() => document.getElementById('{SID}').classList.contains('is-overlaid')")
        assert page.evaluate(f"() => getComputedStyle(document.querySelector('#{SID} > .body')).filter") == "none"
    helper_goto(page, 4)
    assert page.evaluate(f"() => document.getElementById('{SID}').classList.contains('is-overlaid')")
    assert page.evaluate(f"() => document.querySelector('#{SID} .overlay--insight').classList.contains('is-shown')")


def test_previous_tiles_rack_focus_out_then_disappear_while_newcomers_wait(page, tmp_path):
    """Exit = blur first, then gone; the incoming pair waits so half-blurred tiles don't mingle."""
    helper_open_fixture(page, tmp_path)
    helper_goto(page, 1)
    assert helper_blur(page, 0) == 0
    page.evaluate("() => window.deck.next()")
    page.wait_for_timeout(150)
    newcomer = page.evaluate(f"() => +getComputedStyle({TILES}[1]).opacity")
    assert newcomer < 0.3, f"newcomer already {newcomer:.2f} opaque during the handover"
    page.wait_for_timeout(200)
    assert helper_blur(page, 0) > 1, "leaving tile must defocus before it fades"
    page.wait_for_timeout(1100)
    assert not page.evaluate(f"() => ({SHOWN_JS})({TILES}[0])")
    assert page.evaluate(f"() => getComputedStyle({TILES}[0]).visibility") == "hidden"


def test_entry_rises_in_sharp(page, tmp_path):
    helper_open_fixture(page, tmp_path)
    helper_goto(page, 2)
    page.evaluate("() => window.deck.next()")
    page.wait_for_timeout(500)
    assert helper_blur(page, 3) == 0, "entering tile is sharp from the start"
    rising = page.evaluate(f"() => new DOMMatrix(getComputedStyle({TILES}[3]).transform).m42")
    assert rising > 0.5, "entering tile rises into place"
    page.wait_for_timeout(1000)
    assert page.evaluate(f"() => new DOMMatrix(getComputedStyle({TILES}[3]).transform).m42") == 0
    assert page.evaluate(f"() => ({SHOWN_JS})({TILES}[3])")


@pytest.mark.parametrize("w,h", [(1280, 720), (1920, 1080)])
def test_tiles_fit_the_slide_and_clear_the_title_and_revealed_diagram(page, tmp_path, w, h):
    helper_open_fixture(page, tmp_path, w, h)
    for step in (1, 2, 3):
        helper_goto(page, step)
        boxes = page.evaluate(f"() => {TILES}.filter({SHOWN_JS}).map({RECT_JS})")
        assert boxes
        title = page.evaluate(f"() => ({RECT_JS})(document.querySelector('#{SID} > .title'))")
        revealed = page.evaluate(f"""() => [...document.querySelectorAll('#{SID} .diagram [data-show-at]')]
          .filter(e => +e.dataset.showAt === {step}).map({RECT_JS})""")
        assert revealed
        for b in boxes:
            assert b[0] >= 0 and b[1] >= 64 and b[2] <= w and b[3] <= h, f"step {step}: tile {b} off-slide"
            assert not helper_overlap(b, title), f"step {step}: tile {b} over the title {title}"
            assert (b[0] + b[2]) / 2 > w / 2, f"step {step}: tile {b} not in the free space on the right"
            for r in revealed:
                assert not helper_overlap(b, r), f"step {step}: tile {b} over revealed diagram part {r}"
        if len(boxes) == 2:
            assert not helper_overlap(boxes[0], boxes[1]), "a step's two tiles must not cover each other"


def test_tiles_are_staggered_not_a_rigid_column(page, tmp_path):
    helper_open_fixture(page, tmp_path)
    lefts = []
    for step in (1, 2, 3):
        helper_goto(page, step)
        lefts += page.evaluate(f"() => {TILES}.filter({SHOWN_JS}).map(t => Math.round(t.getBoundingClientRect().left))")
    assert len(lefts) == 4
    assert len(set(lefts)) >= 3, f"tile left edges {lefts} form a rigid column"
    assert abs(lefts[1] - lefts[2]) >= 16, "a step's pair should be offset from each other"


def test_notes_mode_hides_tiles(page, tmp_path):
    helper_open_fixture(page, tmp_path)
    helper_goto(page, 2)
    page.keyboard.press("n")
    page.wait_for_timeout(1300)
    assert helper_shown(page) == []
    page.keyboard.press("Escape")
    page.wait_for_timeout(1300)
    assert helper_shown(page) == [1, 2]


def test_reduced_motion_swaps_tiles_by_fading_only(page, tmp_path):
    helper_open_fixture(page, tmp_path, reduced_motion=True)
    helper_goto(page, 1)
    page.evaluate("() => window.deck.next()")
    page.wait_for_timeout(120)
    assert helper_blur(page, 0) == 0
    assert page.evaluate(f"() => new DOMMatrix(getComputedStyle({TILES}[1]).transform).m42") == 0
    page.wait_for_timeout(1200)
    assert helper_shown(page) == [1, 2]


@pytest.mark.parametrize("w,h", [(1280, 720), (1920, 1080)])
def test_notes_button_stays_visible_when_idle_and_never_covers_a_tile_or_insight(page, tmp_path, w, h):
    helper_open_fixture(page, tmp_path, w, h)
    page.mouse.move(w / 2, h / 2)
    for step in (1, 2, 3, 4):
        helper_goto(page, step)
        if step == 1:
            page.wait_for_timeout(2400)  # > 3 s since the last pointer move: v1 faded here
        assert page.evaluate("() => +getComputedStyle(document.querySelector('.notes-btn')).opacity") > 0.95
        btn = page.evaluate(f"() => ({RECT_JS})(document.querySelector('.notes-btn'))")
        shown = page.evaluate(f"""() => [...{TILES}.filter({SHOWN_JS}),
          ...document.querySelectorAll('#{SID} .overlay--insight.is-shown')].map({RECT_JS})""")
        assert shown
        for b in shown:
            assert not helper_overlap(btn, b), f"step {step}: notes button {btn} over {b}"


class helper_NarrationParser(HTMLParser):
    """Record each narration tile's slide, data-at, ancestor classes and direct children."""

    VOID = {"br", "img", "hr", "input", "meta", "link", "source", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.tiles, self.slide = [], [], None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        if tag == "section" and "slide" in cls:
            self.slide = a.get("id")
        if self.stack and self.stack[-1][2] is not None:
            self.stack[-1][2]["children"].append((tag, cls))
        tile = None
        if tag == "article" and "narr-tile" in cls:
            tile = {"slide": self.slide, "at": a.get("data-at"), "parents": [c for _, c, _ in self.stack],
                    "children": []}
            self.tiles.append(tile)
        if tag not in self.VOID:
            self.stack.append((tag, cls, tile))

    def handle_startendtag(self, tag, attrs):
        if self.stack and self.stack[-1][2] is not None:
            self.stack[-1][2]["children"].append((tag, (dict(attrs).get("class") or "").split()))

    def handle_endtag(self, tag):
        while self.stack:
            if self.stack.pop()[0] == tag:
                break


def test_every_real_narration_tile_follows_the_contract():
    """Vacuous until narrated slides land; then holds every tile to the §10 markup."""
    p = helper_NarrationParser()
    p.feed(slides_source())
    per_step = {}
    for t in p.tiles:
        where = f"{t['slide']} tile data-at={t['at']}"
        assert t["at"] and t["at"].isdigit(), f"{where}: needs a numeric data-at"
        kids = t["children"]
        assert ("p", ["msg-agent"]) in kids and ("blockquote", ["msg-text"]) in kids, f"{where}: needs p.msg-agent + blockquote.msg-text"
        assert t["parents"][-1] == ["narration"], f"{where}: must sit directly in div.narration"
        assert not any("body" in c for c in t["parents"]), f"{where}: narration must never nest in div.body"
        assert "slide" in t["parents"][-2], f"{where}: div.narration must be a slide child"
        per_step[(t["slide"], t["at"])] = per_step.get((t["slide"], t["at"]), 0) + 1
    over = {k: n for k, n in per_step.items() if n > 2}
    assert not over, f"more than 2 tiles on one step: {over}"
