#!/usr/bin/env python3
"""Reproducible simulation profiling script for EpiSwarm Studio (Stage R3.2).

Measures runtime, memory, and top cProfile hotspots at 100k and 500k agents.
"""

from __future__ import annotations

import argparse
import cProfile
import io
import os
import pstats
import sys
import time
from pathlib import Path
import psutil
import yaml
import numpy as np

# Ensure src is on PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.engine.sim import run_simulation


def profile_run(scale_agents: int = 100000, horizon_days: int = 40, seed: int = 42) -> dict:
    root = Path(__file__).resolve().parent.parent
    region_dir = root / "regions" / "example_synthetic"
    disease_file = root / "diseases" / "respiratory_generic.yaml"
    scenario_file = root / "scenarios" / "baseline.yaml"

    with open(disease_file, "r", encoding="utf-8") as f:
        disease = DiseasePack(**yaml.safe_load(f))

    with open(scenario_file, "r", encoding="utf-8") as f:
        scenario = ScenarioPack(**yaml.safe_load(f))
    scenario.horizon_days = horizon_days
    scenario.behavior_mode = "none"
    scenario.random_seed = seed

    print(f"\nBuilding synthetic population: {scale_agents:,} agents...")
    t_pop0 = time.perf_counter()
    pop = build_synthetic_population(region_dir=region_dir, scale_agents=scale_agents, random_seed=seed)
    t_pop1 = time.perf_counter()
    print(f"Population built in {t_pop1 - t_pop0:.2f} s")

    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / (1024 * 1024)

    pr = cProfile.Profile()
    t0 = time.perf_counter()
    pr.enable()

    result = run_simulation(
        pop=pop,
        disease_pack=disease,
        scenario_pack=scenario,
    )

    pr.disable()
    t1 = time.perf_counter()
    mem_after = process.memory_info().rss / (1024 * 1024)

    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
    ps.print_stats(20)
    stats_output = s.getvalue()

    total_time = t1 - t0
    ms_per_day = (total_time / horizon_days) * 1000.0
    attack_rate = float(result.attack_rate)

    print(f"\n=== Benchmark Profile: {scale_agents:,} agents, {horizon_days} days ===")
    print(f"Simulation Time  : {total_time:.3f} s ({ms_per_day:.1f} ms/day)")
    print(f"Memory RSS       : {mem_before:.1f} MB -> {mem_after:.1f} MB (Delta: {mem_after - mem_before:.1f} MB)")
    print(f"Attack Rate      : {attack_rate:.1%}")
    print("---------------- Top Hotspots (cumulative time) ----------------")
    for line in stats_output.splitlines()[:22]:
        print(line)

    return {
        "agents": scale_agents,
        "days": horizon_days,
        "sim_time_sec": total_time,
        "ms_per_day": ms_per_day,
        "mem_before_mb": mem_before,
        "mem_after_mb": mem_after,
        "mem_delta_mb": mem_after - mem_before,
        "attack_rate": attack_rate,
        "stats_output": stats_output,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile EpiSwarm Engine")
    parser.add_argument("--agents", type=int, default=100000, help="Agent population")
    parser.add_argument("--days", type=int, default=40, help="Horizon days")
    parser.add_argument("--both", action="store_true", help="Profile both 100k and 500k")
    args = parser.parse_args()

    if args.both:
        profile_run(100000, args.days)
        profile_run(500000, args.days)
    else:
        profile_run(args.agents, args.days)


if __name__ == "__main__":
    main()
