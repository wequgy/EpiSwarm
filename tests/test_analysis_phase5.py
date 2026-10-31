"""Unit and invariant tests for Phase 5: spread matrix, equity audit, and multi-seed metrics."""

import numpy as np
import pytest
import yaml

from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.engine.sim import run_simulation
from episwarm.analysis.spread_matrix import compute_spread_matrix
from episwarm.analysis.equity import evaluate_equity
from episwarm.analysis.metrics import (
    evaluate_single_run_objectives, aggregate_multi_seed_metrics, ObjectiveVector
)


@pytest.fixture
def sim_setup():
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=3000, random_seed=42)
    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        d_pack = DiseasePack(**yaml.safe_load(f))
    with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
        s_data = yaml.safe_load(f)
        s_data["horizon_days"] = 15
        s_pack = ScenarioPack(**s_data)
    return pop, d_pack, s_pack


def test_spread_matrix_computation(sim_setup):
    pop, d_pack, s_pack = sim_setup
    res = compute_spread_matrix(pop, d_pack, s_pack, n_seeds=2, max_days=15)

    assert len(res.area_names) == 2
    # Self-arrival delay must be exactly 0.0 on diagonal
    assert res.mean_arrival_days[0, 0] == 0.0
    assert res.mean_arrival_days[1, 1] == 0.0
    # Off-diagonal arrivals must be >= 0.0
    assert res.mean_arrival_days[0, 1] >= 0.0
    assert len(res.hit_order) == 2


def test_equity_evaluation(sim_setup):
    pop, d_pack, s_pack = sim_setup
    sim_res = run_simulation(pop, d_pack, s_pack)

    report = evaluate_equity(pop, sim_res)
    assert report.worst_off_area in pop.area_id_to_int
    assert report.best_off_area in pop.area_id_to_int
    assert report.area_disparity_gap >= 0.0
    assert "Disparity Audit" in report.summary()


def test_multi_seed_metrics_ci():
    runs = [
        ObjectiveVector(10.0, 5.0, 1.0, 0.0, 100.0, 0.05),
        ObjectiveVector(12.0, 6.0, 2.0, 1.0, 105.0, 0.06),
        ObjectiveVector(11.0, 5.5, 1.5, 0.5, 102.0, 0.055)
    ]
    report = aggregate_multi_seed_metrics(runs)
    assert report.n_seeds == 3
    assert abs(report.mean_objectives.cumulative_deaths - 11.0) < 1e-5
    # CI lower <= mean <= CI upper
    assert report.ci_lower.cumulative_deaths <= report.mean_objectives.cumulative_deaths
    assert report.ci_upper.cumulative_deaths >= report.mean_objectives.cumulative_deaths
