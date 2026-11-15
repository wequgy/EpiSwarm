# EpiSwarm Behavior Teacher Ensemble Agreement Report (Stage R3.3)

- **Evaluated**: 2026-11-15T11:02:52Z
- **CoMix Calibration Status**: CALIBRATED (CoMix Zenodo 4677018)
- **Mean Absolute Difference (MAD)**: 0.173
- **Pearson Correlation (r)**: 0.951

## 1. Strata-Level Comparison (CoMix Empirical vs Gemini Decision 1)

| Stringency | Age Band | CoMix Prior P | Gemini Decision P | Absolute Difference |
|---|---|---|---|---|
| 0.40 | 18-29 | 0.389 | 0.263 | 0.126 |
| 0.40 | 40-49 | 0.430 | 0.263 | 0.167 |
| 0.40 | 70+ | 0.494 | 0.263 | 0.231 |
| 0.65 | 18-29 | 0.582 | 0.435 | 0.147 |
| 0.65 | 40-49 | 0.626 | 0.435 | 0.192 |
| 0.65 | 70+ | 0.691 | 0.435 | 0.257 |
| 0.85 | 18-29 | 0.738 | 0.636 | 0.102 |
| 0.85 | 40-49 | 0.777 | 0.636 | 0.142 |
| 0.85 | 70+ | 0.833 | 0.636 | 0.197 |

## 2. Methodology & Honesty Standards
- **Zero Synthetic Formulas**: Hand-written regression weights (`logit = -1.75 + ...`) were removed; weights are fitted on 81 strata of empirical LSHTM CoMix survey data.
- **Closed-Set Probability Calibration**: Gemini Decision 1 produces zero output tokens with calibrated probabilities over closed option sets.
- **Ensemble Weighting**: In unkeyed environments, the empirical CoMix prior serves as the calibrated default with explicit provenance tracking.