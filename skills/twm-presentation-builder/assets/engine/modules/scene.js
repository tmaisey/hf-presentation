/* Optional engine module: scene. Triggers: [data-scene] .scene
   One persistent diagram (div.scene) shared by consecutive data-scene slides. It stays fixed on screen while
   the deck scrolls, fitted to the current slide's div.scene-slot; every scene slide's title reserves the
   tallest scene title's height, so the scene holds one place whatever the title length. Parts show from
   data-scene-at="slide:step" until data-scene-until; data-scene-is adds state classes over a range; the
   camera (g.cam) takes data-camera per slide and step; data-scene="backdrop" freezes and softens the scene
   behind the slide's body. Contract: architecture/ARCHITECTURE.md §9. DOM via classList/style only. */
(() => {
  'use strict';
  let api = null, scene = null, svg = null, cam = null, items = [], states = [];
  // "slide:step" → { sid, n }
  const point = v => { const [sid, n] = (v || '').trim().split(':'); return sid ? { sid, n: +n || 0 } : null; };
  const isScene = s => s.node.hasAttribute('data-scene');
  const isBackdrop = s => s.node.dataset.scene === 'backdrop';
  // has the deck reached point pt when showing slide s at step k?
  const reached = (pt, s, k) => {
    if (!pt) return false;
    const i = api.slides.findIndex(x => x.id === pt.sid), at = api.slides.indexOf(s);
    return i >= 0 && (i < at || (i === at && k >= pt.n));
  };
  const live = (it, s, k) => reached(it.at, s, k) && !reached(it.until, s, k);
  // data-camera="x y scale, step: x y scale, …": the entry with the largest step ≤ k wins (default 0 0 1)
  const cameras = s => (s.node.dataset.camera || '').split(',').map(c => c.trim().match(
    /^(?:(\d+)\s*:\s*)?(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)$/)).filter(Boolean)
    .map(m => ({ k: +(m[1] || 0), v: [+m[2], +m[3], +m[4]] })).sort((a, b) => a.k - b.k);
  function cameraAt(s, k) {
    let from = s, at = k;
    // a backdrop without its own camera keeps the last live scene slide's camera, at that slide's last step
    if (isBackdrop(s) && !s.node.dataset.camera) {
      from = api.slides.slice(0, api.slides.indexOf(s)).reverse().find(x => isScene(x) && !isBackdrop(x));
      if (!from) return [0, 0, 1];
      at = from.steps;
    }
    const hit = cameras(from).filter(c => c.k <= at).pop();
    return hit ? hit.v : [0, 0, 1];
  }
  // one place across scene slides: each scene slide's title reserves the tallest scene title's height
  function syncTitles() {
    const ts = api.slides.filter(isScene).flatMap(x => api.$$(':scope > .title', x.node));
    ts.forEach(t => { t.style.minHeight = ''; });
    const h = Math.max(0, ...ts.map(t => t.offsetHeight));
    ts.forEach(t => { t.style.minHeight = `${h}px`; });
  }
  // fit the fixed scene to the slot's place in its slide (offsets: the slide sits at the viewport's top when current)
  function fit(s) {
    syncTitles();
    const slot = api.$(':scope > .scene-slot', s.node);
    if (!slot) return;
    Object.assign(scene.style, { left: `${slot.offsetLeft}px`, top: `${slot.offsetTop}px`,
      width: `${slot.offsetWidth}px`, height: `${slot.offsetHeight}px` });
    if (svg) api.layoutDiagram(svg);
  }
  const current = () => api.slides[api.state().index];
  const refit = () => { const s = current(); if (scene && s && isScene(s)) fit(s); };

  (window.deckModules = window.deckModules || []).push({
    name: 'scene',
    init(a) {
      api = a;
      scene = a.$('.scene');
      if (!scene) return;
      svg = a.$('svg', scene);
      cam = a.$('.cam', scene);
      // scale about the viewBox centre: with transform-box view-box, origin lengths are user units from 0,0
      const vb = svg && svg.viewBox.baseVal;
      if (cam && vb && vb.width) cam.style.transformOrigin = `${vb.x + vb.width / 2}px ${vb.y + vb.height / 2}px`;
      items = a.$$('[data-scene-at]', scene).map(e => ({ e, at: point(e.dataset.sceneAt), until: point(e.dataset.sceneUntil) }));
      // data-scene-is="name slide:step [slide:step], …" adds .is-<name> from the first point until the second
      states = a.$$('[data-scene-is]', scene).flatMap(e => e.dataset.sceneIs.split(',').map(c => {
        const [name, at, until] = c.trim().split(/\s+/);
        return { e, cls: `is-${name}`, at: point(at), until: point(until) };
      }));
      // a scene point on a slide is a step of that slide
      a.slides.forEach(s => [...items, ...states].forEach(({ at, until }) => [at, until].forEach(pt => {
        if (pt && pt.sid === s.id) s.steps = Math.max(s.steps, pt.n);
      })));
      addEventListener('resize', refit);
      if (document.fonts) document.fonts.ready.then(refit);
    },
    render(s, k, ctx) {
      if (!scene || !ctx.current) return;
      scene.classList.toggle('is-on', isScene(s));
      if (!isScene(s)) return;
      // a part carried on screen by a jump (not at its own point) is settled: the design may skip its entrance
      items.forEach(it => {
        const on = live(it, s, k);
        if (on && !it.e.classList.contains('is-visible')) it.e.classList.toggle('is-settled', !(it.at.sid === s.id && it.at.n === k));
        it.e.classList.toggle('is-visible', on);
      });
      states.forEach(st => st.e.classList.toggle(st.cls, live(st, s, k)));
      scene.classList.toggle('is-soft', s.node.classList.contains('is-overlaid'));   // a pop-over or Insight has focus
      scene.classList.toggle('is-backdrop', isBackdrop(s));
      if (cam) {
        const [x, y, z] = cameraAt(s, k);
        cam.style.transform = `translate(${x}px, ${y}px) scale(${z})`;
      }
      fit(s);
    },
    noteTarget(sel, s) {
      return scene && isScene(s) ? scene.querySelector(sel) : null;
    },
    noteRange(target, s) {
      if (!scene || !scene.contains(target)) return null;
      const host = target.closest('[data-scene-at]');
      if (!host) return [0, Infinity];
      const it = items.find(x => x.e === host);
      let lo = Infinity, hi = Infinity;
      for (let k = 0; k <= s.steps; k++) {
        const on = live(it, s, k);
        if (on && lo === Infinity) lo = k;
        else if (!on && lo !== Infinity) { hi = k; break; }
      }
      return [lo, hi];
    },
  });
})();
