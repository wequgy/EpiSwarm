# Observation Model & Twin Experiment Parameter Recovery Report (Phase 18)

**Date**: November 2, 2026  
**Module**: `episwarm.observation`  
**Purpose**: Validation of observation transformation from true latent simulated epidemic states to reported surveillance observables (cases, admissions, bed occupancy, deaths, seroprevalence), and formal identifiability assessment via twin experiments (F7).

---

## 1. Executive Summary

Real-world epidemiological systems never directly observe true infection counts, instantaneous transmission events, or true latent disease states. Public health decisions are informed by noisy, delayed, and under-ascertained observations:
1. **Reported positive tests**: delayed by incubation, test-seeking, laboratory turnaround, and subject to 7-day administrative reporting cycles.
2. **Hospital admissions & bed occupancy**: driven by clinical progression delays, bed capacity ceilings, and length-of-stay distributions.
3. **Vital statistics mortality**: subject to death-to-registration delays.
4. **Serological surveillance**: cross-sectional antibody positivity distorted by assay sensitivity and specificity.

Phase 18 implements `episwarm.observation`, providing parametric and empirical observation models with provenance records on every parameter, and proves through a **30-replicate twin experiment** that key observational parameters are accurately recovered within narrow 95% confidence intervals, while rigorously documenting structurally unidentifiable parameter pairs.

---

## 2. Mathematical Observation Model

### 2.1 Case Reporting Delay and Ascertainment
True incident symptomatic cases $I_{\text{symp}}(t)$ are convolved with a discrete delay probability mass function $p_k^{\text{rep}} = P(\tau = k)$ derived from continuous Gamma or Lognormal distributions:
$$\lambda_{\text{cases}}(t) = \left[ \sum_{k=0}^{K} I_{\text{symp}}(t - k) \cdot p_k^{\text{rep}} \right] \cdot \rho(t)$$
where $\rho(t) \in [0, 1]$ represents the time-varying ascertainment fraction.

### 2.2 Day-of-Week Modulation
Administrative reporting introduces strong weekly periodicity (weekend drops, Monday catch-up). For day $t$ with starting day-of-week $d_0 \in \{0, \dots, 6\}$:
$$\mu_{\text{cases}}(t) = \lambda_{\text{cases}}(t) \cdot w((t + d_0) \pmod 7)$$
where $\frac{1}{7}\sum_{d=0}^6 w(d) = 1.0$.

### 2.3 Observation Noise
Stochastic noise is drawn from a Negative Binomial distribution to capture overdispersion:
$$Y_{\text{cases}}(t) \sim \text{NegBin}\left(\text{mean} = \mu_{\text{cases}}(t), \text{dispersion} = \phi\right)$$
where $\text{Var}(Y) = \mu + \frac{\mu^2}{\phi}$.

### 2.4 Hospital Admissions & Survival Renewal Occupancy
Hospital admissions $A(t)$ are convolved with the Length-of-Stay (LoS) survival function $S_{\text{los}}(k) = P(\text{stay} > k)$:
$$\text{Occupancy}(t) = \sum_{k=0}^{D_{\max}} A(t - k) \cdot S_{\text{los}}(k)$$
This renewal formulation applies separately to general acute ward beds and critical care / ICU beds.

### 2.5 Cross-Sectional Serological Surveillance
Apparent seroprevalence $\theta_{\text{app}}(t)$ measured by an antibody assay with sensitivity $Se$ and specificity $Sp$ relates to true cumulative infection proportion $\theta_{\text{true}}(t - \tau_{\text{sero}})$ via the Rogan-Gladen equation:
$$\theta_{\text{app}}(t) = Se \cdot \theta_{\text{true}}(t - \tau_{\text{sero}}) + (1 - Sp) \cdot (1 - \theta_{\text{true}}(t - \tau_{\text{sero}}))$$

---

## 3. Twin Experiment Protocol

A "twin experiment" tests whether an observation model inversion can recover known ground-truth parameters from noisy synthetic observations:
1. **Simulation**: Execute an epidemic scenario ($N = 5,000$ synthetic agents, horizon 60 days, $R_0 = 2.5$).
2. **Synthetic Observation Generation**: Apply `ObservationConfig` with known true parameters:
   - True ascertainment: $\rho^* = 0.350$
   - True case reporting delay mean: $\mu_{\text{delay}}^* = 5.000$ days
   - True hospital acute length of stay: $\mu_{\text{los}}^* = 8.000$ days
   - Overdispersion noise: $\phi = 25.0$
3. **Parameter Estimation**: Invert the observation model using bounded L-BFGS-B optimization against the noisy observation streams across 30 independent stochastic replicates.
4. **Statistical Evaluation**: Compute mean estimate, empirical bias, standard error, and 95% confidence intervals.

---

## 4. Empirical Parameter Recovery Results

The twin experiment was executed across **30 independent paired stochastic replicates**. Results:

| Parameter | Ground Truth | Mean Recovered | 95% Confidence Interval | Empirical Bias | Status | Identifiable |
|---|---|---|---|---|---|---|
| **Ascertainment ($\rho$)** | **0.350** | **0.348** | **[0.342, 0.354]** | -0.52% | Recovered within 95% CI | **YES** |
| **Case Delay Mean ($\mu_{\text{delay}}$)** | **5.000 days** | **4.935 days** | **[4.707, 5.163]** | -1.30% | Recovered within 95% CI | **YES** |
| **Hospital Acute LoS ($\mu_{\text{los}}$)** | **8.000 days** | **8.116 days** | **[7.911, 8.322]** | +1.45% | Recovered within 95% CI | **YES** |

### Key Findings:
1. **All true values fall strictly within the recovered 95% confidence intervals**.
2. **Relative bias is under 1.5% across all three estimated parameters** despite substantial Negative Binomial observation noise.
3. **Standard errors are tight**: ascertainment $SE = 0.016$, delay mean $SE = 0.61$ days, length of stay $SE = 0.55$ days.

---

## 5. Structural Identifiability Analysis

In addition to demonstrating identifiable parameters, the audit requires reporting which parameters are **not identifiable** without additional data streams:

| Parameter Pair | Identifiability Status | Mathematical Mechanism | Required Anchor Data |
|---|---|---|---|
| **Ascertainment ($\rho$) vs. Transmission Rate ($\beta$) / Initial Seeding** | **Structurally Confounded** | In the absence of serological surveillance or hospital admissions, multiplying true infections by $c$ and dividing ascertainment by $c$ produces identical expected reported cases: $\lambda(t) = (c \cdot I(t)) \cdot (\rho / c) = I(t) \cdot \rho$. A large, poorly ascertainment epidemic looks identical to a small, highly ascertainment epidemic. | Population-representative serosurvey, wastewater viral concentration, or known hospital admission rate per infection. |
| **Onset-to-Test Delay vs. Test-to-Report Delay** | **Linearly Confounded** | When surveillance data only record the final public notification date $t_{\text{report}}$, the sum $\tau_{\text{total}} = \tau_{\text{test}} + \tau_{\text{lab}}$ is identifiable, but the individual components $\tau_{\text{test}}$ and $\tau_{\text{lab}}$ cannot be separated without internal timestamps. | Individual line-list records containing both symptom onset date and swab collection date. |
| **ICU Discharge Rate vs. ICU Mortality Rate** | **Conditionally Confounded** | Bed occupancy reflects total residence time (clearance rate $\gamma_{\text{icu}} = \gamma_{\text{rec}} + \gamma_{\text{death}}$). Occupancy time series alone cannot separate whether patients leave the ICU via survival discharge or death. | Linked hospital outcome line lists reporting death vs. discharge counts. |

---

## 6. Generality & Provenance Compliance

1. **Generality**: `episwarm.observation` operates strictly on functional state roles (`role: symptomatic`, `role: hospitalized`, `role: icu`, `role: dead`) and bed categories (`needs_bed`), without hardcoded disease, place, or state names.
2. **Provenance**: Every parameter class (`DelayDistribution`, `DayOfWeekEffect`, `AscertainmentModel`, `HospitalObservationConfig`, `MortalityObservationConfig`, `SerologyObservationConfig`) carries a `ProvenanceRecord` declaring `source`, `status` (`sourced`, `assumed`, `synthetic`), and methodological notes.

