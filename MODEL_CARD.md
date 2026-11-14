# EpiSwarm Studio: Model Card (`MODEL_CARD.md`)

## 1. Model Details
- **Model Name**: EpiSwarm Studio v2 (Authority-Grade Simulation Workbench)
- **Version**: 2.0.0 (Production Framework)
- **Model Architecture**: Dual-Engine Hybrid with Live Control Channel:
  1. Micro-scale Agent-Based Model utilizing NumPy Structure-of-Arrays (SoA) vectorized transitions across physical venue layers (household, school, workplace, community).
  2. Macro-scale Metapopulation Patch Model (`engine_meta`) following **Libin et al. (2020, arXiv:2003.13676)** with age-structured intra-patch SEIR (binomial chain) and inter-patch non-homogeneous Poisson arrival processes via time-scale transformation.
  3. Interactive Live Control & Step Channel (`/api/v2/runs/{id}/live`) supporting step-by-step frame emission, live override injection, and bitwise deterministic checkpoint branching.
- **Reference Standard**: Libin et al. (2020), *Deep reinforcement learning for large-scale epidemic control*, arXiv:2003.13676v1.
- **License**: MIT / Open Science Research

---

## 2. Intended Use & Public Health Scope
EpiSwarm Studio v2 is an authority-grade workbench for regional public health authorities to model epidemics within their own jurisdictions with empirical integrity and transparent provenance:
- **Guided Case File Intake**: 8-section intake wizard for populations, commuting matrices, hospital bed capacities, pathogen genetics, behavioral compliance, and policy schedules.
- **Bitwise Deterministic Pause & Resume**: Checkpoint synchronization preserving exact RNG seeds, unserved days, risk bands, and rumor beliefs (`diff = 0` bitwise reproduction).
- **Interactive Simulation Stage**: 60 fps commuter motion visualization, borough infection heatmaps, hospital capacity breach alerts, and real-time situational briefings.
- **Comprehensive Insights & Policy Optimization**: Unified multi-replicate trajectory ribbons, spatial arrival order, hospital bed strain, demographic equity, counterfactual scenario branching, Pareto frontiers, and local on-device AI policy advisory (Ollama llama3.2).
- **Calibration Studio**: SMC-ABC parameter fitting against empirical public health timelines with explicit prior/posterior inspection.

---

## 3. Operational Integrity & Evidence Classes
Every input and parameter in EpiSwarm Studio v2 is tagged with a transparent Evidence Class:
1. **Class A (User Supplied)**: Directly imported authority data (e.g. local hospital census CSVs). SHA-256 hashed into the local ledger; raw data never leaves the machine.
2. **Class B (Sourced / Calibrated)**: Derived from official benchmark registries (ONS, PHE, NHS, CDC) or calibrated via SMC-ABC.
3. **Class C (Assumed Defaults)**: Literature-backed priors with academic citations (e.g. WHO behavioral surveys, UN population distributions). Requires explicit officer review.
4. **Class D (Synthetic / Demo)**: Synthetic test fixtures (e.g., London Wave 1 Demo, Sandbox Mini-City). Display prominent, persistent DEMO badges.

---

## 4. Out-of-Scope & Capability Boundaries
As documented in `docs/CAPABILITY_GAPS.md`, EpiSwarm Studio strictly forbids surfacing controls for mechanisms the vectorized engine does not model:
1. **Longitudinal Waning Immunity & Reinfection**: Pathogen transitions assume lifelong or single-season immunity during the 30-90 day horizon.
2. **Genomic Variant Drift**: Single circulating strain modeled per run.
3. **Test-Trace-Isolate (TTI) Queueing**: Testing capacity caps and tracing delays are planned for S6.
4. **Individual Point Prediction**: EpiSwarm Studio evaluates relative counterfactual policy deltas, not calendar date point predictions.
