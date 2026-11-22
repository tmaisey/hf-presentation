# Design tokens: layering palette, style and components so themes swap cleanly

Researched 2026-11-22. Question: how mature design systems tier tokens and keep palette,
typography/effects and components separate, and how that maps to our three design layers plus an
architecture contract and an editable PPTX theme.

## 1 · TL;DR for our design

**Adopt the W3C DTCG 2025.10 format as the single source, with three tiers and one file per design
layer.** The format is stable, has a Resolver module for themes/modes, and ships with reference
tooling [1][2][3].

| Tier (Material naming [6]) | Holds | Our layer | Example (current deck token → tier) |
| --- | --- | --- | --- |
| **ref** (primitive) | Raw values with no meaning: hexes, font stacks, curves, blur radii | Palette + style files | `#86BC25` → `ref.green.500` |
| **sys** (semantic role) | Roles that components may consume: `paper`, `ink`, `ink-2`, `accent`, `accent-ink`, `loss`, `alarm`, `fs-title`, `ease`, `shadow-lift`, `frost` | Palette (colour roles) + style (type, depth, motion) | `--accent-ink` → `sys.color.accent-text` |
| **comp** (component) | Component-scoped aliases of sys tokens only | Layout/components | `.bar` frost → `comp.bar.surface = {sys.material.frost}` |

Proposed file split (sources compiled into the single-file deck):

- `tokens/palette/<name>.tokens.json`: `ref.color.*` plus `sys.color.*` roles, each role carrying
  its usage rule (e.g. "accent: fill/stroke only, **never text** (2.05:1 on paper)") in
  `$description`, and its PPTX slot in `$extensions` [1].
- `tokens/style/<name>.tokens.json`: `fontFamily`, `typography` composites (title, lead, body…),
  `shadow` composites (rest/lift/soft/key/overlay), `transition`/`cubicBezier`/`duration` motion
  tokens, plus `$extensions` for effects DTCG lacks (backdrop blur, bokeh, noise) [1].
- `tokens/<deck>.resolver.json`: `sets` = shared ref tokens; `modifiers` = `palette` and `style`,
  each with named `contexts` (e.g. `paper-green`, `night`; `editorial`, `flat`) [2]. Choosing a
  theme is one resolver input, e.g. `{ "palette": "paper-green", "style": "editorial" }`.
- **Components (layer 1)** live in CSS and read **only** `--sys-*`/`--comp-*`, never `--ref-*`
  (lintable). The **architecture contract** (engine, data-attributes, class names/slots/states,
  shared SVG defs) is not tokens: it is the stable API the three layers style.

**In the single HTML file, enforce the layering with cascade layers:**
`@layer arch, components, palette, style, deck;`, where later layers override earlier ones
regardless of specificity, and unlayered rules beat everything [9]. Tokens are emitted as custom
properties inside `@layer palette`/`@layer style`. Register animatable tokens (e.g. accent hue,
frost opacity) with `@property` so they are typed and interpolate [10].

**Generate every output from the one source** with Style Dictionary (DTCG reference
implementation [3]): one platform for CSS variables with `outputReferences` (keeps
`var(--ref-…)` chains readable) and a custom format that writes the OOXML `<a:clrScheme>` +
`<a:fontScheme>` for the PPTX export [4][5]. Terrazzo is the alternative; it adds a built-in
`a11y/min-contrast` lint over declared pairs [13].

**Palette → PPTX theme:** each `sys.color` role declares its slot in
`$extensions["com.twm.pptx"].slot`, and the exporter fills the 12 slots of `a:clrScheme` (dk1, lt1,
dk2, lt2, accent1–6, hlink, folHlink) [14]. Proposed default for the current palette:

| Slot | Role (current value) | Why |
| --- | --- | --- |
| dk1 | `ink` #2B2A27 | Mapped to tx1 by the master's `clrMap`: default text [15] |
| lt1 | `paper` #F6F3EC | bg1: slide background |
| dk2 | `ink-2` #5C5A55 | tx2: secondary text (6.2:1) |
| lt2 | `paper-deep` #EDE8DD | bg2: alternate panels |
| accent1 | `accent` #86BC25 | Fill/stroke emphasis; first chart series |
| accent2 | `accent-ink` #4B6E10 | Accent-coloured text (5.4:1) |
| accent3 | `loss` #7A1F2B | Loss/impact |
| accent4 | `alarm` #D2392C | Alarm (4.3:1: large text/fills only) |
| accent5 | `ink-3` #8A867E | Muted strokes/arrows (3.3:1: not body text) |
| accent6 | `tile` #FDFCF9 | Tile surface |
| hlink | `accent-ink` | Links must be text-safe, so not `accent` |
| folHlink | `ink-2` | |

Contrast figures are WCAG 2 ratios on `paper`, computed for this note from the `:root` values in
`deck/deck-v2.html`. `fs-*` sizes map to `a:fontScheme` major (serif headings) and minor (sans
body) fonts. Shadows/blur map to `a:fmtScheme` effect styles only approximately [16].

## 2 · Findings

**DTCG format is stable (2025.10).** The DTCG announced its first stable specification on
28 Oct 2025, adding theming/multi-brand support, CSS Color 4 spaces (P3, OKLCH) and token
relationships. Style Dictionary, Tokens Studio and Terrazzo are the reference implementations.
Figma, Penpot, Sketch and others support it or are implementing it [3]. The Format module [1]
defines:
- **Primitive types:** color, dimension, fontFamily, fontWeight, duration, cubicBezier, number.
- **Composite types:** strokeStyle, border, transition (`duration`, `delay`, `timingFunction`),
  shadow (`color`, `offsetX`, `offsetY`, `blur`, `spread`, optional `inset`; a value may be an
  **array** of shadows, which fits our layered `inset + drop` shadows), gradient (stops of
  `color` + `position`), and typography (`fontFamily`, `fontSize`, `fontWeight`,
  `letterSpacing`, `lineHeight` as a multiplier).
- **Aliases:** `{group.token}` aliases whole tokens. A JSON Pointer `$ref` can target a
  property-level location.
- **Inheritance and flags:** `$type` inherits from the nearest group, and tools must not infer
  types. Groups can `$extends` another group (deep merge). `$deprecated` is supported.
- **`$extensions`:** vendor data under reverse-domain keys, which tools **must** preserve.
- **Files:** recommended extension `.tokens.json`, media type `application/design-tokens+json`.

Note that the live *draft* at designtokens.org (Sept 2026) warns not to implement it. Pin to the
2025.10 final reports [1][2].

**The Resolver module handles themes without duplication.** A `.resolver.json` has `sets`,
`modifiers` (each with named `contexts`, e.g. light/dark) and a `resolutionOrder`. Later entries
win. Aliases resolve after flattening, so a semantic alias can point at whichever palette is
active. The number of permutations is the product of the context counts [2]. This maps directly
onto independent `palette` and `style` modifiers. One version-string inconsistency
(`2025-10-01` vs `2025-11-01`) appears in the text [2].

**Tiering (ref → sys → comp) is the common pattern.** Material Web documents three tiers:
`--md-ref-*` (concrete values, e.g. typefaces), `--md-sys-*` (roles: colour, typescale, shape)
and component tokens (`--md-filled-button-container-shape`). "Each component token maps to a
system token, which has a concrete reference value", so changing a sys token flows to every
component that uses it [6]. Material Web does not yet support `--md-sys-motion` tokens [6].

**Colour roles come in pairs.** In Material 3, every role has an `on-` partner for content
(primary/on-primary, primary-container/on-primary-container, surface/on-surface and
on-surface-variant), plus surface-container tiers and outline/outline-variant [7]. Compose
guidance: "Use on-primary on top of primary … to provide accessible contrast". Mismatched pairs
are an explicit anti-pattern [8]. Dynamic colour derives five key colours, each with a 13-tone
palette, from a source colour, so roles are generated rather than hand-picked [8]. Radix encodes
roles as positions on a 12-step scale (1–2 backgrounds, 3–5 component fills, 6–8 borders, 9–10
solid, 11–12 text) and guarantees steps 11/12 reach APCA Lc 60/90 on step 2 [11].
*Implication:* our "accent never as text; `accent-ink` for accent text" rule is an `on-`-style
pairing. Encode it as declared fg/bg pairs and test them, rather than leaving it as prose.

**Style/material is tokenised as composites plus scheme objects.** Material 3 treats theming as
subsystems (colour scheme, typography, shapes), with elevation expressed as tonal overlay *plus*
shadow [8]. Motion is now a scheme: `MotionScheme.standard()` vs `expressive()`, each exposing
fast/default/slow × **spatial** (bounds/position) and **effects** (colour/alpha) specs [12]. That
gives us a clean motion-character swap: components ask for `motion.spatial.default`, and the style
picks the curve. Fluent's acrylic is a recipe of layers (background, blur, exclusion blend,
colour/tint overlay, noise) with explicit fallbacks to a solid colour (high contrast, battery
saver, transparency off). Fluent also warns against accent-coloured text on acrylic [17]. Our
`--frost` + `backdrop-filter` should be a style token with a declared solid fallback. Open Props
ships shadows that adapt via `--shadow-color`/`--shadow-strength`, so one shadow ramp can
re-tint per palette [18]. That fits our shadows, which already derive from `--ink` via
`color-mix`.

**CSS mechanics for one file.** Tailwind v4's `@theme` shows namespaced theme variables
(`--color-*`, `--font-*`, `--text-*`, `--shadow-*`, `--ease-*`, `--animate-*`) emitted as plain
`:root` custom properties. A namespace can be reset (`--color-*: initial`) and a theme can be
shared as an imported CSS file. `@theme inline` avoids var-resolution surprises when a theme var
references another var [19]. `@layer` fixes precedence by declared order, ignoring specificity.
Unlayered styles win, `!important` reverses the order, and `@import … layer()` places a
stylesheet in a layer [9]. `@property` (Baseline 2024) gives custom properties a `syntax`,
`inherits` and `initial-value`, enabling type-checking and interpolation [10].

**Generating multiple outputs.** Style Dictionary v4 has "first-class support" for DTCG
`$value`/`$type`, but 2025.10 support is still in progress in v5, so check before depending on
the Resolver [4]. Each platform lists `files` with a `format`. Custom formats
(`registerFormat`) receive `dictionary.allTokens` and return a string, which is how a
`clrScheme` XML writer would work. `outputReferences` keeps alias chains in CSS output [5].

**Validation.** Terrazzo's linter provides `a11y/min-contrast` (WCAG `AA`/`AAA`, declared
`pairs`, `largeText`), `a11y/min-font-size`, `core/colorspace`, `core/max-gamut` and
`core/consistent-naming`. Contrast is checked only for pairs you declare [13]. For us, a pytest
over the resolved token JSON (every declared text pair ≥ 4.5:1, large ≥ 3:1, and `accent` never
paired as text) would run across every palette × style permutation without a Node toolchain.

**Slide frameworks separate layouts from themes, but loosely.**
- **reveal.js:** themes are swappable stylesheets that expose their variables as CSS custom
  properties on `:root`, built from `template/settings.scss` + `theme.scss` [20][21].
- **Slidev:** a theme "should focus on appearance" (styles, layouts, components, default config,
  colour schema). Layouts are Vue components with default and named slots, chosen per slide via
  `layout:` frontmatter, and themes/addons may override built-in layouts [22][23][24].
- **Marp:** themes are CSS files with `/* @theme name */` metadata that style `section` (one per
  slide). They `@import` a base theme and fix slide size per theme [25].

None of the three tiers semantic colour roles. All bundle layout, palette and type into one
"theme". Our three-layer split is stricter than the prior art.

**OOXML themes have three parts.** `a:themeElements` holds `clrScheme` (12 colours: dk1, lt1,
dk2, lt2, accent1–6, hlink, folHlink), `fontScheme` (major/minor) and `fmtScheme` (fill, line,
effect and background-fill style lists) [14][16]. The slide master's `p:clrMap` maps the
logical names bg1/tx1/bg2/tx2 onto those slots, so text defaults follow dk1/dk2 on lt1/lt2
(ISO example shows a dark inversion: `bg1="dk1" tx1="lt1"`) [15]. **Consequences:**
- dk1/dk2 must be text-safe on lt1/lt2.
- The accent1–6 order is what PowerPoint cycles through for charts and shapes, so put the most
  usable fill first.
- A palette with more than 6 accent roles has to drop or merge some in PPTX.

## 3 · Open questions

1. **Is 12 enough?** Our roles today (paper, paper-deep, tile, ink ×3, accent, accent-ink, loss,
   alarm) fit, but `tile` in accent6 is a surface, not an accent. Should it instead go in lt2,
   with `paper-deep` dropped from PPTX?
2. **Night/dark palette:** use a `clrMap` inversion (as in the ISO example [15]), or a separate
   clrScheme context? Which round-trips better when editing in PowerPoint?
3. **Toolchain:** should we take on a Node dependency (Style Dictionary/Terrazzo) for build-time
   generation, or write a small Python resolver + emitters (CSS, clrScheme XML) to stay `uv`-only?
   Style Dictionary's 2025.10/Resolver support is unconfirmed [4].
4. **Where do diagram text floors (`--fs-d-*`, SVG `--k`) live:** style tokens, or the
   architecture contract (engine-computed)?
5. **Blur, bokeh and noise have no DTCG type.** Should they go in `$extensions`, or become
   component-level CSS owned by the style layer?
6. **Contrast metric:** WCAG 2 ratio (PPTX/Office norms) or APCA (Radix [11])? Pick one for the
   CI gate.

## 4 · Sources

1. Design Tokens Format Module 2025.10 (Final CG Report). W3C Design Tokens CG, 2025. https://www.w3.org/community/reports/design-tokens/CG-FINAL-format-20251028/
2. Design Tokens Resolver Module 2025.10 (Final CG Report). W3C Design Tokens CG, 2025. https://www.w3.org/community/reports/design-tokens/CG-FINAL-resolver-20251028/
3. Design Tokens specification reaches first stable version. W3C Design Tokens CG, 2025. https://www.w3.org/community/design-tokens/2025/10/28/design-tokens-specification-reaches-first-stable-version/
4. DTCG support. Style Dictionary, 2025. https://styledictionary.com/info/dtcg/
5. Formats (hooks reference). Style Dictionary, 2025. https://styledictionary.com/reference/hooks/formats/
6. Theming (tokens). Material Web / Google, 2024. https://github.com/material-components/material-web/blob/main/docs/theming/README.md
7. Color theming. Material Web / Google, 2024. https://github.com/material-components/material-web/blob/main/docs/theming/color.md
8. Material Design 3 in Compose. Android Developers / Google, 2025. https://developer.android.com/develop/ui/compose/designsystems/material3
9. @layer. MDN Web Docs / Mozilla, 2025. https://developer.mozilla.org/en-US/docs/Web/CSS/@layer
10. @property. MDN Web Docs / Mozilla, 2025. https://developer.mozilla.org/en-US/docs/Web/CSS/@property
11. Understanding the scale. Radix Colors / WorkOS, 2024. https://www.radix-ui.com/colors/docs/palette-composition/understanding-the-scale
12. MotionScheme (androidx.compose.material3). Android Developers / Google, 2025. https://developer.android.com/reference/kotlin/androidx/compose/material3/MotionScheme
13. Linting. Terrazzo, 2025. https://terrazzo.app/docs/linting/
14. ColorScheme class (a:clrScheme, ISO/IEC 29500 remarks). Microsoft Learn, 2024. https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.drawing.colorscheme
15. ColorMap class (p:clrMap, ISO/IEC 29500 remarks). Microsoft Learn, 2024. https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.presentation.colormap
16. ThemeElements class (a:themeElements). Microsoft Learn, 2024. https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.drawing.themeelements
17. Acrylic material. Microsoft Learn (Fluent / Windows apps), 2026. https://learn.microsoft.com/en-us/windows/apps/design/style/acrylic
18. Open Props. Open Props (Adam Argyle), 2025. https://open-props.style/
19. Theme variables. Tailwind CSS v4 docs, 2025. https://tailwindcss.com/docs/theme
20. Themes. reveal.js, 2025. https://revealjs.com/themes/
21. Creating a theme (css/theme/README.md). reveal.js (GitHub), 2025. https://github.com/hakimel/reveal.js/blob/master/css/theme/README.md
22. Writing themes. Slidev, 2025. https://sli.dev/guide/write-theme
23. Writing layouts. Slidev, 2025. https://sli.dev/guide/write-layout
24. Built-in layouts. Slidev, 2025. https://sli.dev/builtin/layouts
25. Theme CSS (docs/theme-css.md). Marpit / Marp team (GitHub), 2025. https://github.com/marp-team/marpit/blob/main/docs/theme-css.md
