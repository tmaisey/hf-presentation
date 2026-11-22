"""Spec: S-035

v2 close: a "Close" nav chapter after Takeaways with two ambient (title-slide firefly) slides. s-11
"Questions for discussion" builds the three approved discussion questions one per step; s-12 is a
single "Thank you" centred on the page, with no kicker and no notes. s-10 ends at its controls phase.
Coverage: happy (close slides end the deck in order in one Close chapter; kicker, title and the three
questions verbatim from VOICE; one more question per step; fireflies on both; Close is one agenda entry
after Takeaways that opens s-11) · edge (Thank you centred at 1920×1080, 1280×720 and 1288×598; the
agenda still fits at 1288×598) · negative (s-10 keeps no discussion prompts, title or steps; s-12 has no
kicker, body, steps or notes; no answers on s-11).
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
OLD_DISCUSSION_TITLE = "Detection, training and independent oversight remain open questions after this incident"


def helper_section(sid: str) -> str:
    m = re.search(rf'<section[^>]*id="{sid}".*?</section>', slides_source(), re.S)
    assert m, f"{sid} missing"
    return m.group(0)


def helper_flat(html: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", html).replace("&nbsp;", " ").split())


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
    """not-built: answers or speaker prompts on the slide; reader notes, if any, stay in notes mode."""
    sec = re.sub(r'<aside class="note".*?</aside>', "", helper_section("s-11"), flags=re.S)
    body = re.sub(r'<p class="kicker">.*?</p>|<h2 class="title".*?</h2>', "", sec, flags=re.S)
    assert helper_flat(body) == " ".join(f"{q}" for q in QUESTIONS)


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
    assert plan["s-10"] == 4 and plan["s-11"] == 3 and plan["s-12"] == 0
    goto_slide(page, "s-12")
    assert errors == []


def test_s11_adds_one_question_per_step(page):
    open_deck(page)
    for step in range(4):
        page.evaluate("k => window.deck.goto('s-11', k)", step)
        settle_animations(page, "#s-11")
        shown = page.evaluate("""() => [...document.querySelectorAll('#s-11 li.prompt')]
          .map(e => +getComputedStyle(e).opacity > .9 && +getComputedStyle(e.parentElement).opacity > .9)""")
        assert shown == [n < step for n in range(3)], f"step {step}: {shown}"


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
