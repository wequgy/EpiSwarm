# Pre-Registration Calibration & Validation Protocol (Phase 28)

**Protocol Registration Date**: November 10, 2026  
**Status**: PRE-REGISTERED (Committed prior to calibration and held-out evaluation)  
**Target Region**: Greater London Reference Pack (`regions/reference_london`, 33 Local Authorities)  
**Lead Framework**: EpiSwarm Multi-Layer Micro-Metapopulation Simulator  

---

## 1. Data Split & Strict Anti-Leakage Protocol

To adhere strictly to Rules 4 and 5 (no data leakage and pre-registration):

### 1.1 Calibration (Training) Window: Wave 1
* **Window**: March 1, 2020 to May 31, 2020 (92 days).
* **Epidemiological Context**: Initial wild-type ancestral strain (Wuhan-Hu-1/D614G lineage), single-strain dynamics, no vaccination, first UK national lockdown (statutory March 23, 2020).
* **Target Observables for Fitting**:
  - Daily COVID-19 hospital admissions across Greater London acute trusts.
  - Daily occupied invasive mechanical ventilation (IMV) ICU beds.
  - Daily vital statistics registered COVID-19 deaths.
  - *Note*: Confirmed positive cases from Pillar 1/2 are NOT used for likelihood estimation during Wave 1 due to severe laboratory test constraints (under-ascertainment); cases are treated as an unanchored descriptive metric only.

### 1.2 Held-Out Validation Window: Wave 2 (Pre-Alpha)
* **Window**: September 1, 2020 to November 30, 2020 (91 days).
* **Epidemiological Context**: Autumn wave prior to the emergence and dominant sweep of the B.1.1.7 (Alpha) variant (which emerged in Kent/London in Dec 2020) and prior to the commencement of vaccination (December 8, 2020). Features schools reopening, Tier 2 London regional intervention (Oct 17), and National Lockdown 2 (Nov 5).
* **Quarantine Rules**:
  1. The held-out window data is strictly forbidden from parameter tuning, model selection, error analysis, or bug hunting.
  2. The held-out window will be evaluated exactly once per model iteration.
  3. Every evaluation timestamp, parameter set, and metrics will be logged in `docs/validation/HELD_OUT_LOG.jsonl`.

---

## 2. Model Parameters to Calibrate & Prior Distributions

To prevent over-parameterization and structural unidentifiability (as established in Phase 18), we restrict calibration to four parsimonious parameters:

| Parameter | Symbol | Prior Distribution | Rationale |
|---|---|---|---|
| **Transmission Scale ($R_0$ target)** | $R_0$ | $\text{Uniform}(2.0, 3.8)$ | Basic reproduction number prior to intervention under Prem/POLYMOD contact matrices. |
| **Initial Seeding Day** | $t_0$ | $\text{Uniform}(0, 14)$ | Simulation day corresponding to initial community seeding in early March 2020. |
| **Initial Active Cases** | $I_0$ | $\text{LogUniform}(50, 1000)$ | Effective seed volume across London boroughs on day $t_0$. |
| **Behavioral Compliance Multiplier** | $\kappa_{\text{beh}}$ | $\text{Uniform}(0.40, 1.20)$ | Multiplier scaling the empirical CoMix contact reduction under lockdown. |

All clinical progression parameters (incubation 5.2 days, infectious duration 4.5 days, acute length of stay 8.0 days, ICU length of stay 10.0 days) are frozen at their literature-derived values declared in `DiseasePack` and `ObservationConfig`.

---

## 3. Calibration Method: Bayesian Inversion / Observation Likelihood

We employ Bayesian optimization / Approximate Bayesian Computation with an observation likelihood:
$$\mathcal{L}(\boldsymbol{\theta}) = \sum_{t \in T_{\text{train}}} \left[ \log P_{\text{NegBin}}(Y_{\text{adm}}(t) \mid \mu_{\text{adm}}(t, \boldsymbol{\theta}), \phi) + \log P_{\text{NegBin}}(Y_{\text{vent}}(t) \mid \mu_{\text{vent}}(t, \boldsymbol{\theta}), \phi) + \log P_{\text{NegBin}}(Y_{\text{death}}(t) \mid \mu_{\text{death}}(t, \boldsymbol{\theta}), \phi) \right]$$
where $\mu(t, \boldsymbol{\theta})$ is the forward output of the multi-layer agent model passed through the Phase 18 `generate_observations` pipeline.

---

## 4. Pre-Registered Validation Targets & Acceptance Thresholds

### 4.1 Epidemic Curves (Admissions, Ventilated Beds, Deaths)
* **Peak Timing Error**: $|\hat{t}_{\text{peak}} - t_{\text{peak}}^{\text{obs}}| \le 5$ days.
* **Peak Amplitude Ratio**: $0.75 \le \hat{Y}_{\text{peak}} / Y_{\text{peak}}^{\text{obs}} \le 1.25$ (within 25%).
* **Cumulative Volume Relative Error**: $|\sum \hat{Y} - \sum Y^{\text{obs}}| / \sum Y^{\text{obs}} \le 0.20$ (within 20%).
* **Prediction Interval Coverage**: 50% PI covers $\ge 40\%$ of observations; 90% PI covers $\ge 80\%$ of observations across 30 replicates.
* **Continuous Ranked Probability Score (CRPS)**: Must outperform the naive flat baseline and uncalibrated meta engine.

### 4.2 Spatial Arrival Timing
* **Arrival Order Rank Correlation**: Spearman rank correlation $\rho_{\text{spatial}} \ge 0.60$ between observed and simulated local authority dates of reaching 10 hospital admissions.

### 4.3 Healthcare Overflow
* **Ventilated Bed Over-Capacity Days**: Simulated days where occupied mechanical ventilation beds exceeded nominal trust baseline (1,230 beds across London) must match observed overflow duration within $\pm 7$ days.

### 4.4 Behavioral Contact Reduction
* **CoMix Agreement**: Simulated mean contact reduction during National Lockdown 1 (March 23 – May 13, 2020) must match the empirical CoMix survey reduction (72% reduction in non-household contacts, 95% CI [68%, 76%]).

---

## 5. Contingency Plan & Discrepancy Reporting

If any pre-registered threshold is missed during held-out validation:
1. The model status in EpiSwarm Studio UI and documentation will remain **`PARTIALLY VALIDATED`** or **`UNCALIBRATED`**.
2. An honest discrepancy audit will identify the epidemiological mechanism responsible (e.g., absence of age-varying susceptibility, lack of school-term structure, or spatial commuting variance).
3. Adjustments will follow Phase 22 rules: one change at a time, justified by diagnostics, evaluated exclusively on the training window.

