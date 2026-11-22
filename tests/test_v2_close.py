"""Spec: S-035

v2 close: a "Close" nav chapter after Takeaways with two ambient (title-slide firefly) slides. s-11
"Questions for discussion" shows the three approved discussion questions at once (a single state, no
steps), beside one text tile (s-8/s-9/s-10 tile style) on inter-agent vs human alignment: the approved
lead line, a Noam Brown quote verbatim from the research note, a cite linking the Dwarkesh episode, and
a reader note with the METR/TR facts. s-12 is a single "Thank you" centred on the page, with no kicker
and no notes. s-10 ends at its controls phase.
Coverage: happy (close slides end the deck in order in one Close chapter; kicker, title and the three
questions verbatim from VOICE; everything shown at step 0; tile right of the questions in the shared tile
type; fireflies on both; Close is one agenda entry after Takeaways that opens s-11) · edge (s-11 and
Thank you laid out at 1920×1080, 1280×720 and 1288×598) · negative (s-10 keeps no discussion prompts,
title or steps; s-11 has no steps or answers and no copy beyond questions and tile; s-12 has no
kicker, body, steps or notes).
"""

import re

import pytest

from helper_deck import ROOT, goto_slide, open_deck, parse_slides, settle_animations, slides_source

pytestmark = pytest.mark.deck("v2")

SIZES = [(1920, 1080), (1280, 720), (1288, 598)]
QUESTIONS = [   # VOICE "Discussion prompts" ✓ (s-11, 22 Nov), verbatim
    "Where do you see these alignment risks materialising in enterprise environments?",
    "What mitigations could be applied on projects to help enterprises manage risks while benefitting from AI?",
    "What approaches could improve efforts to manage AI safety under pressures to accelerate capability?",
]
LEAD = ("In this incident, training aligned the agents with each other more successfully than with human "
        "intent, and a collective with no dissenting voice can amplify misalignment.")   # STORYBOARD s-11 ✓
BROWN = ("we did manage to train these agents to be extremely aligned with each other, and that's a good thing. "
         "But I think there is a case that it's a bad thing")
DWARKESH = "https://www.dwarkesh.com/p/noam-brown"
RESEARCH = ROOT / "docs" / "research" / "research_notes" / "OpenAI Hugging Face swarm incident" / "agent_collective_alignment.md"
OLD_DISCUSSION_TITLE = "Detection, training and independent oversight remain open questions after this incident"


def helper_section(sid: str) -> str:
    m = re.search(rf'<section[^>]*id="{sid}".*?</section>', slides_source(), re.S)
    assert m, f"{sid} missing"
    return m.group(0)


def helper_flat(html: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", html).replace("&nbsp;", " ").split())


def helper_plain(text: str) -> str:
    """Whitespace- and apostrophe-normalised text, for verbatim comparisons across files."""
    return " ".join(text.replace("\u2019", "'").replace("\u2018", "'").split())


def helper_tile(sec: str) -> str:
    tiles = re.findall(r'<article class="text-tile"[^>]*>.*?</article>', sec, re.S)
    assert len(tiles) == 1, "s-11 carries exactly one text tile"
    return tiles[0]


# ---------- static: order, chapter, copy ----------

def test_close_slides_end_the_deck_in_one_ambient_close_chapter():
    slides = parse_slides()
    assert [s["attrs"]["id"] for s in slides[-3:]] == ["s-10", "s-11", "s-12"]
    for s in slides[-2:]:
        assert s["attrs"]["data-chapter"] == "Close", s["attrs"]["id"]
        assert "data-ambient" in s["attrs"], f"{s['attrs']['id']} uses the title slide's fireflies"
        assert "data-world" not in s["attrs"]


def test_s11_has_the_close_kicker_title_and_the_approved_questions_verbatim():
    sec = helper_section("s-11")
    assert re.search(r'<p class="kicker">(.*?)</p>', sec).group(1) == "11 · Close"
    assert [helper_flat(t) for t in re.findall(r'<h2 class="title"[^>]*>(.*?)</h2>', sec, re.S)] == \
        ["Questions for discussion"]
    prompts = re.findall(r'<li class="prompt"[^>]*>(.*?)</li>', sec, re.S)
    assert [helper_flat(p) for p in prompts] == QUESTIONS
    voice = " ".join((ROOT / "docs" / "VOICE.md").read_text(encoding="utf-8").split())
    assert all(q in voice for q in QUESTIONS), "questions are the VOICE-approved copy"


def test_s11_carries_no_answers_or_other_body_copy():
    """not-built: answers or speaker prompts on the slide; reader notes stay in notes mode, the tile is checked below."""
    sec = re.sub(r'<aside class="note".*?</aside>|<article class="text-tile".*?</article>', "",
                 helper_section("s-11"), flags=re.S)
    body = re.sub(r'<p class="kicker">.*?</p>|<h2 class="title".*?</h2>', "", sec, flags=re.S)
    assert helper_flat(body) == " ".join(f"{q}" for q in QUESTIONS)
    assert not re.search(r"data-(show|hide)-at", helper_section("s-11")), "a single state: nothing builds"


def test_s11_tile_has_the_lead_line_then_the_brown_quote_and_one_dwarkesh_cite():
    tile = helper_tile(helper_section("s-11"))
    paras = [helper_flat(p) for p in re.findall(r'<p(?: [^>]*)?>(.*?)</p>', tile, re.S)]
    assert helper_plain(paras[0]) == LEAD, "the lead line is the tile's body text"
    quotes = re.findall(r'<blockquote[^>]*>(.*?)</blockquote>', tile, re.S)
    assert [helper_plain(helper_flat(q)) for q in quotes] == [BROWN]
    assert tile.index("<p") < tile.index("<blockquote") < tile.index('class="cite"'), "lead, quote, cite"
    cite = re.search(r'<p class="cite">(.*?)</p>', tile, re.S).group(1)
    assert helper_flat(cite).startswith("Noam Brown, OpenAI")
    assert re.findall(r'href="([^"]+)"', cite) == [DWARKESH]


def test_brown_quote_is_verbatim_from_the_research_note():
    """The tile quotes the research note's transcript extract word for word (mid-sentence extract, so it starts lower-case)."""
    raw = RESEARCH.read_text(encoding="utf-8")
    note = helper_plain(raw.replace("\n>", " "))
    assert BROWN in note
    assert DWARKESH in raw


def test_s11_tile_note_carries_the_sourced_facts_and_the_scope_caveat():
    sec = helper_section("s-11")
    tile_id = re.search(r'<article class="text-tile" id="([^"]+)"', sec).group(1)
    notes = re.findall(r'<aside class="note" data-for="#' + tile_id + r'">(.*?)</aside>', sec, re.S)
    assert len(notes) == 1
    text, links = helper_plain(helper_flat(notes[0])), re.findall(r'href="([^"]+)"', notes[0])
    assert "3–6" in text and "1,200" in text, "METR p62: 3–6 of ~1,200 considered alerting a human"
    assert "trained to advance persistence and multiagent collaboration" in text, "TR p12, verbatim"
    assert "measured" in text, "scope caveat: inter-agent vs human alignment is unmeasured in general"
    assert any("metr.org" in u for u in links) and any("OpenAI-Hugging-Face" in u for u in links) \
        and DWARKESH in links


def test_s12_is_a_single_thank_you_with_no_kicker_body_or_notes():
    sec = helper_section("s-12")
    assert [helper_flat(t) for t in re.findall(r'<h2 class="title"[^>]*>(.*?)</h2>', sec, re.S)] == ["Thank you"]
    assert 'class="kicker"' not in sec
    assert 'class="note"' not in sec and "data-show-at" not in sec
    assert helper_flat(sec) == "Thank you"


def test_s10_keeps_no_discussion_phase():
    sec = helper_section("s-10")
    assert 'class="prompt' not in sec and OLD_DISCUSSION_TITLE not in sec
    assert not re.search(r'data-show-at="[5-9]"', sec), "s-10 ends at its controls phase (step 4)"


# ---------- browser ----------

def test_step_plan_and_clean_load(page):
    errors = open_deck(page)
    plan = dict(page.evaluate("window.deck.plan()"))
    assert plan["s-10"] == 4 and plan["s-11"] == 0 and plan["s-12"] == 0
    goto_slide(page, "s-12")
    assert errors == []


S11_BOXES = """() => { const op = e => { for (; e && !e.matches('section'); e = e.parentElement)
    if (+getComputedStyle(e).opacity < .9) return false; return true; };
  const box = e => { const r = e.getBoundingClientRect(); return { l: r.left, r: r.right, t: r.top, b: r.bottom, w: r.width }; };
  const qs = [...document.querySelectorAll('#s-11 li.prompt')], tile = document.querySelector('#s-11 article.text-tile');
  const font = sel => parseFloat(getComputedStyle(document.querySelector(sel)).fontSize), cite = tile.querySelector('.cite');
  return { shown: [...qs, tile].map(op), qs: qs.map(box), tile: box(tile), width: document.getElementById('s-11').clientWidth,
    tileFont: font('#s-11 .text-tile p'), refFont: font('#s-8 .text-tile li'),
    quoteFont: font('#s-11 .text-tile blockquote'), refQuote: font('#s-8 .text-tile > blockquote'),
    citeLines: Math.round(cite.getBoundingClientRect().height / parseFloat(getComputedStyle(cite).lineHeight)) }; }"""


@pytest.mark.parametrize("vw,vh", SIZES)
def test_s11_shows_questions_beside_the_tile_from_the_outset(page, vw, vh):
    assert open_deck(page, vw, vh) == []
    page.evaluate("() => window.deck.goto('s-11', 0)")
    settle_animations(page, "#s-11")
    r = page.evaluate(S11_BOXES)
    assert all(r["shown"]), f"all three questions and the tile at step 0: {r['shown']}"
    q_left, q_right, t = min(q["l"] for q in r["qs"]), max(q["r"] for q in r["qs"]), r["tile"]
    assert t["l"] >= q_right, f"tile right of the questions: {t} vs {q_right}"
    q_top, q_bot = min(q["t"] for q in r["qs"]), max(q["b"] for q in r["qs"])
    assert t["t"] < q_bot and t["b"] > q_top, "tile sits level with the questions, not above or below them"
    assert 0.25 * r["width"] <= t["w"] <= 0.45 * r["width"], f"balanced: tile {t['w']} of {r['width']}"
    assert q_right - q_left >= 0.35 * r["width"], "questions keep the larger share"
    assert t["b"] <= vh and t["r"] <= vw, "tile on screen"
    assert r["tileFont"] == r["refFont"] and r["quoteFont"] == r["refQuote"], f"tile type as on s-8: {r}"
    assert r["citeLines"] == 1, "cite is one line"


def test_close_slides_show_the_fireflies(page):
    open_deck(page)
    n = page.evaluate("""() => ['s-1', 's-11', 's-12'].map(id => document.querySelectorAll('#' + id + ' .orb').length)""")
    assert n[1] == n[0] and n[2] == n[0] and n[0] > 0, f"same firefly template as s-1: {n}"


def test_close_is_one_agenda_entry_after_takeaways_that_opens_s11(page):
    open_deck(page)
    labels = page.evaluate("() => [...document.querySelectorAll('.agenda li')].map(li => li.innerText.trim())")
    assert labels[-2:] == ["Takeaways", "Close"] and labels.count("Close") == 1
    goto_slide(page, "s-12")
    assert page.evaluate("() => document.querySelector('.agenda li.is-current').dataset.chapter") == "Close"
    page.evaluate("() => window.deck.goto('s-1', 0)")
    settle_animations(page, ".bar")
    page.click(".agenda li:last-child button", force=True)
    page.wait_for_function("() => window.deck.state().slide === 's-11'", timeout=5000)
    assert page.evaluate("window.deck.state()")["step"] == 0


@pytest.mark.parametrize("vw,vh", SIZES)
def test_thank_you_is_centred_on_the_page(page, vw, vh):
    assert open_deck(page, vw, vh) == []
    page.evaluate("() => window.deck.goto('s-12', 0)")
    settle_animations(page, "#s-12")
    r = page.evaluate("""() => { const t = document.querySelector('#s-12 h2.title'), s = document.getElementById('s-12');
      const range = document.createRange(); range.selectNodeContents(t);
      const b = range.getBoundingClientRect(), sb = s.getBoundingClientRect(), cs = getComputedStyle(t);
      return { cx: (b.left + b.right) / 2, cy: (b.top + b.bottom) / 2 - sb.top, w: b.width,
               lines: Math.round(b.height / parseFloat(cs.lineHeight)), size: parseFloat(cs.fontSize),
               lead: parseFloat(getComputedStyle(document.querySelector('#s-1 h2.title')).fontSize) }; }""")
    assert abs(r["cx"] - vw / 2) <= 0.02 * vw, f"horizontally centred: {r}"
    assert abs(r["cy"] - vh / 2) <= 0.05 * vh, f"vertically centred: {r}"
    assert r["lines"] == 1 and r["size"] == r["lead"], "one line in the title slide's lead type"
