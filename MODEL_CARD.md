# EpiSwarm Studio: Model Card (`MODEL_CARD.md`)

## Model Details
- **Model Name**: EpiSwarm Studio
- **Version**: 0.1.0 (Framework Version)
- **Model Type**: Multi-Scale Structure-of-Arrays (SoA) Agent-Based Epidemic Model & Healthcare Overflow Planner
- **Developed By**: Antigravity DeepMind Agentic Pair Programming
- **License**: MIT / Open Research

## Intended Use
- **Primary Use Cases**:
  - Comparative counterfactual analysis of public health non-pharmaceutical interventions (NPIs) (e.g., area-targeted school/workplace closures, curfew, mask distribution).
  - Spatial disease spread tracing across administrative zones and commuting flows.
  - Stress testing of regional healthcare capacity (general beds, HDU, ICU, mechanical ventilators, medical oxygen).
  - Exploration of behavioral feedback, public compliance, and misinformation spreading.
- **Out of Scope & Non-Goals**:
  - **Not a Forecasting Tool**: EpiSwarm Studio does not predict the exact date, size, or timing of real-world epidemic waves.
  - **Out-of-Scope Pathogens in v1**: Vector-borne (e.g. Dengue, Malaria) and waterborne (e.g. Cholera) transmission mechanisms are not supported in v1. Only respiratory and direct contact person-to-person state graphs are supported.
  - **No Real Personal Data**: The engine simulates purely synthetic agents generated from aggregate statistical marginals.

## Calibration and Validation Caveats
- **Default Status**: Every simulation run is labeled **`UNCALIBRATED`** unless calibrated against user-supplied empirical time-series data (`observed_cases.csv`).
- **Behavior Layer**: The LLM-driven behavioral module is **unvalidated** for real-world decision fidelity and serves exclusively for counterfactual scenario exploration.
- **Synthetic Data**: Runs utilizing fixture data (`regions/example_synthetic`) display a prominent **`SYNTHETIC DATA`** banner.
