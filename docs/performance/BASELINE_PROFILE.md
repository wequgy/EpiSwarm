# EpiSwarm Baseline Simulation Performance Profile (Stage R3.2)

- **Date**: 2026-11-15
- **Hardware**: 8 Physical Cores (12 Logical), 15.65 GB RAM, NVIDIA GeForce RTX 3050 A Laptop GPU (4 GB VRAM)
- **Runtime**: Python 3.11.9, NumPy 2.4.6, Windows 11 AMD64
- **Profiling Tool**: `scripts/profile_sim.py` (cProfile + psutil)

---

## 1. Baseline Measurements (Before Optimization)

| Configuration | Wall Time (s) | Throughput (ms / day) | RSS Memory (MB) | Attack Rate | Major Hotspots |
|---|---|---|---|---|---|
| **100,000 agents, 40 days** | 12.922 s | 323.1 ms/day | 136.9 MB &rarr; 148.1 MB (+11.2 MB) | 35.6% | `build_social_network` (4.37s), `resolve_next_state` (3.98s), `evaluate_daily_infections` (2.67s) |
| **500,000 agents, 40 days** | 53.875 s | 1346.9 ms/day | 167.9 MB &rarr; 188.4 MB (+20.6 MB) | 14.3% | `build_social_network` (27.17s), `evaluate_daily_infections` (13.38s), `resolve_next_state` (6.09s) |

---

## 2. Identified Hotspots & Optimization Targets

1. **Unconditional `build_social_network`**:
   - Accounts for **34% of runtime at 100k** and **50.4% of runtime at 500k**.
   - Built regardless of whether behavior policies or rumor models are active.
   - **Fix**: Only construct social network when `behavior_pack` requires rumors or behavior mode is enabled.

2. **Per-agent Python loops in `resolve_next_state`**:
   - Accounts for **31% of runtime at 100k**.
   - Iterates agent-by-agent over every transitioning agent.
   - **Fix**: Fully vectorized transition probability matrix computation and inverse-CDF sampling (with optional parallel Numba kernel).

3. **Per-patient Python loop in `calculate_adverse_probability` and `route_patients`**:
   - Breaks SoA rule in healthcare overflow routing with thousands of individual scalar calls.
   - **Fix**: Vectorized array-based logistic evaluation and condition masking.

4. **Edge Transmission and Inner Loops in `evaluate_daily_infections`**:
   - Intermediate array allocations and multiple bincount passes.
   - **Fix**: Efficient preallocated buffers, float32 precision, and Numba JIT accelerated kernels.
