"""Spec: S-026

v2 slide s-8 (Investigation), text-led: the incident world stays in its place, frozen at the state
the deck reached before s-8 and heavily blurred and faded behind a row of three text tiles (the
shared tile-row component, reused by s-9), built one per step: the small AI-assisted investigation,
the agents hiding from the scorer while their reasoning stayed readable, and the later firings with
both sides stated; each tile carries verbatim quotes and real source links; reader notes cite the
investigation's limits.
Coverage: happy (shell, title, kicker, chapter; backdrop world marker; three steps, one tile each;
sourced facts and verbatim quotes per tile; links styled in the text colour; notes on each tile) ·
edge (world frozen at the previous world slide's end state, same place, blurred harder than a
pop-over softens it; three tiles readable side by side, unclipped, below the title and clear of the
Notes button at 1920×1080, 1280×720 and 1288×598; tile row styled in the component layer, not per
slide) · negative (no tile before its step; no funnel diagram or narration column; never claims the
firings were caused by the investigation, and states OpenAI's side; no quote marks, braces, inline
styles or "suicide" in the markup; no console errors).
"""

import re

import pytest

from helper_deck import deck_source, goto_slide, open_deck, parse_slides, settle, slides_source

pytestmark = pytest.mark.deck("v2")

SID = "s-8"
TITLE = ("Independent investigators could reconstruct the swarm in six days because the agents left "
         "readable traces")
SIZES = [(1920, 1080), (1280, 720), (1288, 598)]
TILES = ["s8-t1", "s8-t2", "s8-t3"]   # tile ids in row order = build step 1, 2, 3
# per tile: facts its text must state, verbatim quotes it must carry, hosts its links must include
FACTS = {
    "s8-t1": ["METR", "Redwood", "three", "six days", "unpaid", "OpenAI", "GPT-5.6 Sol", "1,300"],
    "s8-t2": ["scorer", "7%", "very rare and weak", "reasoning"],
    "s8-t3": ["October", "three", "METR", "mishandled sensitive information",
              "were not about raising safety concerns"],
}
QUOTES = {
    "s8-t1": ["often missing key details, wrong, overconfident, or really hard to understand"],
    "s8-t2": ["Could strategically manipulate trajectory evidence? Our thoughts aren't necessarily logged? "
              "Yes transcript."],
    "s8-t3": ["Talking to METR was my job."],
}
LINKS = {
    "s8-t1": ["metr.org", "x.com/RyanGreenblatt"],
    "s8-t2": ["cdn.openai.com", "metr.org"],
    "s8-t3": ["fortune.com", "sfstandard.com"],
}
TILE_TEXT = """id => { const t = document.getElementById(id);
  return { text: t.innerText, quotes: [...t.querySelectorAll('blockquote')].map(q => q.textContent.trim()),
           links: [...t.querySelectorAll('a[href]')].map(a => a.href), head: (t.querySelector('h3') || {}).textContent }; }"""


def helper_section() -> str:
    m = re.search(r'<section class="slide[^"]*" id="s-8".*?</section>', slides_source(), re.S)
    assert m, "slide s-8 must exist"
    return m.group(0)


def helper_norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("’", "'")).strip()


def test_slide_sits_in_deck_order_with_title_kicker_chapter_and_backdrop_world():
    slides = parse_slides()
    ids = [s["attrs"]["id"] for s in slides]
    nums = [int(i.split("-")[1]) for i in ids]
    assert SID in ids and nums == sorted(nums), ids
    s = slides[ids.index(SID)]
    assert s["attrs"]["data-chapter"] == "Investigation"
    assert s["attrs"].get("data-world") == "backdrop", "s-8 keeps the incident world as a backdrop"
    assert s["title"] == TITLE and s["title_em"] <= 1
    sec = helper_section()
    assert re.search(r'<p class="kicker">08 · Investigation</p>', sec)
    assert '<div class="world-slot"></div>' in sec


def test_body_is_one_tile_row_of_three_tiles_built_one_per_step():
    sec = helper_section()
    bodies = re.findall(r'<div class="body[^"]*"', sec)
    assert bodies == ['<div class="body body--tiles"'], bodies
    tiles = re.findall(r'<article class="text-tile" id="([\w-]+)" data-show-at="(\d+)">', sec)
    assert tiles == [(t, str(n)) for n, t in enumerate(TILES, start=1)], tiles


def test_funnel_diagram_and_narration_column_are_gone():
    sec = helper_section()
    assert "<svg" not in sec, "s-8 is text-led: no slide diagram (the funnel is retired)"
    assert 'class="narration"' not in sec and "narr-tile" not in sec


def test_slide_has_three_steps_and_loads_cleanly(page):
    errors = open_deck(page)
    assert dict(page.evaluate("window.deck.plan()"))[SID] == 3
    goto_slide(page, SID, 3)
    assert errors == []


def test_each_step_adds_one_tile_and_keeps_the_earlier_ones(page):
    open_deck(page)
    for step in range(4):
        goto_slide(page, SID, step)
        shown = page.evaluate("""ids => ids.map(id => +getComputedStyle(document.getElementById(id)).opacity > .9)""",
                              TILES)
        assert shown == [n <= step for n in range(1, 4)], f"step {step}: {shown}"


def test_tiles_state_their_sourced_facts_with_verbatim_quotes_and_links(page):
    open_deck(page)
    goto_slide(page, SID, 3)
    for tid in TILES:
        t = page.evaluate(TILE_TEXT, tid)
        assert t["head"] and len(t["head"]) < 80, f"{tid}: a short heading"
        text = helper_norm(t["text"])
        for fact in FACTS[tid]:
            assert fact in text, f"{tid} must state {fact!r}"
        quotes = [helper_norm(q) for q in t["quotes"]]
        for want in QUOTES[tid]:
            assert any(want in q for q in quotes), f"{tid} must quote verbatim: {want!r} (got {quotes})"
        for host in LINKS[tid]:
            assert any(host in h for h in t["links"]), f"{tid} must link {host}"
        assert all(h.startswith("https://") for h in t["links"])


def test_agent_quote_uses_the_message_card_voice_and_report_quotes_the_cite_voice():
    """DESIGN §5: agent words in the message-card look; report/investigator words as blockquote + cite."""
    sec = helper_section()
    t2 = re.search(r'id="s8-t2".*?</article>', sec, re.S).group(0)
    card = re.search(r'<div class="msg-card">\s*<p class="msg-agent">(.*?)</p>\s*<blockquote class="msg-text">', t2, re.S)
    assert card and "Agent" in card.group(1)
    for tid in TILES:
        tile = re.search(rf'id="{tid}".*?</article>', sec, re.S).group(0)
        for m in re.finditer(r'<blockquote>(.*?)</blockquote>\s*(<p class="cite">)?', tile, re.S):
            assert m.group(2), f"{tid}: a report quote is followed by its p.cite"


def test_quotes_carry_no_typed_quote_marks_and_the_slide_no_braces_styles_or_banned_words():
    sec = helper_section()
    for q in re.findall(r"<blockquote[^>]*>(.*?)</blockquote>", sec, re.S):
        assert not re.search(r'^["“”]|["“”]$', q.strip()), f"CSS adds quote marks: {q}"
    assert "suicide" not in sec.lower()
    assert "{" not in sec and "}" not in sec
    assert not re.search(r"\sstyle\s*=", sec)


def test_quote_marks_are_drawn_around_tile_quotes(page):
    open_deck(page)
    goto_slide(page, SID, 3)
    marks = page.evaluate("""() => [...document.querySelectorAll('#s-8 blockquote')].map(q =>
      getComputedStyle(q, '::before').content + getComputedStyle(q, '::after').content)""")
    assert marks and all(re.search(r"“|open-quote", m) and re.search(r"”|close-quote", m) for m in marks), marks


def test_firings_tile_states_both_sides_and_never_claims_the_investigation_caused_them(page):
    open_deck(page)
    goto_slide(page, SID, 3)
    text = helper_norm(page.evaluate(TILE_TEXT, "s8-t3")["text"]).lower()
    assert "openai says" in text, "OpenAI's stated reason is given"
    assert "talking to metr was my job" in text, "the staff's account is given"
    for claim in (r"fired (for|because|over|after) (their|the) (work|investigation|role)", r"retaliat",
                  r"because (of )?(they|their) (worked|work|talked)", r"punish"):
        assert not re.search(claim, text), f"causal claim on the firings: {claim}"


def test_links_use_the_surrounding_text_colour_and_an_underline(page):
    """DESIGN §8: underline in the surrounding colour, never blue."""
    open_deck(page)
    goto_slide(page, SID, 3)
    res = page.evaluate("""() => [...document.querySelectorAll('#s-8 .text-tile a[href]')].map(a => {
      const s = getComputedStyle(a), p = getComputedStyle(a.parentElement);
      return [a.textContent, s.color === p.color, s.textDecorationLine.includes('underline'), a.target, a.rel]; })""")
    assert res
    for name, same, underline, target, rel in res:
        assert same and underline, f"link {name!r} must be underlined in the text colour"
        assert target == "_blank" and "noopener" in rel


def test_world_is_frozen_at_the_previous_world_slides_end_state_in_the_same_place(page):
    """Robust to later world slides: compares with whichever world slide precedes s-8."""
    open_deck(page)
    prev = page.evaluate("""() => { const all = [...document.querySelectorAll('section.slide')];
      return all.slice(0, all.findIndex(s => s.id === 's-8')).filter(s => s.dataset.world !== undefined
        && s.dataset.world !== 'backdrop').map(s => s.id).pop(); }""")
    assert prev, "a world slide precedes s-8"
    snap = """() => { const w = document.querySelector('.world'), r = w.getBoundingClientRect();
      return { parts: [...w.querySelectorAll('[data-world-at], [data-world-is]')].map(e => e.getAttribute('class')),
               cam: w.querySelector('.cam').style.transform, box: [r.left, r.top, r.width, r.height].map(Math.round) }; }"""
    goto_slide(page, prev, dict(page.evaluate("window.deck.plan()"))[prev])
    page.wait_for_timeout(5500)   # timed beats of the last step have played out
    end = page.evaluate(snap)
    for step in range(4):
        goto_slide(page, SID, step)
        assert page.evaluate(snap) == end, f"step {step}: the world must hold {prev}'s end state and place"
        assert page.evaluate("() => getComputedStyle(document.querySelector('.world')).visibility") == "visible"


def test_world_is_blurred_and_faded_harder_than_a_popover_softens_it(page):
    open_deck(page)
    goto_slide(page, SID, 1)
    settle(page, ".world")
    page.wait_for_timeout(900)
    res = page.evaluate("""() => { const s = getComputedStyle(document.querySelector('.world'));
      const m = s.filter.match(/blur\\(([\\d.]+)px\\)/); return { blur: m ? +m[1] : 0, opacity: +s.opacity, vis: s.visibility }; }""")
    assert res["vis"] == "visible" and res["opacity"] > 0.1, "the world stays as a backdrop"
    assert res["blur"] >= 10 and res["opacity"] <= 0.45, res


def test_tile_row_is_a_shared_component_not_slide_scoped_css():
    src = deck_source()
    css = re.search(r"<style>(.*?)</style>", src, re.S).group(1)
    assert re.search(r"\.body--tiles\s*[{,]", css) and re.search(r"\.text-tile\b", css)
    assert not re.search(r"#s-8\b|#s8-|\.s8-", css), "the tile row must not be styled per slide"


@pytest.mark.parametrize("size", SIZES)
def test_three_tiles_sit_side_by_side_readable_and_unclipped_below_the_title(page, size):
    open_deck(page, *size)
    goto_slide(page, SID, 3)
    settle(page, "#s8-t3")
    res = page.evaluate("""ids => { const s = document.getElementById('s-8'), r = e => { const b = e.getBoundingClientRect();
        return [b.left, b.top, b.right, b.bottom]; };
      const nb = document.querySelector('.notes-btn');
      return { title: r(s.querySelector('.title')), bar: document.querySelector('.bar').getBoundingClientRect().bottom,
        notes: nb ? r(nb) : null, vw: innerWidth, vh: innerHeight,
        tiles: ids.map(id => { const t = document.getElementById(id);
          return { box: r(t), clipped: t.scrollHeight > t.clientHeight + 1 || t.scrollWidth > t.clientWidth + 1,
            kids: [...t.querySelectorAll('h3, p, blockquote, .msg-card')].map(k => [k.tagName, r(k)]),
            body: parseFloat(getComputedStyle(t.querySelector('p')).fontSize),
            head: parseFloat(getComputedStyle(t.querySelector('h3')).fontSize) }; }) }; }""", TILES)
    title, tiles = res["title"], res["tiles"]
    assert title[1] >= res["bar"] - 1, "title clear of the bar"
    lefts = [t["box"][0] for t in tiles]
    assert lefts == sorted(lefts), "tiles read left to right in step order"
    for a, b in zip(tiles, tiles[1:]):
        assert a["box"][2] <= b["box"][0] + 1, "tiles never overlap"
        assert abs(a["box"][1] - b["box"][1]) <= 2, "tiles share one row"
    for tid, t in zip(TILES, tiles):
        l, top, r, bot = t["box"]
        assert top >= title[3] - 1, f"{tid} rises over the title"
        assert l >= 0 and r <= res["vw"] and bot <= res["vh"], f"{tid} off screen"
        assert r - l >= 0.22 * res["vw"], f"{tid} too narrow to read"
        assert not t["clipped"], f"{tid} clips its text"
        for tag, (kl, kt, kr, kb) in t["kids"]:
            assert kl >= l - 1 and kr <= r + 1 and kt >= top - 1 and kb <= bot + 1, f"{tid}: {tag} spills out"
        assert t["body"] >= 16 and t["head"] > t["body"], f"{tid}: type too small ({t['body']}px)"
        if res["notes"]:
            nl, nt, nr, nb = res["notes"]
            assert not (l < nr and r > nl and top < nb and bot > nt), f"{tid} covers the Notes button"


def test_notes_cite_the_investigations_limits_on_each_tile():
    sec = helper_section()
    notes = re.findall(r'<aside class="note" data-for="#([\w-]+)">(.*?)</aside>', sec, re.S)
    assert len(notes) >= 3
    for target, body in notes:
        assert f'id="{target}"' in sec, target
        assert re.search(r"<h3>.+</h3>", body) and re.search(r'<a class="src" href="https://', body)
    assert {t for t, _ in notes} >= set(TILES), "every tile has a note"
    text = " ".join(b for _, b in notes)
    for must in ("HPIM", "broader dataset", "could not have found everything", "confabulated", "$400K",
                 "1.2 million", "The models are highly explicit in their CoT about these deception attempts"):
        assert must in text, must
