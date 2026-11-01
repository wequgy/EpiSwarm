# EpiSwarm Studio

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![Tests](https://img.shields.io/badge/pytest-70%20passed-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**EpiSwarm Studio** is an agent-based and spatial-flux epidemic simulation and response planning framework. It integrates micro-simulation using NumPy Structure-of-Arrays (SoA) vectorization with the spatial multi-patch epidemiology methods established in **Libin et al. (2020)** (*Deep reinforcement learning for large-scale epidemic control*, arXiv:2003.13676v1).

---

## Key Features

1. **Four Configurable Data Packs**:
   - `RegionPack` (`regions/<name>/`): Supports 3 levels (L0 Quick Region, L1 Area Table, L2 Full).
   - `DiseasePack` (`diseases/<name>.yaml`): Arbitrary directed state-machine graph, overdispersion ($k$), and healthcare overflow penalties.
   - `BehaviorPack` (`behavior/<name>.yaml`): Discrete question types, psychographic traits, compliance dynamics, and misinformation/rumor spread.
   - `ScenarioPack` (`scenarios/<name>.yaml`): Seeding, phased interventions (school closures, curfew, surge beds), and optimization objectives.

2. **Scientific Transmission Dynamics (Libin et al. 2020)**:
   - Analytical $\beta$ initialization via the Next-Generation Matrix spectral radius:
     $$R_0 = \frac{\beta}{\gamma} \cdot \Upsilon(M)$$
   - Inter-area commuting flows and gravity spatial impedance.
   - Discrete-time scale transformation for non-homogeneous Poisson commute arrivals.

3. **High-Performance Structure-of-Arrays (SoA)**:
   - Pure contiguous NumPy array memory representation (zero per-agent Python objects).
   - Peak RAM at 100,000 agents: **245.9 MB** (70x below the 11 GB hardware budget).
   - Population synthesis speed: **0.10s** for 100,000 agents.

4. **Healthcare Overflow Model**:
   - Multi-category capacity tracking: General, HDU, ICU, and Mechanical Ventilators.
   - Spatial patient overflow routing to nearest administrative areas with spare capacity.
   - Mortality amplification with individual compliance mitigation benefits.

5. **Decision Advisor & Multi-Objective Search**:
   - Autonomous Advisor agent with tool calling (`run_scenario`, `get_metrics`, `compare`, `list_measures`).
   - Optuna NSGA-II multi-objective optimization exploring Pareto frontiers (deaths vs. economic cost proxy).
   - Three-arm comparison harness: Advisor Alone vs. Search Alone vs. Combined.

6. **Interactive Studio App (Streamlit + Plotly)**:
   - Complete 8-step guided workflow: Region, Disease, Healthcare, Scenario, Run, Analysis/Equity, Advisor/Optimizer, and Audit Export.
   - Column mapper wizard for uploading external CSV/Excel data.

---

## Quickstart

### 1. Installation
Clone the repository and install dependencies in editable mode:
```bash
git clone https://github.com/your-username/EpiSwarm.git
cd EpiSwarm
pip install -e .
```

### 2. Run Diagnostics & Unit Tests
Run the API health check (never prints keys) and full unit test suite:
```bash
python scripts/check_apis.py
pytest -v
```

### 3. Run Benchmark
Measure runtime and peak memory scaling across 5k, 50k, and 100k agents:
```bash
python scripts/benchmark.py
```

### 4. Launch EpiSwarm Studio Web App
```bash
streamlit run src/episwarm/app/streamlit_app.py
```

---

## Provenance & Honesty Rules

- **Default Uncalibrated State**: In accordance with project integrity standards, all simulation runs are marked **`UNCALIBRATED`** unless calibrated against empirical `observed_cases.csv`.
- **Synthetic Fixtures**: Runs using fixture data (`regions/example_synthetic`) display a prominent **`SYNTHETIC DATA`** badge.
- **Behavior Layer**: The LLM decision policy layer carries a persistent **`Behavior layer unvalidated for this region`** disclosure.

---

## Repository Layout

```
episwarm/
  README.md  ASSUMPTIONS.md  DATA_SOURCES.md  MODEL_CARD.md
  pyproject.toml  .env.example  .gitignore
  regions/      example_synthetic/
  diseases/     respiratory_generic.yaml  influenza_generic.yaml
  behavior/     default.yaml
  scenarios/    baseline.yaml
  src/episwarm/
    packs/       region.py disease.py behavior.py scenario.py schema.py
    importers/   csv_xlsx.py mapper.py templates.py validate.py quick_region.py
    population/  build.py households.py venues.py traits.py ipf.py
    engine/      state_graph.py contacts.py infection.py healthcare.py sim.py
    behavior/    buckets.py policy_base.py policy_rules.py policy_jev.py policy_gemini.py policy_openai_compat.py cache.py
    advisor/     tools.py agent.py schemas.py memory.py
    optimize/    search.py comparison.py
    analysis/    metrics.py equity.py calibration.py sensitivity.py spread_matrix.py variance_check.py
    app/         streamlit_app.py
  scripts/       benchmark.py validate_region.py make_synthetic_region.py check_apis.py
  tests/         test_packs_phase0.py test_population_phase1.py test_engine_phase2.py test_healthcare_phase3.py test_behavior_phase4.py test_analysis_phase5.py test_advisor_optimizer_phase6.py test_app_calibration_phase7_8.py
```

