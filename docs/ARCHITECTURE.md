# EpiSwarm Studio: Architecture & Data Flow

This document visualizes the complete end-to-end data flow of EpiSwarm Studio, mapping input files, synthetic population synthesis, behavioral decisions, simulation execution, and external integrations.

---

## High-Level System Architecture

```mermaid
flowchart TD
    %% 1. Input Packs
    subgraph Inputs["1. Configuration & Data Packs"]
        Packs["Data Packs (YAML & CSV)<br/>(Region, Disease, Behavior, Scenario)"]
    end

    %% 2. Synthetic Population
    subgraph Population["2. Synthetic Population Synthesis"]
        PopGen["SoA Population Generator<br/>(IPF Demographics, Households, Venues)"]
    end

    %% 3. Behavioral Layer
    subgraph Behavior["3. Behavioral Decisions Layer"]
        PolicyRouter{"Policy Selector<br/>(Jev / Local / Rule)"}
        Cache[("SQLite Decision Cache<br/>(.cache/behavior.sqlite)")]
        JevAPI["TypeSafe AI Jev API<br/>(External HTTPS)"]
        LocalLLM["Local LLM Backend<br/>(Ollama / llama.cpp logprobs)"]
        RuleBase["RulePolicy Fallback<br/>(Offline deterministic)"]
    end

    %% 4. Simulation Engine
    subgraph Engine["4. Simulation Engine (Daily Clock)"]
        DailyClock["Daily Simulation Loop<br/>(Infection, State Graph, Commute)"]
        HospitalEngine["Hospital Routing Engine<br/>(Beds, ICU, Overflow Penalties)"]
    end

    %% 5. Policy Advisor & Output
    subgraph Outputs["5. Analysis, Optimization & UI"]
        Advisor["Policy Advisor Agent<br/>(Tools: run_scenario, compare)"]
        GeminiAPI["Google Gemini API<br/>(Advisor Function Calling)"]
        StudioUI["Streamlit & Plotly Web App<br/>(Interactive Visuals & HTML Report)"]
    end

    %% Data Flow Connections
    Packs -->|Read Config| PopGen
    PopGen -->|Instantiate Arrays| DailyClock
    Packs -->|Define Interventions| DailyClock

    DailyClock -->|Trigger on Events| PolicyRouter
    PolicyRouter <-->|Read / Write| Cache
    PolicyRouter -.->|HTTPS Call| JevAPI
    PolicyRouter -.->|HTTP / Logprobs| LocalLLM
    PolicyRouter -->|Offline Baseline| RuleBase
    PolicyRouter -->|Sampled Actions| DailyClock

    DailyClock -->|Severe Patients| HospitalEngine
    HospitalEngine -->|Telemetry & Deaths| DailyClock

    DailyClock -->|Daily Telemetry| Advisor
    Advisor -.->|Function Calling| GeminiAPI
    Advisor -->|Structured Recommendation| StudioUI
    DailyClock -->|Epidemic Curves & Spread Matrix| StudioUI
```

---

## Key Node Descriptions

1. **Data Packs (Files)**: User-provided CSV and YAML configurations specifying administrative areas, population marginals, disease transition rates, and intervention policies.
2. **SoA Population Generator**: Converts statistical marginals into contiguous Structure-of-Arrays NumPy memory blocks (`agent_id`, `age`, `household_id`, `workplace_id`, `compliance`).
3. **Daily Simulation Loop**: Vectorized transmission engine evaluating contact layers (household, school, workplace, community) using `numpy.bincount`.
4. **Policy Selector**: Routes behavioral prompts to TypeSafe AI Jev (if configured), local LLM logprob engine (if running), or RulePolicy fallback.
5. **SQLite Decision Cache**: Prevents duplicate LLM queries by memoizing probabilities keyed by `(bucket_hash, situation_hash, question_id)`.
6. **Hospital Routing Engine**: Allocates patients to nearest available hospital beds across administrative areas and calculates overflow mortality penalties.
7. **Policy Advisor Agent**: Employs function calling (via Google Gemini) to iterate through candidate measures and generate Pydantic `Recommendation` objects.
8. **Streamlit & Plotly Web App**: User-facing interactive dashboard for visualizing counterfactual trajectories, spatial spread matrices, and demographic equity audits.
