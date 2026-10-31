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


def benchmark_scale(scale: int, horizon: int = 30) -> dict:
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
        s_pack = ScenarioPack(**s_data)

    t1 = time.perf_counter()
    results = run_simulation(pop, d_pack, s_pack)
    sim_time = time.perf_counter() - t1
    total_time = time.perf_counter() - t0
    end_rss, peak_wset = get_process_memory_mb()

    # SoA Theoretical size: ~45 bytes per agent in memory
    theoretical_soa_mb = (scale * 45) / (1024.0 * 1024.0)

    return {
        "scale": scale,
        "pop_time_sec": round(pop_time, 2),
        "sim_time_sec": round(sim_time, 2),
        "total_time_sec": round(total_time, 2),
        "end_rss_mb": round(end_rss, 1),
        "peak_wset_mb": round(peak_wset, 1),
        "theoretical_soa_mb": round(theoretical_soa_mb, 2),
        "attack_rate_pct": round(results.attack_rate * 100, 1)
    }


def main():
    print("================ EpiSwarm Scale Benchmark ================")
    print(f"Target Machine: 16GB RAM constraint (Peak Memory < 11GB target)\n")
    scales = [5000, 50000, 100000]

    # Optional 500k stretch run if memory permits
    import sys
    if "--stretch" in sys.argv:
        scales.append(500000)

    rows = []
    for s in scales:
        print(f"Running benchmark for {s:,} agents...")
        res = benchmark_scale(s, horizon=30)
        rows.append(res)
        print(f" -> Completed in {res['total_time_sec']}s (Peak RAM: {res['peak_wset_mb']} MB, Infections: {res['attack_rate_pct']}%)")

    df = pd.DataFrame(rows)
    print("\n" + df.to_string(index=False))
    print("==========================================================")


if __name__ == "__main__":
    main()

