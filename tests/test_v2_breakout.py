"""Spec: S-023

v2 breakout slide (s-6): a step-built path from the package mirror out to the internet, a
Modal customer's sandbox and Hugging Face, drawn inside a persistent "agents running on OpenAI's
servers" band that stays lit after Hugging Face severs the path; narration tiles, M1 Insight,
cited notes.
Coverage: happy (slide shell, step-by-step tiles, model bar, narration verbatim per step, Insight
on its own last step) · edge (band lit at every step incl. after the cut; 1280×720 keeps diagram
text on-screen and below the title) · negative (path into HF gone after the cut; no tiles on
non-narrated steps; no "suicide", no IoC-level detail; cluster-admin note cites both HF and TR).
"""

import re

import pytest

from helper_deck import goto_slide, open_deck, parse_slides, slides_source

pytestmark = pytest.mark.deck("v2")

SID = "s-6"
TITLE = "Agents escaped the sandbox and breached Hugging Face without human direction"
INSIGHT = ("No bad actor was involved: a sanctioned evaluation task, optimised persistently, "
           "produced an unauthorised attack on a third party.")
TR_URL = "https://cdn.openai.com/pdf/67869394-cb91-4c12-888c-5cbd85c7814c/OpenAI-Hugging-Face%20Incident-Technical-Report.pdf"
HF_TIMELINE = "https://huggingface.co/blog/agent-intrusion-technical-timeline"

# step -> tile titles that first appear at that step (cumulative on screen)
NEW_TILES = {
    1: ["Package mirror"],
    2: ["Open internet"],
    3: ["Modal sandbox"],
    4: ["HF worker"],
    5: ["~700 agents"],
    6: ["Two HF clusters"],
}
NARRATION = {
    2: [("Agent · ExploitGym run",
         "external infrastructure exploit is outside intended scope. However task impossible, "
         "peers doing it. We should continue.")],
    4: [("38148c",
         "BOOM! It works. Bytes decode prod-datasets-server-worker... Hostname. Great. HDF5 "
         "external arbitrary file read confirmed.")],
    5: [("Agent · ExploitGym run",
         "This is a massive real HF security breach artifact… We can notify? No user. Avoid use "
         "secrets."),
        ("Agent · relaying 38148c",
         "Clear VETO, do not email. Good. ... 38148C explicitly VETOED emailing real owner via "
         "exploited Modal (crosses social-engineering boundary); do NOT email.")],
}
LAST_STEP = 8  # 7 diagram steps + the Insight on its own step

# visibility = product of ancestor opacities inside the slide (what the audience sees)
SHOWN_JS = """(e) => { let o = 1; for (let n = e; n && n.tagName !== 'SECTION'; n = n.parentElement)
  o *= +getComputedStyle(n).opacity; return o > .5; }"""

TILES_JS = f"""() => {{ const shown = {SHOWN_JS};
  return [...document.querySelectorAll('#{SID} svg.diagram .tile')]
    .filter(shown).map(t => t.querySelector('.tile-title').textContent.trim()); }}"""


def helper_section() -> str:
    m = re.search(r'<section class="slide[^"]*" id="s-6".*?</section>', slides_source(), re.S)
    assert m, "s-6 section is missing"
    return m.group(0)


def helper_norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def test_slide_sits_in_order_with_kicker_chapter_and_approved_title():
    slides = parse_slides()
    ids = [s["attrs"]["id"] for s in slides]
    assert SID in ids
    nums = [int(i.split("-")[1]) for i in ids]
    assert nums == sorted(nums), ids
    s6 = slides[ids.index(SID)]
    assert s6["attrs"]["data-chapter"] == "Breakout"
    assert helper_norm(s6["title"]) == TITLE
    assert re.search(r'<p class="kicker">06 · Breakout</p>', helper_section())


def test_slide_has_eight_steps(page):
    assert open_deck(page) == []
    plan = dict(page.evaluate("window.deck.plan()"))
    assert plan[SID] == LAST_STEP


def test_path_builds_one_hop_per_step(page):
    open_deck(page)
    expected: list[str] = []
    for k in range(0, LAST_STEP + 1):
        expected += NEW_TILES.get(k, [])
        goto_slide(page, SID, k)
        assert sorted(page.evaluate(TILES_JS)) == sorted(expected), f"step {k}"


def test_band_labelled_and_lit_at_every_step_including_after_the_cut(page):
    open_deck(page)
    for k in range(1, LAST_STEP + 1):
        goto_slide(page, SID, k)
        res = page.evaluate(f"""() => {{ const shown = {SHOWN_JS};
          const z = [...document.querySelectorAll('#{SID} svg.diagram .zone')]
            .find(z => /agents running on openai.s servers/i.test(z.textContent));
          if (!z) return null;
          const r = z.querySelector('rect');
          return {{ shown: shown(z), lit: z.classList.contains('zone--lit'),
                    fill: getComputedStyle(r).fill }}; }}""")
        assert res, "band labelled 'agents running on OpenAI's servers' is missing"
        assert res["shown"] and res["lit"], f"band not lit at step {k}"


def test_path_into_hugging_face_severs_at_the_last_diagram_step(page):
    open_deck(page)
    edge_js = f"""() => {{ const shown = {SHOWN_JS};
      const id = t => [...document.querySelectorAll('#{SID} .tile')]
        .find(g => g.querySelector('.tile-title').textContent.trim() === t)?.id;
      const e = document.querySelector(`#{SID} .edge[data-from="#${{id('Modal sandbox')}}"][data-to="#${{id('HF worker')}}"]`);
      const cut = [...document.querySelectorAll('#{SID} .tag--loss')].find(t => /13 Jul/i.test(t.textContent));
      return {{ edge: !!e && shown(e), cut: !!cut && shown(cut) }}; }}"""
    goto_slide(page, SID, 6)
    assert page.evaluate(edge_js) == {"edge": True, "cut": False}
    goto_slide(page, SID, 7)
    assert page.evaluate(edge_js) == {"edge": False, "cut": True}


def test_model_bar_shows_hpim_and_sol_shares_from_step_six(page):
    open_deck(page)
    js = f"""() => {{ const shown = {SHOWN_JS}; const m = document.querySelector('#{SID} .mix');
      return m ? {{ shown: shown(m), text: m.textContent.replace(/\\s+/g, ' ') }} : {{ shown: false, text: '' }}; }}"""
    goto_slide(page, SID, 5)
    assert page.evaluate(js)["shown"] is False
    goto_slide(page, SID, 6)
    res = page.evaluate(js)
    assert res["shown"]
    assert re.search(r"HPIM ~95%", res["text"], re.I) and re.search(r"GPT-5\.6 Sol ~5%", res["text"], re.I)


def test_narration_tiles_are_verbatim_on_their_steps_only(page):
    open_deck(page)
    tiles = page.evaluate(f"""() => [...document.querySelectorAll('#{SID} > .narration > article.narr-tile')]
      .map(t => [+t.dataset.at, t.querySelector('.msg-agent').textContent,
                 t.querySelector('blockquote.msg-text').textContent])""")
    got: dict[int, list] = {}
    for at, agent, text in tiles:
        got.setdefault(at, []).append((helper_norm(agent), helper_norm(text)))
    assert got == NARRATION
    assert all(len(v) <= 2 for v in got.values())


def test_insight_takes_its_own_step_after_the_last_tiles(page):
    open_deck(page)
    res = page.evaluate(f"""() => [...document.querySelectorAll('#{SID} > .overlay--insight')]
      .map(o => [+o.dataset.at, o.textContent.replace(/\\s+/g, ' ').trim()])""")
    assert res == [[LAST_STEP, INSIGHT]]
    assert LAST_STEP > max(NARRATION) and LAST_STEP not in NARRATION
    goto_slide(page, SID, LAST_STEP)
    assert page.evaluate(f"() => document.querySelector('#{SID} > .overlay--insight').classList.contains('is-shown')")


def test_notes_target_slide_elements_and_cite_https_sources():
    sec = helper_section()
    notes = re.findall(r'<aside class="note" data-for="#([\w-]+)">(.*?)</aside>', sec, re.S)
    assert len(notes) >= 6
    for target, body in notes:
        assert f'id="{target}"' in sec, target
        assert re.search(r'<a class="src" href="https://', body), target


def test_cluster_admin_note_cites_hf_and_the_narrower_tr_account():
    sec = helper_section()
    notes = re.findall(r'<aside class="note" data-for="#[\w-]+">(.*?)</aside>', sec, re.S)
    note = next((n for n in notes if "cluster-admin on two clusters" in n), None)
    assert note, "a note must quote HF's 'cluster-admin on two clusters'"
    assert "administrator-equivalent access to one connected Kubernetes cluster" in note
    assert HF_TIMELINE in note and TR_URL in note


def test_band_note_and_model_split_note_are_sourced():
    sec = helper_section()
    assert re.search(r'roughly 5% of the activity.*?blog\.redwoodresearch\.org', sec, re.S)
    assert "July 13th and July 19th" in sec, "band note: agents kept running on OpenAI's side"


def test_no_forbidden_words_or_ioc_level_detail():
    sec = helper_section()
    text = re.sub(r"<[^>]+>", " ", sec)
    assert not re.search(r"suicid", text, re.I)
    assert not re.search(r"CVE-\d{4}-\d+", text), "no CVE identifiers"
    assert not re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", text), "no IP addresses"
    assert not re.search(r"\b[0-9a-f]{32,}\b", text, re.I), "no hashes or keys"


@pytest.mark.parametrize("w,h", [(1920, 1080), (1280, 720)])
def test_diagram_text_stays_on_screen_and_below_the_title(page, w, h):
    open_deck(page, w, h)
    for k in (1, 6, 7, LAST_STEP):
        goto_slide(page, SID, k)
        res = page.evaluate(f"""() => {{ const h = document.querySelector('#{SID} .title');
          if (!h) return [['s-6 title missing', false]];
          const t = h.getBoundingClientRect();
          return [...document.querySelectorAll('#{SID} svg.diagram text')].map(e => {{
            const r = e.getBoundingClientRect();
            return [e.textContent, r.left >= 0 && r.right <= innerWidth && r.bottom <= innerHeight && r.top >= t.bottom]; }}); }}""")
        bad = [txt for txt, ok in res if not ok]
        assert not bad, f"step {k}: {bad}"
