/* Core deck engine: discovers every behaviour from data attributes on slide markup and drives any
   slides between the SLIDES markers. Contract: architecture/ARCHITECTURE.md. Builds DOM with
   createElement/cloneNode/textContent only (no HTML strings, no eval), so the file stays
   endpoint-safe. Optional modules register on window.deckModules before this runs (MODULES block). */
(() => {
  'use strict';
  const $ = (sel, root = document) => root.querySelector(sel);
  // a note's data-for: any CSS selector, first match on its slide, else a module's (scene) target;
  // an invalid selector matches nothing, so that note is dropped and the others still work
  const query = (sel, root, other) => { try { return sel ? root.querySelector(sel) || other() : null; } catch (e) { return null; } };
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
  const body = document.body, root = document.documentElement;
  const deckEl = $('.deck');
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  // still = reduced-motion rules (:root.still); instant = notes mode, where every build state lands at its end
  let still = reduce, instant = false;
  root.classList.toggle('still', reduce);
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  // seeded PRNG (mulberry32): the same layout on every load, so screenshots and talks match
  const seeded = seed => () => {
    seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const el = (tag, cls, text) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  };

  // ---------- modules: optional behaviours registered before the engine runs ----------
  const modules = (window.deckModules || []).filter(m => m && typeof m === 'object');
  const hook = (name, ...args) => modules.map(m => typeof m[name] === 'function' ? m[name](...args) : undefined);

  // ---------- slide model: a slide's step count = max data-show-at / data-at on it ----------
  const slides = $$('section.slide', deckEl).map(node => ({
    node,
    id: node.id,
    chapter: node.dataset.chapter || '',
    steps: Math.max(0, ...$$('[data-show-at],[data-at]', node).map(e => +(e.dataset.showAt ?? e.dataset.at) || 0)),
  }));
  let cur = 0, step = 0, lastEngineScroll = 0;

  // ---------- title bar: agenda derived from slides' data-chapter ----------
  const bar = $('.bar'), barTitle = $('.bar-title'), nav = $('.nav'), navCurrent = $('.nav-current');
  const agenda = $('.agenda'), progress = $('.progress'), barHome = $('.bar-home');
  const chapters = [...new Set(slides.map(s => s.chapter))];
  const agendaItems = agenda ? chapters.map(ch => {
    const li = el('li'); li.dataset.chapter = ch;
    const b = el('button', null, ch); b.type = 'button';
    b.addEventListener('click', e => {
      e.stopPropagation(); b.blur(); nav.classList.remove('is-open');
      show(slides.findIndex(s => s.chapter === ch), 0);
    });
    li.append(b); agenda.append(li);
    return li;
  }) : [];
  // the deck title links home: click, Enter or Space; Space must not also step the deck
  if (barHome) {
    if (slides[0] && slides[0].id) barHome.setAttribute('href', `#${slides[0].id}`);
    barHome.addEventListener('click', e => { e.preventDefault(); barHome.blur(); show(0, 0); });
    barHome.addEventListener('keydown', e => {
      if (e.key !== ' ') return;
      e.preventDefault(); e.stopPropagation(); show(0, 0);
    });
  }
  // the compact list also opens on click (touch, click-first presenters); an outside click only closes it
  if (navCurrent) navCurrent.addEventListener('click', e => { e.stopPropagation(); nav.classList.toggle('is-open'); });
  addEventListener('click', e => {
    if (!nav || !nav.classList.contains('is-open') || nav.contains(e.target)) return;
    nav.classList.remove('is-open'); e.stopPropagation();
  }, true);
  // compact only when the full row would come within NAV_MIN_GAP of the title: measured, not a breakpoint
  const NAV_MIN_GAP = 32;
  function fitNav() {
    if (!bar || !agenda || !barTitle) return;
    bar.classList.remove('bar--compact');
    const free = bar.clientWidth - parseFloat(getComputedStyle(bar).paddingRight) - barTitle.getBoundingClientRect().right;
    bar.classList.toggle('bar--compact', agenda.scrollWidth + NAV_MIN_GAP > free);
  }
  addEventListener('resize', fitNav);
  if (document.fonts) document.fonts.ready.then(fitNav);
  function updateChrome() {
    const ci = chapters.indexOf(slides[cur].chapter);
    agendaItems.forEach((li, k) => {
      li.classList.toggle('is-current', k === ci); li.classList.toggle('is-done', k < ci);
      li.firstChild.toggleAttribute('aria-current', k === ci);
    });
    if (navCurrent && navCurrent.firstElementChild) navCurrent.firstElementChild.textContent = chapters[ci];
    const s = slides[cur], frac = s.steps ? step / (s.steps + 1) : 0;
    if (progress) progress.style.width = `${clamp((cur + frac) / Math.max(1, slides.length - 1), 0, 1) * 100}%`;
  }

  // ---------- step-only elements ([data-at]): overlays and module tiles ----------
  const exitTimers = new WeakMap();
  function setShown(o, on, delayed) {
    if (o.classList.contains('is-shown') === on) return;
    o.classList.toggle('is-shown', on);
    o.classList.toggle('is-delayed', on && !!delayed);   // a newcomer waits for the outgoing element's exit
    clearTimeout(exitTimers.get(o));
    if (on) o.classList.remove('was-shown');            // entry rises from below
    else {
      o.classList.add('was-shown');                     // exit leaves in place
      if (o.contains(document.activeElement)) document.activeElement.blur();
      exitTimers.set(o, setTimeout(() => o.classList.remove('was-shown'), 900));
    }
  }

  // ---------- render one slide at a step ----------
  function render(s, k, quiet) {
    $$('[data-show-at], [data-hide-at]', s.node).forEach(e => e.classList.toggle('is-visible',
      k >= (+e.dataset.showAt || 0) && !(e.dataset.hideAt && k >= +e.dataset.hideAt)));
    // step lists: the latest revealed item is current, earlier ones done
    $$('.steps', s.node).forEach(list => {
      const items = [...list.children].filter(li => li.dataset.showAt);
      let at = -1;
      items.forEach((li, j) => { if (k >= +li.dataset.showAt) at = j; });
      items.forEach((li, j) => { li.classList.toggle('is-current', j === at); li.classList.toggle('is-done', j < at); });
    });
    // [data-at] shows at exactly its step, never in notes mode (quiet); an .overlay softens the slide
    const only = $$('[data-at]', s.node).map(o => [o, !quiet && k === +o.dataset.at]);
    const leaving = only.some(([o, on]) => !on && o.classList.contains('is-shown'));
    const entering = only.filter(([o, on]) => on && !o.classList.contains('is-shown')).map(([o]) => o);
    const ctx = { quiet: !!quiet, current: s === slides[cur], entering, instant, still };
    if (entering.length) hook('place', s, k, ctx);       // modules may position newcomers before they show
    only.forEach(([o, on]) => setShown(o, on, leaving));
    const overlaid = only.some(([o, on]) => on && o.classList.contains('overlay')) || hook('overlaid', s, k, ctx).some(Boolean);
    s.node.classList.toggle('is-overlaid', overlaid);
    hook('render', s, k, ctx);
    if (instant) settle();
  }
  // notes mode: finish any transition or entrance still under way, so the target is drawn at once
  // (ambient drift is script-driven and keeps moving)
  function settle() {
    deckEl.getAnimations({ subtree: true }).forEach(a => {
      const t = a.effect && a.effect.getComputedTiming();
      if (t && Number.isFinite(t.endTime)) a.finish();
    });
    hook('settle');
  }

  // ---------- navigation: one input = one step; a slide is left only after its last step ----------
  function scrollToSlide(i, now) {
    lastEngineScroll = performance.now();
    deckEl.scrollTo({ top: slides[i].node.offsetTop, behavior: now || still ? 'instant' : 'smooth' });
  }
  function show(i, k, now) {
    i = clamp(i, 0, slides.length - 1);
    const s = slides[i];
    k = clamp(k | 0, 0, s.steps);
    const moved = i !== cur;
    cur = i; step = k;
    slides.forEach((x, j) => x.node.classList.toggle('is-active', j === i));
    render(s, k, notes.on);
    if (moved || now) scrollToSlide(i, now);
    updateChrome();
    if (notes.on && moved) notes.load();
  }
  function next() {
    if (step < slides[cur].steps) show(cur, step + 1);
    else if (cur < slides.length - 1) show(cur + 1, 0);
  }
  function prev() {
    if (step > 0) show(cur, step - 1);
    else if (cur > 0) show(cur - 1, slides[cur - 1].steps);
  }
  function goto(id, k = 0) {
    const i = slides.findIndex(s => s.id === id);
    if (i >= 0) show(i, k, true);
  }

  // ---------- ambient hook: a seeded layer of orbs in three depth planes on data-ambient slides ----------
  // The engine places and drifts the orbs (active slide only, with slight mouse parallax); their look
  // (blur, colour, opacity per plane) is the style layer's. Never built or moved under reduced motion's drift.
  const orbs = [];
  const PLANES = [['far', 5, 340, 560, .015, 12], ['mid', 6, 120, 240, .035, 32], ['near', 6, 30, 80, .07, 53]];
  slides.filter(s => s.node.hasAttribute('data-ambient')).forEach((s, n) => {
    const rnd = seeded(101 + n), r = (a, b) => a + rnd() * (b - a);
    const layer = el('div', 'ambient'); layer.setAttribute('aria-hidden', 'true');
    PLANES.forEach(([plane, count, lo, hi, z, amp]) => {
      for (let i = 0; i < count; i++) {
        const o = el('div', `orb orb--${plane} orb--${(i % 5) + 1}`), size = r(lo, hi);
        Object.assign(o.style, { width: `${size}px`, height: `${size}px`, left: `${r(40, 100)}%`, top: `${r(0, 90)}%` });
        layer.append(o);
        orbs.push({ o, slide: s, z: z * 600, amp, ph: r(0, 6.28) });
      }
    });
    s.node.prepend(layer);
  });
  if (!reduce && orbs.length) {
    let mx = 0, my = 0;
    addEventListener('mousemove', e => { mx = e.clientX / innerWidth - .5; my = e.clientY / innerHeight - .5; });
    const frame = t => {
      const active = slides[cur];
      orbs.forEach(({ o, slide, z, amp, ph }) => {
        if (slide !== active) return;
        const dx = Math.sin(t / 4000 + ph) * amp, dy = Math.cos(t / 4870 + ph * 1.3) * amp * .8;
        o.style.transform = `translate(${mx * z + dx}px, ${my * z + dy}px)`;
      });
      requestAnimationFrame(frame);
    };
    requestAnimationFrame(frame);
  }

  // ---------- diagram kit: --k scale, centred tile text, gapped edges ----------
  const num = (e, a) => parseFloat(e.getAttribute(a)) || 0;
  const boxOf = (svg, sel) => {
    const g = $(sel, svg), rc = g && (g.tagName === 'rect' ? g : $('rect', g));
    return rc && { x: num(rc, 'x'), y: num(rc, 'y'), w: num(rc, 'width'), h: num(rc, 'height') };
  };
  // --k = SVG units per screen px, so later layers' screen-size floors hold however small the diagram is drawn
  function scaleDiagram(svg) {
    const vb = svg.viewBox.baseVal, r = svg.getBoundingClientRect();
    if (!vb || !vb.width || !r.width) return;
    const sc = Math.min(r.width / vb.width, r.height / vb.height || Infinity);
    svg.style.setProperty('--k', (1 / sc).toFixed(4));
  }
  function layoutDiagram(svg) {
    scaleDiagram(svg);
    // tile text: all lines centred as one block in the rect; tiles sharing a row (same y and height)
    // share one block height, so their titles line up; a .tile--centred tile centres its own block
    const tiles = $$('.tile', svg).map(t => {
      const rc = $('rect', t), lines = $$('text', t);
      const b = rc && { x: num(rc, 'x'), y: num(rc, 'y'), w: num(rc, 'width'), h: num(rc, 'height') };
      return b && lines.length && { b, lines, own: t.classList.contains('tile--centred'),
        lh: lines.map(l => (parseFloat(getComputedStyle(l).fontSize) || 20) * 1.3) };
    }).filter(Boolean);
    const rowH = {}, sum = lh => lh.reduce((a, c) => a + c, 0);
    tiles.forEach(({ b, lh, own }) => { const key = b.y + ':' + b.h; if (!own) rowH[key] = Math.max(rowH[key] || 0, sum(lh)); });
    tiles.forEach(({ b, lines, lh, own }) => {
      let y = b.y + b.h / 2 - (own ? sum(lh) : rowH[b.y + ':' + b.h]) / 2;
      lines.forEach((l, k) => { l.setAttribute('x', b.x + b.w / 2); l.setAttribute('y', y + lh[k] / 2); y += lh[k]; });
    });
    // edges: a gapped straight or curved connector between two tiles' rects
    const GAP = 12;
    $$('.edge[data-from][data-to]', svg).forEach(p => {
      const a = boxOf(svg, p.dataset.from), b = boxOf(svg, p.dataset.to);
      if (!a || !b) return;
      const ac = [a.x + a.w / 2, a.y + a.h / 2], bc = [b.x + b.w / 2, b.y + b.h / 2];
      const dx = bc[0] - ac[0], dy = bc[1] - ac[1];
      let d;
      if (Math.abs(dx) >= Math.abs(dy)) {
        const sx = dx > 0 ? a.x + a.w + GAP : a.x - GAP, ex = dx > 0 ? b.x - GAP : b.x + b.w + GAP, mx = (sx + ex) / 2;
        d = ac[1] === bc[1] ? `M${sx},${ac[1]} H${ex}` : `M${sx},${ac[1]} C${mx},${ac[1]} ${mx},${bc[1]} ${ex},${bc[1]}`;
      } else {
        const sy = dy > 0 ? a.y + a.h + GAP : a.y - GAP, ey = dy > 0 ? b.y - GAP : b.y + b.h + GAP, my = (sy + ey) / 2;
        d = ac[0] === bc[0] ? `M${ac[0]},${sy} V${ey}` : `M${ac[0]},${sy} C${ac[0]},${my} ${bc[0]},${my} ${bc[0]},${ey}`;
      }
      p.setAttribute('d', d);
    });
  }
  const diagrams = $$('svg.diagram', deckEl);
  diagrams.forEach(layoutDiagram);
  if (document.fonts) document.fonts.ready.then(() => diagrams.forEach(layoutDiagram));
  addEventListener('resize', () => diagrams.forEach(layoutDiagram));

  // ---------- links: every cited source opens in a new tab ----------
  $$('a[href]', deckEl).forEach(a => { a.target = '_blank'; a.rel = 'noopener'; });

  // ---------- reader notes: veil + spotlight window, numbered pins, callout, static notes bar ----------
  const veil = $('.veil'), ring = $('.ring'), callout = $('.callout'), pos = $('.notes-pos'), notesBtn = $('.notes-btn');
  const notesNav = $('.notes-nav');
  // steps [lo, hi) at which an element and its ancestors are revealed (data-show-at / data-hide-at)
  function shownRange(e, slideNode) {
    let lo = 0, hi = Infinity;
    for (; e && e !== slideNode; e = e.parentElement) {
      if (e.dataset && e.dataset.showAt) lo = Math.max(lo, +e.dataset.showAt);
      if (e.dataset && e.dataset.hideAt) hi = Math.min(hi, +e.dataset.hideAt);
    }
    return [lo, hi];
  }
  // a module may resolve a note target outside the slide, give its step range, or frame it (first answer wins)
  const first = (name, ...args) => hook(name, ...args).find(v => v != null);
  // notes mode's instant build states: the reduced-motion rules plus zero-length motion
  function setInstant(on) {
    instant = on; still = reduce || on;
    root.classList.toggle('still', still);
    root.classList.toggle('instant', on);
    hook('instant', on, still);
  }

  const notes = {
    on: false, list: [], pins: [], idx: 0, saved: null, sig: '', shift: 0,
    set(on) {
      if (on === notes.on || !callout) return;
      notes.on = on;
      body.classList.toggle('notes-on', on);
      if (notesBtn) notesBtn.setAttribute('aria-pressed', String(on));
      if (on) {
        notes.saved = { slide: cur, step };
        setInstant(true);
        show(cur, slides[cur].steps);                 // everything revealed, step-only elements suppressed
        notes.load();
        requestAnimationFrame(notes.track);
      } else {
        notes.clear();
        if (notes.saved && notes.saved.slide === cur) show(cur, notes.saved.step);
        else render(slides[cur], step, false);
        setInstant(false);   // the return to the presenter's step lands at once too; motion resumes from here
      }
    },
    clear() {
      notes.pins.forEach(p => p.remove());
      notes.pins = []; notes.list = [];
      body.classList.remove('notes-focus');
      notes.shift = 0; root.style.removeProperty('--notes-shift');
      callout.classList.remove('fade-t', 'fade-b');
    },
    // a callout scrolling inside itself marks each edge with more to read
    fade() {
      const more = callout.scrollHeight - callout.clientHeight;
      callout.classList.toggle('fade-t', more > 1 && callout.scrollTop > 1);
      callout.classList.toggle('fade-b', more > 1 && callout.scrollTop < more - 1);
    },
    load() {
      notes.clear();
      const s = slides[cur], node = s.node;
      if (step !== s.steps) render(s, (step = s.steps), true);
      notes.list = $$('aside.note', node)
        .map(n => ({ n, target: query(n.dataset.for, node, () => first('noteTarget', n.dataset.for, s)) }))
        .filter(x => x.target)
        .map(x => Object.assign(x, { range: first('noteRange', x.target, s) || shownRange(x.target, node) }));
      notes.pins = notes.list.map((x, k) => {
        const b = el('button', 'pin', String(k + 1)); b.type = 'button';
        b.setAttribute('aria-label', ($('h3', x.n) || x.n).textContent);
        b.addEventListener('click', e => { e.stopPropagation(); notes.focus(k); });
        body.append(b);
        return b;
      });
      if (notes.list.length) notes.focus(0);
      else if (pos) pos.textContent = 'No notes on this slide';
    },
    focus(k) {
      const n = notes.list.length;
      if (!n) return;
      notes.idx = (k + n) % n;
      // show the slide at the last step where this note's target is on screen
      const s = slides[cur], [lo, hi] = notes.list[notes.idx].range;
      const at = Math.min(s.steps, hi - 1) >= lo ? Math.min(s.steps, hi - 1) : s.steps;
      if (at !== step) { step = at; render(s, at, true); updateChrome(); }
      notes.list.forEach((x, j) => notes.pins[j].classList.toggle('is-offstage', step < x.range[0] || step >= x.range[1]));
      const src = notes.list[notes.idx].n;
      const parts = [...src.children].filter(c => !c.matches('a.src')).map(c => c.cloneNode(true));
      const cite = el('p', 'cite', 'Source · ');
      $$('a.src', src).forEach((a, j) => {
        const c = a.cloneNode(true); c.target = '_blank'; c.rel = 'noopener';
        if (j) cite.append(' · ');
        cite.append(c);
      });
      callout.replaceChildren(...parts, ...($('a.src', src) ? [cite] : []));
      if (pos) pos.textContent = `${notes.idx + 1} / ${n}`;
      notes.pins.forEach((p, j) => p.classList.toggle('is-current', j === notes.idx));
      body.classList.add('notes-focus');
      notes.sig = '';
      notes.place();
    },
    place() {
      const pad = 14, barB = bar ? bar.getBoundingClientRect().bottom : 0, top = barB + 12;
      const target = notes.list[notes.idx].target;
      // a target whose window would run into the static notes bar's line is scrolled clear: the slide shifts
      // up just enough, never lifting the target's top under the title bar. Measured unshifted (current shift
      // added back), so re-placing each frame is stable.
      const navT = (notesNav ? notesNav.offsetTop : innerHeight) - 8, r0 = target.getBoundingClientRect();
      const u = { top: r0.top + notes.shift, bottom: r0.bottom + notes.shift };
      const shift = Math.max(0, Math.min(u.bottom + pad - navT, u.top - pad - barB - 4));
      if (shift !== notes.shift) { notes.shift = shift; root.style.setProperty('--notes-shift', `${shift}px`); }
      const r = target.getBoundingClientRect();
      // spotlight window: the target plus pad, each edge pulled in to clip cleanly between the target and any
      // neighbouring line of slide text the pad would show as a sliver
      let wl = r.left - pad, wt = r.top - pad, wr = r.right + pad, wb = r.bottom + pad;
      const lines = notes.textLines(slides[cur].node, target, r);
      for (let pass = 0, moved = true; moved && pass < 6; pass++) {
        moved = false;
        lines.forEach(q => {
          if (q.right <= wl + 1 || q.left >= wr - 1 || q.bottom <= wt + 1 || q.top >= wb - 1) return;   // outside
          if (q.left >= wl - 1 && q.right <= wr + 1 && q.top >= wt - 1 && q.bottom <= wb + 1) return;   // inside
          moved = true;
          if (q.bottom <= r.top + 2) wt = Math.min(r.top, (q.bottom + r.top) / 2 + 1);
          else if (q.top >= r.bottom - 2) wb = Math.max(r.bottom, (q.top + r.bottom) / 2 - 1);
          else if (q.right <= r.left + 2) wl = Math.min(r.left, (q.right + r.left) / 2 + 1);
          else wr = Math.max(r.right, (q.left + r.right) / 2 - 1);
        });
      }
      const x = wl, y = wt, w = wr - wl, h = wb - wt;
      if (veil) {
        veil.style.setProperty('--x', `${x}px`); veil.style.setProperty('--y', `${y}px`);
        veil.style.setProperty('--w', `${w}px`); veil.style.setProperty('--h', `${h}px`);
      }
      if (ring) Object.assign(ring.style, { left: `${x}px`, top: `${y}px`, width: `${w}px`, height: `${h}px` });
      // callout: below the window, else above, else right, else left, wherever it fits whole (narrowing to
      // MINW beside a wide target); else the first side where a wider callout (to WIDE) fits whole; if none,
      // the side with the most height, and the callout scrolls inside itself. Never over the window, under
      // the title bar or over the static notes bar (offsetTop: its transform doesn't count).
      const floor = (notesNav ? notesNav.offsetTop : innerHeight) - 12, L = 16, RX = innerWidth - 16, gap = 18, MINW = 300, WIDE = 640;
      const W = Math.min(440, innerWidth * .86);
      const natural = cw => { callout.style.width = `${cw}px`; callout.style.maxHeight = 'none'; return callout.offsetHeight; };
      const sides = [
        { side: 'below', l: L, r: RX, t: y + h + gap, b: floor },
        { side: 'above', l: L, r: RX, t: top, b: y - gap },
        { side: 'right', l: x + w + gap, r: RX, t: top, b: floor },
        { side: 'left', l: L, r: x - gap, t: top, b: floor },
      ].map(a => Object.assign(a, { cw: Math.min(W, a.r - a.l), ah: a.b - a.t })).filter(a => a.cw >= Math.min(MINW, W) && a.ah >= 120);
      sides.forEach(a => { a.ch = natural(a.cw); });
      const widened = () => sides.find(a => {
        const w2 = Math.min(WIDE, a.r - a.l);
        if (w2 <= a.cw) return false;
        const h2 = natural(w2);
        return h2 <= a.ah && Object.assign(a, { cw: w2, ch: h2 });
      });
      const pick = sides.find(a => a.ch <= a.ah) || widened() || sides.slice().sort((p, q) => q.ah - p.ah)[0]
        || { side: 'below', l: L, r: RX, t: top, b: floor, cw: W, ah: floor - top, ch: natural(W) };   // last resort
      const cw = pick.cw, ch = Math.min(pick.ch, pick.ah);
      callout.style.width = `${cw}px`; callout.style.maxHeight = `${pick.ah}px`;
      let cx, cy;
      if (pick.side === 'below' || pick.side === 'above') { cx = clamp(x, L, RX - cw); cy = pick.side === 'below' ? pick.t : pick.b - ch; }
      else { cx = pick.side === 'right' ? pick.l : pick.r - cw; cy = clamp(y, top, floor - ch); }
      callout.style.left = `${cx}px`; callout.style.top = `${cy}px`;
      notes.fade();
      // pins sit just outside each target's top-right corner; pins the callout would cover hide; other pins keep
      // off the focus frame (nearest free spot just outside it, or hide). A module may give a larger frame for a
      // target (noteFrame), whose box then clips the pins it covers. The current pin stays on top.
      const R = 20, near = 44, inFrame = (px, py) => px > x - R && px < x + w + R && py > y - R && py < y + h + R;
      const underCallout = (px, py) => px > cx - 15 && px < cx + cw + 15 && py > cy - 15 && py < cy + ch + 15;
      const fr = first('noteFrame', target);
      const hole = fr && { l: Math.min(fr.left, x), t: Math.min(fr.top, y), r: Math.max(fr.right, x + w), b: Math.max(fr.bottom, y + h) };
      notes.list.forEach((t, j) => {
        const b = t.target.getBoundingClientRect(), pin = notes.pins[j];
        let px = clamp(b.right + 6, 20, innerWidth - 20), py = clamp(b.top - 6, top + 4, innerHeight - 20), hidden = false;
        if (j !== notes.idx && !hole && inFrame(px, py)) {
          const spots = [[px, y - R], [px, y + h + R], [x - R, py], [x + w + R, py]]
            .filter(([qx, qy]) => qx >= 20 && qx <= innerWidth - 20 && qy >= top + 4 && qy <= innerHeight - 20 && !underCallout(qx, qy))
            .map(([qx, qy]) => [qx, qy, Math.hypot(qx - px, qy - py)]).sort((p, q) => p[2] - q[2]);
          if (spots.length && spots[0][2] <= near) [px, py] = spots[0]; else hidden = true;
        }
        Object.assign(pin.style, { left: `${px}px`, top: `${py}px` });
        const cut = j !== notes.idx && hole && px + R > hole.l && px - R < hole.r && py + R > hole.t && py - R < hole.b;
        pin.style.clipPath = cut ? (() => {
          const ox = px - 15, oy = py - 15, l = hole.l - ox, tp = hole.t - oy, rr = hole.r - ox, bt = hole.b - oy;
          return `polygon(evenodd, -10px -10px, 40px -10px, 40px 40px, -10px 40px, -10px -10px, ${l}px ${tp}px, ${rr}px ${tp}px, ${rr}px ${bt}px, ${l}px ${bt}px, ${l}px ${tp}px)`;
        })() : '';
        pin.classList.toggle('is-covered', j !== notes.idx && (hidden || underCallout(px, py)));
      });
    },
    // boxes of every visible line of the slide's text outside the target and not over it (window clipping)
    textLines(node, target, r) {
      const out = [], seen = new Map();
      const shown = e => {
        if (seen.has(e)) return seen.get(e);
        const cs = getComputedStyle(e);
        const v = !(cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity < 0.05) && (e === node || shown(e.parentElement));
        seen.set(e, v); return v;
      };
      const walk = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
      for (let n; (n = walk.nextNode());) {
        const p = n.parentElement;
        if (!n.textContent.trim() || target.contains(n) || p.closest('aside.note, .ambient') || !shown(p)) continue;
        const range = document.createRange(); range.selectNodeContents(n);
        for (const q of range.getClientRects())
          if (q.width && q.height && !(q.left < r.right - 2 && q.right > r.left + 2 && q.top < r.bottom - 2 && q.bottom > r.top + 2)) out.push(q);
      }
      return out;
    },
    // geometry re-tracks every frame while open, so reflow never strands the spotlight
    track() {
      if (!notes.on) return;
      if (notes.list.length) {
        const r = notes.list[notes.idx].target.getBoundingClientRect();
        const sig = [r.left, r.top, r.width, r.height, innerWidth, innerHeight, callout.offsetHeight].join();
        if (sig !== notes.sig) { notes.sig = sig; notes.place(); }
      }
      requestAnimationFrame(notes.track);
    },
    slide(delta) {
      const i = clamp(cur + delta, 0, slides.length - 1);
      if (i !== cur) show(i, slides[i].steps);
    },
  };
  if (notesBtn) notesBtn.addEventListener('click', e => { e.stopPropagation(); notesBtn.blur(); notes.set(!notes.on); });
  if (callout) callout.addEventListener('scroll', () => notes.fade(), { passive: true });
  $$('[data-notes]').forEach(b => b.addEventListener('click', e => {
    e.stopPropagation(); b.blur();
    const act = { prev: () => notes.focus(notes.idx - 1), next: () => notes.focus(notes.idx + 1), close: () => notes.set(false) }[b.dataset.notes];
    if (act) act();
  }));

  // ---------- input: one input = one step ----------
  const NEXT = ['ArrowRight', 'ArrowDown', 'PageDown', ' '], PREV = ['ArrowLeft', 'ArrowUp', 'PageUp'];
  addEventListener('keydown', e => {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const k = e.key;
    if (k === 'n' || k === 'N') { notes.set(!notes.on); return; }
    if (notes.on) {
      if (k === 'Escape') notes.set(false);
      else if (k === 'ArrowRight' || k === 'ArrowDown') notes.focus(notes.idx + 1);
      else if (k === 'ArrowLeft' || k === 'ArrowUp') notes.focus(notes.idx - 1);
      else if (k === 'PageDown' || k === ' ') notes.slide(1);
      else if (k === 'PageUp') notes.slide(-1);
      else return;
    } else if (NEXT.includes(k)) next();
    else if (PREV.includes(k)) prev();
    else if (k === 'Home') show(0, 0);
    else if (k === 'End') show(slides.length - 1, 0);
    else return;
    e.preventDefault();
  });
  // wheel: a gesture is a burst of events; only its first event steps
  let wheelAt = -1e9, stepAt = -1e9;
  addEventListener('wheel', e => {
    if (notes.on && callout && callout.contains(e.target)) return;   // a scrolling callout scrolls itself
    e.preventDefault();
    const now = performance.now(), fresh = now - wheelAt > 250;
    wheelAt = now;
    if (notes.on || !fresh || now - stepAt < 400 || Math.abs(e.deltaY) < 4) return;
    stepAt = now;
    if (e.deltaY > 0) next(); else prev();
  }, { passive: false });
  deckEl.addEventListener('click', e => {
    if (notes.on || e.target.closest('a, button') || String(getSelection())) return;
    next();
  });
  // keep position on resize; adopt a slide reached by other scrolling (e.g. keyboard focus)
  addEventListener('resize', () => scrollToSlide(cur, true));
  deckEl.addEventListener('scrollend', () => {
    if (performance.now() - lastEngineScroll < 1200) return;
    const i = Math.round(deckEl.scrollTop / Math.max(1, deckEl.clientHeight));
    if (i !== cur) show(i, 0);
  });

  // ---------- start ----------
  const api = {
    slides, $, $$, el, seeded, clamp, layoutDiagram,
    state: () => ({ slide: slides[cur].id, index: cur, step, steps: slides[cur].steps }),
    show, goto, next, prev, render: (s, k) => render(s, k, notes.on), settle,
    get still() { return still; }, get instant() { return instant; }, get notesOn() { return notes.on; },
  };
  hook('init', api);
  slides.forEach(s => render(s, 0, false));
  if (slides[0]) slides[0].node.classList.add('is-active');
  updateChrome();
  fitNav();
  window.deck = {
    ready: true,
    state: api.state,
    goto, next, prev,
    plan: () => slides.map(s => [s.id, s.steps]),
  };
})();
