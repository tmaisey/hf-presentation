/* Optional engine module: narration. Triggers: .narration .narr-tile
   Narration tiles: div.narration > article.narr-tile[data-at], step-only elements the core shows at exactly
   their step (1–2 per step). This module places each step's tiles in free space in the column before they
   enter: staggered widths and left offsets (a pair leans apart; seeded per slide + step, so every load
   matches), centred on what the step reveals, clear of any title, kicker or fixed chrome the column runs
   beside, and clear of tiles still leaving when there is room. Tiles never soften the slide.
   Contract: architecture/ARCHITECTURE.md §9. DOM via style only. */
(() => {
  'use strict';
  let api = null;
  const GAP = 16;
  // column-relative boxes the tiles keep out of: the slide's titles/kickers, and the fixed chrome as it
  // sits when this slide is current (its top at the viewport's top)
  function keepOut(s, col) {
    const cr = col.getBoundingClientRect(), sr = s.node.getBoundingClientRect(), dy = cr.top - sr.top;
    const own = api.$$(':scope > .title, :scope > .kicker', s.node).map(e => e.getBoundingClientRect())
      .filter(r => r.height).map(r => ({ l: r.left, r: r.right, t: r.top - cr.top, b: r.bottom - cr.top }));
    const chrome = api.$$('.bar, .notes-btn').map(e => e.getBoundingClientRect())
      .filter(r => r.height).map(r => ({ l: r.left, r: r.right, t: r.top - dy, b: r.bottom - dy }));
    return [...own, ...chrome].filter(q => q.l < cr.right && q.r > cr.left);
  }
  function placeTiles(s, k, col, now) {
    const W = col.clientWidth, H = col.clientHeight, cr = col.getBoundingClientRect();
    // free band: below anything over the column's upper half, above anything over its lower half
    let lo = 0, hi = H;
    keepOut(s, col).forEach(q => { if ((q.t + q.b) / 2 < H / 2) lo = Math.max(lo, q.b + GAP); else hi = Math.min(hi, q.t - GAP); });
    const rnd = api.seeded([...s.id].reduce((h, c) => (h * 31 + c.charCodeAt(0)) | 0, k + 1));
    const pair = now.length > 1;
    const gaps = now.map((t, j) => (j ? Math.max(GAP, H * (.03 + .03 * rnd())) : 0));
    const lay = full => now.map((t, j) => {
      const w = full ? W : W * (pair ? .8 + .08 * rnd() : .82 + .14 * rnd()), slack = W - w;
      const x = full ? 0 : pair ? (j % 2 ? slack * .2 * rnd() : slack * (.7 + .3 * rnd())) : slack * rnd();
      t.style.width = `${w}px`; t.style.left = `${x}px`;
      return t.offsetHeight;
    });
    let hs = lay(false), total = hs.reduce((a, h, j) => a + h + gaps[j], 0);
    if (total > hi - lo) { hs = lay(true); total = hs.reduce((a, h, j) => a + h + gaps[j], 0); }   // full width: fewer lines
    // focus: the slide parts this step reveals, else the latest revealed so far, else the band's upper middle
    const shown = api.$$('[data-show-at]', s.node).filter(e => !e.closest('.narration, .popover, aside.note') && +e.dataset.showAt <= k);
    const latest = Math.max(0, ...shown.map(e => +e.dataset.showAt));
    const rects = shown.filter(e => +e.dataset.showAt === latest).map(e => e.getBoundingClientRect()).filter(r => r.height);
    const fy = rects.length ? (Math.min(...rects.map(r => r.top)) + Math.max(...rects.map(r => r.bottom))) / 2 - cr.top : lo + (hi - lo) * .4;
    const fit = y => api.clamp(y, lo, Math.max(lo, hi - total));
    let top = fit(fy - total / 2);
    // clear of outgoing tiles, so blurred and sharp tiles don't stack
    const out = api.$$('.narr-tile.is-shown', col).filter(t => !now.includes(t)).map(t => [t.offsetTop, t.offsetTop + t.offsetHeight]);
    const clash = y => out.some(([a, b]) => y < b && y + total > a);
    if (clash(top)) {
      const alt = out.flatMap(([a, b]) => [a - GAP - total, b + GAP]).filter(y => y >= lo && y + total <= hi && !clash(y));
      if (alt.length) top = alt.sort((p, q) => Math.abs(p - top) - Math.abs(q - top))[0];
    }
    now.forEach((t, j) => { top += gaps[j]; t.style.top = `${top}px`; top += hs[j]; });
  }
  const tilesAt = (col, k) => api.$$('.narr-tile', col).filter(t => +t.dataset.at === k);

  (window.deckModules = window.deckModules || []).push({
    name: 'narration',
    init(a) {
      api = a;
      // re-place the shown tiles when the viewport changes
      addEventListener('resize', () => {
        if (api.notesOn) return;
        const st = api.state(), s = api.slides[st.index], col = api.$(':scope > .narration', s.node);
        const now = col ? tilesAt(col, st.step) : [];
        if (now.length) placeTiles(s, st.step, col, now);
      });
    },
    place(s, k, ctx) {
      const col = api.$(':scope > .narration', s.node);
      if (!col || !ctx.entering.some(e => col.contains(e))) return;
      placeTiles(s, k, col, tilesAt(col, k));
    },
  });
})();
