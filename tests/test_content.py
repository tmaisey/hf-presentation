"""Spec: S-010, S-011, S-012, S-013, S-014, S-015

Slide copy follows STORYBOARD.md and VOICE.md; every storyboard slide is built.
Coverage: happy (all 18 slide ids present, titles finding-first incl. discussion, prompts styled
as questions) · edge (≤1 italic, one sentence) · negative (no trailing full stop, no placeholders,
no aphoristic "X, not Y", no agent quote styled as a report quote).
"""

import re

import pytest

from helper_deck import parse_slides, slides_source

STORYBOARD_IDS = ["s-0-1", "s-1-1", "s-1-2", "s-2-1", "s-2-2", "s-2-3", "s-3-1", "s-3-2", "s-3-3",
                  "s-4-1", "s-4-2", "s-4-3", "s-5-1", "s-5-2", "s-5-3", "s-5-4", "s-5-5", "s-6-1"]


def _slide(sid):
    return next((s for s in parse_slides() if s["attrs"]["id"] == sid), None)


@pytest.mark.parametrize("sid", STORYBOARD_IDS)
def test_storyboard_slide_is_built(sid):
    s = _slide(sid)
    assert s is not None, f"{sid} missing"
    assert "data-todo" not in s["attrs"], f"{sid} still a placeholder"


@pytest.mark.parametrize("sid", STORYBOARD_IDS)
def test_title_follows_voice_rules(sid):
    s = _slide(sid)
    if s is None or "data-todo" in s["attrs"]:
        pytest.fail(f"{sid} not built")
    t = " ".join(s["title"].split())
    assert t and not t.endswith("."), f"{sid}: no trailing full stop"
    assert s["title_em"] <= 1, f"{sid}: italic sparingly"
    assert len(re.findall(r"[.!?](\s|$)", t)) == 0, f"{sid}: one sentence"
    assert not t.endswith("?"), f"{sid}: titles are claims, not questions"


def test_no_aphoristic_antitheses_in_copy():
    text = re.sub(r"<blockquote.*?</blockquote>", "", slides_source(), flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    assert not re.search(r",\s+not\s+(the|a|an)\b", text, re.I), "avoid 'X, not Y' constructions"


def test_discussion_slide_has_three_prompts():
    s = _slide("s-6-1")
    assert s is not None
    assert sum(1 for t, a in s["tags"] if t == "li" and "prompt" in (a.get("class") or "")) == 3


def test_agent_quotes_always_use_the_message_card():
    """Agent voice looks the same everywhere; report voice stays a plain blockquote."""
    src = slides_source()
    assert not re.search(r'<p class="cite">\s*Agent\b', src), "agent quote styled as a report quote"
    outside = re.sub(r'<(article|div) class="(overlay overlay--msg|msg-card)[^"]*"[^>]*>.*?</\1>', "", src, flags=re.S)
    assert 'class="msg-text"' not in outside and 'class="msg-agent"' not in outside


def test_discussion_prompts_render_as_numbered_serif_questions(page):
    from helper_deck import goto_slide, open_deck

    open_deck(page)
    goto_slide(page, "s-6-1", 3)
    res = page.evaluate("""() => { const p = [...document.querySelectorAll('#s-6-1 .prompt')];
      const body = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--fs-text')) || 0;
      return p.map(e => [getComputedStyle(e).fontFamily, parseFloat(getComputedStyle(e).fontSize),
        getComputedStyle(e, '::before').content, parseFloat(getComputedStyle(document.querySelector('#s-1-1 .body p')).fontSize)]); }""")
    assert len(res) == 3
    for fam, size, marker, text in res:
        assert fam.startswith('"Newsreader"') or fam.startswith("Newsreader"), fam
        assert size > text, "prompts read larger than body text"
        assert marker not in ("none", "normal", '""'), "prompts are numbered"
