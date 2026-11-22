"""Spec: S-033

Timeline day tags: every dated entry on a world-slide timeline shows its day count from 8 May 2026
(day 0), derived from the date already in the entry, so the room keeps the incident's duration.
Coverage: happy (each dated entry's tag equals the day count of its own date; known anchors 8 May,
12 May, 26 Jun, 26 Aug) · edge (a range "5–6 Jul" counts from its first day; tag stays on the date's
line at every review size) · negative (undated entries and sub-points get no tag; no tag is typed in
the slide source; the tag is quieter than the date).
"""

import re
from datetime import date

import pytest

from helper_deck import goto_slide, open_deck, slides_source

pytestmark = pytest.mark.deck("v2")

DAY0 = date(2026, 5, 8)
MONTHS = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}
DATE = re.compile(r"^(\d{1,2})(?:[–-]\d{1,2})?\s+([A-Z][a-z]{2})$")

# every timeline entry on world slides: its date text, the text right after the date, li classes
ENTRIES = """() => [...document.querySelectorAll('section.slide[data-world] .body--timeline ol.steps > li')].map(li => {
  const d = li.querySelector(':scope > strong');
  const tag = d && d.nextElementSibling && d.nextElementSibling.tagName === 'SPAN'
    && !d.nextElementSibling.classList.contains('tl-aside') ? d.nextElementSibling : null;
  return {id: li.id, sub: li.classList.contains('sub'), date: d ? d.textContent.trim() : null,
          tag: tag ? tag.textContent.trim() : null}; })"""


def helper_expected(date_text: str) -> str | None:
    """Day tag a date text should carry, or None for an undated/unparseable entry."""
    m = DATE.match(date_text or "")
    if not m or m.group(2) not in MONTHS:
        return None
    n = (date(2026, MONTHS[m.group(2)], int(m.group(1))) - DAY0).days
    return "day 0" if n == 0 else f"+{n} d"


@pytest.fixture
def entries(page):
    open_deck(page)
    return page.evaluate(ENTRIES)


def test_every_dated_entry_shows_its_day_count_from_8_may(entries):
    dated = [e for e in entries if helper_expected(e["date"])]
    assert len(dated) >= 15, "world timelines carry their dated entries"
    for e in dated:
        assert e["tag"] == helper_expected(e["date"]), f"{e['id']} ({e['date']}) shows {e['tag']!r}"


@pytest.mark.parametrize("date_text,tag", [("8 May", "day 0"), ("12 May", "+4 d"), ("26 Jun", "+49 d"),
                                           ("5–6 Jul", "+58 d"), ("26 Aug", "+110 d")])
def test_known_dates_carry_the_agreed_tags(entries, date_text, tag):
    """Anchors from the PRD decision; a range counts from its first day."""
    hits = [e for e in entries if e["date"] == date_text]
    assert hits, f"a timeline entry dated {date_text}"
    assert all(e["tag"] == tag for e in hits), hits


def test_undated_entries_and_sub_points_carry_no_tag(entries):
    """'Apr–May' and 'June' are not single dates; sub-point dashes have no date at all."""
    plain = [e for e in entries if not helper_expected(e["date"])]
    assert {"Apr–May", "June"} <= {e["date"] for e in plain}
    assert any(e["sub"] for e in plain)
    assert all(e["tag"] is None for e in plain), [e for e in plain if e["tag"]]


def test_day_tags_are_never_typed_in_the_slide_source():
    """One source of truth: the tag is derived from the date, so slide markup never spells one."""
    assert not re.search(r"\+\d+\s?d\b|\bday 0\b", slides_source())


@pytest.mark.parametrize("w,h", [(1920, 1080), (1280, 720), (1288, 598)])
def test_tag_is_quiet_and_sits_on_its_dates_line(page, w, h):
    """Smaller and muted beside the date, never wrapping away from it or competing with it."""
    open_deck(page, w, h)
    for sid in ["s-3", "s-4", "s-5", "s-6", "s-7"]:
        goto_slide(page, sid, 9)
        rows = page.evaluate("""id => [...document.querySelectorAll(`#${id} ol.steps > li > strong`)].map(d => {
            const t = d.nextElementSibling, cs = e => getComputedStyle(e);
            if (!t || t.tagName !== 'SPAN' || t.classList.contains('tl-aside')) return null;
            const a = d.getBoundingClientRect(), b = t.getBoundingClientRect(), p = s => parseFloat(cs(s).fontSize);
            return {li: d.parentElement.id, dateFs: p(d), tagFs: p(t), dateTop: a.top, dateBottom: a.bottom,
                    tagTop: b.top, tagBottom: b.bottom, tagLines: t.getClientRects().length,
                    tagColor: cs(t).color, dateColor: cs(d).color, tagWeight: +cs(t).fontWeight, dateWeight: +cs(d).fontWeight}; })
            .filter(Boolean)""", sid)
        assert rows, f"{sid} has tagged entries"
        for r in rows:
            assert r["tagFs"] < r["dateFs"], f"{r['li']}: tag smaller than the date"
            assert r["tagColor"] != r["dateColor"], f"{r['li']}: tag muted, not the date's ink"
            assert r["tagWeight"] < r["dateWeight"], f"{r['li']}: tag lighter than the date"
            assert r["tagLines"] == 1, f"{r['li']}: tag never breaks across lines"
            mid = (r["tagTop"] + r["tagBottom"]) / 2
            assert r["dateTop"] <= mid <= r["dateBottom"], f"{r['li']}: tag on the date's line at {w}x{h}"
