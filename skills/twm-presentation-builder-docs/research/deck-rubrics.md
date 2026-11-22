# Deck-quality rubrics: prior art for the eval criterion library

Researched 2026-11-22. Question: which existing rubrics, benchmarks and expert guidance for judging
slide quality should the skill's LLM-as-judge eval borrow, and how should rubrics differ by deck type?
Evidence legend: **D** = deterministic (DOM/render/code check), **S** = screenshot judge,
**T** = text judge.

## 1 · TL;DR for our design

**Borrow the structure, not the scores.** Academic evals converge on three to five axes
(content · design · coherence/narrative, plus fidelity to source) [1][2][5][7]. The strongest 2026
result is that **atomic binary checklist items** with localised evidence (slide index) track human
rankings better than holistic 1–5 scores: PresentBench ρ 0.53 against humans, against PPTEval's 0.30
on the same study (human–human 0.66) [5]. Holistic judging is weakest on deck-level coherence
(PPTEval human–judge r 0.55, against 0.90 for design) [1]. Giving the judge an explicit **flaw
taxonomy** lifted defect-detection F1 from 0.48 to 0.66. Adding computed saliency or colour metrics
to the prompt did **not** help [6]. So: criteria should be binary or tightly anchored, carry a flaw
taxonomy in the prompt, and have geometry checked in code, not by the judge.

**Proposed core dimensions (every profile)**

| Concern | Criterion (anchor idea) | Evidence | Sources |
| --- | --- | --- | --- |
| design-layout | No overlap, occlusion, clipping, overflow or off-canvas element at each review size × step | **D** (bounding boxes per step) | [3][6][9] |
| design-layout | Margins and alignment: elements on a shared grid, safe-area margins respected | **D** + S | [3][6] |
| design-palette | Text contrast ≥ 4.5:1 (≥ 3:1 for large text: ≥ 24 px, or ≥ 18.5 px bold); diagram strokes and fills ≥ 3:1; never round down | **D** | [10][11] |
| design-style | Consistent type/colour system; no "inconsistent or distracting text styling"; few fonts and colours | S (+ D token audit) | [6][16] |
| design-style | Clear visual hierarchy: one focal point per slide/step | S | [6][13] |
| content | One message per slide, graspable at a glance (~3 s glance test) | S | [13][14] |
| content | Text density appropriate to profile (no "excessive text density") | D (word count) + S | [6][12] |
| content | Visuals carry the evidence for the claim; image/figure is relevant to the text | S | [1][15] |
| architecture | Executes/renders; every slide reachable; deterministic step state | **D** | [3][9] |
| accessibility | Every slide has a unique title; non-text content has alt text; logical reading order | **D** | [11] |
| coherence | Deck-level storyline: ordered, transitions explicit, each slide advances the argument | T (deck-level, checklist not holistic) | [1][7] |
| research/sourcing | Every factual claim traceable to a cited source; no unsupported or contradicting detail | T (per-slide fidelity items) | [5][7] |

**Profile-specific dimensions**

| Profile | Extra/weighted criteria | Sources |
| --- | --- | --- |
| **Editorial talk** (our HF deck) | Assertion titles: full-sentence finding, not topic (∴ our VOICE.md titles); visual evidence over bullets; step builds reveal one idea at a time; reader notes carry caveats; survives screen-share at small or short-wide windows (layout check at 1288×598) | [12][14][15][16] |
| **Pitch** | Persuasive arc (problem → stakes → resolution), audience relevance and call to action weighted up; source fidelity weighted lower but still required for numbers | [13][17] |
| **Data review** | Quantified evidence with units, scales, comparisons and uncertainty; no dequantified colour codes; chart integrity (non-text contrast, labelled axes) | [8][10] |
| **Read-alone handout / slidedoc** | Must stand alone without a presenter: denser, complete sentences allowed and expected; glance test relaxed; reading order and structure weighted up | [8][12] |
| **PPTX export** | Accessibility-checker errors (missing titles, alt text, table headers) are blocking; warnings (contrast, reading order) scored | [11] |

Deterministic-checkable now: overlap/overflow/off-canvas, contrast, font-size floor, alt text, unique
titles, reading order (DOM order versus visual order), word count, executability. Our S-030 layout
guard already covers the first of these. Everything else needs a judge.

## 2 · Findings by source cluster

### Academic slide-generation evals

- **PPTAgent / PPTEval (2025)** [1]: a reference-free MLLM judge (GPT-4o on rendered slide images,
  not extracted text) that scores three dimensions 1–5 with a rationale. *Content* (amount of
  information, clear text, images support text) and *Design* (harmonious but contrasting colour,
  visual elements, no overlapping elements) are scored per slide and averaged. *Coherence*
  (progressive storyline, context) is scored once per deck. The paper gives no per-point anchors.
  Human–judge Pearson: content 0.70, design 0.90, coherence 0.55. Human Fleiss κ was ~0.59, so
  even humans agree only moderately. **Borrow:** the content/design/coherence split and the
  per-slide versus per-deck granularity. **Avoid:** unanchored 1–5 scores.
- **AutoPresent / SlidesBench (CVPR 2025)** [2][3]: splits *reference-based* metrics, computed in
  code (element matching, embedding text similarity, CIEDE2000 colour difference, normalised
  position), from *reference-free* GPT-4o scores 0–5 on text (clear title, concise, consistent
  font), image (quality, proportion), layout (aligned, no overlap, sufficient margins, nothing off
  the page) and colour (high text–background contrast, no glaring colours). Judge–human ICC was
  0.74–0.85. It also scores *executability* and gives a failed slide 0. **Borrow:** the four
  reference-free anchors almost verbatim, and gating on execution.
- **DOC2PPT (AAAI 2022)** [4]: early reference-based metrics: slide-level ROUGE with a slide-count
  penalty, longest common figure subsequence (figure choice *and order*), text–figure relevance, and
  layout mIoU against gold boxes. Useful only when a gold deck exists, which is not our case. The
  idea of figure order as a narrative signal is reusable.
- **PresentBench (Mar 2026)** [5]: 238 expert instances, ~54 **instance-specific binary checklist
  items** each, across five dimensions. Two are material-independent (presentation fundamentals;
  visual design and layout) and three material-dependent (content completeness, correctness,
  fidelity). Fidelity is checked one slide at a time against the sources, with unsupported detail
  counted as hallucination. Each item gets its own judge call and returns slide-level evidence.
  It critiques SlidesBench-style open-ended settings as unable to verify faithfulness. **Borrow:**
  this is the closest template for our criterion library and research/sourcing concern.
- **SlideAudit (UIST 2025)** [6]: a taxonomy of 27 slide design flaws drawn from an expert
  formative study and Gestalt principles, in five groups: composition and layout, typography,
  colour, imagery, animation and interaction. Named flaws include cluttered layout, misaligned
  elements, inconsistent text styling, insufficient contrast, illegible typeface, lack of
  hierarchy, excessive text density, occluded content, inappropriate font sizing, unbalanced
  margins, content overflow and mismatched colours. Putting the full taxonomy in the prompt raised
  GPT-4o F1 from 0.476 to 0.655. Computed augmentations (saliency, grouping, colour metrics) did
  not help. **Borrow:** the flaw names as negative anchors for our design-* criteria. Use 2,400
  annotated slides as a calibration set if needed. (I could not read the full 27-item figure.)
- **DECKBench (Feb 2026)** [7]: separates slide-level from deck-level metrics. At deck level it
  uses an LLM-judged *narrative* score (transitions, logical flow, ordering, summarisation) plus
  coverage and faithfulness to the source paper. It reports no human validation, so treat it as
  design inspiration only.
- **Others seen, not read in depth:** SlideCoder / Slide2Code (EMNLP 2025: layout fidelity,
  execution accuracy, visual consistency against a reference image) [18]; PreGenie (2025: aesthetics
  and text–image consistency, Slidev-rendered) [19]; SlidesGen-Bench (Jan 2026: computational
  content, aesthetics and **editability** metrics, plus the Slides-Align1.5k human-preference set) [20].
  Editability is relevant to our PPTX sub-skill, but its metric definitions were not readable.
  ReDeck (Sep 2026) [9] gives render feedback for **overflow, overlap, clipping and off-canvas
  placement** after each edit. That supports our design choice of render-grounded deterministic
  layout checks inside the build loop, not only at eval time.

### Accessibility standards

- **WCAG 2.2 SC 1.4.3 (AA)** [10]: 4.5:1 for normal text and 3:1 for large text. Large means
  ≥ 18 pt (~24 px), or ≥ 14 pt bold (~18.5 px). Thresholds are not rounded: 4.499 fails.
  Logotypes and incidental text are exempt. 1.4.6 (AAA) is 7:1. 1.4.11 covers non-text
  contrast (chart strokes, diagram arrows), with a 3:1 threshold in the standard. Our tokens
  already do this: `--ink-3` 3.3:1 is limited to labels ≥ 24 px, and `--accent` 2.0:1 is never
  used as text.
- **Microsoft Accessibility Checker (PowerPoint)** [11]. Errors: missing alt text, missing table
  column headers, unnamed sections, slides without titles, restricted access. Warnings: complex
  tables, insufficient contrast, missing captions on media, illogical reading order. Tips: unique
  section names and **unique slide titles**. These map directly to PPTX-concern criteria, and
  most are deterministic on the exported file.

### Practitioner guidance (argument and storytelling)

- **Assertion–evidence (Alley, Garner et al.)** [14][15]: a sentence headline stating the message,
  supported by visual evidence, with no bullet lists. Penn State studies found it helped
  comprehension and recall of *complex* concepts (2011) and long-term recall of key ideas. Common
  practice slides did better on short-term recall of simple facts, and one replication with heavy
  animation was not significant. A 2006 ASEE study found sentence headlines beat phrase or question
  headlines on recall [15]. Most of this evidence comes from one research group. **Borrow:**
  "title is a full-sentence finding" as a binary check. It is our VOICE.md rule already.
- **Doumont, *Trees, Maps, and Theorems*** [16]: adapt to the audience, maximise signal-to-noise
  ratio, use effective redundancy, and keep the title of an effective slide as the message the
  audience should remember. Prefers few colours and fonts and simple layouts. Read via secondary
  summaries (MIT CommLab, reviews), not the book. **Borrow:** signal-to-noise as the anchor for the
  density and decoration criteria.
- **Duarte** [12][13]: the *Glance Test* says a slide's point should be graspable in ~3 s, like a
  billboard, with one idea per slide, contrast and whitespace for emphasis, and every element
  aiding comprehension. Duarte's own materials score slide attributes as signal or noise.
  *Slidedocs* separates **read-alone visual documents** (pre-reads, leave-behinds) from projected
  slides, which is the key justification for a separate handout profile with different density
  anchors.
- **Reynolds, *Presentation Zen*** [17]: restraint in preparation, simplicity in design,
  naturalness in delivery. Favours large visuals over bullets and warns against reading the same
  text aloud that is on screen. It is mostly about delivery, so it fits a talk or pitch profile
  more than a judgeable criterion. Read via secondary sources.
- **Tufte, *Cognitive Style of PowerPoint*** [8]: argues bullet hierarchies fragment reasoning
  ("effects without causes… verbs without subjects") and that low-resolution slides drop scales,
  units and dense data. Recommends sending a detailed written document or handout and keeping
  slides simple, with quantified evidence (units, uncertainty, comparisons, context) and no
  decoration or branding chrome. **Borrow:** data-review anchors and the handout profile. It is
  also a counterweight to assertion–evidence's sparseness when the deck must stand alone.

### How rubrics differ by deck type

The sources disagree on density because they target different reading modes. Projected talks,
covered by Duarte's glance test, assertion–evidence and Reynolds, want sparse, visual,
one-message slides with the argument carried by the speaker and notes. Read-alone decks, covered
by Duarte's Slidedocs and Tufte, want complete sentences, quantified detail and self-sufficiency.
Pitch decks weight persuasion and audience relevance (Duarte's message singularity and relevance
attributes [13]). Data reviews weight evidence integrity (Tufte). None of the academic benchmarks
profile by deck type: PresentBench's domains (academia, education, economics, talk, advertising)
come closest [5]. Hence our profile layer is new and must be judged by us, not inherited.

## 3 · Gaps and open questions

- **No published anchors per score point** in PPTEval or SlidesBench. We must write our own
  anchors, or prefer binary checklist items [5].
- **Step-built and animated slides are unevaluated.** Every benchmark judges static slides.
  SlideAudit has an animation category, but I could not read its items. Judging each step and size
  (as our S-030 guard does) has no precedent, so we need our own design.
- **Screen-share robustness** (Teams compression, small or short-wide windows) is absent from
  all sources. Closest proxies are the WCAG large-text thresholds and our own size matrix.
- **Coherence remains the least reliable judgement** (r 0.55 [1]). Consider deck-level checklist
  items (each slide's title advances the stated thesis, chapter order matches the storyboard) over
  a holistic score.
- **Judge validation:** we have one human-accepted deck. We need a small, presenter-rated
  calibration set (good, flawed and seeded-defect variants) to measure agreement before trusting
  weights. Human–human agreement is itself only ~0.6–0.66 [1][5].
- **Unverified here:** Doumont and Reynolds read only via secondary sources. SlidesGen-Bench
  aesthetic and editability formulas and the SlideAudit full taxonomy were not readable. Read
  these before finalising the design-* and pptx criteria.
- **Voice** is presenter-specific. No external rubric applies beyond the sentence-headline
  evidence. It stays a profile owned by VOICE.md.

## 4 · Sources

1. *PPTAgent: Generating and Evaluating Presentations Beyond Text-to-Slides* (PPTEval). Zheng H., Guan X., Kong H. et al., 2025. https://arxiv.org/abs/2501.03936 (HTML: https://arxiv.org/html/2501.03936)
2. *AutoPresent: Designing Structured Visuals from Scratch* (SlidesBench). Ge J. et al., CVPR 2025. https://arxiv.org/abs/2501.00912
3. AutoPresent, metric definitions and human study (v2 HTML). Ge J. et al., 2025. https://arxiv.org/html/2501.00912v2
4. *DOC2PPT: Automatic Presentation Slides Generation from Scientific Documents*. Fu T.-J., Wang W. Y., McDuff D., Song Y., AAAI 2022. https://arxiv.org/abs/2101.11796
5. *PresentBench: A Fine-Grained Rubric-Based Benchmark for Slide Generation*. Chen X.-S., Zhu J., Li P., Wang H., Yang S., Guo M.-H., 2026. https://arxiv.org/abs/2603.07244
6. *SlideAudit: A Dataset and Taxonomy for Automated Evaluation of Presentation Slides*. Zhang Z., Chen et al., Wobbrock J. O., UIST 2025. https://arxiv.org/abs/2508.03630
7. *DECKBench: Benchmarking Multi-Agent Frameworks for Academic Slide Generation and Editing*. Jang D., Heisler M. L., Xing L. et al., 2026. https://arxiv.org/abs/2602.13318
8. *PowerPoint Does Rocket Science, and Better Techniques for Technical Reports*; *The Cognitive Style of PowerPoint*. Tufte E. R., 2003/2006. https://www.edwardtufte.com/notebook/powerpoint-does-rocket-science-and-better-techniques-for-technical-reports/
9. *ReDeck: Step-Level Render-Grounded Refinement for Document-to-Slide Generation*. Tian M. et al., 2026. https://arxiv.org/abs/2609.00194
10. *Understanding SC 1.4.3 Contrast (Minimum)*, WCAG 2.2. W3C WAI, 2023. https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
11. *Rules for the Accessibility Checker*. Microsoft Support, accessed 2026. https://support.microsoft.com/en-us/office/rules-for-the-accessibility-checker-651e08f2-0fc3-4e10-aaca-74b4a67101c1
12. *Slidedocs*. Duarte N., Duarte Inc., 2014. https://www.duarte.com/resources/books/slidedocs/
13. *The Glance Test*. Duarte Inc., accessed 2026. https://www.duarte.com/?p=11718
14. *The Assertion-Evidence Approach*. Alley M. et al., Penn State, accessed 2026. https://www.assertion-evidence.com/ (research list: https://writing.engr.psu.edu/research.html)
15. *Assertion-Evidence Slides Appear to Lead to Better Comprehension and Recall of More Complex Concepts*. Garner J., Alley M. et al., ASEE 2011. https://peer.asee.org/assertion-evidence-slides-appear-to-lead-to-better-comprehension-and-recall-of-more-complex-concepts.pdf; *Testing the Effect of Sentence Headlines in Teaching Slides*. Alley M. et al., ASEE 2006. https://peer.asee.org/testing-the-effect-of-sentence-headlines-in-teaching-slides.pdf
16. *Trees, Maps, and Theorems: Effective Communication for Rational Minds*. Doumont J.-l., Principiae, 2009, read via MIT CommLab *Slide Design* (https://mitcommlab.mit.edu/nse/commkit/slide-design) and review (https://idratherbewriting.com/2009/06/25/page-layout-and-design-tips-from-jean-luc-doumonts-trees-maps-and-theorems/)
17. *Presentation Zen: Simple Ideas on Presentation Design and Delivery* (3rd ed.). Reynolds G., New Riders, 2019. https://oreilly.com/library/view/presentation-zen-simple/9780135897751
18. *SlideCoder: Layout-aware RAG-enhanced Hierarchical Slide Generation from Design*. EMNLP 2025. https://arxiv.org/abs/2506.07964
19. *PreGenie: An Agentic Framework for High-quality Visual Presentation Generation*. 2025. https://arxiv.org/abs/2505.21660
20. *SlidesGen-Bench: Evaluating Slides Generation via Computational and Quantitative Metrics*. Yang Y., Li W., Ren H. et al., 2026. https://arxiv.org/abs/2601.09487
