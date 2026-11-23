# Eval report: baseline-hf-subset (261123)

**Calibration: agreement with the presenter is unmeasured until a calibration set exists.**

- Target: `skills/twm-presentation-builder/examples/hf-incident/deck.html` · profile `editorial-talk` · mode pointwise · depth judges · k = 3
- Concerns: content, research, voice, design-layout, design-palette, design-style, architecture · transcripts read: no
- **Outcome: fail** · overall score 0.76 (coverage 0.64)

## Gates

| Gate | Status |
| --- | --- |
| RS-01 | pass |
| RS-02 | pass |
| DL-01 | pass |
| DL-02 | fail |
| DP-01 | pass |
| DP-02 | fail |
| AR-01 | pass |
| AR-02 | pass |
| AR-03 | pass |
| AR-05 | pass |

## Concerns

| Concern | Score | Coverage |
| --- | --- | --- |
| content | 0.47 | 0.67 |
| research | 1.00 | 0.71 |
| voice | 1.00 | 0.41 |
| design-layout | 0.93 | 0.62 |
| design-palette | 0.96 | 0.43 |
| design-style | 0.28 | 0.86 |
| architecture | 1.00 | 0.86 |

## Criteria

| Criterion | Concern | Weight | Gate | Status | Score |
| --- | --- | --- | --- | --- | --- |
| CN-01 | content | 3 |  | fail | 0.00 |
| CN-02 | content | 3 |  | missing | – |
| CN-03 | content | 3 |  | scored | 0.60 |
| CN-04 | content | 2 |  | fail | 0.33 |
| CN-05 | content | 3 |  | fail | 0.00 |
| CN-06 | content | 2 |  | insufficient-evidence | – |
| CN-07 | content | 1 |  | missing | – |
| CN-08 | content | 2 |  | pass | 1.00 |
| CN-09 | content | 2 |  | missing | – |
| CN-10 | content | 3 |  | pass | 1.00 |
| RS-01 | research | 3 | yes | pass | 1.00 |
| RS-02 | research | 3 | yes | pass | 1.00 |
| RS-03 | research | 2 |  | missing | – |
| RS-04 | research | 2 |  | pass | 1.00 |
| RS-05 | research | 2 |  | pass | 1.00 |
| RS-06 | research | 2 |  | missing | – |
| VC-01 | voice | 2 |  | missing | – |
| VC-02 | voice | 2 |  | missing | – |
| VC-03 | voice | 2 |  | pass | 1.00 |
| VC-04 | voice | 2 |  | missing | – |
| VC-05 | voice | 2 |  | pass | 1.00 |
| VC-06 | voice | 2 |  | missing | – |
| VC-07 | voice | 2 |  | missing | – |
| VC-08 | voice | 3 |  | scored | 1.00 |
| DL-01 | design-layout | 3 | yes | pass | 1.00 |
| DL-02 | design-layout | 2 | yes | fail | 0.83 |
| DL-03 | design-layout | 2 |  | missing | – |
| DL-04 | design-layout | 2 |  | missing | – |
| DL-05 | design-layout | 3 |  | scored | 0.80 |
| DL-06 | design-layout | 2 |  | missing | – |
| DL-07 | design-layout | 2 |  | pass | 1.00 |
| DL-08 | design-layout | 2 |  | missing | – |
| DL-09 | design-layout | 2 |  | pass | 1.00 |
| DL-10 | design-layout | 1 |  | pass | 1.00 |
| DP-01 | design-palette | 2 | yes | pass | 1.00 |
| DP-02 | design-palette | 2 | yes | fail | 0.87 |
| DP-03 | design-palette | 2 |  | pass | 1.00 |
| DP-04 | design-palette | 2 |  | missing | – |
| DP-05 | design-palette | 2 |  | missing | – |
| DP-06 | design-palette | 2 |  | missing | – |
| DP-07 | design-palette | 2 |  | missing | – |
| DS-01 | design-style | 2 |  | fail | 0.00 |
| DS-02 | design-style | 2 |  | fail | 0.00 |
| DS-03 | design-style | 2 |  | fail | 0.00 |
| DS-04 | design-style | 2 |  | fail | 0.00 |
| DS-05 | design-style | 2 |  | missing | – |
| DS-06 | design-style | 3 |  | scored | 0.80 |
| DS-07 | design-style | 1 |  | pass | 1.00 |
| AR-01 | architecture | 2 | yes | pass | 1.00 |
| AR-02 | architecture | 2 | yes | pass | 1.00 |
| AR-03 | architecture | 2 | yes | pass | 1.00 |
| AR-04 | architecture | 2 |  | pass | 1.00 |
| AR-05 | architecture | 2 | yes | pass | 1.00 |
| AR-06 | architecture | 2 |  | pass | 1.00 |
| AR-07 | architecture | 2 |  | missing | – |

## Missing criteria

- CN-02: no judge verdict in this run (not dispatched)
- CN-07: no judge verdict in this run (not dispatched)
- CN-09: no judge verdict in this run (not dispatched)
- RS-03: no judge verdict in this run (not dispatched)
- RS-06: no judge verdict in this run (not dispatched)
- VC-01: no judge verdict in this run (not dispatched)
- VC-02: no judge verdict in this run (not dispatched)
- VC-04: no judge verdict in this run (not dispatched)
- VC-06: no judge verdict in this run (not dispatched)
- VC-07: no judge verdict in this run (not dispatched)
- DL-03: no judge verdict in this run (not dispatched)
- DL-04: no judge verdict in this run (not dispatched)
- DL-06: no judge verdict in this run (not dispatched)
- DL-08: no judge verdict in this run (not dispatched)
- DP-04: no judge verdict in this run (not dispatched)
- DP-05: needs a second shipped palette to swap to; only one palette ships (add the check with the second theme)
- DP-06: no judge verdict in this run (not dispatched)
- DP-07: repo-target T criterion; output-only scope
- DS-05: no judge verdict in this run (not dispatched)
- AR-07: repo-target D criterion; no --repo (the example has no history)

## Flagged for the presenter

- CN-06 @ deck: insufficient-evidence
- RS-02 @ s-4: high-spread
