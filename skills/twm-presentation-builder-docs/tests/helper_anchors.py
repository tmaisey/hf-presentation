"""Build the eval's flawed anchor decks (PB-020) into ``evals/anchors/``.

Each anchor is assembled by the shipped ``scripts/assemble.py`` exactly as a skill-built deck is (skeleton,
engine and the modules its slides trigger, the shipped components layer, the generated paper-green /
editorial theme and the style's embedded fonts), with its flaw carried only by its copy, its markup or a
short deck-layer rule, so a judge sees the skill's real look and only the flaw differs. The decks carry no
comment or name that tells a judge what is wrong; the labels live in ``anchors.json``.

Regenerate after an engine, skeleton, components or token change::

    uv run python skills/twm-presentation-builder-docs/tests/helper_anchors.py
"""

from __future__ import annotations

from pathlib import Path

from helper_engine import load_assemble
from helper_skill import SKILL_DIR

ANCHOR_DIR = SKILL_DIR / "evals" / "anchors"

def _note(target: str, head: str, text: str, src: tuple[str, str] | None) -> str:
    link = f'\n    <a class="src" href="{src[1]}">{src[0]}</a>' if src else ""
    return f'  <aside class="note" data-for="#{target}"><h3>{head}</h3><p>{text}</p>{link}</aside>'


def _tile(tid: str, x: int, y: int, w: int, h: int, title: str, sub: str = "", at: int | None = None) -> str:
    show = f' data-show-at="{at}"' if at else ""
    sub_t = f'<text class="tile-sub">{sub}</text>' if sub else ""
    return (f'<g class="tile" id="{tid}"{show}><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14"/>'
            f'<text class="tile-title">{title}</text>{sub_t}</g>')


def _edge(eid: str, a: str, b: str, at: int | None = None) -> str:
    show = f' data-show-at="{at}"' if at else ""
    return f'<path class="edge" id="{eid}" data-from="#{a}" data-to="#{b}" marker-end="url(#arr)"{show}/>'


def _diagram(label: str, view: str, edges: list[str], tiles: list[str]) -> str:
    return (f'<svg class="diagram" viewBox="{view}" role="img" aria-label="{label}">\n'
            f'      <g class="layer-edges">{"".join(edges)}</g>\n'
            f'      <g class="layer-nodes">{"".join(tiles)}</g>\n    </svg>')


SRC = "https://{}.example.org/{}"

# ---------- AN-00: clean (pharmacy pick-up slots) ----------
AN00 = f"""
<section class="slide slide--lead" id="a0-1" data-chapter="Opening" data-ambient>
  <p class="kicker">Queue review</p>
  <h2 class="title" id="a0-1-title">Booked pick-up slots shortened the pharmacy queue</h2>
  <div class="body"><p>What changed when refills moved to a booked time</p></div>
{_note("a0-1-title", "About this review", "A summary of the branch's own queue logs and staff interviews.", ("Branch queue review", SRC.format("pharmacy-review", "summary")))}
</section>

<section class="slide" id="a0-2" data-chapter="Change">
  <p class="kicker">01 · Change</p>
  <h2 class="title">Booking moved refill collection out of the lunchtime peak</h2>
  <div class="body body--stack">
    {_diagram("Walk-in queue, booking page and pick-up slot, joined in order", "0 0 760 420",
              [_edge("a0-e1", "a0-walk", "a0-book", 1), _edge("a0-e2", "a0-book", "a0-slot", 2)],
              [_tile("a0-walk", 20, 40, 240, 110, "Walk-in queue", "midday"),
               _tile("a0-book", 500, 40, 240, 110, "Booking page", "online", 1),
               _tile("a0-slot", 500, 270, 240, 110, "Pick-up slot", "15 minutes", 2)])}
  </div>
  <div class="narration">
    <article class="narr-tile" id="a0-n1" data-at="1"><p class="msg-from">Pharmacist</p><blockquote class="msg-text">Most people chose a time after three.</blockquote></article>
    <article class="narr-tile" id="a0-n2" data-at="2"><p class="msg-from">Counter assistant</p><blockquote class="msg-text">The bags are ready before they arrive.</blockquote></article>
  </div>
{_note("a0-book", "Booking page", "Bookings opened for repeat prescriptions only. The pharmacist, interviewed in week six: “Most people chose a time after three.”", ("Booking launch notice", SRC.format("pharmacy-review", "booking")))}
{_note("a0-slot", "Pick-up slot", "Each slot is 15 minutes; staff pack the order the evening before. The counter assistant: “The bags are ready before they arrive.”", ("Staff interview notes", SRC.format("pharmacy-review", "interviews")))}
</section>

<section class="slide" id="a0-3" data-chapter="Change">
  <p class="kicker">02 · Change</p>
  <h2 class="title" id="a0-3-title">Staff said the afternoons became calmer</h2>
  <div class="body">
    <div class="msg-card quote" id="a0-q"><p class="msg-agent">Pharmacist, interview</p>
      <blockquote class="msg-text">The afternoons are calmer […] we can talk to people again.</blockquote></div>
  </div>
{_note("a0-q", "Full quote", "“The afternoons are calmer now, and we can talk to people again.” Cut marked […].", ("Staff interview notes", SRC.format("pharmacy-review", "interviews")))}
</section>

<section class="slide" id="a0-4" data-chapter="Next">
  <p class="kicker">03 · Next</p>
  <h2 class="title" id="a0-4-title">Offer booked slots at the next two branches</h2>
  <div class="body"><ul class="points">
    <li>Start with repeat prescriptions</li>
    <li>Keep walk-in collection open</li>
  </ul></div>
{_note("a0-4-title", "Next branches", "Both branches have the longest midday queues in the region.", ("Regional queue table", SRC.format("pharmacy-review", "regional")))}
</section>
"""

# ---------- AN-01: bottom caption collides with the diagram in a short-wide window (bike share) ----------
AN01 = f"""
<section class="slide" id="a1-1" data-chapter="Network">
  <p class="kicker">01 · Network</p>
  <h2 class="title">Overnight van runs refill the busiest docks</h2>
  <div class="body">
    {_diagram("Depot, van and two docks, joined by refill routes", "0 0 900 420",
              [_edge("a1-e1", "a1-depot", "a1-van"), _edge("a1-e2", "a1-van", "a1-busy", 1), _edge("a1-e3", "a1-van", "a1-quiet", 2)],
              [_tile("a1-depot", 20, 30, 240, 110, "Depot", "40 bikes"),
               _tile("a1-van", 330, 30, 240, 110, "Van", "night run"),
               _tile("a1-busy", 160, 290, 280, 110, "Station dock", "empties by 9am", 1),
               _tile("a1-quiet", 460, 290, 280, 110, "Park dock", "rarely used", 2)])}
  </div>
  <p class="caption" id="a1-cap">Refills follow the morning demand, not the map</p>
{_note("a1-busy", "Station dock", "The station dock is the first to empty on weekdays.", ("Dock occupancy log", SRC.format("bikes", "occupancy")))}
{_note("a1-cap", "Routing", "Van routes are planned from the previous week's empty-dock alerts.", ("Operations handbook", SRC.format("bikes", "handbook")))}
</section>
"""
AN01_DECK = """@layer deck {
  #a1-1 .diagram { width: min(100%, 62vw); height: auto; max-height: none; }
  #a1-1 > .caption { position: absolute; left: var(--comp-slide-pad-x); bottom: 9vh; margin: 0;
    font-size: var(--sys-type-small-size); color: var(--sys-color-ink-2); }
}"""

# ---------- AN-02: low-contrast body text (school library) ----------
AN02 = f"""
<section class="slide" id="a2-1" data-chapter="Loans">
  <p class="kicker">01 · Loans</p>
  <h2 class="title" id="a2-1-title">Self-service kiosks doubled lunchtime loans</h2>
  <div class="body">
    <p>Pupils borrowed 210 books a week at lunch after the kiosks arrived, up from 104.</p>
    <p class="caption">Counts are weekly averages over the spring term.</p>
  </div>
{_note("a2-1-title", "Loan counts", "Weekly lunchtime loans, before and after the kiosks.", ("Library loan report", SRC.format("library", "loans")))}
</section>

<section class="slide" id="a2-2" data-chapter="Loans">
  <p class="kicker">02 · Loans</p>
  <h2 class="title" id="a2-2-title">Librarians spent the time saved on reading groups</h2>
  <div class="body"><ul class="points"><li>Two new reading groups</li><li>Weekly book talks for Year 7</li></ul></div>
{_note("a2-2-title", "Reading groups", "Both groups started in the spring term.", ("Library newsletter", SRC.format("library", "newsletter")))}
</section>
"""
AN02_DECK = """@layer deck {
  .body p, .body li { color: var(--sys-color-ink-3); font-size: var(--sys-type-small-size); }
}"""

# ---------- AN-03: voice-rejected titles (bakery pre-orders) ----------
AN03 = f"""
<section class="slide slide--lead" id="a3-1" data-chapter="Opening">
  <p class="kicker">Pre-order review</p>
  <h2 class="title" id="a3-1-title">What if the queue was never the problem?</h2>
  <div class="body"><p>A look at the bakery's first season of pre-orders</p></div>
</section>

<section class="slide" id="a3-2" data-chapter="Orders">
  <p class="kicker">01 · Orders</p>
  <h2 class="title" id="a3-2-title">The surprising reason pre-orders stalled</h2>
  <div class="body"><ul class="points"><li>The order form closed at 6pm the day before</li><li>Most orders arrived after 8pm</li></ul></div>
{_note("a3-2-title", "Order times", "Order timestamps from the shop's booking tool.", ("Order export", SRC.format("bakery", "orders")))}
</section>

<section class="slide" id="a3-3" data-chapter="Orders">
  <p class="kicker">02 · Orders</p>
  <h2 class="title" id="a3-3-title">Pre-orders fell. Walk-ins rose.</h2>
  <div class="body"><ul class="points"><li>Pre-orders dropped in the second month</li><li>Walk-in sales grew in the same weeks</li></ul></div>
{_note("a3-3-title", "Sales mix", "Monthly sales split by channel.", ("Till summary", SRC.format("bakery", "till")))}
</section>

<section class="slide" id="a3-4" data-chapter="Next">
  <p class="kicker">03 · Next</p>
  <h2 class="title" id="a3-4-title">A <em>rising</em> tide of <em>dough</em>.</h2>
  <div class="body"><ul class="points"><li>Move the order cut-off to 10pm</li><li>Bake to the order count first</li></ul></div>
{_note("a3-4-title", "Cut-off", "A later cut-off was the change most customers asked for.", ("Customer survey", SRC.format("bakery", "survey")))}
</section>
"""

# ---------- AN-04: unsourced figures and a paraphrase shown as a quote (community garden) ----------
AN04 = f"""
<section class="slide" id="a4-1" data-chapter="Water">
  <p class="kicker">01 · Water</p>
  <h2 class="title" id="a4-1-title">Drip lines cut the garden's summer water use by a third</h2>
  <div class="body">
    <p class="stat"><strong>−34%</strong></p>
    <p>41,000 litres in summer 2024, 27,000 litres in summer 2025.</p>
  </div>
{_note("a4-1-title", "Why it matters", "Water is the garden's largest running cost after rent, so the saving pays for new plots.", None)}
</section>

<section class="slide" id="a4-2" data-chapter="Water">
  <p class="kicker">02 · Water</p>
  <h2 class="title" id="a4-2-title">The saving paid for six new plots</h2>
  <div class="body">
    <div class="msg-card quote" id="a4-q"><p class="msg-agent">Plot coordinator</p>
      <blockquote class="msg-text">Once the drip lines went in we used much less water, which paid for six new plots.</blockquote></div>
  </div>
{_note("a4-q", "Coordinator", "From the annual meeting minutes: “We used noticeably less water once the drip lines went in, and that freed up budget for six new plots.”", ("Annual meeting minutes", SRC.format("garden", "minutes")))}
</section>
"""

# ---------- AN-05: crammed slide, step list restating a sparse diagram (returns desk) ----------
AN05 = f"""
<section class="slide" id="a5-1" data-chapter="Returns">
  <p class="kicker">01 · Returns</p>
  <h2 class="title" id="a5-1-title">Returns now take three days from request to refund instead of eleven</h2>
  <ol class="steps">
    <li data-show-at="1">Step 1: the customer opens a Return request online</li>
    <li data-show-at="2">Step 2: the Warehouse checks the parcel on arrival</li>
    <li data-show-at="3">Step 3: Finance issues the Refund the same day</li>
  </ol>
  <p class="caption" id="a5-cap">Median days, January to March, all regions</p>
  <div class="body">
    {_diagram("Return request, warehouse and refund", "0 0 900 640",
              [_edge("a5-e1", "a5-req", "a5-wh", 2), _edge("a5-e2", "a5-wh", "a5-ref", 3)],
              [_tile("a5-req", 290, 60, 320, 90, "Return request", "", 1),
               _tile("a5-wh", 290, 275, 320, 90, "Warehouse", "", 2),
               _tile("a5-ref", 290, 490, 320, 90, "Refund", "", 3)])}
  </div>
  <div id="a5-quotes">
    <div class="msg-card quote" data-show-at="1"><p class="msg-agent">Customer</p><blockquote class="msg-text">The form takes a minute.</blockquote></div>
    <div class="msg-card quote" data-show-at="2"><p class="msg-agent">Warehouse lead</p><blockquote class="msg-text">We scan it the morning it lands.</blockquote></div>
    <div class="msg-card quote" data-show-at="3"><p class="msg-agent">Finance</p><blockquote class="msg-text">Refunds go out in the afternoon batch.</blockquote></div>
  </div>
{_note("a5-1-title", "Timing", "Median days from request to refund, before and after the new process.", ("Returns dashboard", SRC.format("returns", "dashboard")))}
{_note("a5-wh", "Warehouse", "Parcels are checked on the day they arrive.", ("Warehouse procedure", SRC.format("returns", "procedure")))}
{_note("a5-quotes", "Interviews", "Verbatim from the interview notes: “The form takes a minute.” “We scan it the morning it lands.” “Refunds go out in the afternoon batch.”", ("Returns interview notes", SRC.format("returns", "interviews")))}
</section>
"""
AN05_DECK = """@layer deck {
  #a5-1 { grid-template: "kicker kicker kicker" auto "title title title" auto "steps diagram quotes" minmax(0, 1fr)
      / minmax(0, 3fr) minmax(0, 4fr) minmax(0, 3fr); column-gap: 1.2vw; }
  #a5-1 > .kicker { grid-area: kicker; } #a5-1 > .title { grid-area: title; max-width: none; }
  #a5-1 > .steps { grid-area: steps; font-size: var(--sys-type-small-size); }
  #a5-1 > .caption { grid-area: steps; align-self: end; margin: 0; font-size: var(--sys-type-small-size); color: var(--sys-color-ink-2); }
  #a5-1 > .body { grid-area: diagram; padding: 2vh 1vw; border-radius: 18px; background: var(--sys-color-tile); box-shadow: var(--sys-shadow-rest); }
  #a5-1 .tile rect { fill: var(--sys-color-paper); }
  #a5-quotes { grid-area: quotes; display: grid; align-content: start; gap: 6px; }
  #a5-quotes .quote { padding: 8px 12px; }
}"""

# ---------- AN-06: quote tiles stacked far from the nodes they narrate, the first over the title (ferry) ----------
AN06 = f"""
<section class="slide" id="a6-1" data-chapter="Crossing">
  <p class="kicker">01 · Crossing</p>
  <h2 class="title" id="a6-1-title">A second ferry halved the north pier wait</h2>
  <div class="body">
    {_diagram("North pier, two ferries and the south pier", "0 0 900 460",
              [_edge("a6-e1", "a6-north", "a6-f1", 1), _edge("a6-e2", "a6-north", "a6-f2", 2), _edge("a6-e3", "a6-f2", "a6-south", 3)],
              [_tile("a6-north", 20, 175, 220, 110, "North pier"),
               _tile("a6-f1", 380, 30, 220, 110, "Ferry A", "", 1),
               _tile("a6-f2", 380, 320, 220, 110, "Ferry B", "", 2),
               _tile("a6-south", 660, 175, 220, 110, "South pier", "", 3)])}
  </div>
  <div id="a6-quotes">
    <div class="msg-card quote" data-show-at="1"><p class="msg-agent">Commuter</p><blockquote class="msg-text">One boat an hour was too few.</blockquote></div>
    <div class="msg-card quote" data-show-at="2"><p class="msg-agent">Deckhand</p><blockquote class="msg-text">The half-past boat is never full.</blockquote></div>
    <div class="msg-card quote" data-show-at="3"><p class="msg-agent">Skipper</p><blockquote class="msg-text">We land on time now.</blockquote></div>
  </div>
{_note("a6-1-title", "Waiting times", "Average wait at the north pier in the morning peak, before and after Ferry B.", ("Pier survey", SRC.format("ferry", "survey")))}
{_note("a6-f2", "Ferry B", "Ferry B leaves at half past each hour.", ("Timetable", SRC.format("ferry", "timetable")))}
{_note("a6-quotes", "Pier interviews", "Verbatim from the pier interviews: “One boat an hour was too few.” “The half-past boat is never full.” “We land on time now.”", ("Pier survey", SRC.format("ferry", "survey")))}
</section>
"""
AN06_DECK = """@layer deck {
  #a6-1 { grid-template: "kicker kicker" auto "title title" auto "quotes body" minmax(0, 1fr) / minmax(0, 2fr) minmax(0, 3fr); column-gap: 3vw; }
  #a6-1 > .kicker { grid-area: kicker; } #a6-1 > .title { grid-area: title; }
  #a6-1 > .body { grid-area: body; }
  #a6-quotes { grid-column: quotes; grid-row: 2 / 4; margin-top: 1.3em; display: grid; align-content: start; gap: 14px; }
}"""

# ---------- AN-07: accent colour used as text (rooftop solar) ----------
AN07 = f"""
<section class="slide" id="a7-1" data-chapter="Output">
  <p class="kicker">01 · Output</p>
  <h2 class="title" id="a7-1-title">The school's roof panels now cover most daytime power use</h2>
  <div class="body">
    <p class="stat"><strong>71%</strong></p>
    <p>Share of weekday daytime electricity from the panels in the first year</p>
  </div>
{_note("a7-1-title", "Panel output", "Metered panel output against the school's daytime use.", ("Energy meter report", SRC.format("solar", "meter")))}
</section>

<section class="slide" id="a7-2" data-chapter="Output">
  <p class="kicker">02 · Output</p>
  <h2 class="title" id="a7-2-title">Battery storage would carry the surplus into the evening</h2>
  <div class="body"><ul class="points"><li>Weekend output is mostly exported</li><li>Evening clubs draw from the grid</li></ul></div>
{_note("a7-2-title", "Surplus", "Export readings from the same meter.", ("Energy meter report", SRC.format("solar", "meter")))}
</section>
"""
AN07_DECK = """@layer deck {
  .body .stat strong, .body p, .points li { color: var(--sys-color-accent); }
}"""

# ---------- AN-08: ambient motion behind a step-built diagram (recycling) ----------
AN08 = f"""
<section class="slide slide--lead" id="a8-1" data-chapter="Opening">
  <p class="kicker">Sorting review</p>
  <h2 class="title" id="a8-1-title">A second sorting line cut contamination in recycled paper</h2>
  <div class="body"><p>The first six months of the new line</p></div>
</section>

<section class="slide" id="a8-2" data-chapter="Line" data-ambient>
  <p class="kicker">01 · Line</p>
  <h2 class="title" id="a8-2-title">Paper now passes an optical sorter before baling</h2>
  <div class="body">
    {_diagram("Collection, optical sorter and baler, joined in order", "0 0 900 300",
              [_edge("a8-e1", "a8-in", "a8-sort", 1), _edge("a8-e2", "a8-sort", "a8-bale", 2)],
              [_tile("a8-in", 20, 95, 230, 110, "Collection", "mixed paper"),
               _tile("a8-sort", 335, 95, 230, 110, "Optical sorter", "", 1),
               _tile("a8-bale", 650, 95, 230, 110, "Baler", "clean paper", 2)])}
  </div>
{_note("a8-sort", "Optical sorter", "The sorter removes plastic film and card before baling.", ("Plant upgrade note", SRC.format("recycling", "upgrade")))}
</section>
"""

# ---------- AN-09: a reader note whose source is bare text (commuter survey) ----------
AN09 = f"""
<section class="slide" id="a9-1" data-chapter="Travel">
  <p class="kicker">01 · Travel</p>
  <h2 class="title" id="a9-1-title">Most staff would cycle if the site had showers</h2>
  <div class="body">
    <p class="stat"><strong>58%</strong></p>
    <p>of staff who drive said showers would make them cycle twice a week</p>
  </div>
{_note("a9-1-title", "Survey", "Asked of staff who drive to the site at least three days a week. Source: regional commuter survey, 2025.", None)}
</section>

<section class="slide" id="a9-2" data-chapter="Travel">
  <p class="kicker">02 · Travel</p>
  <h2 class="title" id="a9-2-title">Two showers fit in the existing plant room</h2>
  <div class="body"><ul class="points"><li>No new building needed</li><li>Water supply already in place</li></ul></div>
{_note("a9-2-title", "Plant room", "Facilities checked the plant room layout and supply.", ("Facilities site survey", SRC.format("travel", "site")))}
</section>
"""

ANCHORS = {
    "an-00": ("Pharmacy pick-up", "Queue review", AN00, ""),
    "an-01": ("Bike share", "Overnight refills", AN01, AN01_DECK),
    "an-02": ("School library", "Lunchtime loans", AN02, AN02_DECK),
    "an-03": ("Bakery pre-orders", "First season", AN03, ""),
    "an-04": ("Community garden", "Water use", AN04, ""),
    "an-05": ("Returns desk", "Process change", AN05, AN05_DECK),
    "an-06": ("River ferry", "Morning crossing", AN06, AN06_DECK),
    "an-07": ("School solar", "First year", AN07, AN07_DECK),
    "an-08": ("Paper recycling", "Sorting line", AN08, ""),
    "an-09": ("Staff travel", "Cycling survey", AN09, ""),
}


def build(name: str, out_dir: Path = ANCHOR_DIR) -> Path:
    """Assemble one anchor deck with the shipped assembler (theme, components, fonts) plus its deck-layer rule.

    Args:
        name: Key in ``ANCHORS`` (also the file stem).
        out_dir: Folder to write ``<name>.html`` into.

    Returns:
        The written file.
    """
    asm = load_assemble()
    title, subtitle, slides, deck_css = ANCHORS[name]
    t = asm.theme_blocks("paper-green", "editorial", "components")
    src = asm.build(slides.strip("\n"), title, subtitle, fonts=t["FONTS"], components=t["COMPONENTS"],
                    palette=t["PALETTE"], style=t["STYLE"], deck=deck_css)
    out = out_dir / f"{name}.html"
    asm._write(out, src)
    return out


def build_all(out_dir: Path = ANCHOR_DIR) -> list[Path]:
    """Assemble every anchor deck.

    Args:
        out_dir: Destination folder (created if missing).

    Returns:
        The written files.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    return [build(n, out_dir) for n in ANCHORS]


if __name__ == "__main__":
    for p in build_all():
        print(f"{p.name}: {p.stat().st_size} bytes")
