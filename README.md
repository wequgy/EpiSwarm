# EpiSwarm Studio

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![Tests](https://img.shields.io/badge/pytest-143%20passed-brightgreen.svg)]()
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
   - Peak RAM at 100,000 agents: **239.6 MB** (70x below the 11 GB hardware budget).
   - Population synthesis speed: **0.10s** for 100,000 agents.

4. **Healthcare Overflow Model**:
   - Multi-category capacity tracking: General, HDU, ICU, and Mechanical Ventilators.
   - Spatial patient overflow routing to nearest administrative areas with spare capacity.
   - Mortality amplification with individual compliance mitigation benefits.

5. **Decision Advisor & Multi-Objective Search**:
   - Autonomous Advisor agent with tool calling (`run_scenario`, `get_metrics`, `compare`, `list_measures`).
   - Optuna NSGA-II multi-objective optimization exploring Pareto frontiers (deaths vs. economic cost proxy).
   - Three-arm comparison harness: Advisor Alone vs. Search Alone vs. Combined.

6. **Decoupled Modern Web Studio & API v1**:
   - Modern React 18 + TypeScript + Vite + Tailwind CSS + ECharts frontend.
   - Interactive 3D Isometric City Diorama with spatial wavefront scrubbing and borough block extrusion.
   - FastAPI headless service facade with RFC 7807 problem details error handling.
   - Persistent SQLite job queue with Server-Sent Events (SSE) streaming real-time simulation progress.

---

## Quickstart

### 1. Installation
Clone the repository and install dependencies in editable mode:
```bash
git clone https://github.com/your-username/EpiSwarm.git
cd EpiSwarm
pip install -e .
```

To build the web frontend:
```bash
cd web
npm install
npm run build
cd ..
```

### 2. Run Diagnostics & Unit Tests
Run the API test suite:
```bash
pytest tests/test_api_v1_contract.py tests/test_api_phase24.py -v
```

### 3. Launch EpiSwarm Studio Web Platform
Run full-stack development mode:
```powershell
.\scripts\dev.ps1
```

Or run the production server (FastAPI directly serving the modern Vite build):
```bash
uvicorn episwarm.api.main:app --host 0.0.0.0 --port 8000
```
Open [http://localhost:8000](http://localhost:8000) in your browser.

Or with Docker Compose:
```bash
docker compose up --build
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
    service/     models.py packs.py simulation.py jobs.py trust.py system.py
    api/         main.py v1/
  web/           src/ dist/ package.json vite.config.ts openapi.json
  scripts/       export_openapi.py dev.ps1 benchmark.py check_apis.py
  tests/         test_api_v1_contract.py test_api_phase24.py
```

