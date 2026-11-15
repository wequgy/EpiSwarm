"""Regression test ensuring simulation throughput does not degrade (Stage R3.2)."""

import time
from pathlib import Path
import yaml
import pytest

from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.population.build import build_synthetic_population
from episwarm.engine.sim import run_simulation


def test_simulation_throughput_regression():
    """Fail if simulation speed at 50,000 agents drops below acceptable threshold."""
    root = Path(__file__).resolve().parent.parent
    region_dir = root / "regions" / "example_synthetic"
    with open(root / "diseases" / "respiratory_generic.yaml", "r", encoding="utf-8") as f:
        d_pack = DiseasePack(**yaml.safe_load(f))
    with open(root / "scenarios" / "baseline.yaml", "r", encoding="utf-8") as f:
        s_data = yaml.safe_load(f)

    s_data["horizon_days"] = 30
    s_data["behavior_mode"] = "none"
    s_pack = ScenarioPack(**s_data)

    pop = build_synthetic_population(region_dir=region_dir, scale_agents=50000, random_seed=42)

    t0 = time.perf_counter()
    res = run_simulation(pop, d_pack, s_pack)
    duration = time.perf_counter() - t0

    ms_per_day = (duration / 30.0) * 1000.0
    # Must complete in under 5.0 seconds (< 160 ms per day) on modern hardware
    assert duration < 5.0, f"Performance regression detected: 50k agents took {duration:.2f}s ({ms_per_day:.1f} ms/day) > 5.0s threshold"
    assert res.attack_rate > 0.05
