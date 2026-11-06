"""Tests for simulation pause & resume checkpointing and history logging."""
import pytest
import numpy as np
import yaml
from pathlib import Path

from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.engine.sim import run_simulation, SimulationCheckpoint
from episwarm.analysis.history import SimulationHistoryManager


@pytest.fixture
def test_env(tmp_path):
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=1000, random_seed=42)
    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        disease = DiseasePack(**yaml.safe_load(f))
    with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
        scenario = ScenarioPack(**yaml.safe_load(f))
    scenario.horizon_days = 30
    scenario.behavior_mode = "none"
    return pop, disease, scenario, tmp_path


def test_pause_and_resume_simulation(test_env):
    """Verify that a simulation can pause at day 10, save checkpoint, and resume to day 30."""
    pop, disease, scenario, _ = test_env

    # 1. Run full 30-day baseline as reference
    res_full = run_simulation(pop, disease, scenario, enable_behavior=False)
    assert res_full.is_paused is False
    assert res_full.horizon_days == 30

    # 2. Run with pause at day 10
    res_paused = run_simulation(pop, disease, scenario, enable_behavior=False, pause_at_day=10)
    assert res_paused.is_paused is True
    assert res_paused.horizon_days == 10
    assert res_paused.checkpoint is not None
    assert res_paused.checkpoint.day == 9
    assert len(res_paused.event_logs) > 0

    # 3. Resume from checkpoint to completion
    res_resumed = run_simulation(pop, disease, scenario, enable_behavior=False, checkpoint=res_paused.checkpoint)
    assert res_resumed.is_paused is False
    assert res_resumed.horizon_days == 30
    assert res_resumed.total_infections > 0
    # Attack rate should be within close statistical range of full run
    assert abs(res_resumed.attack_rate - res_full.attack_rate) < 0.05


def test_simulation_history_manager(test_env):
    """Verify simulation history manager logs and retrieves structured run records."""
    pop, disease, scenario, tmp_path = test_env
    mgr = SimulationHistoryManager(logs_dir=tmp_path / "logs")

    res = run_simulation(pop, disease, scenario, enable_behavior=False)

    record = mgr.save_run(
        results=res,
        region_id="example_synthetic",
        scenario_name=scenario.name,
        disease_name=disease.name,
        behavior_mode="none",
        population_scale=1000,
        interventions=[]
    )

    assert "run_id" in record
    assert record["metrics"]["attack_rate_pct"] > 0
    assert len(record["daily_timeline"]) == 30

    # Test load history
    history = mgr.load_history()
    assert len(history) == 1
    assert history[0]["run_id"] == record["run_id"]

    # Test get run
    retrieved = mgr.get_run(record["run_id"])
    assert retrieved is not None
    assert retrieved["run_id"] == record["run_id"]

    # Test summary dataframe export
    df = mgr.export_summary_df()
    assert len(df) == 1
    assert "Attack Rate (%)" in df.columns

