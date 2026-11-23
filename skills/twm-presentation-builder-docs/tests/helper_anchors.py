"""Build the eval's flawed anchor decks (PB-020) into ``evals/anchors/``.

Each anchor is the skill's skeleton + engine (+ the modules its slides trigger) + the generated
paper-green/editorial theme + one shared components stand-in, with its flaw carried only by its copy,
its markup or a short deck-layer rule. No fonts are embedded (the theme's fallbacks render), so each
file stays small. The decks carry no comment or name that tells a judge what is wrong; the labels live
in ``anchors.json``.

Regenerate after an engine, skeleton or token change::

    uv run python skills/twm-presentation-builder-docs/tests/helper_anchors.py
"""

from __future__ import annotations

from pathlib import Path

from helper_engine import assemble, fill
from helper_skill import SKILL_DIR
from helper_tokens import load_script

ANCHOR_DIR = SKILL_DIR / "evals" / "anchors"

# Stand-in for the components layer (PB-004 owns the real one): layout and look from sys tokens only.
COMPONENTS = """@layer components {
  body { font: var(--sys-type-body-weight) var(--sys-type-body-size)/var(--sys-type-body-leading) var(--sys-type-body-family);
    background: var(--sys-color-paper); color: var(--sys-color-ink); }
  a { color: inherit; }
  .bar { height: 64px; display: flex; align-items: center; gap: 24px; padding: 0 32px;
    background: var(--sys-material-chrome); backdrop-filter: blur(var(--sys-material-chrome-blur)) saturate(var(--sys-material-chrome-saturate));
    box-shadow: 0 1px 0 var(--sys-color-paper-deep); }
  .bar-title { margin: 0; font: 500 var(--sys-type-small-size)/1 var(--sys-type-small-family); white-space: nowrap; }
  .bar-title span { margin: 0 .5em; color: var(--sys-color-ink-2); }
  .bar-title em { color: var(--sys-color-ink-2); }
  .bar-home { text-decoration: none; }
  .nav { margin-left: auto; }
  .agenda { gap: 4px; }
  .agenda button, .nav-current { font: 500 15px/1 var(--sys-font-sans); background: none; border: 0; padding: 9px 14px;
    border-radius: 999px; color: var(--sys-color-ink-2); }
  .agenda .is-current button, .nav-current { color: var(--sys-color-ink); background: var(--sys-material-chip); box-shadow: var(--sys-shadow-rest); }
  .bar--compact .agenda { background: var(--sys-color-tile); padding: 8px; border-radius: 14px; box-shadow: var(--sys-shadow-lift); }
  .progress { background: var(--sys-color-accent); }

  .slide { display: grid; grid-template-columns: minmax(0, 1fr); align-content: start; padding: calc(64px + 5vh) 7vw 9vh; }
  .slide--lead { align-content: center; }
  .kicker { margin: 0; font: var(--sys-type-kicker-weight) var(--sys-type-kicker-size)/var(--sys-type-kicker-leading) var(--sys-type-kicker-family);
    letter-spacing: var(--sys-type-kicker-tracking); text-transform: uppercase; color: var(--sys-color-ink-2); }
  .title { margin: .45em 0 .7em; max-width: 32ch; font: var(--sys-type-title-weight) var(--sys-type-title-size)/var(--sys-type-title-leading) var(--sys-type-title-family);
    letter-spacing: var(--sys-type-title-tracking); text-wrap: balance; }
  .title em { font-style: italic; }
  .slide--lead .title { max-width: 20ch; font-size: var(--sys-type-lead-size); line-height: var(--sys-type-lead-leading); }
  .body { font: var(--sys-type-text-weight) var(--sys-type-text-size)/var(--sys-type-text-leading) var(--sys-type-text-family); min-height: 0; }
  .body p { margin: 0 0 .75em; max-width: 46ch; }
  .lede { color: var(--sys-color-ink-2); }
  .points { margin: 0; padding-left: 1.1em; max-width: 50ch; }
  .points li { margin: .4em 0; }
  .body .stat { margin: 0 0 .12em; font: var(--sys-type-stat-weight) var(--sys-type-stat-size)/var(--sys-type-stat-leading) var(--sys-type-stat-family);
    letter-spacing: var(--sys-type-stat-tracking); }
  .caption { margin: 0; font: var(--sys-type-small-weight) var(--sys-type-small-size)/var(--sys-type-small-leading) var(--sys-type-small-family);
    color: var(--sys-color-ink-2); }
  .steps { margin: 0; padding-left: 1.3em; }
  .steps li { margin: .5em 0; }
  .steps li.is-done { color: var(--sys-color-ink-2); }
  .steps li.is-current { font-weight: 600; }

  .quote { margin: 0; padding: 22px 26px; max-width: 44ch; border-radius: 18px; background: var(--sys-color-tile); box-shadow: var(--sys-shadow-lift);
    font: var(--sys-type-msg-weight) var(--sys-type-msg-size)/var(--sys-type-msg-leading) var(--sys-type-msg-family); }
  .quote p { margin: 0 0 .5em; }
  .quote-from, .msg-from { margin: 0; font: 600 var(--sys-type-kicker-size)/1.3 var(--sys-font-sans); color: var(--sys-color-ink-2); }
  .quotes { display: grid; align-content: start; gap: 14px; }
  .quotes .quote { padding: 14px 18px; font-size: var(--sys-type-small-size); }

  /* diagram slides; a narration column runs beside the diagram when the slide has one */
  .slide:has(> .narration) { grid-template: "kicker kicker" auto "title title" auto "body narr" minmax(0, 1fr)
      / minmax(0, 3fr) minmax(0, 2fr); column-gap: 3vw; }
  .slide:has(> .narration) > .kicker { grid-area: kicker; }
  .slide:has(> .narration) > .title { grid-area: title; }
  .slide:has(> .narration) > .body { grid-area: body; }
  .slide:has(> .narration) > .narration { grid-area: narr; }
  .slide:has(> .body--diagram) { grid-template-rows: auto auto minmax(0, 1fr); }
  .body--diagram { display: grid; align-items: center; }
  .diagram { width: 100%; height: 100%; max-height: 100%; }
  .tile rect { fill: var(--sys-color-tile); stroke: var(--sys-color-ink-3); stroke-width: calc(1.5px * var(--k)); filter: url(#lift); }
  .tile-title { font: var(--sys-type-d-title-weight) calc(var(--sys-type-d-title-size) * var(--k)) var(--sys-type-d-title-family);
    fill: var(--sys-color-ink); text-anchor: middle; dominant-baseline: central; }
  .tile-sub { font: var(--sys-type-d-sub-weight) calc(var(--sys-type-d-sub-size) * var(--k)) var(--sys-type-d-sub-family);
    fill: var(--sys-color-ink-2); text-anchor: middle; dominant-baseline: central; }
  .edge { fill: none; stroke: var(--sys-color-ink-2); stroke-width: calc(2px * var(--k)); }
  #arr path { fill: var(--sys-color-ink-2); }
  #lift feDropShadow { flood-color: var(--sys-color-ink); }
  [data-show-at], [data-hide-at] { transition: opacity var(--sys-motion-reveal); }

  .narr-tile { padding: 14px 20px; border-radius: 16px; background: var(--sys-color-tile); box-shadow: var(--sys-shadow-lift);
    font: var(--sys-type-msg-weight) var(--sys-type-msg-size)/var(--sys-type-msg-leading) var(--sys-type-msg-family);
    transform: translateY(var(--sys-motion-rise));
    transition: opacity var(--sys-motion-reveal), transform var(--sys-motion-reveal), filter var(--sys-motion-reveal); }
  .narr-tile.is-shown { transform: none; }
  .narr-tile.was-shown { filter: blur(6px); transform: none; }
  .narr-tile p, .narr-tile blockquote { margin: 0; }
  .msg-text { margin-top: .3em; }

  .ambient .orb--far { filter: blur(var(--sys-ambient-far-blur)); opacity: var(--sys-ambient-far-opacity); }
  .ambient .orb--mid { filter: blur(var(--sys-ambient-mid-blur)); opacity: var(--sys-ambient-mid-opacity); }
  .ambient .orb--near { filter: blur(var(--sys-ambient-near-blur)); opacity: var(--sys-ambient-near-opacity); }
  .orb--1 { background: var(--sys-ambient-tint-1); } .orb--2 { background: var(--sys-ambient-tint-2); }
  .orb--3 { background: var(--sys-ambient-tint-3); } .orb--4 { background: var(--sys-ambient-tint-4); }
  .orb--5 { background: var(--sys-ambient-tint-5); }

  .notes-btn { padding: 9px 16px; border: 0; border-radius: 999px; font: 500 15px/1 var(--sys-font-sans);
    background: var(--sys-material-chip); color: var(--sys-color-ink); box-shadow: var(--sys-shadow-lift); }
  .notes-on .notes-btn { background: var(--sys-color-ink); color: var(--sys-color-paper); }
  .veil { background: var(--sys-material-veil); backdrop-filter: blur(var(--sys-material-veil-blur)); transition: opacity var(--sys-motion-reveal); }
  .ring { outline: 0; border-radius: 14px; box-shadow: 0 0 0 2px var(--sys-color-accent-ink); }
  .callout { max-width: 420px; padding: 22px 26px; border-radius: 18px; background: var(--sys-color-tile); box-shadow: var(--sys-shadow-key);
    font: var(--sys-type-small-weight) var(--sys-type-small-size)/var(--sys-type-small-leading) var(--sys-type-small-family); }
  .callout h3 { margin: 0 0 .4em; font: 600 1em/1.25 var(--sys-font-sans); }
  .callout p { margin: 0 0 .6em; }
  .callout .cite { color: var(--sys-color-ink-2); }
  .notes-nav { gap: 6px; padding: 6px; border-radius: 999px; background: var(--sys-material-chip); box-shadow: var(--sys-shadow-lift); }
  .notes-nav button { padding: 8px 14px; border: 0; border-radius: 999px; background: none; color: var(--sys-color-ink); font: 500 15px/1 var(--sys-font-sans); }
  .pin { width: 28px; height: 28px; margin: -14px 0 0 -14px; border: 0; border-radius: 50%; font: 600 14px/1 var(--sys-font-sans);
    background: var(--sys-color-ink); color: var(--sys-color-paper); }
  .pin.is-current { background: var(--sys-color-accent-ink); }
  :root.still .narr-tile { transform: none; }
}"""


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
  <div class="body"><p class="lede">What changed when refills moved to a booked time</p></div>
{_note("a0-1-title", "About this review", "A summary of the branch's own queue logs and staff interviews.", ("Branch queue review", SRC.format("pharmacy-review", "summary")))}
</section>

<section class="slide" id="a0-2" data-chapter="Change">
  <p class="kicker">01 · Change</p>
  <h2 class="title">Booking moved refill collection out of the lunchtime peak</h2>
  <div class="body body--diagram">
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
    <blockquote class="quote" id="a0-q"><p>“The afternoons are calmer […] we can talk to people again.”</p>
      <p class="quote-from">Pharmacist, interview</p></blockquote>
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
  <div class="body body--diagram">
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
  #a1-1 > .caption { position: absolute; left: 7vw; bottom: 9vh; }
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
  .body p, .body li { color: var(--sys-color-ink-3); }
  .body { font-size: var(--sys-type-small-size); }
}"""

# ---------- AN-03: voice-rejected titles (bakery pre-orders) ----------
AN03 = f"""
<section class="slide slide--lead" id="a3-1" data-chapter="Opening">
  <p class="kicker">Pre-order review</p>
  <h2 class="title" id="a3-1-title">What if the queue was never the problem?</h2>
  <div class="body"><p class="lede">A look at the bakery's first season of pre-orders</p></div>
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
    <p class="stat">−34%</p>
    <p>41,000 litres in summer 2024, 27,000 litres in summer 2025.</p>
  </div>
{_note("a4-1-title", "Why it matters", "Water is the garden's largest running cost after rent, so the saving pays for new plots.", None)}
</section>

<section class="slide" id="a4-2" data-chapter="Water">
  <p class="kicker">02 · Water</p>
  <h2 class="title" id="a4-2-title">The saving paid for six new plots</h2>
  <div class="body">
    <blockquote class="quote" id="a4-q"><p>“Once the drip lines went in we used much less water, which paid for six new plots.”</p>
      <p class="quote-from">Plot coordinator</p></blockquote>
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
  <div class="body body--diagram">
    {_diagram("Return request, warehouse and refund", "0 0 900 640",
              [_edge("a5-e1", "a5-req", "a5-wh", 2), _edge("a5-e2", "a5-wh", "a5-ref", 3)],
              [_tile("a5-req", 290, 60, 320, 90, "Return request", "", 1),
               _tile("a5-wh", 290, 275, 320, 90, "Warehouse", "", 2),
               _tile("a5-ref", 290, 490, 320, 90, "Refund", "", 3)])}
  </div>
  <div class="quotes" id="a5-quotes">
    <blockquote class="quote" data-show-at="1"><p>“The form takes a minute.”</p><p class="quote-from">Customer</p></blockquote>
    <blockquote class="quote" data-show-at="2"><p>“We scan it the morning it lands.”</p><p class="quote-from">Warehouse lead</p></blockquote>
    <blockquote class="quote" data-show-at="3"><p>“Refunds go out in the afternoon batch.”</p><p class="quote-from">Finance</p></blockquote>
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
  #a5-1 > .caption { grid-area: steps; align-self: end; }
  #a5-1 > .body { grid-area: diagram; padding: 2vh 1vw; border-radius: 18px; background: var(--sys-color-tile); box-shadow: var(--sys-shadow-rest); }
  #a5-1 .tile rect { fill: var(--sys-color-paper); }
  #a5-1 > .quotes { grid-area: quotes; gap: 6px; }
  #a5-1 .quotes .quote { padding: 8px 12px; }
}"""

# ---------- AN-06: quote tiles stacked far from the nodes they narrate, the first over the title (ferry) ----------
AN06 = f"""
<section class="slide" id="a6-1" data-chapter="Crossing">
  <p class="kicker">01 · Crossing</p>
  <h2 class="title" id="a6-1-title">A second ferry halved the north pier wait</h2>
  <div class="body body--diagram">
    {_diagram("North pier, two ferries and the south pier", "0 0 900 460",
              [_edge("a6-e1", "a6-north", "a6-f1", 1), _edge("a6-e2", "a6-north", "a6-f2", 2), _edge("a6-e3", "a6-f2", "a6-south", 3)],
              [_tile("a6-north", 20, 175, 220, 110, "North pier"),
               _tile("a6-f1", 380, 30, 220, 110, "Ferry A", "", 1),
               _tile("a6-f2", 380, 320, 220, 110, "Ferry B", "", 2),
               _tile("a6-south", 660, 175, 220, 110, "South pier", "", 3)])}
  </div>
  <div class="quotes" id="a6-quotes">
    <blockquote class="quote" data-show-at="1"><p>“One boat an hour was too few.”</p><p class="quote-from">Commuter</p></blockquote>
    <blockquote class="quote" data-show-at="2"><p>“The half-past boat is never full.”</p><p class="quote-from">Deckhand</p></blockquote>
    <blockquote class="quote" data-show-at="3"><p>“We land on time now.”</p><p class="quote-from">Skipper</p></blockquote>
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
  #a6-1 > .quotes { grid-column: quotes; grid-row: 2 / 4; margin-top: 1.3em; }
}"""

# ---------- AN-07: accent colour used as text (rooftop solar) ----------
AN07 = f"""
<section class="slide" id="a7-1" data-chapter="Output">
  <p class="kicker">01 · Output</p>
  <h2 class="title" id="a7-1-title">The school's roof panels now cover most daytime power use</h2>
  <div class="body">
    <p class="stat">71%</p>
    <p class="lede">Share of weekday daytime electricity from the panels in the first year</p>
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
  .stat, .lede, .points li::marker { color: var(--sys-color-accent); }
}"""

# ---------- AN-08: ambient motion behind a step-built diagram (recycling) ----------
AN08 = f"""
<section class="slide slide--lead" id="a8-1" data-chapter="Opening">
  <p class="kicker">Sorting review</p>
  <h2 class="title" id="a8-1-title">A second sorting line cut contamination in recycled paper</h2>
  <div class="body"><p class="lede">The first six months of the new line</p></div>
</section>

<section class="slide" id="a8-2" data-chapter="Line" data-ambient>
  <p class="kicker">01 · Line</p>
  <h2 class="title" id="a8-2-title">Paper now passes an optical sorter before baling</h2>
  <div class="body body--diagram">
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
    <p class="stat">58%</p>
    <p class="lede">of staff who drive said showers would make them cycle twice a week</p>
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


def theme_blocks() -> tuple[str, str]:
    """Generate the paper-green palette and editorial style blocks with the shipped generator.

    Returns:
        ``(palette_css, style_css)`` block contents (markers excluded).
    """
    tok = load_script()
    theme = tok.load("paper-green", "editorial")
    return tok.palette_css(theme), tok.style_css(theme)


def build(name: str, out_dir: Path = ANCHOR_DIR) -> Path:
    """Assemble one anchor deck.

    Args:
        name: Key in ``ANCHORS`` (also the file stem).
        out_dir: Folder to write ``<name>.html`` into.

    Returns:
        The written file.
    """
    title, subtitle, slides, deck_css = ANCHORS[name]
    out = out_dir / f"{name}.html"
    assemble(out, slides=slides, title=title, subtitle=subtitle, css=deck_css)
    palette, style = theme_blocks()
    src = out.read_text(encoding="utf-8")
    for block_name, css in (("COMPONENTS", COMPONENTS), ("PALETTE", palette), ("STYLE", style)):
        src = fill(src, block_name, css)
    out.write_text(src, encoding="utf-8")
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
