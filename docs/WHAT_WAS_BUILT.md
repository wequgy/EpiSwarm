# What Was Built: A Plain-Language Guide to EpiSwarm Studio

This document explains what EpiSwarm Studio is, how it works, and what it contains in simple words for non-experts.

---

## 1. What EpiSwarm Studio Does

Imagine you are managing public health for a region facing a new infectious disease outbreak. You want to understand:
- *If an outbreak starts in Ward 1, how many days before it spreads to Ward 4?*
- *Will our intensive care beds run out, and if so, on what day?*
- *If we close schools for three weeks versus reducing workplace capacity by half, which policy saves more lives with less economic damage?*

EpiSwarm Studio creates a **synthetic city inside the computer**:
1. It creates thousands of simulated residents with ages, jobs, homes, and schools.
2. It simulates daily routines: residents leave home, go to work or school, visit markets, and return home.
3. If an infected resident meets a susceptible resident in a shared venue (home, school, office, or transit), the disease can transmit.
4. If residents get sick, they progress through incubation, symptoms, and either recover at home or require a hospital bed.
5. If hospitals run out of beds, the system tracks the overflow and estimates the consequences.
6. An automated Policy Advisor compares different interventions (closing schools, curfew, adding temporary beds) and finds the most effective balance.

> [!IMPORTANT]
> **What EpiSwarm Studio Is NOT**: It is not a crystal ball. It does **not** predict the exact future date when an outbreak will happen. It is an exploration tool that answers: *"Under these stated assumptions, what would happen if we took Measure A versus Measure B?"*

---

## 2. Repository Map (Folder by Folder)

- `src/episwarm/packs/`: Defines the structure and rules for user input files (regions, diseases, behaviors, and scenarios) using Pydantic.
- `src/episwarm/importers/`: Loads spreadsheets (CSV/Excel), auto-maps column names, validates numbers, and includes a Quick-Region generator.
- `src/episwarm/population/`: Generates synthetic residents, groups them into households with adults, and assigns workplaces, schools, and commuting paths.
- `src/episwarm/engine/`: The core daily simulation clock; calculates transmissions per venue, runs disease state changes, routes patients to hospital beds, and tracks overflow.
- `src/episwarm/behavior/`: Handles how simulated residents react to news and policies; includes local free AI models, paid APIs, rules, and a fast SQLite cache.
- `src/episwarm/advisor/`: An automated planning agent that tests different response policies and writes a structured recommendation for human leaders.
- `src/episwarm/optimize/`: Uses Optuna (NSGA-II) to mathematically search thousands of policy combinations and discover the best trade-offs (Pareto frontier).
- `src/episwarm/analysis/`: Calculates spatial arrival times (spread matrix), fairness across demographic groups (equity audit), and sensitivity to key assumptions.
- `src/episwarm/app/`: The interactive web dashboard built with Streamlit and Plotly charts.
- `regions/`: Holds region data folders; contains `example_synthetic/` used for testing.
- `diseases/`: Holds disease definition YAML files (`respiratory_generic.yaml` and `influenza_generic.yaml`).
- `behavior/`: Holds decision prompt templates and trait distributions (`default.yaml`).
- `scenarios/`: Holds test scenarios with seeding and policy timelines (`baseline.yaml`).
- `scripts/`: Diagnostic and utility commands (`setup_keys.py`, `check_apis.py`, `benchmark.py`, `demo.py`, `mutation_test.py`).
- `tests/`: 45 automated pytest verification checks ensuring population conservation, reproducibility, and mathematical invariants.
- `docs/`: Plain-language guides, implementation specs, status audits, and architecture diagrams.

---

## 3. What is Real, What is Placeholder, and What is Synthetic?

- **Real & Verified**:
  - The mathematics of transmission ($R_0 \leftrightarrow \beta$ calibration via Next-Generation Matrix spectral radius $\Upsilon(M)$ from Libin et al. 2020).
  - The high-speed memory layout (NumPy Structure-of-Arrays), ensuring 100,000 agents run in under 160 MB of RAM.
  - The household composer (guaranteeing 100% of households contain at least one adult).
  - The automated policy search and spatial routing to nearest open hospital beds.
- **Placeholders (To be expanded in Phases 10–13)**:
  - Dynamic rumor network (agents currently possess rumor traits, but peer-to-peer social network transmission will be added in Phase 11).
  - Multi-factor individual patient survival model (currently uses a base overflow multiplier modulated by compliance; will become a 6-parameter logistic model in Phase 10).
  - Generic resources (currently models general beds and ICU; will be abstracted into fully customizable resources in Phase 10).
- **Synthetic**:
  - The data in `regions/example_synthetic/` is completely artificial. It does not represent any real-world city or real patient records. It exists solely to test the code.

---

## 4. What Has NOT Been Tested with Real Data or Live APIs

- **No Live Paid APIs Tested Yet**: We have intentionally not made live paid calls to TypeSafe AI Jev or Google Gemini. The system was tested using the offline `RulePolicy` and local mock/Ollama logprob handlers.
- **No Real Epidemic Data Calibrated**: The model has not been calibrated against real-world hospital time-series data yet. Therefore, all outputs are honestly labeled **UNCALIBRATED**.
- **Behavior Layer Fidelity**: The decisions of synthetic residents are hypothetical models of human behavior, not validated psychological forecasts.
