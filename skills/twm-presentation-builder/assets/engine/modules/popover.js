/* Optional engine module: popover. Triggers: .popover
   Pop-overs: div.popover[data-show-at][data-hide-at], an illustration on a lifted tile over the slide (and
   any scene) for a step range; the core reveals and hides it. While one is revealed the slide is softened
   (.is-overlaid, which a scene also follows), and in notes mode a pop-over target frames its pins by the
   whole pop-over, so pins behind it are cut where it covers them.
   Contract: architecture/ARCHITECTURE.md §9. Reads state only. */
(() => {
  'use strict';
  (window.deckModules = window.deckModules || []).push({
    name: 'popover',
    overlaid(s) {
      return [...s.node.querySelectorAll('.popover')].some(p => p.classList.contains('is-visible'));
    },
    noteFrame(target) {
      const p = target.closest('.popover');
      return p ? p.getBoundingClientRect() : null;
    },
  });
})();
