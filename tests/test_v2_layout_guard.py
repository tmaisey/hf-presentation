"""Spec: S-030

Always-on layout guard for the deck under build: every slide, stepped from 0 to its last step in one
page, at 1920×1080, 1280×720 and short-wide 1288×598 (one test per slide × size, so ``-n auto``
spreads them; a pending slide is one test over all sizes). The checker (``helper_layout.CHECK``) is generic, so new slides are covered on arrival.
Coverage: happy (every accepted slide is clean at every step and size) · edge (short-wide screen;
timed beats settle before checking) · negative (the checker reports a planted overlap, a title pushed
under the bar, off-slide text and clipped text; pending slides that become clean fail loudly).

Slides still being built are listed in ``PENDING_SLIDES``: their known faults are strict xfails.
A builder **removes their slide from PENDING_SLIDES** when it is done; a listed slide that has
become clean then fails (XPASS strict), so the set never outlives its faults, and any slide not
listed is guarded at every size from the start.
"""

import pytest

from helper_deck import open_deck, parse_slides, settle_animations
from helper_layout import CHECK, helper_layout_faults, helper_settle

pytestmark = pytest.mark.deck("v2")

VIEWPORTS = [(1920, 1080), (1280, 720), (1288, 598)]
SLIDES = [s["attrs"]["id"] for s in parse_slides()]

# Slides under build with known layout faults, checked as one strict xfail per slide across all sizes
# (a slide is clean only when clean at every size). A builder removes their slide when its build is
# done; while listed, a slide that turns clean at every size fails as XPASS(strict).
# Faults at S-030 red (Nov 2026): s-5, s-6 step list/caption off-slide and over the title at 1288x598;
# s-7 step list over the title at every size; s-10 controls table over the title at step 3, 1288x598.
PENDING_SLIDES: set[str] = set()


def helper_cases():
    """One case per slide x viewport; a pending slide is one strict-xfail case over all viewports."""
    for sid in SLIDES:
        if sid in PENDING_SLIDES:
            yield pytest.param(sid, VIEWPORTS, id=f"{sid}-pending", marks=pytest.mark.xfail(
                strict=True, reason=f"{sid} is in PENDING_SLIDES (under build)"))
        else:
            for vw, vh in VIEWPORTS:
                yield pytest.param(sid, [(vw, vh)], id=f"{sid}-{vw}x{vh}")


@pytest.mark.parametrize("sid,sizes", list(helper_cases()))
def test_slide_has_no_layout_faults_at_any_step(page, sid, sizes):
    faults, errors = [], []
    for vw, vh in sizes:
        errors += open_deck(page, vw, vh)
        faults += [f"{vw}x{vh} {f}" for f in helper_layout_faults(page, sid)]
    assert faults == [], "\n".join(faults)
    assert errors == []


def test_pending_slides_are_real_slides():
    """A stale or misspelt id in PENDING_SLIDES would silently guard nothing."""
    assert PENDING_SLIDES <= set(SLIDES)


# ---------- the checker itself catches planted faults ----------

PLANT = {
    "covers title": """id => { const t = document.querySelector('#' + id + ' .title').getBoundingClientRect();
        const d = document.createElement('p'); d.textContent = 'planted';
        d.style.cssText = `position:fixed;z-index:9;margin:0;left:${t.left + 20}px;top:${t.top + 4}px;width:200px;height:40px;background:red`;
        document.getElementById(id).appendChild(d); }""",
    "title under bar": """id => { const t = document.querySelector('#' + id + ' .title');
        t.style.transition = 'none'; t.style.translate = '0 -' + (t.getBoundingClientRect().top - 10) + 'px'; }""",
    "off-slide": """id => { const d = document.createElement('p'); d.textContent = 'planted off-slide';
        d.style.cssText = 'position:absolute;z-index:9;left:-400px;top:50%;width:300px;margin:0';
        document.getElementById(id).appendChild(d); }""",
    "clipped": """id => { const d = document.createElement('p');
        d.textContent = 'planted text much too long for its narrow box';
        d.style.cssText = 'position:absolute;z-index:9;right:40px;bottom:40px;width:60px;white-space:nowrap;overflow:hidden;margin:0';
        document.getElementById(id).appendChild(d); }""",
}


@pytest.mark.parametrize("fault", list(PLANT))
def test_checker_reports_a_planted_fault_on_a_clean_slide(page, fault):
    """s-3 (accepted) starts clean; each planted fault must then be reported by its kind."""
    open_deck(page, 1280, 720)
    page.evaluate("() => window.deck.goto('s-3', 0)")
    helper_settle(page)
    assert page.evaluate(CHECK, "s-3") == []
    page.evaluate(PLANT[fault], "s-3")
    settle_animations(page, "#s-3")
    found = page.evaluate(CHECK, "s-3")
    assert any(f.startswith(fault) for f in found), found
