# EpiSwarm Studio: Audit & Status (`docs/STATUS.md`)

This audit records the factual implementation status of all requirements across the framework specification, user additions, and Phase 9 audit checks. In adherence to our **Evidence Before Claims** rule, every status is grounded in reproducible command outputs.

---

## 1. Explicit Status of Key Requested Capabilities

| Capability | Status | Current Code Location | Test Coverage | Evidence & Audit Assessment |
|---|---|---|---|---|
| **1. Rumor & Misinformation Layer** | **PARTIAL / STUBBED** | `src/episwarm/population/traits.py` (line 14), `behavior/default.yaml` | `tests/test_behavior_phase4.py` | Agent `rumor_susceptibility` trait and topic parameters exist; however, the dynamic social network propagation ($A \cdot \text{share}_k$, sparse adjacency matrix, belief updates, correction campaigns per Spec Section 7) is **not yet implemented** (scheduled for Phase 11). |
| **2. Dynamic Compliance Model** | **PARTIAL / STUBBED** | `src/episwarm/population/traits.py`, `src/episwarm/engine/infection.py` (line 103) | `tests/test_healthcare_phase3.py` | Static compliance trait and linear scaling exist; dynamic fatigue accumulation, social norm feedback ($w_{\text{norm}}$), and rumor erosion (Spec Section 8) are **not yet implemented** (scheduled for Phase 11). |
| **3. Sanitation & Environment Inputs** | **PARTIAL** | `src/episwarm/importers/templates.py`, `regions/example_synthetic/sanitation.csv` | `tests/test_packs_phase0.py` | `sanitation.csv` exists and is validated; generalized `environment.csv` with multi-dimensional indicators (water, sanitation, crowding scaling per Spec 5.2) is **partially complete** (scheduled for Phase 10). |
| **4. Disease-Specific Vulnerability Factors** | **PARTIAL** | `src/episwarm/packs/disease.py`, `src/episwarm/population/traits.py` | `tests/test_population_phase1.py` | Comorbidity table and age multipliers exist; full bit-flag vulnerability factors with logit-scale odds ratios (`vulnerability_factors[]`, `risk_factors.csv` per Spec 5.1) are **scheduled for Phase 10**. |
| **5. Individual-Factor Outcomes for Unserved Patients** | **PARTIAL / STUBBED** | `src/episwarm/engine/healthcare.py` (line 140) | `tests/test_healthcare_phase3.py` | Basic overflow mortality multiplier modulated by compliance exists; the multi-factor individual logistic outcome model ($\theta_0, \theta_{\text{care}}, \theta_{\text{sup}}, \theta_{\text{alt}}, \theta_{\text{delay}}$ per Spec 6.3) is **scheduled for Phase 10**. |
| **6. Per-Agent Life Histories & Routines** | **PARTIAL / STUBBED** | `src/episwarm/population/build.py` | `tests/test_population_phase1.py` | Demographics and occupations exist; structured life history facts (`financial_buffer`, `caregiver`, `chronic_bits`, routine templates, showcase biographies per Spec 9) are **scheduled for Phase 10**. |
| **7. Resource What-If & Generic Resources** | **PARTIAL** | `src/episwarm/engine/healthcare.py`, `scenarios/baseline.yaml` | `tests/test_healthcare_phase3.py` | Beds and ICU capacity routing exist; fully generic resources (removing all specific names from `src/`, `resource_adds`, marginal value sweeps per Spec 6.4) are **scheduled for Phase 10 & 12**. |
| **8. Social-Space Venues** | **PARTIAL** | `src/episwarm/population/venues.py` | `tests/test_population_phase1.py` | Schools, workplaces, and markets are modeled; persistent preferred leisure/social-space routine venues per Spec 9 are **scheduled for Phase 10**. |

---

## 2. Core Framework Requirements Matrix

| Requirement | Status | Implementation File | Verification Test | Real Command Evidence & Result |
|---|---|---|---|---|
| **Pydantic Pack Schemas** | **IMPLEMENTED** | `src/episwarm/packs/*.py` | `tests/test_packs_phase0.py` | `pytest tests/test_packs_phase0.py` -> 9 passed |
| **Generality Rule (No place/disease names in src/)** | **IMPLEMENTED** | `tests/test_packs_phase0.py` | `test_generality_rule` | `pytest tests/test_packs_phase0.py` -> PASSED (0 hardcoded strings) |
| **Structure-of-Arrays (NumPy)** | **IMPLEMENTED** | `src/episwarm/population/build.py` | `tests/test_population_phase1.py` | 100,000 agents in 4.29 MB array memory |
| **Iterative Proportional Fitting (IPF)** | **IMPLEMENTED** | `src/episwarm/population/ipf.py` | `test_ipf_convergence_2d` | `pytest tests/test_population_phase1.py` -> PASSED (tol < 1e-5) |
| **Household Adult Guarantee** | **IMPLEMENTED** | `src/episwarm/population/households.py` | `test_household_adult_invariant` | 100% households have $\ge 1$ adult |
| **Next-Gen Matrix Spectral Radius Υ(M)** | **IMPLEMENTED** | `src/episwarm/engine/contacts.py` | `test_spectral_radius_and_beta_analytical` | $R_0 = \frac{\beta}{\gamma}\Upsilon(M)$ verified |
| **Layered Infection (`numpy.bincount`)** | **IMPLEMENTED** | `src/episwarm/engine/infection.py` | `test_population_conservation_invariant` | O(N) daily complexity, 100k agents in 13.6s |
| **Spatial Gravity Commute Flux** | **IMPLEMENTED** | `src/episwarm/population/venues.py` | `tests/test_population_phase1.py` | Libin et al. (2020) gravity impedance $T_{ij} \propto P_j / d_{ij}^\alpha$ |
| **Spatial Spread Matrix** | **IMPLEMENTED** | `src/episwarm/analysis/spread_matrix.py` | `test_spread_matrix_computation` | Mean arrival days & hit order computed |
| **Demographic & Geographic Equity** | **IMPLEMENTED** | `src/episwarm/analysis/equity.py` | `test_equity_evaluation` | Area and age attack rate disparity gaps |
| **Decision Cache (SQLite)** | **IMPLEMENTED** | `src/episwarm/behavior/cache.py` | `test_decision_cache_persistence` | Keyed by (bucket, situation, question) |
| **Free Local Logprob Policy** | **IMPLEMENTED** | `src/episwarm/behavior/policy_local.py` | `tests/test_policy_local.py` | Top logprobs over single-token labels with order-shuffling |
| **Advisor Agent** | **IMPLEMENTED** | `src/episwarm/advisor/agent.py` | `test_advisor_toolkit_and_agent` | Generates Pydantic `Recommendation` |
| **NSGA-II Multi-Objective Search** | **IMPLEMENTED** | `src/episwarm/optimize/search.py` | `test_optuna_nsga2_search` | Optuna Pareto front (deaths vs cost) |
| **Three-Arm Comparison** | **IMPLEMENTED** | `src/episwarm/optimize/comparison.py` | `test_three_arm_comparison` | Advisor vs Search vs Combined vs Brute Force |
| **Streamlit Studio App** | **IMPLEMENTED** | `src/episwarm/app/streamlit_app.py` | `test_streamlit_studio_all_steps_headless` | `pytest tests/test_app_headless.py` -> PASSED (AppTest 0 errors) |
| **Observed Data Calibration** | **IMPLEMENTED** | `src/episwarm/analysis/calibration.py` | `test_calibration_honesty_rule` | Enforces UNCALIBRATED label without empirical data |

---

## 3. Real Test & Benchmark Evidence

### 3.1 Test Suite Summary Line Clarification
Earlier reports referred to test suites passing. Specifically:
- **Test Files**: 9 test files (`test_packs_phase0.py`, `test_population_phase1.py`, `test_engine_phase2.py`, `test_healthcare_phase3.py`, `test_behavior_phase4.py`, `test_analysis_phase5.py`, `test_advisor_optimizer_phase6.py`, `test_app_calibration_phase7_8.py`, `test_policy_local.py`, `test_app_headless.py`).
- **Individual Test Functions**: **45 total test functions** across all files.
- **pytest Output**: `45 passed in 23.4s` (100% green).

### 3.2 Benchmark Output (`python scripts/benchmark.py`)
```
================ EpiSwarm Scale Benchmark ================
Target Machine: 16GB RAM constraint (Peak Memory < 11GB target)

 scale  pop_time_sec  sim_time_sec  total_time_sec  end_rss_mb  peak_wset_mb  theoretical_soa_mb  attack_rate_pct
  5000          0.03          0.59            0.63       145.5         145.5                0.21              1.8
 50000          0.05          5.53            5.59       147.1         151.3                2.15              0.1
100000          0.12         13.68           13.83       152.6         157.0                4.29              0.0
==========================================================
```
**Measurement Methodology**:
- Execution times measured with high-precision `time.perf_counter()`.
- Memory measured via Windows OS Working Set (`psutil.Process().memory_info().peak_wset`).
- Peak memory for 100,000 agents is **157.0 MB**, which is **70x below** the 11 GB ceiling.

### 3.3 Mutation Sanity Check Evidence (`python scripts/mutation_test.py`)
```
=== Running 5 Mutation Sanity Checks ===
[PASSED] 1. Population conservation violation: Test correctly caught mutation and FAILED.
[PASSED] 2. Absorbing state schema invariant violation: Test correctly caught mutation and FAILED.
[PASSED] 3. Household adult invariant violation: Test correctly caught mutation and FAILED.
[PASSED] 4. Generality rule violation (hardcoded place): Test correctly caught mutation and FAILED.
[PASSED] 5. Healthcare capacity violation (ignore 0 capacity): Test correctly caught mutation and FAILED.
All 5 mutations successfully detected and reverted.
```
