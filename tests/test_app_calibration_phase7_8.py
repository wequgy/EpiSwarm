"""Unit and invariant tests for Phase 7 & 8: calibration, sensitivity, and app modules."""

import numpy as np
import pandas as pd
import pytest
import yaml

from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.analysis.sensitivity import run_oat_sensitivity
from episwarm.analysis.calibration import calibrate_to_observed_data


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


def test_calibration_honesty_rule_uncalibrated_by_default(sim_setup):
    pop, d_pack, s_pack = sim_setup
    # No observed data -> must say UNCALIBRATED
    report = calibrate_to_observed_data(pop, d_pack, s_pack, None)
    assert report.is_calibrated is False
    assert "UNCALIBRATED" in report.status_label


def test_calibration_flags_synthetic_observed_data(sim_setup):
    pop, d_pack, s_pack = sim_setup
    # Synthetic fixture data -> calibration disabled
    obs_df = pd.DataFrame([
        {"date": "2024-01-01", "positives": 10, "status": "synthetic"}
    ])
    report = calibrate_to_observed_data(pop, d_pack, s_pack, obs_df)
    assert report.is_calibrated is False
    assert "SYNTHETIC" in report.status_label


def test_oat_sensitivity_analysis(sim_setup):
    pop, d_pack, s_pack = sim_setup
    df_sens = run_oat_sensitivity(
        pop, d_pack, s_pack,
        param_variations={"r0": [1.5, 3.0]}
    )
    assert not df_sens.empty
    assert "parameter" in df_sens.columns
    assert "delta_deaths" in df_sens.columns
    assert len(df_sens) >= 2


def test_streamlit_app_script_exists_and_parses():
    import py_compile
    res = py_compile.compile("src/episwarm/app/streamlit_app.py", doraise=True)
    assert res is not None

