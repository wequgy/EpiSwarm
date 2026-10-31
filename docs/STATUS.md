# EpiSwarm Studio: Audit & Status (`docs/STATUS.md`)

This audit records the factual implementation status of all requirements across the framework specification, user additions, and roadmap phases. In adherence to our **Evidence Before Claims** rule, every status is grounded in reproducible command outputs.

---

## 1. Explicit Status of Key Requested Capabilities

| Capability | Status | Current Code Location | Test Coverage | Evidence & Audit Assessment |
|---|---|---|---|---|
| **1. Rumor & Misinformation Layer** | **IMPLEMENTED** | `src/episwarm/behavior/network.py`, `src/episwarm/behavior/rumor.py` | `tests/test_rumor_compliance_phase11.py` | Sparse CSR network $A \cdot \text{share}_k$, sharing trials, saturating exposure $f(\text{exp})$, official correction campaigns, behavioral distortions, and counterfactual paired-seed CI analysis. |
| **2. Dynamic Compliance Model** | **IMPLEMENTED** | `src/episwarm/behavior/compliance.py` | `tests/test_rumor_compliance_phase11.py` | Dynamic compliance $c_i(t)$ incorporating base traits, risk perception, peer network norm ($A \cdot c$), area enforcement, policy fatigue accumulation/recovery, and rumor erosion ($\kappa \cdot \text{belief}$). |
| **3. Sanitation & Environment Inputs** | **IMPLEMENTED** | `src/episwarm/engine/infection.py`, `regions/example_synthetic/environment.csv` | `tests/test_core_model_phase10.py` | `environment.csv` schema and `environment_modifiers` implemented. Household transmission scales with `persons_per_room` crowding. Verified in Phase 10 suite. |
| **4. Disease-Specific Vulnerability Factors** | **IMPLEMENTED** | `src/episwarm/packs/disease.py`, `src/episwarm/population/build.py` | `tests/test_core_model_phase10.py` | `VulnerabilityFactor` schemas, `risk_factors.csv` contract, uint32 bitmasks, and logit-scale odds ratios ($\text{logit}(p') = \text{logit}(p) + \log(\text{OR})$) fully operational. |
| **5. Individual-Factor Outcomes for Unserved Patients** | **IMPLEMENTED** | `src/episwarm/engine/resources.py` | `tests/test_core_model_phase10.py` | Spec 6.3 multi-factor formula ($\theta_0, \theta_{\text{sev}}, \theta_{\text{care}}, \theta_{\text{sup}}, \theta_{\text{alt}}, \theta_{\text{delay}}$) verified: $\theta_0 = 0 \implies$ unserved equals served; high $\theta_{\text{care}} \implies$ low self-care agents suffer worse outcomes under identical overflow. |
| **6. Per-Agent Life Histories & Routines** | **IMPLEMENTED** | `src/episwarm/population/build.py` | `tests/test_core_model_phase10.py` | `PopulationSoA` stores structured facts (`income_band`, `household_role`, `caregiver`, `financial_buffer`, `past_bereavement`, `routine_template`, `pref_market_id`, `pref_leisure_id`, `self_care`, `support`). Showcase biographies generated with `[GENERATED NARRATIVE - SYNTHETIC DATA ONLY]`. |
| **7. Resource What-If & Generic Resources** | **IMPLEMENTED** | `src/episwarm/engine/resources.py`, `src/episwarm/analysis/resource_whatif.py`, `src/episwarm/analysis/marginal_value.py` | `tests/test_resource_whatif_phase12.py` | Zero instances of "oxygen" in `src/`. `resources.csv` contract, `ResourceAddAction` with `upper_cap_of_extra` bounds, paired-seed delta reports with 95% CI, diminishing returns curves, best-area ranking, and Studio panel. |
| **8. Social-Space Venues** | **IMPLEMENTED** | `src/episwarm/population/venues.py` | `tests/test_core_model_phase10.py` | Instantiates discrete school, workplace, market, leisure, and worship venues. Assigns persistent preferred market and leisure venues per agent for tie stability across days. |

---

## 2. Core Framework Requirements Matrix

| Requirement | Status | Implementation File | Verification Test | Real Command Evidence & Result |
|---|---|---|---|---|
| **Pydantic Pack Schemas** | **IMPLEMENTED** | `src/episwarm/packs/*.py` | `tests/test_packs_phase0.py` | `pytest tests/test_packs_phase0.py` -> 9 passed |
| **Generality Rule (No place/disease names in src/)** | **IMPLEMENTED** | `tests/test_core_model_phase10.py` | `test_grep_no_forbidden_resource_or_disease_names_in_src` | `pytest tests/test_core_model_phase10.py` -> PASSED (0 hardcoded strings) |
| **Structure-of-Arrays (NumPy)** | **IMPLEMENTED** | `src/episwarm/population/build.py` | `tests/test_population_phase1.py` | 100,000 agents in 4.29 MB array memory |
| **Iterative Proportional Fitting (IPF)** | **IMPLEMENTED** | `src/episwarm/population/ipf.py` | `test_ipf_convergence_2d` | `pytest tests/test_population_phase1.py` -> PASSED (tol < 1e-5) |
| **Household Adult Guarantee** | **IMPLEMENTED** | `src/episwarm/population/households.py` | `test_household_adult_invariant` | 100% households have $\ge 1$ adult |
| **Next-Gen Matrix Spectral Radius Υ(M)** | **IMPLEMENTED** | `src/episwarm/engine/contacts.py` | `test_spectral_radius_and_beta_analytical` | $R_0 = \frac{\beta}{\gamma}\Upsilon(M)$ verified |
| **Layered Infection (`numpy.bincount`)** | **IMPLEMENTED** | `src/episwarm/engine/infection.py` | `test_population_conservation_invariant` | O(N) daily complexity, 100k agents in 13.4s |
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

### 3.1 Test Suite Summary Line
- **Test Files**: 13 test files (`test_packs_phase0.py`, `test_population_phase1.py`, `test_engine_phase2.py`, `test_healthcare_phase3.py`, `test_behavior_phase4.py`, `test_analysis_phase5.py`, `test_advisor_optimizer_phase6.py`, `test_app_calibration_phase7_8.py`, `test_policy_local.py`, `test_app_headless.py`, `test_core_model_phase10.py`, `test_rumor_compliance_phase11.py`, `test_resource_whatif_phase12.py`).
- **Individual Test Functions**: **58 total test functions** across all files.
- **pytest Output**: `58 passed in 44.17s` (100% green).

### 3.2 Benchmark Output (`python scripts/benchmark.py`)
```
================ EpiSwarm Scale Benchmark ================
Target Machine: 16GB RAM constraint (Peak Memory < 11GB target)

 scale  pop_time_sec  sim_time_sec  total_time_sec  end_rss_mb  peak_wset_mb  theoretical_soa_mb  attack_rate_pct
  5000          0.03          0.53            0.57       146.2         146.2                0.21              2.0
 50000          0.06          4.99            5.05       148.8         154.0                2.15              0.1
100000          0.09         13.39           13.49       152.4         162.7                4.29              0.0
==========================================================
```

### 3.3 Mutation Testing Output (`python scripts/mutation_test.py`)
```
=== Running 5 Mutation Sanity Checks ===
[PASSED] 1. Population conservation violation: Test correctly caught mutation and FAILED.
[PASSED] 2. Absorbing state schema invariant violation: Test correctly caught mutation and FAILED.
[PASSED] 3. Household adult invariant violation: Test correctly caught mutation and FAILED.
[PASSED] 4. Generality rule violation (hardcoded place): Test correctly caught mutation and FAILED.
[PASSED] 5. Healthcare capacity violation (ignore 0 capacity): Test correctly caught mutation and FAILED.
```
