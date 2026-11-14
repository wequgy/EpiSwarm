"""Unit tests for Stage A3 SMC-ABC Calibration and Parameter Identification."""

import numpy as np
import pytest
from episwarm.calibrate.smc_abc import (
    SMCABCConfig,
    Particle,
    PosteriorEnsemble,
    compute_trajectory_distance,
    run_smc_abc,
    run_twin_experiment
)


def test_trajectory_distance_metric():
    obs = np.array([0.0, 5.0, 20.0, 50.0, 20.0, 5.0, 0.0])
    sim_identical = obs.copy()
    dist, p_day, p_val, s_tot = compute_trajectory_distance(
        sim_identical, obs, obs_peak_day=3, obs_peak_val=50.0
    )
    assert p_day == 3
    assert p_val == 50.0
    assert pytest.approx(dist, abs=1e-5) == 0.0

    sim_shifted = np.array([0.0, 0.0, 5.0, 20.0, 50.0, 20.0, 5.0])
    dist_shift, p_day_s, _, _ = compute_trajectory_distance(
        sim_shifted, obs, obs_peak_day=3, obs_peak_val=50.0
    )
    assert p_day_s == 4
    assert dist_shift > 0.0


def test_posterior_ensemble_summary():
    particles = [
        Particle(params={"r0": 2.5, "i0": 20.0}, weight=0.5, distance=1.0, sim_peak_day=30, sim_peak_val=100.0, sim_total=1000.0),
        Particle(params={"r0": 3.5, "i0": 40.0}, weight=0.5, distance=1.5, sim_peak_day=28, sim_peak_val=120.0, sim_total=1200.0),
    ]
    ensemble = PosteriorEnsemble(
        particles=particles,
        generation=1,
        tolerance=2.0,
        parameter_names=["r0", "i0"]
    )
    summ = ensemble.summary()
    assert pytest.approx(summ["r0"]["mean"], 0.01) == 3.0
    assert pytest.approx(summ["i0"]["mean"], 0.01) == 30.0
    assert summ["r0"]["std"] > 0.0


def test_smc_abc_twin_experiment_recovery():
    """Verify twin experiment parameter recovery on synthetic truth."""
    true_params = {"r0": 2.75, "i0": 32.0, "kappa": 0.60}
    results = run_twin_experiment(true_params=true_params, n_particles=60, random_seed=42)
    assert results["success"] is True, "Twin experiment recovery must succeed"
    for p_name in ["r0", "i0", "kappa"]:
        assert results["recovery_report"][p_name]["status"] == "PASS"
        assert results["recovery_report"][p_name]["covered_95_ci"] is True
