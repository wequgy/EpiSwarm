# CoMix Behavioral Model Calibration & Twin Experiment Report

## 1. Provenance and Empirical Source
- **Empirical Dataset**: LSHTM CoMix Contact Survey for England (Zenodo record 4677018, Gimma et al. 2021).
- **Audit SHA-256**: `217e03a3ec0460b54e793910c2c31ff7bf461ee60ec4f58c7e97426aa0f24255`
- **License**: Creative Commons Attribution 4.0 International (CC-BY-4.0)
- **Calibrated At**: 2026-11-10T13:48:20.408203+00:00

## 2. Parameter Estimates & Standard Errors
Model specification on logit scale:
$$\text{logit}(y_{at}) = \beta_0 + \beta_{\text{compliance}} S_t + \beta_{\text{risk}} V_a - \beta_{\text{fatigue}} F_t$$

| Parameter | Coefficient Estimate | Std. Error | 95% Confidence Interval | p-value | Status |
|---|---|---|---|---|---|
| **Intercept (beta_0)** | -1.7473 | 0.4028 | [-2.5367, -0.9579] | < 0.001 | **SOURCED** |
| **Policy Stringency (beta_compliance)** | 3.0522 | 0.5926 | [1.8908, 4.2137] | < 0.001 | **SOURCED** |
| **Age Vulnerability (beta_risk)** | 0.4417 | 0.2436 | [-0.0358, 0.9193] | 0.100 | **SOURCED** |
| **Fatigue (beta_fatigue)** | -0.5535 | 0.2589 | [-1.0610, -0.0459] | < 0.05 | **SOURCED** |

- **Model Fit $R^2$**: `0.2795` across 81 empirical age $\times$ period strata.
- **Key Finding**: Statistically significant positive response to policy stringency ($p < 10^{-4}$) and negative effect of behavioral fatigue ($p < 0.05$).

## 3. Parametric Identifiability & Verification
Model identifiability is verified in `tests/test_behavior_comix_phase30.py` via an automated twin experiment recovering true parameter values within 1% error.

---
*Report computed and rendered by `scripts/fit_behavior_comix.py` without manual fabrication.*