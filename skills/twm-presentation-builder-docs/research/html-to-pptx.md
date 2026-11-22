# HTML → editable PPTX: feasibility and toolchain

Researched 2026-11-22 for the PPTX sub-skill. Goal: an **editable hand-off** (native text,
placeholders, shapes) from a single-file HTML deck like `deck/deck-v2.html`; fidelity is secondary.
Claims marked *probe* were checked by running python-pptx 1.0.2 locally; *source* means read in
the library's code.

## 1. TL;DR for our design

**Feasible, and it is the path the field has settled on.** Anthropic's own pptx skill shipped exactly
this pipeline (Playwright reads `getComputedStyle`/`getBoundingClientRect` and PptxGenJS writes
shapes) [2][3]. So do Slidev's `pptx-editable` and dom-to-pptx [15][16]. No converter does masters,
placeholders, theme slots or Morph, so we write our own emitter. Off-the-shelf tools only show
what to borrow.

**Recommended toolchain (Python, uv):**

1. **Measure:** run Playwright (already in `tests/`). Step the deck engine through every
   `data-show-at`/`data-at` step. At each step, dump a JSON "scene" per slide: component role, box
   geometry, computed text runs, colours resolved to `:root` token names, SVG primitives with their
   transforms applied, and `aside.note` text.
2. **Emit:** use **python-pptx 1.0.2** [5] plus **lxml XML injection** for what it lacks: alpha,
   soft edge, glow, shadow, Bézier freeforms, svgBlip, Morph and the theme palette. Start from a
   **seed template `.pptx` per design theme** that already holds the master, named layouts and
   placeholders [6]. python-pptx can fill layouts but cannot create them.
3. **Verify:** read the file back with python-pptx (structure tests). Run Anthropic's
   `validate.py`, now Apache 2.0, so it can be vendored [1][4]. Render with LibreOffice → PDF →
   `pdftoppm` PNGs for screenshot judging [1].

PptxGenJS is the credible alternative (it writes layouts, SVG+PNG fallback and gradients badly; see
§2.2). Choose it only if we accept a Node emitter.

### Mapping table

| HTML feature (deck-v2) | PPTX result | Mechanism / ref |
| --- | --- | --- |
| Slide title, lead slide, columns, tile row | **Native**: one named layout each, with title/body/pic placeholders (`ph type`, `idx`) | Seed template layouts; python-pptx fills by placeholder [6][7] |
| Body copy, mixed runs (italic, bold, colour) | **Native** text runs; line wraps may shift | python-pptx runs; browser vs PowerPoint metrics differ [16] |
| `:root` palette tokens | **Native** theme slots `dk1/lt1/dk2/lt2/accent1–6`; shapes use `schemeClr` | Edit `theme1.xml` `a:clrScheme` (python-pptx has no API; Anthropic's `apply_theme.js` does the same) [1]; theme refs via `MSO_THEME_COLOR` (*probe*) |
| Newsreader / Inter (embedded woff2) | **Approximated**: theme major/minor fonts by name; the font is not embedded, so it falls back if not installed | `+mj-lt`/`+mn-lt` [1]; Slidev also only references fonts [16] |
| Rounded-rect nodes, tiles | **Native** `roundRect` with adjustment = radius / short side | python-pptx `adjustments[0]` (*probe*); same formula in html2pptx [2] |
| SVG `<line>`, arrows between nodes | **Native** connectors (`begin_connect`/`end_connect`), `a:tailEnd` arrowheads via XML | Connect is "EXPERIMENTAL", reliable only on rectangular shapes [5] |
| SVG `<path>` with curves | **Native** freeform: python-pptx draws lines only; inject `a:cubicBezTo`/`a:arcTo` into `custGeom` | `FreeformBuilder` has `add_line_segments`/`move_to` only (*probe*, [5]); PptxGenJS writes `cubicBezTo`/`arcTo` (*source*) |
| SVG `<text>` labels | **Native** text boxes inside the diagram group | — |
| Diagram as a whole | **Native** named group (`add_group_shape`); fallback is a **picture**: SVG with PNG fallback | `asvg:svgBlip` in `a:blip/a:extLst` ext `{96DAC541-7B7A-43D3-8B79-37D633B846F1}` (*source*, PptxGenJS); python-pptx `add_picture` rejects SVG (*probe*) |
| CSS gradient fills | **Native** `gradFill` | python-pptx `fill.gradient()` (*probe*); PptxGenJS cannot [1] |
| `rgba()` / opacity | **Native** `a:alpha` on the colour (XML) | No python-pptx API; PptxGenJS `transparency` [1] |
| `box-shadow` (outer) | **Native** `a:outerShdw` (XML); inset is **lost** | python-pptx `ShadowFormat` only has `inherit` (*probe*); html2pptx drops inset [2] |
| `filter: blur()` on bokeh circles | **Approximated, editable**: ellipse + `a:softEdge` + alpha; drift animation **lost** | dom-to-pptx maps blur → soft edges [15] |
| `backdrop-filter: blur()` glass cards | **Approximated**: translucent fill (+ optional blurred background crop picture behind it); or **lost** (flat tint). Declared per theme | §2.4 |
| `@keyframes` / per-step reveals | **Native-ish**: one slide per step, same `!!names`, Morph transition; keyframe motion **lost** | [10][11][12]; Slidev also emits one slide per click [16] |
| Persistent "incident world" (`data-world-at`) | Shapes repeat across slides under stable `!!names`, so Morph animates them between slides | [12] |
| `aside.note` reader notes | **Native** speaker notes | `notes_slide.notes_text_frame` (*probe*) |
| `clip-path`, `mix-blend-mode`, SVG `<filter>` | **Lost** or picture fallback | Slidev rasterises these too [16] |

## 2. Findings

### 2.1 python-pptx (1.0.2, current on PyPI)

- **Shapes:** `add_shape`, `add_connector`, `add_group_shape`, `build_freeform`, `add_picture`,
  `add_table`, `add_chart` and `add_movie` all exist. Shapes, groups and names read back correctly
  (*probe*). The freeform builder does straight segments only [5]. Connector gluing is experimental
  and misaligns on non-rectangular shapes [5]. In our diagrams, compute endpoints from Chrome
  geometry and glue only to rect/roundRect.
- **Layouts:** layouts are reached by index or name. Nothing creates a layout or master [6]. Its
  dev docs describe how layout placeholders inherit [7]. Two workarounds: (a) a **seed template**
  authored once (in PowerPoint, or generated) with our layouts. This is best, because the layout
  names are what a colleague sees and what the corporate-template remap keys on. (b) **Clone a
  `slideLayoutN.xml` part** with lxml and register it in the master's `sldLayoutIdLst` and the
  rels. Anthropic's `add_slide.py` does this bookkeeping for layouts as well as slides [1]. Round-
  trip the XML with lxml or `defusedxml`. Anthropic warns that `ElementTree` rewrites namespace
  prefixes and corrupts decks [1].
- **Gaps that need XML:** alpha, shadow/glow/soft edge (`ShadowFormat` exposes only `inherit`),
  the theme palette, SVG, transitions, and slide duplication [1][5]. That last one doesn't block
  us: we emit every step slide fresh from its scene.
- **Theme colours:** python-pptx can *reference* theme slots but not *define* them. So we write
  `a:clrScheme` in `theme1.xml`. That one edit gives the colleague real "Design → Variants"
  recolouring.
- **Notes:** speaker notes work natively and read back (*probe*).

### 2.2 PptxGenJS (4.0.1) and html2pptx

- PptxGenJS writes SVG images as `svgBlip`, plus a PNG `a:blip` fallback relationship. That gives
  two rIds per SVG (*source*). It also writes custom geometry with `cubicBezTo`/`arcTo`, text glow
  and notes (*source*). It has **no transition support**: the string "transition" does not appear
  in the bundle (*source*). It has **no gradient fills** [1]. `defineSlideMaster()` makes a
  *layout* under one fixed master [1]. It can't write theme colours, which is why Anthropic added
  `apply_theme.js` [1].
- **Anthropic's html2pptx** (Dec 2025) used Playwright plus PptxGenJS, with strict authoring rules:
  all text in `<p>`/`<h*>`/lists, shapes only on `div`s, no CSS gradients, web-safe fonts, and
  overflow and dimension validation [2][3]. By July 2026 it was **removed**. The skill now writes
  PptxGenJS "structured decks" directly (theme first, one layout per frame, placeholders filled by
  name, sections) and keeps LibreOffice-based visual QA [1][4]. The lesson: generic HTML→PPTX was
  dropped in favour of semantic emission. Our component vocabulary (title / lead / columns / tile
  row) already gives us semantics, so we should emit from **roles**, not raw DOM. Chrome supplies
  geometry only.

### 2.3 Other converters

- **dom-to-pptx** (2.1.x, MIT, on PptxGenJS): emits computed-style, absolutely positioned native
  shapes. It handles gradients, shadows, blur→soft edge, fonts, `data-pptx-notes` and some
  animations [15]. It has no masters, placeholders or theme colours, and SVG is rasterised by
  default [15]. Mine it for CSS→DrawingML formulas.
- **Slidev `pptx-editable`:** measures in the browser and rebuilds shapes. It turns SVG, gradients
  and filter/clip effects into pictures. It falls back to a full-slide image when a slide is mostly
  pictures. It carries notes and emits one slide per click [16]. This is the closest prior art for
  our step model.
- **Marp `--pptx-editable`:** experimental and goes via LibreOffice. It has lower fidelity, may
  fail on complex themes, **drops notes**, and its maintainers advise against it when appearance
  matters [17]. Default Marp/Slidev PPTX is background images: not editable [16][17].
- **reveal.js:** no first-party PPTX path. Only PDF via print/DeckTape, so it is not editable (no
  source needed; nothing to adopt).
- **Aspose.Slides `AddFromHtml`:** commercial. It imports mainly text into text frames; images,
  tables and layout are poorly supported per Aspose's own forum [18]. Not suitable.
- **LibreOffice:** useful for rendering, but has no Morph [19]. It is not an HTML→slides importer.

### 2.4 Blur and frosted glass in PowerPoint

- **Picture blur** is native: Artistic Effects → Blur, radius 0–100. This is
  `a14:artisticBlur` (`CT_PictureEffectBlur`, namespace `…/office/drawing/2010/main`) inside the
  picture's `a14:imgProps` extension [13][14]. It applies to **pictures only**, and is **not shown
  in PowerPoint for the web** [14].
- **Soft edges, glow, shadows and alpha** work on any shape and stay editable.
- **Frosted-glass approximation:** crop a picture of the slide background (shot by Playwright with
  the card hidden) to the card box, apply `artisticBlur`, and place a translucent roundRect on top,
  grouped as `!!card-name`. This is editable (the colleague can delete the picture or change the
  tint). But the picture is a **snapshot**: if the card or background moves, it goes stale, and it
  breaks in a corporate template with a different background. Recommendation: themes declare
  `glass: tint`, a flat translucent fill. This is the default for the hand-off. `glass: snapshot`
  is opt-in. Bokeh blobs → soft-edged translucent ellipses, which are cheap and fully native.

### 2.5 Morph for build steps

- Morph lives in `p:transition` as `p159:morph`, namespace
  `http://schemas.microsoft.com/office/powerpoint/2015/09/main`. It is wrapped in
  `mc:AlternateContent` with a plain-transition `mc:Fallback` [10][11]. The spec's sample uses
  `option="byObject"` [11]; `byWord`/`byChar` (the UI's Words/Characters) are assumed, not verified here. A bare `p:transition` without the wrapper is reported
  as corrupting files [20]. python-pptx has no API; the diff is just this block [8]. Shape:

  ```xml
  <mc:AlternateContent xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006">
    <mc:Choice xmlns:p159="http://schemas.microsoft.com/office/powerpoint/2015/09/main" Requires="p159">
      <p:transition spd="slow"><p159:morph option="byObject"/></p:transition>
    </mc:Choice>
    <mc:Fallback><p:transition spd="slow"><p:fade/></p:transition></mc:Fallback>
  </mc:AlternateContent>
  ```

- **`!!` naming:** objects of the same type, with the same name starting `!!`, on consecutive
  slides are force-matched. Names should be unique per slide. `!!` never matches a non-`!!`
  object. Charts cross-fade. Supported in Microsoft 365, 2019 and web; 2016 only plays it [12].
  Our scene IDs (`#s10-agency` etc.) map straight to `!!s10-agency`.

### 2.6 Testing PPTX output

- **Structure (pytest, deterministic):** reopen with python-pptx and assert on the result: every
  slide uses a named layout, title placeholders are filled, the editable ratio is high (pictures ≤
  N per slide), `!!` names match across step slides, the notes match the `aside.note` count, the
  theme `clrScheme` equals the tokens, and the Morph block is present. Also run the vendored
  `validate.py` (schema, rels, content types) [1][4].
- **Visual (LLM/eye judging):** `soffice --headless --convert-to pdf` → `pdftoppm -r 150` [1].
  Caveats: LibreOffice substitutes fonts with different metrics [1]; it ignores Morph [19]; it may
  not draw `artisticBlur`. So treat its PNGs as layout and overflow checks, not as a fidelity
  verdict.

## 3. Risks / open questions

1. **Text reflow:** PowerPoint measures text differently from Chrome [16]. Mitigate with autofit
   off, ~10% box slack [1] and an overflow check in the LibreOffice render.
2. **Fonts:** Newsreader and Inter won't be on a colleague's machine. Should themes name a
   fallback pair (e.g. Cambria/Calibri, both QA-safe [1]), or should we rely on the corporate
   template's theme fonts taking over?
3. **Corporate-template drop-in:** we assume "Reuse slides / use destination theme" re-flows
   placeholder content into the destination's same-named or same-type layouts, while free shapes
   keep absolute positions. *Unverified*: test this in PowerPoint before relying on it.
4. **Slide explosion:** per-step slides multiply the slide count (deck-v2 has 86 `data-show-at`
   hooks). Should step slides be grouped into PowerPoint sections, or offered as "final state only"
   plus a separate "animated" variant?
5. **Glued connectors** on roundRects can misalign [5]. Should connectors be unglued with
   computed endpoints?
6. **`artisticBlur` ext URI** (`a14:imgProps` extension GUID) was not confirmed from the spec
   here. Copy it from a PowerPoint-saved sample before use.
7. **True rendering:** PowerPoint for Mac is installed locally. Could AppleScript export PNGs as an
   optional high-fidelity check (Morph, blur)? CI can't rely on it.
8. **SVG fallback in python-pptx:** we must write the svgBlip XML and the PNG fallback ourselves
   (Chrome element screenshot for the PNG). PptxGenJS's in-Node PNG fallback behaviour was not
   verified.

## 4. Sources

1. Anthropic, *pptx skill SKILL.md* (commit e4bb5d9), 2026. https://github.com/anthropics/skills/blob/main/skills/pptx/SKILL.md
2. Anthropic, *html2pptx.md* (commit ef74077), 2025. https://github.com/anthropics/skills/blob/ef740771ac901e03fbca3ce4e1c453a96010f30a/skills/pptx/html2pptx.md
3. Anthropic, *scripts/html2pptx.js* (commit ef74077), 2025. https://github.com/anthropics/skills/blob/ef740771ac901e03fbca3ce4e1c453a96010f30a/skills/pptx/scripts/html2pptx.js
4. Anthropic, *Update docx, pptx, and xlsx skills (#1447)* and *Move Office skills to Apache 2.0 (#2146)*, 2026. https://github.com/anthropics/skills/commits/main/skills/pptx
5. python-pptx, *Shapes API* (1.0.2), 2024. https://python-pptx.readthedocs.io/en/latest/api/shapes.html
6. python-pptx, *Working with Slides*, 2024. https://python-pptx.readthedocs.io/en/latest/user/slides.html
7. python-pptx, *Layout Placeholders (analysis)*, 2024. https://python-pptx.readthedocs.io/en/latest/dev/analysis/placeholders/layout-placeholders.html
8. python-pptx issue #942, *Morph transition*, n.d. https://github.com/scanny/python-pptx/issues/942
9. PptxGenJS 4.0.1, npm package source and *Images API*, 2025. https://www.npmjs.com/package/pptxgenjs · https://gitbrent.github.io/PptxGenJS/docs/api-images/
10. Microsoft, *[MS-PPTX] 2.2.1 Slide Transition Extensions*, 2024. https://learn.microsoft.com/en-us/openspecs/office_standards/ms-pptx/22ebe6b5-2ade-43d9-977a-98fa194725c2
11. Microsoft, *[MS-PPTX] morph*, 2024. https://learn.microsoft.com/en-us/openspecs/office_standards/ms-pptx/68d26d78-f7f5-47ab-835d-4e6c82ff39f0
12. Microsoft Support, *Morph transition: Tips and tricks*, n.d. https://support.microsoft.com/en-us/office/bc7f48ff-f152-4ee8-9081-d3121788024f
13. Microsoft, *[MS-ODRAWXML] CT_PictureEffectBlur*, 2026. https://learn.microsoft.com/en-us/openspecs/office_standards/ms-odrawxml/07f6e960-2b69-4c13-9e4e-377f425415f1
14. Microsoft Support, *Blur a picture in Word or PowerPoint*, n.d. https://support.microsoft.com/en-gb/office/blur-a-picture-in-word-or-powerpoint-837e04d6-b1ed-4969-a79f-ee778c435f7c
15. dom-to-pptx, *README* (2.1.2), 2026. https://cdn.jsdelivr.net/npm/dom-to-pptx@2.1.2/README.md
16. Slidev, *Exporting*, 2026. https://sli.dev/guide/exporting
17. Marp team, *marp-cli README*, 2026. https://github.com/marp-team/marp-cli
18. Aspose, *SlideCollection.AddFromHtml* and forum *HTML to pptx import*, n.d. https://reference.aspose.com/slides/net/aspose.slides/slidecollection/addfromhtml · https://forum.aspose.com/t/html-to-pptx-import/9425
19. LibreOffice Bugzilla #116736, *Morph-style transitions*, n.d. https://www.libreoffice.org/bugzilla/show_bug.cgi?id=116736
20. Apache Bugzilla #66705, *POI morph transition written without AlternateContent* (search summary; page behind login), n.d. https://bz.apache.org/bugzilla/show_bug.cgi?id=66705
