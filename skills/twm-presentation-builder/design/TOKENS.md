# Design tokens: palette and style

A deck's colour (**palette**) and material (**style**: fonts, type scale, shadows, frost, bokeh,
motion) live as **W3C DTCG 2025.10** token files. One generator turns a palette + style pair into
the skeleton's `PALETTE` and `STYLE` CSS blocks and the PPTX theme (`a:clrScheme`, `a:fontScheme`),
behind a contrast gate. Read before choosing, editing or adding a palette or style, or styling a
component against tokens. Never hand-edit the generated blocks in a deck: change the tokens and
regenerate.

Files: `assets/tokens/palettes/<name>.tokens.json`, `assets/tokens/styles/<name>.tokens.json`,
generator `scripts/tokens.py` (stdlib only, PEP 723 header).

| Shipped | What |
| --- | --- |
| palette `paper-green` | Warm paper ground, charcoal inks, a single green accent (`accent-ink` for accent text) |
| style `editorial` | Newsreader titles over Inter, frosted cards, three-plane bokeh, soft ink-tinted shadows, slow eased motion |

## 1 · Tiers (ref → sys → comp)

| Tier | Holds | Rule |
| --- | --- | --- |
| `ref` | Raw values with no meaning: hexes (`ref.color.green.500`), font stacks, curves | Literals only, never aliases. The **only** place a colour, font family or cubic-bezier literal may appear |
| `sys` | Roles components consume: `sys.color.accent`, `sys.type.title.size`, `sys.shadow.lift`, `sys.material.frost`, `sys.motion.ease` | Alias `ref` or `sys`; never read `comp`. Dimensions, durations and numbers may be literal |
| `comp` | Component-scoped aliases (owned by the layout/components layer) | Alias `sys`/`comp` only, never `ref` |

- Components read only `--sys-*`/`--comp-*` custom properties, never `--ref-*` or literals.
- The **style holds no colour literal**: every tint (shadow, frost, bokeh) aliases a palette role,
  so a palette swap retints the style. The palette never aliases the style.
- Choosing a theme = one palette name + one style name (the DTCG Resolver's two modifiers): the
  trees merge, then aliases resolve across them. A path defined in both is an error.
- CSS name = `--` + the dotted path with `-`: `sys.color.accent-ink` → `--sys-color-accent-ink`.
  Aliases stay `var()` references, so the chain stays readable in the deck.

## 2 · File schema

Standard DTCG: a node with `$value` is a token and needs a `$type` (own or inherited from a group);
anything else is a group. Aliases are `"{sys.color.paper}"`. Colours are
`{"colorSpace": "srgb", "components": [r, g, b], "hex": "#rrggbb"}` (components 0–1, matching hex).
Vendor data sits in `$extensions` under these keys:

| Key · field | On | Meaning |
| --- | --- | --- |
| `com.twm.pptx` · `slots` | each `sys.color` role | PPTX `a:clrScheme` slots it fills (`dk1 lt1 dk2 lt2 accent1–6 hlink folHlink`); all 12 claimed **exactly once** per palette. dk1/dk2/hlink/folHlink roles must be text-safe |
| `com.twm.palette` · `textSafe` | each `sys.color` role | `false` = never text (fills, strokes, surfaces only). The gate rejects such a role as a text foreground |
| `com.twm.palette` · `pairs` | palette root | Declared `{fg, bg, use}` pairs the gate checks; `use` = `text` / `large-text` / `non-text` / `decorative` |
| `com.twm.pptx` · `band` (+ `note`) | every style `sys`/`comp` token, or its nearest group | How the effect survives PPTX: `native` / `approximated` / `lost` |
| `com.twm.pptx` · `fontSlot` | `sys.font.*` | `major` (headings) / `minor` (body) in `a:fontScheme`; exactly one each |
| `com.twm.css` · `mix` | colour or shadow token | Emit `color-mix(in srgb, <value> N%, <with>)`; `with` = `transparent` or a colour alias. On a shadow, a list aligned with its layers (`null` = unmixed) |
| `com.twm.css` · `fluid` | dimension | Emit `clamp(min, preferred, $value)`; `$value` is the cap |
| `com.twm.css` · `unit` | number | CSS unit appended on output (e.g. `em` for tracking, which DTCG dimensions can't express) |

Every `sys.color` role **MUST** carry its usage rule in `$description` (e.g. accent: "fills/strokes
only, never text"). Text roles in `sys.type.<role>` are split into `family`, `size`, `weight`,
`leading`, `tracking`, because DTCG typography composites can't hold `em` tracking or fluid sizes.

## 3 · Contrast gate

WCAG 2 ratios over the palette's declared pairs: `text` ≥ **4.5:1**, `large-text` (≥ 24px, or
≥ 18.66px bold) and `non-text` (strokes, arrows, status lights) ≥ **3:1**, `decorative` reported
only (it must never be the sole carrier of meaning). Ratios are **never rounded up** (4.48 fails
and prints `4.48:1`). A failing gate stops every command: no CSS or XML is emitted. Declare a pair
for every real fg/bg use; an undeclared pair is unchecked.

## 4 · Running

```bash
uv run scripts/tokens.py check --palette paper-green --style editorial   # validate + contrast table
uv run scripts/tokens.py css   --palette paper-green --style editorial   # PALETTE + STYLE blocks, with markers
uv run scripts/tokens.py pptx  --palette paper-green --style editorial   # a:clrScheme + a:fontScheme
```

Run from the skill folder (or prefix `${CLAUDE_SKILL_DIR}/`). `--palette`/`--style` take a shipped
name or a `.tokens.json` path. Output is deterministic. Exit 1 with `FAIL` lines on stderr for any
validation or gate failure. The assembler (`scripts/assemble.py`) writes these blocks between the
deck's markers; the PPTX emitter writes the `pptx` XML into `theme1.xml`.

## 5 · Adding a palette

1. Copy `palettes/paper-green.tokens.json` to `palettes/<name>.tokens.json` (neutral name; **NEVER**
   name or reference an organisation or brand).
2. Replace `ref.color` with the new raw colours; point each `sys.color` role at one. Keep the role
   names (components and the style read them); add a role only if the components need it.
3. Rewrite each role's `$description` usage rule and `textSafe`; re-assign the 12 `slots`
   (most usable fill in `accent1`, accent-as-text in `hlink`).
4. Declare every fg/bg pair the deck uses; a bright that misses 4.5:1 is fills/strokes only and
   gets a darker `-ink` role for text.
5. Run `check` until it passes, then regenerate and look at the assembled deck.

## 6 · Adding a style

1. Copy `styles/editorial.tokens.json` to `styles/<name>.tokens.json`.
2. Keep the `sys` group names (`font`, `type`, `shadow`, `material`, `ambient`, `motion`) and the
   token paths components read; change values, fonts (`ref.font`) and curves (`ref.curve`).
3. Colours only by alias to palette roles (with `mix` for tints); no colour literals.
4. Give every effect a `band` with a `note` saying what PowerPoint does instead.
5. Ship any new font: woff2 + licence in `assets/fonts/` and a `fonts.json` entry (the assembler
   embeds by family). Run `check`, rebuild with `scripts/assemble.py`, then look at the assembled
   deck at every review size.
