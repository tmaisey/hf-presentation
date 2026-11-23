# Eval report: baseline-hf-subset-bright (261123)

**Calibration: agreement with the presenter is unmeasured until a calibration set exists.**

- Target: `skills/twm-presentation-builder/examples/hf-incident/deck-bright.html` · profile `editorial-talk` · mode pointwise · depth judges · k = 3
- Concerns: design-layout, design-palette, design-style, architecture, pptx · transcripts read: no
- **Outcome: fail** · overall score 0.76 (coverage 0.71)

## Gates

| Gate | Status |
| --- | --- |
| DL-01 | pass |
| DL-02 | fail |
| DP-01 | pass |
| DP-02 | pass |
| AR-01 | pass |
| AR-02 | pass |
| AR-03 | pass |
| AR-05 | pass |

## Concerns

| Concern | Score | Coverage |
| --- | --- | --- |
| design-layout | 0.96 | 0.38 |
| design-palette | 1.00 | 0.71 |
| design-style | 0.28 | 0.86 |
| architecture | 1.00 | 0.86 |
| pptx | 0.69 | 0.88 |

## Criteria

| Criterion | Concern | Weight | Gate | Status | Score |
| --- | --- | --- | --- | --- | --- |
| DL-01 | design-layout | 3 | yes | pass | 1.00 |
| DL-02 | design-layout | 2 | yes | fail | 0.83 |
| DL-03 | design-layout | 2 |  | missing | – |
| DL-04 | design-layout | 2 |  | missing | – |
| DL-05 | design-layout | 3 |  | missing | – |
| DL-06 | design-layout | 2 |  | missing | – |
| DL-07 | design-layout | 2 |  | missing | – |
| DL-08 | design-layout | 2 |  | missing | – |
| DL-09 | design-layout | 2 |  | pass | 1.00 |
| DL-10 | design-layout | 1 |  | pass | 1.00 |
| DP-01 | design-palette | 2 | yes | pass | 1.00 |
| DP-02 | design-palette | 2 | yes | pass | 1.00 |
| DP-03 | design-palette | 2 |  | pass | 1.00 |
| DP-04 | design-palette | 2 |  | pass | 1.00 |
| DP-05 | design-palette | 2 |  | missing | – |
| DP-06 | design-palette | 2 |  | pass | 1.00 |
| DP-07 | design-palette | 2 |  | missing | – |
| DS-01 | design-style | 2 |  | fail | 0.00 |
| DS-02 | design-style | 2 |  | missing | – |
| DS-03 | design-style | 2 |  | fail | 0.00 |
| DS-04 | design-style | 2 |  | fail | 0.00 |
| DS-05 | design-style | 2 |  | fail | 0.00 |
| DS-06 | design-style | 3 |  | scored | 0.80 |
| DS-07 | design-style | 1 |  | pass | 1.00 |
| AR-01 | architecture | 2 | yes | pass | 1.00 |
| AR-02 | architecture | 2 | yes | pass | 1.00 |
| AR-03 | architecture | 2 | yes | pass | 1.00 |
| AR-04 | architecture | 2 |  | pass | 1.00 |
| AR-05 | architecture | 2 | yes | pass | 1.00 |
| AR-06 | architecture | 2 |  | pass | 1.00 |
| AR-07 | architecture | 2 |  | missing | – |
| PX-01 | pptx | 2 |  | fail | 0.83 |
| PX-02 | pptx | 2 |  | pass | 1.00 |
| PX-03 | pptx | 2 |  | fail | 0.00 |
| PX-04 | pptx | 2 |  | pass | 1.00 |
| PX-05 | pptx | 2 |  | fail | 0.00 |
| PX-06 | pptx | 2 |  | missing | – |
| PX-07 | pptx | 2 |  | pass | 1.00 |
| PX-08 | pptx | 1 |  | pass | 1.00 |
| PX-09 | pptx | 1 |  | pass | 1.00 |

## Missing criteria

- DL-03: no judge verdict in this run (not dispatched)
- DL-04: no judge verdict in this run (not dispatched)
- DL-05: no judge verdict in this run (not dispatched)
- DL-06: no judge verdict in this run (not dispatched)
- DL-07: no judge verdict in this run (not dispatched)
- DL-08: no judge verdict in this run (not dispatched)
- DP-05: needs a second shipped palette to swap to; only one palette ships (add the check with the second theme)
- DP-07: repo-target T criterion; organisation naming is covered by the skill's dev tests
- DS-02: line breaks do not change with a palette swap; judged on hf-subset
- AR-07: target repo not given (pass --repo)
- PX-06: needs PPTX renders; LibreOffice (soffice) is not installed, so no PNG of the PPTX exists

## Flagged for the presenter

- none
