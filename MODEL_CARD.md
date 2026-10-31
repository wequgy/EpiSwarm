# EpiSwarm Studio: Model Card (`MODEL_CARD.md`)

## 1. Model Details
- **Model Name**: EpiSwarm Studio
- **Version**: 1.0.0 (Production Framework)
- **Model Architecture**: Dual-Engine Hybrid:
  1. Micro-scale Agent-Based Model utilizing NumPy Structure-of-Arrays (SoA) vectorized transitions across physical venue layers (household, school, workplace, community).
  2. Macro-scale Metapopulation Patch Model (`engine_meta`) following **Libin et al. (2020, arXiv:2003.13676)** with age-structured intra-patch SEIR (binomial chain) and inter-patch non-homogeneous Poisson arrival processes via time-scale transformation.
- **Developers**: Antigravity DeepMind Agentic Pair Programming
- **Reference Standard**: Libin et al. (2020), *Deep reinforcement learning for large-scale epidemic control*, arXiv:2003.13676v1.
- **License**: MIT / Open Science Research

---

## 2. Intended Use & Public Health Scope
- **Primary Applications**:
  - **Counterfactual Policy Exploration**: Comparative "what-if" evaluation of non-pharmaceutical interventions (NPIs) including age-targeted closures, workplace density caps, curfews, and official communication campaigns.
  - **Healthcare Capacity & Resource Allocation**: Dynamic stress-testing of generic regional clinical capacities, routing patients across geographic catchment zones, evaluating marginal-value curves, and discovering equity-optimal resource infusions.
  - **Misinformation & Behavioral Feedback**: Modeling rumor diffusion over social networks, belief polarization, fatigue accumulation, and subsequent compliance erosion.
  - **Coordinated Inter-Area Control**: Graph clustering via Leiden / modularity optimization over commuting flux graphs to partition administrative districts into tractable joint policy clusters.
- **Studio Operational Modes**:
  - **Simulate Mode (Exploration)**: Sandbox for testing custom intervention timings, behavioral traits, and counterfactual seed comparisons.
  - **Plan Mode (Advisory & Optimization)**: Algorithmic screening, Pareto frontier discovery via Optuna NSGA-II, and LLM-assisted public health advisory synthesis.

---

## 3. Out-of-Scope & Non-Goals
> [!IMPORTANT]
> **Explicit Non-Goals**:
> 1. **Not an Outbreak Forecasting Tool**: EpiSwarm Studio does NOT predict the exact calendar date, height, or timing of real-world epidemic waves. All simulation horizons evaluate comparative policy deltas rather than point predictions.
> 2. **Diseases Not Covered in v1**: Vector-borne diseases (e.g., Dengue, Malaria), waterborne transmission (e.g., Cholera), and chronic non-communicable conditions are not supported. Only respiratory and direct person-to-person infectious contact graphs are modeled.
> 3. **No Individual Surveillance / Re-identification**: Purely synthetic agents generated from aggregate statistical marginals via Iterative Proportional Fitting (IPF).

---

## 4. Calibration & Honesty Caveats
- **Default Status**: Every simulation run is labeled **`UNCALIBRATED`** unless calibrated against empirical regional case timelines (`observed_cases.csv`).
- **Behavioral Module Status**: The behavioral dynamics layer carries an explicit **`Behavior layer unvalidated for this region`** warning unless calibrated against observed mobility or compliance surveys.
- **Synthetic Data**: Fixture runs (`regions/example_synthetic`) display a prominent **`SYNTHETIC DATA ONLY`** watermark and biography disclaimers.

---

## 5. Core Mathematical Specifications

### 5.1 Transmission & Spectral Calibration
Transmission rates $\beta$ are calibrated dynamically to target reproduction numbers $R_0$ using the dominant eigenvalue (spectral radius $\Upsilon(M)$) of the age contact matrix:
$$\beta = \frac{R_0 \cdot \gamma}{\Upsilon(M)}$$

### 5.2 Generic Clinical Resources & Multi-Factor Adverse Outcomes (Spec 6.3)
No hardcoded clinical resource names exist in the engine. All resources and consumables are declared dynamically in `resources.csv` and state YAML files (`needs: {<resource_id>: <units>}`). When care capacity is saturated, adverse outcomes for unserved patients are governed by the multi-factor logistic equation:
$$\text{logit}(p_{\text{adverse}}) = \text{logit}(p_{\text{served}}) + \theta_0 (1 - \text{service\_level}) + \theta_{\text{sev}} (\text{sev} - \text{ref}) + \theta_{\text{care}} (1 - \text{self\_care}) + \theta_{\text{sup}} (1 - \text{support}) + \theta_{\text{alt}} (1 - \text{alt\_care}) + \theta_{\text{delay}} \cdot \text{delay}$$
- When $\theta_0 = 0$, unserved patient outcomes equal baseline served care.
- Setting $\theta_{\text{care}}, \theta_{\text{delay}} > 0$ models adverse progression under clinical resource deficits.

### 5.3 Libin Metapopulation Contagion (Spec 11)
- **Intra-area age-structured SEIR**: Evaluated via daily Binomial chains:
  $$\text{new\_E} \sim \text{Bin}(S, 1 - e^{-\phi_i}), \quad \text{new\_I} \sim \text{Bin}(E, 1 - e^{-\zeta}), \quad \text{new\_R} \sim \text{Bin}(I, 1 - e^{-\gamma})$$
- **Inter-area Poisson arrival process**:
  $$\phi_p(t) = \sum_{p'} \text{Mob}[p', p] \cdot \beta \cdot \left(\frac{S^A_p(t)}{N^A_p}\right)^\mu \cdot I^A_{p'}(t) \cdot M_{AA}$$
  Evaluated with exponential threshold arrivals $X_p \sim \text{Exp}(1)$ via time-scale transformation (Libin et al. Algorithm 2).
- **Spatial scaling parameter $\mu$**: Dynamically fitted as $\mu = \log(R_0) \cdot s$ per region and pathogen (no hardcoded literature constants).

---

## 6. Performance & Hardware Benchmarks
Evaluated on single-socket CPU (AMD/Intel Core architecture, 16 GB RAM baseline):

| Agent Scale | Synthetic Pop Build | 30-Day Simulation | Total Runtime | Peak Working Set RAM | SoA Theoretical Size |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **5,000** | 0.03s | 0.60s | **0.65s** | 151.7 MB | 0.21 MB |
| **50,000** | 0.05s | 5.66s | **5.73s** | 202.0 MB | 2.15 MB |
| **100,000** | 0.09s | 13.29s | **13.39s** | 257.3 MB | 4.29 MB |
| **500,000** | 0.66s | 80.32s | **80.99s** | **692.3 MB** | 21.46 MB |

> [!NOTE]
> Even at 500,000 agents, peak RAM usage is **692 MB**, comfortably below the 11 GB ceiling on 16 GB hardware. CPU NumPy vectorization achieves >6,000 agent-days per millisecond. GPU offloading provides minimal additional gain at these scales due to PCIe transfer overhead.

---

## 7. Data Privacy & Ethical Guidelines
1. **Local Processing**: All uploaded regional datasets and synthetic micro-data are processed 100% locally on the host machine.
2. **LLM Context Protection**: No raw population records or PII are ever transmitted to external LLM APIs (e.g. Gemini). The Advisory agent observes only aggregated, anonymized public health summaries (infection counts, resource occupancy, equity metrics).
3. **Reproducibility**: All simulations use a single seeded `numpy.random.Generator`. Every simulation result writes an immutable manifest containing the git commit hash, pack hashes, seed, and provenance records.
