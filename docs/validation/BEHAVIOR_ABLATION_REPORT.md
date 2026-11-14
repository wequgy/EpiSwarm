# EpiSwarm Behavior System v3 Ablation Report (Stage A4)

**Generated**: 2026-11-14 13:50:17 UTC  
**Evaluation Resolution**: 50,000 synthetic agents  
**Total Runtime**: 9.9s  

---

## 1. Executive Summary

Stage A4 upgrades the EpiSwarm behavioral architecture to a high-performance **Teacher-Student** model:
- **Empirical CoMix Teacher**: Calibrated directly against the LSHTM CoMix longitudinal contact survey (81 demographic strata) to provide macro priors by period and age.
- **Vectorized Student Evaluator**: Translates archetype priors into continuous individual agent choices in microseconds via vectorized numpy logit operations, ensuring zero block-quantization.
- **Out-of-Range Detector**: Automatically flags policy configurations and demographic distributions that venture outside empirical survey support.
- **Data-Constrained Tier**: Provides principled uncertainty widening for regions without localized longitudinal surveys.

---

## 2. Behavioral Architecture Ablation Comparison

| Architecture Tier | Model Description | Latency (50k agents) | Throughput (agents/sec) | Variance ($\sigma^2$) | Unique Output Values | Agency & Heterogeneity |
|:---|:---|:---:|:---:|:---:|:---:|:---|
| **Tier A: Fixed Heuristic** | Constant scalar compliance | 21.0 $\mu$s | > 100M | 0.00000 | 1 | None (all agents identical) |
| **Tier B: Discrete Archetype** | 4 coarse age clusters | 713.9 $\mu$s | > 50M | 0.00790 | 3 | Step-function block quantization |
| **Tier C: Teacher-Student v3** | CoMix Teacher + Vectorized Individual Student | **2527.3 $\mu$s** | **19,783,959** | **0.01142** | **4,989** | **Full continuous heterogeneous agency** |
| **Tier D: Data-Constrained** | International envelope + 2.5x uncertainty penalty | 58.9 $\mu$s | > 20M | 0.01142 | 4,989 | Continuous with widened CI span (mean $\Delta$=0.41) |

---

## 3. Out-of-Range Detection Diagnostic

- **Nominal Configuration (London Wave 1 baseline)**: 0 warnings (Fully within empirical CoMix support).
- **Extreme Configuration (Stringency=0.98, Zero Fatigue)**: Flagged **2 out-of-range warnings**:
  * `[POLICY_STRINGENCY_OUT_OF_BOUNDS]`
  * `[UNREALISTIC_FATIGUE_ASSUMPTION]`

---

## 4. Epidemiological Outcome Impact

Evaluating the dynamic feedback between individual agent compliance and pandemic transmission dynamics on Reference London:

| Scenario | Attack Rate | Peak Active Infections | Peak Reduction vs Unmitigated |
|:---|:---:|:---:|:---:|
| **Unmitigated Baseline (Behavior Disabled)** | 59.4% | 5,146 | 0.0% |
| **Endogenous Mitigated (Behavior System v3)** | **0.1%** | **34** | **-99.3%** |

---
*Report generated automatically by `scripts/run_behavior_ablation.py`.*