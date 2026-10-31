"""Unit and invariant tests for Phase 2: infection engine, state transitions, conservation, and multiple disease packs."""

from pathlib import Path
import numpy as np
import pytest
import yaml

from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.engine.contacts import parse_contact_matrix, compute_spectral_radius, analytical_beta_from_r0
from episwarm.engine.sim import run_simulation


def test_spectral_radius_and_beta_analytical():
    # Symmetric 2x2 test matrix
    M = np.array([
        [5.0, 2.0],
        [2.0, 5.0]
    ])
    # Dominant eigenvalue is 5 + 2 = 7.0
    upsilon = compute_spectral_radius(M)
    assert abs(upsilon - 7.0) < 1e-5

    target_r0 = 2.5
    mean_inf_days = 5.0
    beta, sr = analytical_beta_from_r0(target_r0, mean_inf_days, M)
    # beta = (2.5 * (1/5)) / 7.0 = 0.5 / 7.0 ~ 0.0714
    expected_beta = 0.5 / 7.0
    assert abs(beta - expected_beta) < 1e-5


def test_population_conservation_invariant():
    """Invariant: total agents across all disease states must sum to N_agents on every single day."""
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=5000, random_seed=42)

    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        d_pack = DiseasePack(**yaml.safe_load(f))

    with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
        s_data = yaml.safe_load(f)
        s_data["horizon_days"] = 20
        s_pack = ScenarioPack(**s_data)

    results = run_simulation(pop, d_pack, s_pack)

    # Check conservation across every single simulated day
    daily_totals = results.daily_state_counts.sum(axis=1)
    for day, total in enumerate(daily_totals):
        assert total == pop.n_agents, f"Day {day}: Population total {total} != {pop.n_agents}"

    # Invariant: no negative counts
    assert np.all(results.daily_state_counts >= 0), "Found negative compartment counts!"


def test_absorbing_state_invariant():
    """Invariant: absorbing state counts (D, R) must be monotonically non-decreasing."""
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=5000, random_seed=777)

    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        d_pack = DiseasePack(**yaml.safe_load(f))

    with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
        s_data = yaml.safe_load(f)
        s_data["horizon_days"] = 30
        s_pack = ScenarioPack(**s_data)

    results = run_simulation(pop, d_pack, s_pack)

    # Find absorbing states R and D
    for s_name in ["R", "D"]:
        if s_name in results.state_names:
            s_idx = results.state_names.index(s_name)
            counts = results.daily_state_counts[:, s_idx]
            # Check non-decreasing
            diffs = np.diff(counts)
            assert np.all(diffs >= 0), f"Absorbing state {s_name} decreased on some day! Diffs: {diffs[diffs < 0]}"


def test_engine_runs_two_different_disease_packs():
    """Acceptance criterion: Same engine runs two distinct disease packs without code modifications."""
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=5000, random_seed=101)

    # 1. Run respiratory_generic
    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        d1 = DiseasePack(**yaml.safe_load(f))

    with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
        s1 = ScenarioPack(**yaml.safe_load(f))
        s1.horizon_days = 15

    res1 = run_simulation(pop, d1, s1)
    assert res1.total_infections > 0
    assert res1.disease_name == "respiratory_generic"

    # 2. Run influenza_generic (different state names, R0, overdispersion, transitions)
    with open("diseases/influenza_generic.yaml", "r", encoding="utf-8") as f:
        d2 = DiseasePack(**yaml.safe_load(f))

    with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
        s2 = ScenarioPack(**yaml.safe_load(f))
        s2.horizon_days = 15

    res2 = run_simulation(pop, d2, s2)
    assert res2.total_infections > 0
    assert res2.disease_name == "influenza_generic"
    assert res2.target_r0 == 1.60


def test_simulation_reproducibility():
    """Identical seed and inputs produce bit-exact simulation outcomes."""
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=5000, random_seed=42)

    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        d = DiseasePack(**yaml.safe_load(f))

    with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
        s1 = ScenarioPack(**yaml.safe_load(f))
        s1.horizon_days = 20

    with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
        s2 = ScenarioPack(**yaml.safe_load(f))
        s2.horizon_days = 20

    r1 = run_simulation(pop, d, s1)
    r2 = run_simulation(pop, d, s2)

    np.testing.assert_array_equal(r1.daily_state_counts, r2.daily_state_counts)
    assert r1.total_infections == r2.total_infections
    assert r1.total_deaths == r2.total_deaths
