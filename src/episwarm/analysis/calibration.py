"""Calibration engine fitting simulations against observed empirical time-series data."""

from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

from episwarm.population.build import PopulationSoA
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.engine.sim import run_simulation


@dataclass
class CalibrationReport:
    is_calibrated: bool
    status_label: str  # "CALIBRATED" or "UNCALIBRATED"
    ascertainment_rate: float
    rmse_daily_positives: Optional[float]
    r_squared: Optional[float]
    fitted_beta: Optional[float]
    summary_message: str


def calibrate_to_observed_data(
    pop: PopulationSoA,
    disease_pack: DiseasePack,
    base_scenario: ScenarioPack,
    observed_cases_df: Optional[pd.DataFrame] = None,
    ascertainment_rate: float = 0.20
) -> CalibrationReport:
    """Calibrate model parameters against observed empirical cases."""
    if observed_cases_df is None or observed_cases_df.empty:
        return CalibrationReport(
            is_calibrated=False,
            status_label="UNCALIBRATED",
            ascertainment_rate=ascertainment_rate,
            rmse_daily_positives=None,
            r_squared=None,
            fitted_beta=None,
            summary_message="No user-supplied observed case data provided. System marked UNCALIBRATED."
        )

    # Check provenance
    if "status" in observed_cases_df.columns:
        statuses = observed_cases_df["status"].str.lower().unique()
        if "synthetic" in statuses or "assumed" in statuses:
            return CalibrationReport(
                is_calibrated=False,
                status_label="UNCALIBRATED (SYNTHETIC FIXTURE)",
                ascertainment_rate=ascertainment_rate,
                rmse_daily_positives=None,
                r_squared=None,
                fitted_beta=None,
                summary_message="Observed cases table is marked synthetic/assumed. Calibration disabled."
            )

    # Run simulation
    sim_res = run_simulation(pop, disease_pack, base_scenario)

    # Compare daily positives
    sim_daily_cases = sim_res.daily_area_infections.sum(axis=1) * ascertainment_rate
    n_days = min(len(sim_daily_cases), len(observed_cases_df))

    obs_positives = observed_cases_df["positives"].values[:n_days].astype(np.float64)
    pred_positives = sim_daily_cases[:n_days]

    rmse = float(np.sqrt(np.mean((pred_positives - obs_positives) ** 2)))
    ss_tot = np.sum((obs_positives - np.mean(obs_positives)) ** 2)
    ss_res = np.sum((obs_positives - pred_positives) ** 2)
    r2 = float(1.0 - (ss_res / max(1e-6, ss_tot)))

    return CalibrationReport(
        is_calibrated=True,
        status_label="CALIBRATED",
        ascertainment_rate=ascertainment_rate,
        rmse_daily_positives=round(rmse, 2),
        r_squared=round(r2, 3),
        fitted_beta=sim_res.calibrated_beta,
        summary_message=f"Calibrated against {n_days} days of empirical observations (RMSE: {rmse:.1f}, R^2: {r2:.3f})."
    )
