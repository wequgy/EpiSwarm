"""Test for Phase 33: Front-End Streamlit Components & Diorama."""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pytest
from episwarm.viz.diorama import write_diorama_html, generate_isometric_city_diorama_svg
from episwarm.analysis.history import SimulationHistoryManager
from episwarm.engine.sim import SimulationResults


def test_diorama_rendering(tmp_path):
    svg = generate_isometric_city_diorama_svg()
    assert "<svg" in svg
    assert "</svg>" in svg
    assert "Diorama" in svg or "isometric" in svg.lower()

    html_file = tmp_path / "diorama.html"
    write_diorama_html(html_file)
    assert html_file.exists()
    content = html_file.read_text(encoding="utf-8")
    assert "<svg" in content


def test_simulation_history_persistence(tmp_path):
    mgr = SimulationHistoryManager(logs_dir=tmp_path)

    # Test empty load
    assert mgr.load_history() == []

    # Mock SimulationResults
    res = SimulationResults(
        run_id="run_test_phase33",
        scenario_name="baseline",
        disease_name="novel_high_virulence",
        horizon_days=10,
        n_agents=1000,
        sampling_ratio=1.0,
        calibrated_beta=0.08,
        target_r0=2.50,
        empirical_r0=2.45,
        daily_state_counts=np.zeros((10, 5), dtype=np.int32),
        state_names=["S", "E", "I", "R", "D"],
        daily_area_infections=np.zeros((10, 2), dtype=np.int32),
        daily_hospital_demand=np.zeros(10, dtype=np.int32),
        daily_icu_demand=np.zeros(10, dtype=np.int32),
        total_infections=500,
        total_deaths=12,
        attack_rate=0.50,
        overflow_deaths=2
    )

    rec = mgr.save_run(
        results=res,
        region_id="reference_london",
        scenario_name="baseline",
        disease_name="novel_high_virulence",
        behavior_mode="none",
        population_scale=1000
    )

    loaded = mgr.load_history()
    assert len(loaded) == 1
    assert loaded[0]["run_id"] == "run_test_phase33"
    assert loaded[0]["metrics"]["total_infections"] == 500

    df = mgr.export_summary_df()
    assert len(df) == 1
    assert "Attack Rate (%)" in df.columns
