/* Optional engine module: tile-row. Triggers: .body--tiles
   Tile row: div.body--tiles > article.text-tile[data-show-at], a row of equal text tiles (2–4) revealed by
   the core's steps, often over a backdrop scene. The row is measured on the current slide, on resize and
   once fonts load: .is-tight is set when the tiles overflow the row at their natural spacing (measured,
   not a breakpoint), so the layout layer can tighten them.
   Contract: architecture/ARCHITECTURE.md §9. DOM via classList only. */
(() => {
  'use strict';
  let api = null;
  function fit(s) {
    api.$$('.body--tiles', s.node).forEach(row => {
      row.classList.remove('is-tight');
      // layout boxes, not scrollHeight: a tile's entry transform (e.g. rising from below) is not an overflow
      const over = [...row.children].some(t => t.offsetTop + t.offsetHeight > row.clientHeight + 1
        || t.scrollHeight > t.clientHeight + 1);
      row.classList.toggle('is-tight', over);
    });
  }
  const refit = () => { const s = api.slides[api.state().index]; if (s) fit(s); };

  (window.deckModules = window.deckModules || []).push({
    name: 'tile-row',
    init(a) {
      api = a;
      addEventListener('resize', refit);
      if (document.fonts) document.fonts.ready.then(refit);
    },
    render(s, k, ctx) {
      if (ctx.current) fit(s);
    },
  });
})();
