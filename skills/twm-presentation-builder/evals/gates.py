# /// script
# requires-python = ">=3.12"
# dependencies = ["playwright>=1.49", "pytest>=8", "python-pptx>=1.0.2", "lxml>=5"]
# ///
"""Deterministic gate runner: check every in-scope ``D`` criterion and write judge-format verdicts.

Given a run folder and its scope (a deck, its emitted PPTX and/or a deck repo, a profile, the
concerns), it resolves
the profile's ``D`` criteria, checks each one in code, and writes one verdict per unit
(``repeat`` 1, ``unit`` per the criterion's scope: ``deck``, a slide id, ``<slide>/<step>`` or a
spec id) to ``<run>/verdicts/<criterion>_<unit>_r1.json``, the files ``aggregate.py`` reads. It
also writes ``<run>/evidence/gates.json``: what was checked, what is missing and why, and, with a
``.pptx``, ``judge_inputs``: whether each judged PPTX criterion in scope (PX-06) has a renderer
(``soffice``) or why it will be missing.

**Deck checks** open the deck in the system Chrome (Playwright, network blocked) and step every
slide × step × review size through ``window.deck`` with ``scripts/layout_guard.py``'s helpers,
waiting on a settle condition, never a fixed sleep. **PPTX checks** are the PPTX part's own
(``pptx/scripts/check.py`` ``verdicts``), run on the given ``.pptx`` with its scene and emitter
report (default: the sidecars beside it). **Repo checks** read git history only
(``git`` via subprocess, read-only on the target: tests are re-run in throwaway ``git worktree``
checkouts under ``<run>/evidence/worktrees/``, removed afterwards). A self-reported process log
is never read: every process fact comes from commits, the SPEC file at each commit, test runs
and file timestamps. ``coverage()`` lists every ``D`` criterion as checked (with its rule) or
missing (with the reason); a criterion with no rule here gets no verdict, so the report shows it
``missing``.

Usage (from the skill folder)::

    uv run evals/gates.py <run-dir> [--deck deck.html] [--pptx deck.pptx [--scene s.json] [--report r.json]]
        [--repo path] [--profile editorial-talk] [--concerns design-layout,process]
        [--sizes 1920x1080,1280x720,1288x598] [--no-rerun] [--test-cmd "uv run pytest"]

``--profile``/``--concerns`` default to the run's ``manifest.json`` (concerns: all). ``--no-rerun``
skips re-running spec tests (PR-02 is then missing). Exit codes: 0 every verdict passes, 1 any
verdict fails, 2 usage error or unusable input.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

EVAL_DIR = Path(__file__).resolve().parent
SKILL_DIR = EVAL_DIR.parent
SCRIPTS = SKILL_DIR / "scripts"
PPTX_CHECK = SKILL_DIR / "pptx" / "scripts" / "check.py"
CONTRACT_DOCS = (SKILL_DIR / "architecture" / "ARCHITECTURE.md", SKILL_DIR / "design" / "LAYOUT.md")
MAX_EVIDENCE = 12
SPEC_FILE = "docs/SPEC.jsonl"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, mod)
    spec.loader.exec_module(mod)
    return mod


crit_mod = _load("skill_gates_criteria", EVAL_DIR / "criteria.py")
guard_mod = _load("layout_guard", SCRIPTS / "layout_guard.py")
asm_mod = _load("skill_gates_assemble", SCRIPTS / "assemble.py")
tok_mod = _load("skill_gates_tokens", SCRIPTS / "tokens.py")

# ---------- coverage: what each D criterion's check is, or why it has none ----------

CHECKS = {
    "CN-04": "visible words per slide (max over steps, notes excluded) ≤ params.max_words (default 40)",
    "CN-08": "every slide except lead/closing slides has an aside.note with text",
    "RS-05": "every link in notes and slides is https with a real host (no example.com/TODO/#); no 'Source:' text without a link",
    "VC-03": "each title: no trailing full stop, one sentence, ≤ 1 em/i run",
    "VC-05": "each .overlay holds ≤ 3 sentences",
    "DL-01": "layout_guard faults plus pairwise text/tile box collisions and off-canvas boxes, at every size; "
             "deliberate stacks are not collisions: a textless tile with another shape of its own diagram, or a "
             "focus card (overlay, pop-over) over body content (never over a title or chrome)",
    "DL-02": "rendered text px ≥ params.min_px_1920 (20) at ≥ 1920 wide, else ≥ params.min_px_1280 (15); labels "
             "(uppercase and tracked ≥ .05em, or a .cite/.quote-from source line) ≥ params.min_label_px_1920 (18) "
             "/ params.min_label_px_1280 (12)",
    "DL-09": "bar, agenda and notes button keep their box (±1 px) between consecutive slides",
    "DL-10": "every connector ends ≥ 0.5 units clear of both tiles; markers orient=auto with refY centred",
    "DP-01": "WCAG 2 ratio of each visible text run against its composited background (4.5, large 3), unrounded; "
             "never-text palette roles used as text fail; text softened (blurred) beneath a focus layer is skipped",
    "DP-02": "unsoftened connector strokes ≥ 3:1 against the diagram's composited background",
    "DP-03": "no hex/rgb()/hsl()/oklch()/lab()/lch() colour literal outside the PALETTE block",
    "DS-01": "≤ 2 primary font families, each declared in --sys-font-*; every size on the --sys-type-*/--comp-* size "
             "scale (diagram text: rendered size on the scale, or its SVG size on a --comp-*-floor)",
    "DS-03": "ambient layer only on lead or build-free, diagram-free slides; no other looping animation; reduced motion stops all drift",
    "DS-07": "no visible link (slide or notes callout) in the browser's default link colours",
    "AR-01": "network blocked: no external request, no failed resource, no console error; no external reference in the source",
    "AR-02": "assemble.endpoint_faults finds nothing",
    "AR-03": "keyboard (→ then ←) reaches every slide × step in order both ways; each state renders the same both ways and via goto",
    "AR-04": "no <style>, <script>, style= or on*= inside slide sections",
    "AR-05": "one non-empty, unique title per slide; no DOM-later block sits above an earlier one in the same column",
    "AR-06": "every img has alt; every slide svg/role=img has an accessible name (aria-label, labelledby or <title>)",
    "AR-07": "every class and data-* attribute in slide markup is named in the skill contract or the repo's docs",
    "PR-01": "the spec's last cycle has a commit flipping it to build that adds its Spec-marked tests and no implementation (test config allowed), before the done flip",
    "PR-02": "spec tests re-run in a worktree: every new test fails on an assertion at red (no errors), and the spec's tests pass at done",
    "PR-03": "every doc (.md) added or removed in the spec's commits lands with an index change naming it; every touched doc is indexed",
    "PR-04": "a spec whose commits change the deck has shots <slide>-<step>-<WxH>.png for every changed slide × step × review size, dated within the spec's red..done window",
    "PR-09": "no commit adds a skip/xfail decorator, call or module mark to a test file that runs the layout guard",
}
MISSING = {
    "DP-05": "needs a second shipped palette to swap to; only one palette ships (add the check with the second theme)",
}


def pptx_rules() -> dict[str, str]:
    """Read the PPTX checks' criteria and rules from ``pptx/scripts/check.py`` without importing it.

    Returns:
        ``{criterion: rule}`` for each id in its ``CRITERIA`` (the rule from its docstring table).
    """
    if not PPTX_CHECK.is_file():
        return {}
    tree = ast.parse(PPTX_CHECK.read_text(encoding="utf-8"))
    ids = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
               and any(getattr(t, "id", "") == "CRITERIA" for t in n.targets))
    doc, out = ast.get_docstring(tree) or "", {}
    for cid in ids:
        m = re.search(rf"^{cid}\s+(.+(?:\n {{12}}.+)*)", doc, re.M)
        out[cid] = "pptx/scripts/check.py: " + (" ".join(m.group(1).split()) if m else "see its rule table")
    return out

FLAW = {  # flaw tag(s) a failure carries, from each criterion's own taxonomy
    "CN-04": ["excessive-text-density"], "CN-08": ["missing-note"], "RS-05": ["broken-link"],
    "VC-03": ["title-form"], "VC-05": ["overlong-overlay"], "DL-02": ["inappropriate-font-sizing"],
    "DL-09": ["unstable-placement"], "DL-10": ["misaligned-arrowhead"], "DP-01": ["insufficient-contrast"],
    "DP-02": ["insufficient-contrast"], "DP-03": ["hardcoded-colour"], "DS-01": ["inconsistent-text-styling"],
    "DS-03": ["distracting-animation"], "DS-07": ["inconsistent-text-styling"], "AR-01": ["external-dependency"],
    "AR-02": ["endpoint-risk"], "AR-03": ["unreachable-step"], "AR-04": ["per-slide-styling"],
    "AR-06": ["missing-alt-text"], "AR-07": ["undocumented-contract"], "PR-01": ["green-before-red"],
    "PR-02": ["false-red"], "PR-03": ["stale-docs"], "PR-04": ["unlooked-screenshots"],
    "PR-09": ["disabled-guard"],
}


def coverage(library: dict | None = None) -> dict[str, dict]:
    """Say, for every ``D`` criterion in the library, how it is checked or why it is not.

    Args:
        library: Output of ``criteria.load_library`` (default: the shipped library).

    Returns:
        ``{criterion: {"checked": rule}}`` or ``{criterion: {"missing": reason}}``.
    """
    library = library or crit_mod.load_library(EVAL_DIR)
    out = {}
    for cid, c in library.items():
        if c["evidence"] != "D":
            continue
        if c["target"] == "pptx":
            rule = pptx_rules().get(cid)
            out[cid] = {"checked": rule} if rule else {"missing": "no PPTX check implements it"}
        elif cid in CHECKS:
            out[cid] = {"checked": CHECKS[cid]}
        else:
            out[cid] = {"missing": MISSING.get(cid, "no deterministic rule implemented")}
    return out


# ---------- verdicts ----------

def _verdict(crit: dict, unit: str, bad: list[dict], ok_note: dict, rule: str, flaws=None) -> dict:
    """Build one verdict: fail when ``bad`` holds evidence items, else pass with ``ok_note``."""
    fail = bool(bad)
    ev = bad[:MAX_EVIDENCE] if fail else [ok_note]
    if fail and len(bad) > MAX_EVIDENCE:
        ev[-1] = dict(ev[-1], note=ev[-1]["note"] + f" (+{len(bad) - MAX_EVIDENCE} more)")
    rationale = (f"Gate rule: {rule}. " + (f"{len(bad)} finding(s) break it." if fail else "No finding breaks it."))
    tags = [t for t in (flaws or FLAW.get(crit["id"], [])) if t in crit["flaws"]] or crit["flaws"][:1]
    return {"criterion": crit["id"], "unit": unit, "repeat": 1, "evidence": ev,
            "rationale": rationale[:600], "flaws": tags if fail else [], "result": "fail" if fail else "pass"}


def _slug(unit: str) -> str:
    return re.sub(r"[^A-Za-z0-9-]+", "-", unit).strip("-")


# ---------- deck: in-page probes ----------

# One rendered state of the current slide: text runs (colour, composited background, size,
# family), layout boxes, connectors, links, chrome boxes, ambient drift inputs and a state signature.
PROBE = r"""(id) => {
  const s = document.getElementById(id);
  const cv = document.createElement('canvas'); cv.width = cv.height = 1;
  const cx = cv.getContext('2d', { willReadFrequently: true });
  const rgba = c => { if (!c || c === 'none' || c.startsWith('url(')) return [0, 0, 0, 0]; cx.clearRect(0, 0, 1, 1);
    cx.fillStyle = 'rgba(0,0,0,0)'; cx.fillStyle = c; cx.fillRect(0, 0, 1, 1);
    const d = cx.getImageData(0, 0, 1, 1).data; return [d[0], d[1], d[2], d[3] / 255]; };
  const over = (top, bot) => { const a = top[3]; return [0, 1, 2].map(i => top[i] * a + bot[i] * (1 - a)).concat(1); };
  const hidden = e => { for (let n = e; n && n !== document.documentElement; n = n.parentElement) {
      const cs = getComputedStyle(n); if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity < .05) return true; }
    return false; };
  const alpha = e => { let a = 1; for (let n = e; n && n !== document.documentElement; n = n.parentElement) a *= +getComputedStyle(n).opacity; return a; };
  const out = e => e.closest('aside.note, .ambient');
  const label = e => (e.id ? '#' + e.id : e.tagName.toLowerCase() + '.' + [...e.classList].join('.')) + ' «' + (e.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 32) + '»';
  const R = r => ({ l: r.left, t: r.top, r: r.right, b: r.bottom });
  const lines = e => { const rg = document.createRange(); rg.selectNodeContents(e);
    return [...rg.getClientRects()].filter(r => r.width > 1 && r.height > 1).map(R); };
  // softened = blurred by a focus state (body under an Insight, scene under a pop-over): out of focus on purpose
  const soft = e => { for (let n = e; n && n !== document.documentElement; n = n.parentElement) {
      const f = getComputedStyle(n).filter; if (f && /blur\((?!0(px)?\))/.test(f)) return true; } return false; };
  const svgs = [...s.querySelectorAll('svg')];
  const BLOCKS = 'h2, h3, p, li, blockquote, figcaption, .narr-tile, .quote, g.tile';
  const cands = [...s.querySelectorAll(BLOCKS)].filter(e => !out(e) && !hidden(e));
  const top = cands.filter(e => !cands.some(o => o !== e && o.contains(e)));
  const solid = e => e.matches('.narr-tile, .quote, g.tile');
  const boxes = top.map(e => ({ who: label(e), rects: solid(e) ? [R(e.getBoundingClientRect())] : lines(e),
      svg: e instanceof SVGElement ? svgs.indexOf(e.ownerSVGElement) : -1, textless: !(e.textContent || '').trim(),
      focus: !!e.closest('.overlay, .popover'), title: !!e.closest('.title') }))
    .concat(['.bar', '.notes-btn'].map(q => document.querySelector(q)).filter(e => e && !hidden(e))
      .map(e => ({ who: label(e), chrome: true, rects: [R(e.getBoundingClientRect())] })));
  const bodyBg = (() => { const c = rgba(getComputedStyle(document.body).backgroundColor); return c[3] > 0 ? over(c, [255, 255, 255, 1]) : [255, 255, 255, 1]; })();
  const bgOf = e => { const layers = [];
    const tile = e instanceof SVGElement && e.closest('g.tile');
    if (tile && tile.querySelector('rect')) layers.push(rgba(getComputedStyle(tile.querySelector('rect')).fill));
    for (let n = e; n && n !== document.documentElement; n = n.parentElement) {
      const c = rgba(getComputedStyle(n).backgroundColor); if (c[3] > 0) layers.push(c); if (c[3] >= 1) break; }
    return layers.reverse().reduce((bot, l) => over(l, bot), bodyBg); };
  const fam = cs => cs.fontFamily.split(',')[0].trim().replace(/^["']|["']$/g, '').toLowerCase();
  const runs = [...s.querySelectorAll('*')].filter(e => !out(e) && !hidden(e)
      && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()))
    .map(e => { const cs = getComputedStyle(e), svg = e instanceof SVGElement;
      const fg = rgba(svg ? cs.fill : cs.color), bg = bgOf(e);
      const scale = svg && e.getScreenCTM ? Math.hypot(e.getScreenCTM().a, e.getScreenCTM().b) : 1;
      return { who: label(e), text: [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join(' ').trim(),
        fg: over([fg[0], fg[1], fg[2], fg[3] * alpha(e)], bg), raw: fg, bg, px: parseFloat(cs.fontSize),
        rpx: parseFloat(cs.fontSize) * scale, weight: +cs.fontWeight, family: fam(cs), svg,
        kicker: !!e.closest('.kicker'), soft: soft(e),
        label: (cs.textTransform === 'uppercase' && parseFloat(cs.letterSpacing) >= 0.05 * parseFloat(cs.fontSize))
          || !!e.closest('.cite, .quote-from') }; });
  const edges = [...s.querySelectorAll('svg path.edge')].filter(e => !hidden(e) && e.getTotalLength).map(e => {
    const svg = e.ownerSVGElement, cs = getComputedStyle(e), n = e.getTotalLength();
    const p0 = e.getPointAtLength(0), p1 = e.getPointAtLength(n);
    const gap = (p, sel) => { const t = sel && svg.querySelector(sel), r = t && t.querySelector('rect');
      if (!r) return null; const x = r.x.baseVal.value, y = r.y.baseVal.value, w = r.width.baseVal.value, h = r.height.baseVal.value;
      return Math.hypot(Math.max(x - p.x, 0, p.x - x - w), Math.max(y - p.y, 0, p.y - y - h)); };
    const mref = (e.getAttribute('marker-end') || '').match(/url\(#([^)]+)\)/);
    const m = mref && document.getElementById(mref[1]);
    let marker = null;
    if (mref) { const vb = m && m.viewBox && m.viewBox.baseVal;
      marker = { found: !!m, orient: m ? (m.getAttribute('orient') || '') : '',
        centred: !!(m && vb && vb.height && Math.abs(m.refY.baseVal.value - (vb.y + vb.height / 2)) <= 0.5) }; }
    const st = rgba(cs.stroke);
    return { who: label(e), len: n, gapFrom: gap(p0, e.dataset.from), gapTo: gap(p1, e.dataset.to), marker, soft: soft(e),
      stroke: over([st[0], st[1], st[2], st[3] * alpha(e) * (+cs.strokeOpacity || 1)], bgOf(svg)), bg: bgOf(svg) }; });
  const links = [...s.querySelectorAll('a[href]')].filter(a => !out(a) && !hidden(a))
    .map(a => ({ who: label(a), color: rgba(getComputedStyle(a).color) }));
  const chrome = {};
  [['bar', '.bar'], ['agenda', '.agenda'], ['notes-btn', '.notes-btn']].forEach(([k, q]) => {
    const e = document.querySelector(q); if (e && !hidden(e)) chrome[k] = R(e.getBoundingClientRect()); });
  const amb = s.querySelector(':scope > .ambient');
  const sig = [...s.querySelectorAll('[data-show-at], [data-hide-at], [data-at], .title, ol.steps > li')].map(e =>
    (hidden(e) ? '0' : '1') + ['is-visible', 'is-shown', 'is-current', 'is-done'].filter(c => e.classList.contains(c)).join('+'))
    .join('|') + (s.classList.contains('is-overlaid') ? '|overlaid' : '');
  const kids = [...s.children].filter(e => !e.matches('aside.note, .ambient') && !hidden(e))
    .map(e => ({ who: label(e), r: R(e.getBoundingClientRect()) })).filter(k => k.r.r > k.r.l && k.r.b > k.r.t);
  const loops = document.getAnimations().filter(a => a.playState === 'running' && a.effect
      && a.effect.getComputedTiming().iterations === Infinity && a.effect.target
      && !a.effect.target.closest('.ambient') && s.contains(a.effect.target))
    .map(a => label(a.effect.target));
  return { vw: innerWidth, vh: innerHeight, boxes, runs, edges, links, chrome, sig, kids, loops,
    ambient: !!(amb && !hidden(amb)) };
}"""

# Static facts of one slide (markup, independent of size and step).
STATIC = r"""(id) => {
  const s = document.getElementById(id);
  const txt = e => (e.textContent || '').replace(/\s+/g, ' ').trim();
  const name = e => (e.getAttribute('aria-label') || '').trim() || (e.getAttribute('aria-labelledby') || '').split(/\s+/)
    .map(i => document.getElementById(i)).filter(Boolean).map(txt).join(' ') || txt(e.querySelector(':scope > title') || document.createElement('i'));
  const titles = [...s.querySelectorAll('.title')].filter(t => !t.closest('aside.note'));
  return {
    lead: s.classList.contains('slide--lead'),
    titles: titles.map(t => ({ text: txt(t), em: t.querySelectorAll('em, i').length })),
    notes: [...s.querySelectorAll('aside.note')].map(n => {
      const c = n.cloneNode(true); c.querySelectorAll('a').forEach(a => a.remove());
      return { text: txt(n), bare: txt(c), hrefs: [...n.querySelectorAll('a')].map(a => a.getAttribute('href') || '') }; }),
    hrefs: [...s.querySelectorAll('a')].filter(a => !a.closest('aside.note')).map(a => a.getAttribute('href') || ''),
    overlays: [...s.querySelectorAll('.overlay')].map(o => ({ id: o.id, text: txt(o) })),
    imgs: [...s.querySelectorAll('img')].map(i => ({ src: (i.getAttribute('src') || '').slice(0, 40), alt: i.hasAttribute('alt'),
      empty: (i.getAttribute('alt') || '').trim() === '', decorative: i.getAttribute('role') === 'presentation' || i.getAttribute('aria-hidden') === 'true' })),
    graphics: [...s.querySelectorAll('svg, [role="img"]')].filter(g => g.getAttribute('aria-hidden') !== 'true'
        && !g.closest('svg:not(:scope)') || g.matches('[role="img"]'))
      .filter(g => !(g.parentElement && g.parentElement.closest('svg')) || g.matches('[role="img"]'))
      .map(g => ({ who: (g.id ? '#' + g.id : g.tagName.toLowerCase() + '.' + [...g.classList].join('.')), named: !!name(g),
        decorative: g.getAttribute('aria-hidden') === 'true' || g.getAttribute('role') === 'presentation' })),
    builds: !!s.querySelector('[data-show-at], [data-at], [data-hide-at]') || s.hasAttribute('data-scene'),
    diagram: !!s.querySelector('svg.diagram') || s.hasAttribute('data-scene'),
    hasNote: !!s.querySelector('aside.note'),
  };
}"""

# Ambient drift: compare orb transforms across animation frames (a frame count, not a clock).
DRIFT = r"""([id, frames]) => new Promise(res => {
  const s = document.getElementById(id), orbs = s ? [...s.querySelectorAll('.ambient .orb')] : [];
  if (!orbs.length) return res(false);
  const snap = () => orbs.map(o => getComputedStyle(o).transform + '|' + o.style.transform).join(';');
  const a = snap(); let n = 0;
  const tick = () => { if (snap() !== a) return res(true); if (++n >= frames) return res(false); requestAnimationFrame(tick); };
  requestAnimationFrame(tick); })"""

LOOPS = r"""(id) => { const s = document.getElementById(id);
  return document.getAnimations().filter(a => a.playState === 'running' && a.effect && a.effect.target
    && a.effect.getComputedTiming().iterations === Infinity && s.contains(a.effect.target)).length; }"""

SIZE_PROBE = r"""(names) => { const p = document.createElement('span'); document.body.append(p); const out = {};
  names.forEach(n => { p.style.fontSize = 'var(' + n + ')'; const v = parseFloat(getComputedStyle(p).fontSize);
    if (getComputedStyle(document.documentElement).getPropertyValue(n).trim()) out[n] = v; });
  p.remove(); return out; }"""

DEFAULT_LINK = ((0, 0, 238), (85, 26, 139), (0, 0, 255))


def _hex(c) -> str:
    return "#" + "".join(f"{max(0, min(255, round(x))):02X}" for x in c[:3])


def _ratio(fg, bg) -> float:
    return tok_mod.contrast(_hex(fg), _hex(bg))


def _never_text_colours(src: str) -> dict[str, str]:
    """Map the hex of each palette role flagged ``textSafe: false`` to its role, when the deck's
    PALETTE block is a shipped palette's generated block (else empty: the check is skipped)."""
    try:
        block = asm_mod.read_block(src, "PALETTE")
    except Exception:
        return {}
    body = re.sub(r"^/\*[^\n]*\*/\n", "", block).strip()
    styles = sorted((tok_mod.TOKENS_DIR / "styles").glob("*.tokens.json"))
    for pal in sorted((tok_mod.TOKENS_DIR / "palettes").glob("*.tokens.json")):
        name = pal.name.removesuffix(".tokens.json")
        try:
            theme = tok_mod.load(name, styles[0].name.removesuffix(".tokens.json"))
            if tok_mod.palette_css(theme).strip() != body:
                continue
        except Exception:
            continue
        return {tok_mod.hex_of(theme, p): p for p, t in theme.tokens.items()
                if p.startswith("sys.color.") and t.own_ext(tok_mod.PAL, "textSafe") is False}
    return {}


def _guard_faults(page, sid: str) -> list[str]:
    return page.evaluate(guard_mod.LAYOUT_CHECK, sid)


def _stacked(a: dict, b: dict) -> bool:
    """True for a deliberate stack, not a collision: a textless tile (a decorative card behind a
    labelled one) with another shape of its own diagram, or a focus card (overlay, pop-over) over
    body content. A focus card over a title or chrome, or two labelled tiles, still collide."""
    if a.get("svg", -1) >= 0 and a.get("svg") == b.get("svg") and (a.get("textless") or b.get("textless")):
        return True
    return any(x.get("focus") and not (y.get("focus") or y.get("title") or y.get("chrome")) for x, y in ((a, b), (b, a)))


def _collisions(m) -> list[str]:
    hits, boxes = [], m["boxes"]
    for i, a in enumerate(boxes):
        for r in a["rects"]:
            if not a.get("chrome") and (r["l"] < -1 or r["t"] < -1 or r["r"] > m["vw"] + 1 or r["b"] > m["vh"] + 1):
                hits.append(f"off-canvas {a['who']}")
        for b in boxes[i + 1:]:
            if a.get("chrome") and b.get("chrome") or _stacked(a, b):
                continue
            if any(min(r["r"], q["r"]) - max(r["l"], q["l"]) > 2 and min(r["b"], q["b"]) - max(r["t"], q["t"]) > 2
                   for r in a["rects"] for q in b["rects"]):
                hits.append(f"collision {a['who']} × {b['who']}")
    return hits


def _words(m) -> int:
    return sum(len([w for w in r["text"].split() if re.search(r"\w", w)]) for r in m["runs"])


def _offline_context(browser, size, log: dict, reduced: bool = False):
    ctx = browser.new_context(viewport={"width": size[0], "height": size[1]},
                              reduced_motion="reduce" if reduced else "no-preference")

    def route(r):
        url = r.request.url
        if url.startswith(("file:", "data:", "blob:", "about:")):
            return r.continue_()
        log["external"].append(url)
        return r.abort()

    ctx.route("**/*", route)
    return ctx


def _watch(page, log: dict) -> None:
    page.on("console", lambda m: m.type == "error" and log["console"].append(m.text[:160]))
    page.on("pageerror", lambda e: log["console"].append(f"page error: {str(e)[:160]}"))
    page.on("requestfailed", lambda r: r.url.startswith("file:") and log["failed"].append(r.url[-80:]))


def measure_deck(deck: Path, sizes, browser, needs: set[str]) -> dict:
    """Render a deck once per review size and collect every fact the deck checks read.

    Args:
        deck: Assembled deck HTML file.
        sizes: Viewport sizes ``(w, h)``; the first one also carries the size-independent checks.
        browser: A launched Playwright Chromium browser.
        needs: Criterion ids in scope (skips the keyboard, motion and notes passes when unused).

    Returns:
        Facts: ``plan``, per-size ``states`` probes and ``guard`` faults, per-slide ``static``,
        and the ``net``, ``keys``, ``motion`` and ``callout`` passes.
    """
    log = {"external": [], "console": [], "failed": []}
    facts = {"plan": None, "states": {}, "guard": {}, "static": {}, "net": log, "keys": None,
             "motion": None, "callout": None, "scale": {}, "families": {}}
    src = deck.read_text(encoding="utf-8")
    size_names = sorted(set(re.findall(r"(--(?:sys-type-[\w-]*size|comp-[\w-]*(?:size|floor)))\s*:", src)))
    font_names = sorted(set(re.findall(r"(--sys-font-[\w-]+)\s*:", src)))
    for i, size in enumerate(sizes):
        sid_ = guard_mod.size_id(size)
        ctx = _offline_context(browser, size, log)
        page = ctx.new_page()
        _watch(page, log)
        plan = guard_mod.open_deck(page, deck)
        facts["plan"] = facts["plan"] or plan
        facts["scale"][sid_] = page.evaluate(SIZE_PROBE, size_names)
        if i == 0:
            facts["families"] = {n: page.evaluate(
                "n => getComputedStyle(document.documentElement).getPropertyValue(n)", n) for n in font_names}
        states, faults = {}, {}
        for sid, last in plan:
            if i == 0:
                facts["static"][sid] = page.evaluate(STATIC, sid)
            for k in range(last + 1):
                guard_mod.goto_step(page, sid, k)
                faults[(sid, k)] = _guard_faults(page, sid)
                states[(sid, k)] = page.evaluate(PROBE, sid)
                if i == 0 and k == 0 and "DS-03" in needs:
                    states[(sid, k)]["drift"] = page.evaluate(DRIFT, [sid, 30])
        facts["states"][sid_], facts["guard"][sid_] = states, faults
        if i == 0 and "DS-07" in needs:
            facts["callout"] = _callout_links(page, plan, facts["static"])
        ctx.close()
    first = sizes[0]
    if "AR-03" in needs:
        facts["keys"] = _keyboard_walk(browser, deck, first, facts["plan"], log)
    if "DS-03" in needs:
        facts["motion"] = _reduced_motion(browser, deck, first, facts["plan"], facts["static"], log)
    return facts


def _callout_links(page, plan, static) -> dict:
    """Open notes mode on the first slide with a note and read the callout's link colours."""
    target = next((s for s, _ in plan if static[s]["hasNote"]), None)
    if not target or not page.query_selector(".notes-btn"):
        return {"slide": target, "links": [], "reason": "no note or no notes button"}
    try:
        guard_mod.goto_step(page, target, 0)
        page.click(".notes-btn")
        page.wait_for_function("document.body.classList.contains('notes-on')", timeout=3000)
        page.wait_for_function("!!document.querySelector('.callout a[href]')", timeout=3000)
        guard_mod.settle(page)
        links = page.evaluate("""() => [...document.querySelectorAll('.callout a[href]')].map(a => {
            const c = getComputedStyle(a).color.match(/[\\d.]+/g).map(Number); return {who: a.textContent.trim().slice(0, 40), color: c}; })""")
        page.click(".notes-btn")
        return {"slide": target, "links": links, "reason": ""}
    except Exception as e:  # notes mode unreachable: report, do not guess
        return {"slide": target, "links": [], "reason": f"notes mode not reachable: {str(e)[:80]}"}


def _keyboard_walk(browser, deck, size, plan, log) -> dict:
    order = [(s, k) for s, last in plan for k in range(last + 1)]
    ctx = _offline_context(browser, size, log)
    page = ctx.new_page()
    _watch(page, log)
    guard_mod.open_deck(page, deck)
    out = {"fwd": {}, "bwd": {}, "unreachable": []}
    page.keyboard.press("Home")
    for direction, key, seq in (("fwd", "ArrowRight", order), ("bwd", "ArrowLeft", order[::-1])):
        for j, (sid, k) in enumerate(seq):
            if j:
                page.keyboard.press(key)
            try:
                page.wait_for_function("([s, k]) => deck.state().slide === s && deck.state().step === k",
                                       arg=[sid, k], timeout=4000)
            except Exception:
                st = page.evaluate("deck.state()")
                out["unreachable"].append({"dir": direction, "slide": sid, "step": k,
                                           "at": f"{st['slide']}/{st['step']}"})
                break
            guard_mod.settle(page)
            out[direction][(sid, k)] = page.evaluate(PROBE, sid)["sig"]
    ctx.close()
    return out


def _reduced_motion(browser, deck, size, plan, static, log) -> dict:
    ctx = _offline_context(browser, size, log, reduced=True)
    page = ctx.new_page()
    guard_mod.open_deck(page, deck)
    out = {}
    for sid, _ in plan:
        guard_mod.goto_step(page, sid, 0)
        out[sid] = {"drift": page.evaluate(DRIFT, [sid, 30]), "loops": page.evaluate(LOOPS, sid)}
    ctx.close()
    return out


# ---------- deck: per-criterion rules ----------

def _states(facts):
    return [(s, k) for s, last in facts["plan"] for k in range(last + 1)]


def _deck_rules(facts: dict, src: str, crit: dict, deck: Path) -> list[dict]:
    cid, params = crit["id"], crit.get("params", {})
    rule = CHECKS[cid]
    fname = deck.name
    plan, static = facts["plan"], facts["static"]
    sizes = list(facts["states"])
    first = sizes[0]
    out = []

    def per_state(check, ok_text):
        for sid, k in _states(facts):
            bad = []
            for size in sizes:
                bad += [{"slide": sid, "step": k, "size": size, "note": n} for n in check(sid, k, size)]
            out.append(_verdict(crit, f"{sid}/{k}", bad, {"slide": sid, "step": k, "note": ok_text}, rule))

    def per_slide(check, ok_text):
        for sid, _ in plan:
            bad = [{"slide": sid, "note": n} for n in check(sid)]
            out.append(_verdict(crit, sid, bad, {"slide": sid, "note": ok_text}, rule))

    def deck_level(bad, ok_text):
        out.append(_verdict(crit, "deck", bad, {"file": fname, "note": ok_text}, rule))

    if cid == "DL-01":
        def chk(sid, k, size):
            return ([f"layout guard: {f}" for f in facts["guard"][size][(sid, k)]]
                    + _collisions(facts["states"][size][(sid, k)]))
        per_state(chk, f"no overlap, overflow or off-canvas box at {', '.join(sizes)}")
    elif cid == "DL-02":
        def chk(sid, k, size):
            big = int(size.split("x")[0]) >= 1920
            text = params.get("min_px_1920", 20) if big else params.get("min_px_1280", 15)
            label = params.get("min_label_px_1920", 18) if big else params.get("min_label_px_1280", 12)
            bad = []
            for r in facts["states"][size][(sid, k)]["runs"]:
                floor = label if r.get("label") else text
                if r["rpx"] < floor - 0.05:
                    bad.append(f"{r['who']} at {r['rpx']:.1f}px < {floor}px" + (" (label floor)" if r.get("label") else ""))
            return bad
        per_state(chk, "reading text at or above the text floor, labels at or above the label floor")
    elif cid == "DL-09":
        bad = []
        for size in sizes:
            prev = None
            for sid, _ in plan:
                ch = facts["states"][size][(sid, 0)]["chrome"]
                for key in sorted(set(ch) & set(prev[1]) if prev else ()):
                    a, b = prev[1][key], ch[key]
                    if max(abs(a[x] - b[x]) for x in "ltrb") > 1:
                        bad.append({"slide": sid, "size": size, "region": key,
                                    "note": f"{key} box moves or rescales from {prev[0]} to {sid}"})
                prev = (sid, ch)
        deck_level(bad, f"bar, agenda and notes button hold their boxes across slides at {', '.join(sizes)}")
    elif cid == "DP-01":
        never = _never_text_colours(src)

        def chk(sid, k, size):
            bad = []
            for r in facts["states"][size][(sid, k)]["runs"]:
                if r.get("soft"):
                    continue
                large = r["rpx"] >= 24 or (r["rpx"] >= 18.5 and r["weight"] >= 700)
                ratio, need = _ratio(r["fg"], r["bg"]), (3.0 if large else 4.5)
                if ratio < need:
                    bad.append(f"{r['who']} {tok_mod.fmt_ratio(ratio)} < {need}:1 at {r['rpx']:.0f}px")
                elif _hex(r["raw"]) in never and r["raw"][3] > 0:
                    bad.append(f"{r['who']} uses never-text role {never[_hex(r['raw'])]}")
            return bad
        per_state(chk, "every text run meets its WCAG threshold")
    elif cid == "DP-02":
        def chk(sid, k, size):
            return [f"{e['who']} stroke {tok_mod.fmt_ratio(_ratio(e['stroke'], e['bg']))} < 3:1"
                    for e in facts["states"][size][(sid, k)]["edges"]
                    if not e.get("soft") and _ratio(e["stroke"], e["bg"]) < 3.0]
        per_state(chk, "every visible connector stroke ≥ 3:1 (or none at this step)")
    elif cid == "DL-10":
        def chk(sid, k, size):
            bad = []
            for e in facts["states"][size][(sid, k)]["edges"]:
                for end in ("gapFrom", "gapTo"):
                    if e[end] is not None and e[end] < 0.5:
                        bad.append(f"{e['who']} touches its {'source' if end == 'gapFrom' else 'target'} tile")
                m = e["marker"]
                if m and (not m["found"] or m["orient"] not in ("auto", "auto-start-reverse") or not m["centred"]):
                    bad.append(f"{e['who']} arrowhead marker not tangent-oriented and centred ({m})")
            return bad
        per_state(chk, "every visible connector is gapped with a tangent, centred head (or none at this step)")
    elif cid == "CN-04":
        budget = params.get("max_words", 40)

        def chk(sid):
            last = dict(plan)[sid]
            worst = max(range(last + 1), key=lambda k: _words(facts["states"][first][(sid, k)]))
            n = _words(facts["states"][first][(sid, worst)])
            return [f"{n} visible words at step {worst} > {budget}"] if n > budget else []
        per_slide(chk, f"visible words within {budget} at every step")
    elif cid == "CN-08":
        per_slide(lambda sid: [] if static[sid]["lead"] or any(n["text"] for n in static[sid]["notes"])
                  else ["content slide without a reader note"], "reader note present, or a lead slide")
    elif cid == "VC-03":
        def chk(sid):
            bad = []
            for t in static[sid]["titles"]:
                if t["text"].endswith("."):
                    bad.append(f"title ends with a full stop: {t['text'][:60]!r}")
                if re.search(r"[.!?]\s+\S", t["text"]):
                    bad.append(f"title has more than one sentence: {t['text'][:60]!r}")
                if t["em"] > 1:
                    bad.append(f"title has {t['em']} emphasised runs: {t['text'][:60]!r}")
            return bad
        per_slide(chk, "every title is one sentence, no final stop, ≤ 1 emphasis")
    elif cid == "VC-05":
        def chk(sid):
            return [f"overlay {o['id'] or ''} has {n} sentences" for o in static[sid]["overlays"]
                    if (n := len([x for x in re.split(r"(?<=[.!?])\s+", o["text"]) if re.search(r"\w", x)])) > 3]
        per_slide(chk, "every overlay ≤ 3 sentences (or none)")
    elif cid == "RS-05":
        bad = []
        for sid, _ in plan:
            st = static[sid]
            for h in st["hrefs"] + [h for n in st["notes"] for h in n["hrefs"]]:
                why = _bad_href(h)
                if why:
                    bad.append({"slide": sid, "note": f"link {h!r}: {why}"})
            for n in st["notes"]:
                if re.search(r"\bsources?\s*:", n["bare"], re.I):
                    bad.append({"slide": sid, "note": f"bare-text citation in note: {n['bare'][-70:]!r}"})
        deck_level(bad, "every citation is a well-formed https link")
    elif cid == "DP-03":
        bad = []
        try:
            for name in asm_mod.BLOCKS:
                if name in ("PALETTE", "FONTS"):
                    continue
                block = asm_mod.read_block(src, name)
                for m in re.finditer(r"(?<![\w&(])#[0-9a-fA-F]{3,8}\b(?![-\w])|\b(?:rgba?|hsla?|oklch|oklab|lab|lch)\(",
                                     _colour_context(block, name)):
                    bad.append({"file": fname, "region": name, "note": f"colour literal {m.group(0)!r} in {name}"})
        except Exception as e:
            out.append({"criterion": cid, "unit": "deck", "repeat": 1, "evidence": [],
                        "rationale": f"Deck has no assembler block markers, so the theme block cannot be located ({str(e)[:80]}).",
                        "flaws": [], "result": "insufficient-evidence"})
            return out
        deck_level(bad, "colour literals only in the PALETTE block")
    elif cid == "DS-01":
        declared = {v.split(",")[0].strip().strip("'\"").lower() for v in facts["families"].values() if v.strip()}
        bad, used = [], {}
        for size in sizes:
            scale = [v for n, v in facts["scale"][size].items() if not n.endswith("-floor")]
            floors = [v for n, v in facts["scale"][size].items() if n.endswith("-floor")]

            def off(r):  # diagram text is max(floor, --k × role size): on the scale, or at a floor in SVG units
                return min(abs(r["rpx"] - v) for v in scale) > 0.6 and not (
                    r.get("svg") and floors and min(abs(r["px"] - v) for v in floors) <= 0.6)
            for (sid, k), m in facts["states"][size].items():
                for r in m["runs"]:
                    used.setdefault(r["family"], f"{sid}/{k} {r['who']}")
                    if declared and r["family"] not in declared:
                        bad.append({"slide": sid, "step": k, "size": size, "note": f"{r['who']} in undeclared family {r['family']!r}"})
                    if scale and off(r):
                        bad.append({"slide": sid, "step": k, "size": size, "note": f"{r['who']} at {r['rpx']:.1f}px is off the type scale"})
        if len(used) > 2:
            bad.append({"file": fname, "note": f"{len(used)} families: {sorted(used)}"})
        deck_level(_dedupe(bad), f"families {sorted(used)} declared; sizes on the type scale")
    elif cid == "DS-03":
        bad = []
        for sid, last in plan:
            st, m = static[sid], facts["states"][first][(sid, 0)]
            allowed = st["lead"] or not (st["builds"] or st["diagram"])
            if m["ambient"] and not allowed:
                bad.append({"slide": sid, "note": "ambient layer on a slide that builds or holds a diagram"
                            + (" (drifting)" if m.get("drift") else "")})
            for k in range(last + 1):
                for who in facts["states"][first][(sid, k)]["loops"]:
                    bad.append({"slide": sid, "step": k, "note": f"looping animation outside the ambient layer: {who}"})
            mo = (facts["motion"] or {}).get(sid)
            if mo and (mo["drift"] or mo["loops"]):
                bad.append({"slide": sid, "note": f"reduced motion not respected: drift={mo['drift']}, loops={mo['loops']}"})
        deck_level(_dedupe(bad), "ambient only on lead or build-free slides; nothing loops; still under reduced motion")
    elif cid == "DS-07":
        bad = []
        for (sid, k), m in facts["states"][first].items():
            for ln in m["links"]:
                if tuple(round(x) for x in ln["color"][:3]) in DEFAULT_LINK:
                    bad.append({"slide": sid, "step": k, "note": f"{ln['who']} in the default link colour"})
        co = facts["callout"] or {}
        for ln in co.get("links", []):
            if tuple(round(x) for x in ln["color"][:3]) in DEFAULT_LINK:
                bad.append({"slide": co["slide"], "region": "notes callout", "note": f"link {ln['who']!r} in the default link colour"})
        n = len(co.get("links", []))
        deck_level(_dedupe(bad), f"slide links and {n} notes-callout link(s) use the style's link colour"
                   + (f" ({co['reason']})" if co.get("reason") else ""))
    elif cid == "AR-01":
        net = facts["net"]
        bad = [{"file": fname, "note": f"external request blocked: {u[:90]}"} for u in sorted(set(net["external"]))]
        bad += [{"file": fname, "note": f"resource failed: {u}"} for u in sorted(set(net["failed"]))]
        bad += [{"file": fname, "note": f"console: {c}"} for c in sorted(set(net["console"]))]
        bad += [{"file": fname, "note": f"external reference: {f}"} for f in asm_mod.endpoint_faults(src)
                if re.search(r"remote|<link>|@import|url\(\)|<script src>|embedding", f)]
        deck_level(bad, f"rendered all {len(_states(facts))} states at {len(sizes)} sizes with the network blocked; "
                   "no request, failure or console error")
    elif cid == "AR-02":
        deck_level([{"file": fname, "note": f} for f in asm_mod.endpoint_faults(src)], "no endpoint-risk pattern")
    elif cid == "AR-03":
        keys, bad = facts["keys"], []
        for u in keys["unreachable"]:
            bad.append({"slide": u["slide"], "step": u["step"],
                        "note": f"not reached by {'→' if u['dir'] == 'fwd' else '←'} (stuck at {u['at']})"})
        for st in _states(facts):
            f, b = keys["fwd"].get(st), keys["bwd"].get(st)
            g = facts["states"][first][st]["sig"]
            if f is not None and b is not None and f != b:
                bad.append({"slide": st[0], "step": st[1], "note": "renders differently going back than going forward"})
            elif f is not None and f != g:
                bad.append({"slide": st[0], "step": st[1], "note": "keyboard state differs from the same step reached directly"})
        deck_level(bad, f"all {len(_states(facts))} states reached by → and ← and identical each way")
    elif cid == "AR-04":
        bad = []
        for m in re.finditer(r"<style\b|<script\b|\sstyle\s*=|\son[a-z]+\s*=", _slides_markup(src)[0], re.I):
            text, base = _slides_markup(src)
            bad.append({"file": fname, "line": src.count("\n", 0, base + m.start()) + 1,
                        "note": f"{m.group(0).strip()!r} inside slide markup"})
        deck_level(bad, "slide markup carries only contract attributes and classes")
    elif cid == "AR-05":
        bad, seen = [], {}
        for sid, last in plan:
            titles = [t["text"] for t in static[sid]["titles"] if t["text"]]
            if not titles:
                bad.append({"slide": sid, "note": "slide has no title"})
                continue
            key = titles[0].lower()
            if key in seen:
                bad.append({"slide": sid, "note": f"title duplicates slide {seen[key]}: {titles[0][:60]!r}"})
            seen.setdefault(key, sid)
            kids = facts["states"][first][(sid, last)]["kids"]
            for a, b in zip(kids, kids[1:]):
                ra, rb = a["r"], b["r"]
                if rb["b"] <= ra["t"] - 2 and min(ra["r"], rb["r"]) - max(ra["l"], rb["l"]) > 2:
                    bad.append({"slide": sid, "step": last, "size": first,
                                "note": f"{b['who']} comes after {a['who']} in the DOM but sits above it"})
        deck_level(bad, "titles unique; DOM order follows visual order")
    elif cid == "AR-06":
        bad = []
        for sid, _ in plan:
            for i in static[sid]["imgs"]:
                if not i["alt"] and not i["decorative"]:
                    bad.append({"slide": sid, "note": f"img {i['src']!r} without alt"})
            for g in static[sid]["graphics"]:
                if not g["named"] and not g["decorative"]:
                    bad.append({"slide": sid, "note": f"{g['who']} without an accessible name"})
        deck_level(bad, "every image and graphic has alt text or an accessible name")
    return out


def _dedupe(items: list[dict]) -> list[dict]:
    seen, out = set(), []
    for x in items:
        key = (x.get("slide"), x["note"])
        if key not in seen:
            seen.add(key)
            out.append(x)
    return out


def _bad_href(h: str) -> str:
    h = (h or "").strip()
    if not h or h.startswith("#"):
        return "empty or in-page link"
    if re.search(r"todo|tbd|placeholder|xxx", h, re.I):
        return "placeholder"
    u = urlparse(h)
    if u.scheme != "https":
        return "not https"
    host = (u.hostname or "").lower()
    if "." not in host or host in {"example.com", "example.org", "example.net", "www.example.com",
                                   "www.example.org", "www.example.net"}:
        return "placeholder or malformed host"
    return ""


def _colour_context(block: str, name: str) -> str:
    """CSS blocks are scanned whole; HTML blocks only inside style/colour attributes."""
    if name not in asm_mod.HTML_BLOCKS:
        return re.sub(r"/\*.*?\*/", "", block, flags=re.S)
    return "\n".join(m.group(2) for m in re.finditer(
        r"\b(style|fill|stroke|color|stop-color|flood-color|lighting-color)\s*=\s*(\"[^\"]*\"|'[^']*')", block))


def _slides_markup(src: str) -> tuple[str, int]:
    """Return the slide markup and its offset in the source (SLIDES block, else every slide section)."""
    try:
        s, _ = asm_mod.spans(src)["SLIDES"]
        return asm_mod.read_block(src, "SLIDES"), s
    except Exception:
        m = re.search(r"<section\b[^>]*\bclass\s*=\s*[\"'][^\"']*\bslide\b.*</section>", src, re.S | re.I)
        return (m.group(0), m.start()) if m else ("", 0)


def deck_verdicts(deck: Path, criteria: list[dict], sizes=guard_mod.REVIEW_SIZES, browser=None) -> list[dict]:
    """Check deck-target ``D`` criteria on an assembled deck.

    Args:
        deck: Deck HTML file.
        criteria: Resolved criteria (``criteria.resolve``) to check; others are ignored.
        sizes: Review sizes ``(w, h)``.
        browser: Optional launched Playwright browser (one is launched when ``None``).

    Returns:
        Verdicts in the judge format.
    """
    todo = [c for c in criteria if c["id"] in CHECKS and c["target"] == "deck"]
    if not todo:
        return []
    deck = Path(deck)
    src = deck.read_text(encoding="utf-8")
    needs = {c["id"] for c in todo}
    if browser is None:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = guard_mod.launch(p)
            try:
                facts = measure_deck(deck, sizes, b, needs)
            finally:
                b.close()
    else:
        facts = measure_deck(deck, sizes, browser, needs)
    return [v for c in todo for v in _deck_rules(facts, src, c, deck)]


# ---------- repo: git facts ----------

def _git(repo: Path, *args, check=True) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=check, capture_output=True,
                          text=True, errors="replace").stdout


def _spec_at(repo: Path, commit: str, spec_file: str) -> dict[str, str]:
    p = subprocess.run(["git", "-C", str(repo), "show", f"{commit}:{spec_file}"], capture_output=True, text=True, errors="replace")
    out = {}
    for ln in p.stdout.splitlines() if p.returncode == 0 else []:
        try:
            d = json.loads(ln)
            out[d["id"]] = d.get("status")
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    return out


def _changes(repo: Path, commit: str) -> list[tuple[str, str]]:
    """``(status, path)`` for each file a non-merge commit changes (renames as delete + add)."""
    out = []
    for ln in _git(repo, "show", "--no-renames", "--name-status", "--format=", commit).splitlines():
        if "\t" in ln:
            st, path = ln.split("\t", 1)
            out.append((st[0], path))
    return out


def _is_test(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return name.startswith("test_") and name.endswith(".py") or name.endswith("_test.py")


TEST_CONFIG = {"pyproject.toml", "uv.lock", "requirements.txt", "requirements-dev.txt", ".gitignore",
               "conftest.py", "pytest.ini", "setup.cfg", "tox.ini", "package.json", "package-lock.json"}


def _is_impl(path: str, spec_file: str) -> bool:
    """Implementation = anything but tests, test config, docs, the spec file, run records and prototypes."""
    name = path.rsplit("/", 1)[-1]
    return not (path == spec_file or _is_test(path) or path.endswith(".md") or name in TEST_CONFIG
                or path.startswith(("tests/", "docs/", "evals/", "design/prototypes/"))
                or "/tests/" in path or name.startswith("helper_"))


def _marked(repo: Path, commit: str, sid: str) -> list[str]:
    """Test files at ``commit`` whose text carries a ``Spec:`` marker naming ``sid``."""
    p = subprocess.run(["git", "-C", str(repo), "grep", "-l", "-F", "Spec:", commit],
                       capture_output=True, text=True, errors="replace")
    files = [ln.split(":", 1)[1] for ln in p.stdout.splitlines() if ":" in ln]
    pat = re.compile(rf"Spec:[^\n]*(?<![\w-]){re.escape(sid)}(?![\w-])")
    return sorted(f for f in files if _is_test(f) and pat.search(_git(repo, "show", f"{commit}:{f}", check=False)))


def _names(path: str, index: str, text: str) -> bool:
    """True when ``text`` (the markdown file ``index``) names ``path`` repo- or folder-relative."""
    return path in text or os.path.relpath(path, os.path.dirname(index) or ".") in text


def repo_history(repo: Path, spec_file: str = SPEC_FILE) -> dict:
    """Read each spec's status flips from git history (non-merge commits, oldest first).

    Args:
        repo: Deck repo root.
        spec_file: Repo-relative SPEC file.

    Returns:
        ``commits`` (``[{sha, time, parent}]``), ``flips`` (``{spec: [(sha, old, new)]}``)
        and ``current`` (``{spec: status}`` at HEAD).
    """
    rows = _git(repo, "log", "--reverse", "--topo-order", "--no-merges", "--format=%H %ct %P").splitlines()
    commits, flips = [], {}
    for ln in rows:
        sha, t, *parents = ln.split()
        commits.append({"sha": sha, "time": int(t), "parent": parents[0] if parents else None})
    for c in commits:
        now = _spec_at(repo, c["sha"], spec_file)
        before = _spec_at(repo, c["parent"], spec_file) if c["parent"] else {}
        for sid, st in now.items():
            if before.get(sid) != st:
                flips.setdefault(sid, []).append((c["sha"], before.get(sid), st))
    return {"commits": commits, "flips": flips, "current": _spec_at(repo, "HEAD", spec_file)}


def _cycle(hist: dict, sid: str) -> tuple[str | None, str | None]:
    """The spec's latest red (→ build) and done (→ done) commits of its current cycle."""
    flips = hist["flips"].get(sid, [])
    done = next((sha for sha, _, new in reversed(flips) if new == "done"), None)
    if hist["current"].get(sid) != "done":
        done = None
    order = [c["sha"] for c in hist["commits"]]
    limit = order.index(done) if done else len(order)
    red = next((sha for sha, old, new in reversed(flips) if new == "build" and order.index(sha) < limit
                and old in (None, "todo")), None)
    # a later reopen (done → todo) after this red belongs to a newer cycle with no red
    if red and any(new == "todo" and limit > order.index(sha) > order.index(red) for sha, _, new in flips):
        red = None
    return red, done


def _span(repo: Path, red: str | None, done: str | None) -> list[str]:
    if red and done:
        rows = _git(repo, "rev-list", "--reverse", "--no-merges", "--ancestry-path", f"{red}^..{done}", check=False)
        shas = rows.split()
        return shas if red in shas else [red] + shas
    if red:
        return [red] + _git(repo, "rev-list", "--reverse", "--no-merges", "--ancestry-path", f"{red}..HEAD").split()
    return [done] if done else []


def _time(hist, sha) -> int:
    return next(c["time"] for c in hist["commits"] if c["sha"] == sha)


# ---------- repo: test re-runs in throwaway worktrees ----------

def _test_cmd(wt: Path, test_cmd: str | None) -> list[str]:
    if test_cmd:
        return shlex.split(test_cmd)
    if (wt / "pyproject.toml").is_file():
        return ["uv", "run", "--directory", str(wt), "pytest"]
    return [sys.executable, "-m", "pytest"]


def _run_tests(repo: Path, commit: str, files: list[str], work: Path, tag: str, test_cmd: str | None) -> dict:
    """Run test files at a commit in a throwaway worktree; return per-test outcomes from JUnit XML."""
    wt = work / tag
    if wt.exists():
        shutil.rmtree(wt)
    work.mkdir(parents=True, exist_ok=True)
    _git(repo, "worktree", "add", "--detach", "--quiet", str(wt), commit)
    xml = work / f"{tag}.xml"
    try:
        proc = subprocess.run(_test_cmd(wt, test_cmd) + ["-q", "-p", "no:cacheprovider", f"--junitxml={xml}", *files],
                              cwd=wt, capture_output=True, text=True, timeout=900)
        tests, errors = {}, 0
        if xml.is_file():
            for tc in ET.parse(xml).getroot().iter("testcase"):
                name = re.sub(r"\[.*\]$", "", tc.get("name", ""))
                f, e = tc.find("failure"), tc.find("error")
                if e is not None:
                    errors += 1
                    outcome = "error"
                elif f is not None:
                    msg = (f.get("message") or "") + "\n" + (f.text or "")
                    outcome = "assert" if re.search(r"^\s*assert\b|AssertionError", msg, re.M) else "fail-other"
                elif tc.find("skipped") is not None:
                    outcome = "skipped"
                else:
                    outcome = "pass"
                tests.setdefault(name, outcome)
        return {"code": proc.returncode, "tests": tests, "errors": errors,
                "tail": (proc.stdout + proc.stderr).strip().splitlines()[-3:]}
    except subprocess.TimeoutExpired:
        return {"code": -1, "tests": {}, "errors": 1, "tail": ["timed out"]}
    finally:
        subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(wt)], capture_output=True)
        subprocess.run(["git", "-C", str(repo), "worktree", "prune"], capture_output=True)


def _defined_tests(repo: Path, commit: str | None, files: list[str]) -> set[str]:
    names = set()
    for f in files if commit else []:
        p = subprocess.run(["git", "-C", str(repo), "show", f"{commit}:{f}"], capture_output=True, text=True, errors="replace")
        names |= set(re.findall(r"^\s*(?:async\s+)?def\s+(test_\w+)", p.stdout, re.M))
    return names


# ---------- repo: per-criterion rules ----------

def _doc_indexed(repo: Path, commit: str, doc: str) -> bool:
    """True when some other markdown file at ``commit`` names ``doc`` (repo- or folder-relative)."""
    p = subprocess.run(["git", "-C", str(repo), "grep", "-l", "-F", doc.rsplit("/", 1)[-1], commit, "--", "*.md"],
                       capture_output=True, text=True, errors="replace")
    for ln in p.stdout.splitlines():
        f = ln.split(":", 1)[1]
        if f == doc:
            continue
        if _names(doc, f, _git(repo, "show", f"{commit}:{f}", check=False)):
            return True
    return False


INDEX_ROOTS = {"AGENTS.md", "CLAUDE.md", "README.md"}


def _pr03(repo, span) -> list[dict]:
    """Docs added or removed without an index edit naming them in the same commit; touched docs no
    index names. Whether the *other* docs a change affects were updated is a judge's call."""
    bad = []
    for sha in span:
        ch = _changes(repo, sha)
        edited_md = {p for st, p in ch if p.endswith(".md")}
        for st, p in ch:
            if not p.endswith(".md") or p in INDEX_ROOTS or p.startswith("evals/runs/"):
                continue
            if st in ("A", "D"):
                at = sha if st == "A" else f"{sha}^"  # an added doc is named after, a removed one before
                named = any(_names(p, f, _git(repo, "show", f"{at}:{f}", check=False)) for f in edited_md - {p})
                if not named:
                    bad.append({"commit": sha[:10], "file": p,
                                "note": f"doc {'added' if st == 'A' else 'removed'} without an index edit naming it"})
            elif st == "M" and not _doc_indexed(repo, sha, p):
                bad.append({"commit": sha[:10], "file": p, "note": "doc changed but no index names it"})
    return bad


def _sections(html: str) -> dict[str, str]:
    return {m.group(1): m.group(0) for m in re.finditer(
        r"<section\b[^>]*\bid\s*=\s*[\"']([^\"']+)[\"'][^>]*>.*?</section>", html, re.S | re.I)}


def _steps(section: str) -> int:
    nums = [int(n) for n in re.findall(r"data-(?:show-at|at|hide-at)\s*=\s*[\"'](\d+)", section)]
    return max(nums, default=0)


def _pr04(repo, hist, span, red, done, run_dir) -> tuple[list[dict], str]:
    decks = [p for sha in span for st, p in _changes(repo, sha)
             if p.endswith(".html") and _is_impl(p, "")]
    if not decks:
        return [], "not a visual spec: no deck change in its commits"
    start = span[0]
    base = f"{start}^" if _git(repo, "rev-list", "--parents", "-n1", start).split()[1:] else None
    affected = {}
    for d in sorted(set(decks)):
        new = _sections(_git(repo, "show", f"{done}:{d}", check=False))
        old = _sections(_git(repo, "show", f"{base}:{d}", check=False)) if base else {}
        for sid, sec in new.items():
            if old.get(sid) != sec:
                affected[sid] = _steps(sec)
    lo, hi = _time(hist, start), _time(hist, done)
    shots = {}
    run_dir = Path(run_dir).resolve()
    for p in Path(repo).rglob("*.png"):
        if ".git" in p.parts or run_dir in p.resolve().parents:
            continue
        m = re.fullmatch(r"(.+)-(\d+)-(\d+x\d+)\.png", p.name)
        if m:
            t = p.stat().st_mtime
            if lo <= t <= hi:
                shots[(m[1], int(m[2]), m[3])] = p
    sizes = [guard_mod.size_id(s) for s in guard_mod.REVIEW_SIZES]
    bad = [{"commit": done[:10], "slide": sid, "step": k, "size": size,
            "note": "no screenshot of this state dated between the red and done commits"}
           for sid, last in sorted(affected.items()) for k in range(last + 1) for size in sizes
           if (sid, k, size) not in shots]
    return bad, f"{sum((v + 1) * 3 for v in affected.values())} slide-step-size shots dated within red..done"


SKIP_LINE = re.compile(r"^\+\s*(@pytest\.mark\.(skip|skipif|xfail)\b|pytest\.(skip|xfail)\(|pytestmark\s*=.*\b(skip|xfail))")
GUARD_TEST = re.compile(r"layout[_ ]guard", re.I)


def _pr09(repo, hist) -> list[dict]:
    """Skip/xfail decorators, calls or module marks added to a test file that runs the layout guard.
    Parametrised per-case marks (a declared pending list) are not flagged: whether a pending slide
    was under work is a judge's call."""
    bad = []
    for c in hist["commits"]:
        diff = _git(repo, "show", "--format=", "-U0", c["sha"])
        path = None
        for ln in diff.splitlines():
            if ln.startswith("+++ "):
                path = ln[6:] if ln.startswith("+++ b/") else None
            elif path and _is_test(path) and SKIP_LINE.search(ln):
                text = _git(repo, "show", f"{c['sha']}:{path}", check=False)
                if GUARD_TEST.search(text):
                    bad.append({"commit": c["sha"][:10], "file": path, "note": f"layout check disabled: {ln[1:].strip()[:80]}"})
    return bad


def _ar07(repo: Path, deck: Path) -> list[dict]:
    markup = _slides_markup(deck.read_text(encoding="utf-8"))[0]
    used = set()
    for m in re.finditer(r"\bclass\s*=\s*[\"']([^\"']*)[\"']", markup):
        used |= set(m.group(1).split())
    used |= set(re.findall(r"\s(data-[\w-]+)\s*=", markup)) | set(re.findall(r"\s(data-[\w-]+)(?=[\s>])", markup))
    docs = "\n".join(p.read_text(encoding="utf-8") for p in CONTRACT_DOCS if p.is_file())
    docs += "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in (Path(repo) / "docs").rglob("*.md"))
    return [{"file": deck.name, "note": f"{u!r} is used in slides but named in no contract doc"}
            for u in sorted(used) if not re.search(rf"(?<![\w-]){re.escape(u)}(?![\w-])", docs)]


def repo_verdicts(repo: Path, criteria: list[dict], run_dir: Path, rerun: bool = True,
                  deck: Path | None = None, test_cmd: str | None = None,
                  spec_file: str = SPEC_FILE) -> tuple[list[dict], dict[str, str]]:
    """Check repo-target ``D`` criteria from git history (read-only on the repo).

    Args:
        repo: Deck repo root.
        criteria: Resolved criteria; only repo-target ones with a rule are checked.
        run_dir: The run folder (worktrees and test reports go under its ``evidence/``).
        rerun: Re-run each spec's tests at its red and done commits (PR-02).
        deck: The deck file, for AR-07.
        test_cmd: Command that runs pytest in a checkout (default: ``uv run pytest`` when the
            checkout has ``pyproject.toml``, else this interpreter's ``pytest``).
        spec_file: Repo-relative SPEC file.

    Returns:
        Verdicts, and ``{criterion: reason}`` for in-scope criteria that got none.
    """
    repo = Path(repo)
    todo = [c for c in criteria if c["id"] in CHECKS and c["target"] == "repo"]
    missing: dict[str, str] = {}
    if not todo:
        return [], missing
    hist = repo_history(repo, spec_file)
    work = Path(run_dir) / "evidence" / "worktrees"
    specs = [s for s, st in hist["current"].items() if st in ("build", "done")]
    out = []
    for c in todo:
        cid, rule = c["id"], CHECKS[c["id"]]
        if cid == "PR-09":
            out.append(_verdict(c, "deck", _pr09(repo, hist),
                                {"file": "tests/", "note": f"no skip/xfail added to a layout test in {len(hist['commits'])} commits"}, rule))
            continue
        if cid == "AR-07":
            if not deck:
                missing[cid] = "needs the deck (--deck) as well as the repo"
                continue
            out.append(_verdict(c, "deck", _ar07(repo, Path(deck)),
                                {"file": Path(deck).name, "note": "every class and data attribute is in the contract"}, rule))
            continue
        if cid == "PR-02" and not rerun:
            missing[cid] = "skipped: --no-rerun (tests not re-run at red and done)"
            continue
        if not specs:
            missing[cid] = f"no spec in {spec_file} has reached build or done"
            continue
        for sid in specs:
            red, done = _cycle(hist, sid)
            anchor = done or red
            ok_loc = {"commit": (anchor or "HEAD")[:10], "file": spec_file}
            bad = []
            if cid == "PR-01":
                if not red:
                    bad.append({"commit": (done or "HEAD")[:10], "file": spec_file,
                                "note": f"{sid} never flipped todo→build before {'done' if done else 'now'}: no red commit"})
                else:
                    ch = _changes(repo, red)
                    marked = set(_marked(repo, red, sid))
                    if not marked & {p for _, p in ch}:
                        bad.append({"commit": red[:10], "note": f"red commit adds or changes no test marked Spec: {sid}"})
                    bad += [{"commit": red[:10], "file": p, "note": "implementation file changed in the red commit"}
                            for _, p in ch if _is_impl(p, spec_file)]
                ok_loc = {"commit": (red or "")[:10], "file": spec_file,
                          "note": f"red commit flips {sid} to build with its tests only, before done"}
            elif cid == "PR-02":
                if not red:
                    bad.append({"commit": (done or "HEAD")[:10], "note": f"no red commit for {sid} to re-run"})
                else:
                    files = _marked(repo, red, sid)
                    r = _run_tests(repo, red, files, work, f"{_slug(sid)}-red", test_cmd) if files else None
                    if not files:
                        bad.append({"commit": red[:10], "note": f"no test file marked Spec: {sid} at the red commit"})
                    else:
                        before = _defined_tests(repo, hist_parent(hist, red), files)
                        new = {n: o for n, o in r["tests"].items() if n not in before} or r["tests"]
                        if r["errors"] or r["code"] not in (1,):
                            bad.append({"commit": red[:10], "file": files[0],
                                        "note": f"red run exit {r['code']} with {r['errors']} error(s): {' | '.join(r['tail'])[:140]}"})
                        bad += [{"commit": red[:10], "file": files[0], "note": f"{n} {o} at red (needs an assertion failure)"}
                                for n, o in sorted(new.items()) if o != "assert"]
                    if done and files:
                        dfiles = _marked(repo, done, sid)
                        d = _run_tests(repo, done, dfiles, work, f"{_slug(sid)}-done", test_cmd)
                        if d["code"] != 0:
                            bad.append({"commit": done[:10], "file": dfiles[0] if dfiles else "",
                                        "note": f"spec tests do not pass at done (exit {d['code']}): {' | '.join(d['tail'])[:120]}"})
                ok_loc = {"commit": (red or "")[:10], "note": "new tests fail on assertions at red"
                          + (" and pass at done" if done else "")}
            elif cid == "PR-03":
                span = _span(repo, red, done)
                bad = _pr03(repo, span)
                ok_loc = {"commit": (anchor or "")[:10], "note": f"{len(span)} commit(s): every doc change lands with its index row"}
            elif cid == "PR-04":
                if not done:
                    missing.setdefault(cid, "")
                    continue
                span = _span(repo, red, done)
                bad, what = _pr04(repo, hist, span, red, done, run_dir)
                ok_loc = {"commit": done[:10], "note": what}
            out.append(_verdict(c, sid, bad, ok_loc, rule))
        if cid == "PR-04" and missing.get(cid) == "":
            if any(v["criterion"] == cid for v in out):
                missing.pop(cid)
            else:
                missing[cid] = "no spec is done yet"
    if work.exists() and not any(work.iterdir()):
        work.rmdir()
    return out, missing


def hist_parent(hist: dict, sha: str) -> str | None:
    """First parent of a commit in the walked history.

    Args:
        hist: Output of ``repo_history``.
        sha: Commit id.

    Returns:
        The parent id, or ``None`` for a root commit.
    """
    return next((c["parent"] for c in hist["commits"] if c["sha"] == sha), None)


# ---------- run ----------

def pptx_verdicts(pptx: Path, criteria: list[dict], scene: Path | None = None,
                  report: Path | None = None) -> list[dict]:
    """Check pptx-target ``D`` criteria with the PPTX part's own checks (``pptx/scripts/check.py``).

    Args:
        pptx: The emitted ``.pptx``.
        criteria: Resolved criteria; only pptx-target ones are kept.
        scene: The deck's scene JSON (default: ``<stem>.scene.json`` beside the file).
        report: The emitter's report (default: ``<stem>.pptx-report.json`` beside the file).

    Returns:
        Verdicts in the judge format (``insufficient-evidence`` where the scene or report is needed
        and missing).

    Raises:
        ValueError: When the file cannot be opened as a presentation.
    """
    want = {c["id"] for c in criteria if c["target"] == "pptx"}
    if not want:
        return []
    check = _load("skill_gates_pptx_check", PPTX_CHECK)
    try:
        vs = check.verdicts(Path(pptx), scene, report)
    except check.CheckError as e:
        raise ValueError(str(e)) from e
    return [v for v in vs if v["criterion"] in want]


PPTX_RENDERERS = ("soffice", "libreoffice")
NO_RENDERER = ("no PPTX renderer: LibreOffice (soffice) is not on PATH, so no image of the PPTX exists for "
               "its judges; install LibreOffice and render it (EVAL.md §2), or leave the criterion missing")


def pptx_renderer() -> str | None:
    """Name of the PPTX renderer on PATH (LibreOffice's ``soffice``), or None when none is installed."""
    return next((name for name in PPTX_RENDERERS if shutil.which(name)), None)


def _judge_inputs(prof: dict, library: dict, concerns: list[str], pptx: Path | None) -> dict:
    """What the judged (``S``/``T``) PPTX criteria in scope need beyond the file: a renderer.

    Returns:
        ``{criterion: {"renderer": name}}`` or ``{criterion: {"missing": reason}}`` for each
        in-scope judged pptx criterion (e.g. PX-06), when a ``.pptx`` is given; else ``{}``.
    """
    if not pptx:
        return {}
    judged = [c["id"] for c in crit_mod.resolve(prof, library)
              if c["target"] == "pptx" and c["evidence"] != "D" and c["concern"] in concerns]
    renderer = pptx_renderer()
    return {cid: ({"renderer": renderer} if renderer else {"missing": NO_RENDERER}) for cid in judged}


def run_gates(run_dir: Path, *, deck: Path | None = None, repo: Path | None = None,
              pptx: Path | None = None, scene: Path | None = None, report: Path | None = None,
              profile: str | None = None, concerns: list[str] | None = None, rerun: bool = True,
              sizes=guard_mod.REVIEW_SIZES, test_cmd: str | None = None, browser=None,
              eval_dir: Path = EVAL_DIR) -> dict:
    """Run every in-scope ``D`` criterion and write its verdicts into ``<run_dir>/verdicts/``.

    Args:
        run_dir: The run folder (created if needed); ``manifest.json`` there supplies a missing
            profile or concerns.
        deck: Deck HTML file (deck-target criteria, and AR-07).
        repo: Deck repo root (repo-target criteria).
        pptx: Emitted ``.pptx`` (pptx-target criteria, through ``pptx/scripts/check.py``).
        scene: The PPTX's scene JSON (default: the sidecar beside ``pptx``).
        report: The emitter's report (default: the sidecar beside ``pptx``).
        profile: Profile id (default: the manifest's).
        concerns: Concerns in scope (default: the manifest's, else all).
        rerun: Re-run spec tests at red and done (PR-02).
        sizes: Review sizes for the deck checks.
        test_cmd: Override for the pytest command used in re-runs.
        browser: Optional launched Playwright browser to reuse.
        eval_dir: Eval folder holding the library and profiles.

    Returns:
        The gate log also written to ``evidence/gates.json``: scope, written verdict files and,
        per in-scope ``D`` criterion, ``checked`` units/fails or ``missing`` with the reason.

    Raises:
        ValueError: With no deck, pptx or repo, an unknown profile, a missing path, or an unreadable pptx.
    """
    run_dir = Path(run_dir)
    manifest = {}
    if (run_dir / "manifest.json").is_file():
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    profile = profile or manifest.get("profile")
    concerns = concerns or manifest.get("concerns") or list(crit_mod.CONCERN_PREFIX)
    if not profile:
        raise ValueError("no profile: pass --profile or write manifest.json first")
    if not deck and not repo and not pptx:
        raise ValueError("nothing to check: give a deck, a pptx and/or a repo")
    for p, what in ((deck, "deck"), (repo, "repo"), (pptx, "pptx"), (scene, "scene"), (report, "report")):
        if p and not Path(p).exists():
            raise ValueError(f"{what} not found: {p}")
    library = crit_mod.load_library(eval_dir)
    prof_path = Path(eval_dir) / "profiles" / f"{profile}.json"
    if not prof_path.is_file():
        raise ValueError(f"unknown profile {profile!r}")
    prof = crit_mod.load_profile(prof_path, library)
    scope = [c for c in crit_mod.resolve(prof, library) if c["evidence"] == "D" and c["concern"] in concerns]
    cov = coverage(library)
    verdicts, missing = [], {}
    if deck:
        verdicts += deck_verdicts(Path(deck), scope, sizes, browser)
    if pptx:
        verdicts += pptx_verdicts(Path(pptx), scope, scene, report)
    if repo:
        vs, miss = repo_verdicts(Path(repo), scope, run_dir, rerun, deck, test_cmd)
        verdicts += vs
        missing |= miss
    vdir = run_dir / "verdicts"
    vdir.mkdir(parents=True, exist_ok=True)
    written = []
    for v in verdicts:
        path = vdir / f"{v['criterion']}_{_slug(v['unit'])}_r1.json"
        path.write_text(json.dumps(v, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        written.append(path.name)
    log = {"tool": "gates", "version": 1, "deck": str(deck) if deck else None,
           "pptx": str(pptx) if pptx else None,
           "repo": str(repo) if repo else None, "profile": profile, "concerns": concerns,
           "rerun": rerun, "verdicts": written, "criteria": {},
           "judge_inputs": _judge_inputs(prof, library, concerns, pptx)}
    for c in scope:
        cid = c["id"]
        mine = [v for v in verdicts if v["criterion"] == cid]
        if mine:
            log["criteria"][cid] = {"checked": cov[cid]["checked"], "units": len(mine),
                                    "fail": sum(v["result"] == "fail" for v in mine)}
        else:
            given = {"deck": deck, "repo": repo, "pptx": pptx}[c["target"]]
            reason = missing.get(cid) or cov[cid].get("missing") or (
                "checked, but the target has no unit to judge" if given else
                f"target {c['target']} not given (pass --{c['target']})")
            log["criteria"][cid] = {"missing": reason}
    ev = run_dir / "evidence"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "gates.json").write_text(json.dumps(log, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return log


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Arguments (defaults to ``sys.argv[1:]``).

    Returns:
        0 every verdict passes, 1 any fails, 2 usage error or unusable input.
    """
    ap = argparse.ArgumentParser(description="Run the eval's deterministic (D) gates on a deck and/or a deck repo.")
    ap.add_argument("run_dir", type=Path, help="run folder (evals/runs/yymmdd-label/ in the deck project)")
    ap.add_argument("--deck", type=Path, help="assembled deck HTML file")
    ap.add_argument("--pptx", type=Path, help="emitted .pptx (PX criteria via pptx/scripts/check.py)")
    ap.add_argument("--scene", type=Path, help="the .pptx's scene JSON (default: <stem>.scene.json beside it)")
    ap.add_argument("--report", type=Path, help="the emitter report (default: <stem>.pptx-report.json beside it)")
    ap.add_argument("--repo", type=Path, help="deck repo root (git)")
    ap.add_argument("--profile", help="profile id (default: the run manifest's)")
    ap.add_argument("--concerns", help="comma-separated concerns (default: the manifest's, else all)")
    ap.add_argument("--sizes", default=",".join(guard_mod.size_id(s) for s in guard_mod.REVIEW_SIZES))
    ap.add_argument("--no-rerun", action="store_true", help="do not re-run spec tests (PR-02 left missing)")
    ap.add_argument("--test-cmd", help="pytest command for re-runs, e.g. 'uv run pytest'")
    args = ap.parse_args(argv)
    try:
        log = run_gates(args.run_dir, deck=args.deck, repo=args.repo, pptx=args.pptx, scene=args.scene,
                        report=args.report, profile=args.profile,
                        concerns=args.concerns.split(",") if args.concerns else None,
                        rerun=not args.no_rerun, sizes=guard_mod.parse_sizes(args.sizes), test_cmd=args.test_cmd)
    except (ValueError, guard_mod.ToolError) as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 2
    fails = 0
    for cid, c in log["criteria"].items():
        if "missing" in c:
            print(f"MISSING {cid}: {c['missing']}")
        else:
            fails += c["fail"]
            print(f"{'FAIL' if c['fail'] else 'PASS'} {cid}: {c['units']} unit(s), {c['fail']} failed")
    print(f"wrote {len(log['verdicts'])} verdict(s) to {args.run_dir / 'verdicts'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
