"""Benchmark script measuring runtime and peak memory scaling across agent counts."""

import time
import psutil
import os
from pathlib import Path
import numpy as np
import pandas as pd
import yaml

from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.engine.sim import run_simulation


def get_process_memory_mb() -> tuple[float, float]:
    process = psutil.Process(os.getpid())
    info = process.memory_info()
    rss = info.rss / (1024.0 * 1024.0)
    peak = getattr(info, "peak_wset", info.rss) / (1024.0 * 1024.0)
    return rss, peak


def benchmark_scale(scale: int, horizon: int = 45) -> dict:
    start_rss, _ = get_process_memory_mb()
    t0 = time.perf_counter()

    # 1. Build Population
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=scale, random_seed=42)
    pop_time = time.perf_counter() - t0

    # 2. Run Simulation
    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        d_pack = DiseasePack(**yaml.safe_load(f))

    with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
        s_data = yaml.safe_load(f)
        s_data["horizon_days"] = horizon
        s_data["seeding"]["initial_cases_per_area"] = 200
        s_data["interventions"] = []
        s_pack = ScenarioPack(**s_data)

    t1 = time.perf_counter()
    results = run_simulation(pop, d_pack, s_pack)
    sim_time = time.perf_counter() - t1
    total_time = time.perf_counter() - t0
    end_rss, peak_wset = get_process_memory_mb()

    # Find infectious state indices and peak infectious count over time
    inf_indices = [i for i, s in enumerate(d_pack.states) if s.infectious]
    daily_active = np.sum(results.daily_state_counts[:, inf_indices], axis=1)
    peak_active = int(np.max(daily_active))

    # SoA Theoretical size: ~45 bytes per agent in memory
    theoretical_soa_mb = (scale * 45) / (1024.0 * 1024.0)

    return {
        "scale": scale,
        "horizon_days": horizon,
        "attack_rate_pct": round(results.attack_rate * 100, 1),
        "peak_infectious": peak_active,
        "time_per_day_ms": round((sim_time / horizon) * 1000.0, 1),
        "sim_time_sec": round(sim_time, 2),
        "total_time_sec": round(total_time, 2),
        "peak_memory_mb": round(peak_wset, 1),
        "theoretical_soa_mb": round(theoretical_soa_mb, 2)
    }


def main():
    print("================ EpiSwarm Scale Benchmark (Phase 15 Validated) ================")
    print("Target Machine: 16GB RAM constraint (Peak Memory < 11GB target)\n")
    scales = [5000, 50000, 100000]

    # Include 500k stretch run
    import sys
    if "--stretch" in sys.argv or "--all" in sys.argv:
        scales.append(500000)

    rows = []
    for s in scales:
        print(f"Running benchmark for {s:,} agents...")
        res = benchmark_scale(s, horizon=45)
        rows.append(res)
        print(f" -> Completed in {res['total_time_sec']}s (Attack Rate: {res['attack_rate_pct']}%, Peak Cases: {res['peak_infectious']:,}, Peak RAM: {res['peak_memory_mb']} MB)")

    df = pd.DataFrame(rows)
    print("\n" + df.to_string(index=False))
    print("===============================================================================")


if __name__ == "__main__":
    main()

