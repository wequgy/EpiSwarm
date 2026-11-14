"""Test suite for Stage S1: LiveRun stepping, bitwise determinism, injection, branching, and throughput."""

import time
import numpy as np
import pytest
import yaml
from pathlib import Path
from fastapi.testclient import TestClient

from episwarm.api.main import app
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import InterventionAction, ScenarioPack
from episwarm.population.build import build_synthetic_population
from episwarm.engine.sim import run_simulation
from episwarm.service.live import LiveRun, LiveDayFrame
from episwarm.service.parameters import ParameterRegistryService
from episwarm.service.estimator import ResourceEstimator

client = TestClient(app)


def test_s1_bitwise_determinism_pause_resume():
    """Verify uninterrupted run vs paused/resumed run produces bitwise identical trajectories."""
    pop_full = build_synthetic_population("regions/example_synthetic", scale_agents=3000, random_seed=42)
    pop_step = build_synthetic_population("regions/example_synthetic", scale_agents=3000, random_seed=42)

    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        d_pack = DiseasePack(**yaml.safe_load(f))
    with open("scenarios/targeted_containment.yaml", "r", encoding="utf-8") as f:
        s_pack = ScenarioPack(**yaml.safe_load(f))

    # Uninterrupted run for 60 days
    res_full = run_simulation(pop_full, d_pack, s_pack)

    # Paused at day 15, then resumed to completion
    res_part1 = run_simulation(pop_step, d_pack, s_pack, pause_at_day=15)
    assert res_part1.is_paused is True
    assert res_part1.current_day == 14
    assert res_part1.checkpoint is not None

    res_resumed = run_simulation(pop_step, d_pack, s_pack, checkpoint=res_part1.checkpoint)
    assert res_resumed.is_paused is False
    assert res_resumed.current_day == 59

    # Strict Bitwise Determinism across all daily state counts and deaths
    diff = np.max(np.abs(res_full.daily_state_counts - res_resumed.daily_state_counts))
    assert diff == 0, f"Divergence detected in daily state counts: max diff {diff}"
    assert res_full.total_deaths == res_resumed.total_deaths
    assert np.isclose(res_full.attack_rate, res_resumed.attack_rate, atol=1e-7)


def test_s1_live_run_step_and_frames():
    """Verify LiveRun session advances step-by-step and emits compliant LiveDayFrames."""
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=2000, random_seed=42)
    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        d_pack = DiseasePack(**yaml.safe_load(f))
    with open("scenarios/targeted_containment.yaml", "r", encoding="utf-8") as f:
        s_pack = ScenarioPack(**yaml.safe_load(f))

    live_run = LiveRun(
        job_id="test_live_s1_step",
        pop=pop,
        disease_pack=d_pack,
        scenario_pack=s_pack,
    )

    # Step 5 days
    frames = live_run.step(5)
    assert len(frames) == 5
    assert live_run.current_day == 4
    for idx, f in enumerate(frames):
        assert isinstance(f, LiveDayFrame)
        assert f.day == idx
        assert "S" in f.global_counts
        assert len(f.sampled_agents) > 0

    # Step another 5 days
    more_frames = live_run.step(5)
    assert len(more_frames) == 5
    assert live_run.current_day == 9


def test_s1_live_intervention_injection():
    """Verify runtime injection of a non-pharmaceutical intervention alters future timeline."""
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=2000, random_seed=42)
    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        d_pack = DiseasePack(**yaml.safe_load(f))
    with open("scenarios/targeted_containment.yaml", "r", encoding="utf-8") as f:
        s_pack = ScenarioPack(**yaml.safe_load(f))

    live_run = LiveRun(
        job_id="test_live_s1_inject",
        pop=pop,
        disease_pack=d_pack,
        scenario_pack=s_pack,
    )

    live_run.step(10)
    assert live_run.current_day == 9

    # Inject emergency curfew on Day 9 effective Day 10
    action = InterventionAction(
        name="emergency_curfew",
        measure_type="curfew",
        area_id="ALL",
        start_day=10,
        end_day=30,
        stringency=0.85,
    )
    rec = live_run.inject_intervention(action)
    assert rec["injected_at_day"] == 9
    assert any(iv.measure_type == "curfew" for iv in live_run.scenario_pack.interventions)

    # Step through injected window
    frames = live_run.step(5)
    assert "curfew" in frames[-1].active_measures


def test_s1_branching_correctness():
    """Verify branching a run from a checkpoint forks an independent simulation."""
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=2000, random_seed=42)
    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        d_pack = DiseasePack(**yaml.safe_load(f))
    with open("scenarios/targeted_containment.yaml", "r", encoding="utf-8") as f:
        s_pack = ScenarioPack(**yaml.safe_load(f))

    parent_run = LiveRun(
        job_id="test_parent_run",
        pop=pop,
        disease_pack=d_pack,
        scenario_pack=s_pack,
    )
    parent_run.step(12)
    assert parent_run.current_day == 11

    # Branch with an increased stringency override
    branch_run = parent_run.branch(
        branch_job_id="test_branch_run",
        checkpoint_day=11,
        overrides={"/scenario/interventions/mask_mandate/stringency": 0.95},
    )
    assert branch_run.job_id == "test_branch_run"
    assert branch_run.current_day == 11
    assert branch_run.checkpoint is not None


def test_s1_parameter_registry_and_estimator_apis():
    """Test v2 REST APIs for parameter schema discovery and resource estimation."""
    res_schema = client.get("/api/v2/parameters/schema")
    assert res_schema.status_code == 200
    params = res_schema.json()
    assert len(params) >= 5
    r0_param = next(p for p in params if p["path"] == "/disease/transmission/r0")
    assert r0_param["default_value"] == 2.8

    res_est = client.get("/api/v2/runs/estimate?scale_agents=50000&n_replicates=5&horizon_days=60")
    assert res_est.status_code == 200
    est = res_est.json()
    assert est["stability_status"] == "STABLE"
    assert est["recommended_min_agents"] == 50000
    assert est["within_memory_budget"] is True


def test_s1_throughput_50k_and_100k():
    """Benchmark engine stepping throughput at 50,000 and 100,000 agent scales."""
    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        d_pack = DiseasePack(**yaml.safe_load(f))
    with open("scenarios/targeted_containment.yaml", "r", encoding="utf-8") as f:
        s_pack = ScenarioPack(**yaml.safe_load(f))

    # 50k agents over 10 days
    pop_50k = build_synthetic_population("regions/example_synthetic", scale_agents=50000, random_seed=42)
    t0 = time.perf_counter()
    res_50k = run_simulation(pop_50k, d_pack, s_pack, pause_at_day=10)
    dur_50k = time.perf_counter() - t0
    rate_50k = (50000.0 * 10) / dur_50k
    print(f"\n[Throughput 50k]: {dur_50k:.2f}s -> {rate_50k:,.0f} agent-days/sec")
    assert rate_50k > 50000, "Throughput at 50k must exceed 50k agent-days/sec"

    # 100k agents over 5 days
    pop_100k = build_synthetic_population("regions/example_synthetic", scale_agents=100000, random_seed=42)
    t0 = time.perf_counter()
    res_100k = run_simulation(pop_100k, d_pack, s_pack, pause_at_day=5)
    dur_100k = time.perf_counter() - t0
    rate_100k = (100000.0 * 5) / dur_100k
    print(f"[Throughput 100k]: {dur_100k:.2f}s -> {rate_100k:,.0f} agent-days/sec")
    assert rate_100k > 50000, "Throughput at 100k must exceed 50k agent-days/sec"

