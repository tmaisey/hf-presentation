"""Spec: S-002, S-003

Presenter navigation and in-slide step builds, observed in a real browser.
Coverage: happy (advance/back through slides and steps, agenda tracks chapter) · edge
(first/last slide clamps, wheel = one step) · negative (slide never left before its last step).
"""

from helper_deck import goto_slide, open_deck, settle_animations, state

FIRST_STEPPED = """() => {
  const s = [...document.querySelectorAll('section.slide')].find(
    x => x.querySelector('[data-show-at],[data-at]'));
  return s && s.id;
}"""


def test_loads_without_errors_and_starts_on_first_slide(page):
    errors = open_deck(page)
    st = state(page)
    assert st["index"] == 0 and st["step"] == 0
    assert errors == []


def test_arrow_keys_advance_and_go_back_one_slide(page):
    open_deck(page)
    page.keyboard.press("ArrowRight")
    settle_animations(page)
    assert state(page)["index"] == 1
    page.keyboard.press("ArrowLeft")
    settle_animations(page)
    assert state(page)["index"] == 0


def test_back_on_first_slide_stays_put(page):
    open_deck(page)
    page.keyboard.press("ArrowLeft")
    settle_animations(page)
    assert state(page)["index"] == 0


def test_stepped_slide_is_not_left_until_last_step(page):
    open_deck(page)
    sid = page.evaluate(FIRST_STEPPED)
    assert sid, "deck must contain at least one stepped slide"
    goto_slide(page, sid, 0)
    total = state(page)["steps"]
    assert total >= 2
    for k in range(1, total + 1):
        page.keyboard.press("ArrowRight")
        settle_animations(page, f"#{sid}")
        st = state(page)
        assert st["slide"] == sid and st["step"] == k
    page.keyboard.press("ArrowRight")
    settle_animations(page)
    assert state(page)["slide"] != sid


def test_show_at_elements_appear_from_their_step(page):
    open_deck(page)
    sid = page.evaluate(FIRST_STEPPED)
    goto_slide(page, sid, 0)
    hidden = page.evaluate(
        "id => [...document.querySelectorAll('#'+id+' [data-show-at]')]"
        ".filter(e => +e.dataset.showAt > 0).every(e => !e.classList.contains('is-visible'))", sid)
    assert hidden
    goto_slide(page, sid, 1)
    assert page.evaluate(
        "id => [...document.querySelectorAll('#'+id+' [data-show-at=\"1\"]')]"
        ".every(e => e.classList.contains('is-visible'))", sid)


def test_step_list_marks_current_and_done(page):
    open_deck(page)
    sid = page.evaluate("() => document.querySelector('section.slide .steps').closest('section').id")
    goto_slide(page, sid, 2)
    items = page.evaluate("id => [...document.querySelectorAll('#'+id+' .steps > li')].map(l => [+l.dataset.showAt, l.className])", sid)
    current = max(i for i, (at, _) in enumerate(items) if at <= 2)   # last item reached by step 2
    assert "is-current" in items[current][1]
    assert all("is-done" in c for _, c in items[:current]) and current >= 1


def test_wheel_gesture_moves_one_step_only(page):
    open_deck(page)
    page.mouse.move(400, 400)
    for _ in range(5):
        page.mouse.wheel(0, 120)
    # the gesture lands (condition), then everything it set off settles before counting the steps it made
    page.wait_for_function("() => window.deck.state().index >= 1", timeout=10000)
    settle_animations(page)
    assert state(page)["index"] == 1


def test_agenda_marks_current_chapter_and_progress(page):
    open_deck(page)
    sid = page.evaluate("() => [...document.querySelectorAll('section.slide')].at(-1).id")
    goto_slide(page, sid, 0)
    chapter = page.evaluate("id => document.getElementById(id).dataset.chapter", sid)
    current = page.evaluate("() => document.querySelector('.agenda .is-current').dataset.chapter")
    assert current == chapter
    width = page.evaluate("() => parseFloat(getComputedStyle(document.querySelector('.progress')).width)")
    assert width > 0
