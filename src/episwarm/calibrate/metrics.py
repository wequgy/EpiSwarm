"""Validation metrics and scoring functions for epidemiological comparison (Phase 21)."""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
from scipy import stats


@dataclass
class CurveValidationTarget:
    """Validation target evaluation for a single time series (e.g. admissions, deaths)."""
    name: str
    observed_peak_day: int
    simulated_peak_day: int
    peak_timing_error_days: int
    observed_peak_value: float
    simulated_peak_value: float
    peak_ratio: float
    cumulative_observed: float
    cumulative_simulated: float
    cumulative_relative_error: float
    pi_50_coverage: float
    pi_90_coverage: float
    crps_score: float
    passed: bool
    notes: str


def compute_crps(observed: np.ndarray, simulated_replicates: np.ndarray) -> float:
    """Compute empirical Continuous Ranked Probability Score (CRPS) across N replicates.

    CRPS measures calibration and sharpness: CRPS(F, y) = E|X - y| - 0.5 * E|X - X'|
    where X, X' are independent draws from the predictive ensemble F.
    """
    n_days = len(observed)
    n_reps = simulated_replicates.shape[0]
    crps_days = np.zeros(n_days, dtype=np.float64)

    for d in range(n_days):
        y = observed[d]
        draws = simulated_replicates[:, d].astype(np.float64)
        term1 = np.mean(np.abs(draws - y))
        term2 = 0.5 * np.mean(np.abs(draws[:, None] - draws[None, :]))
        crps_days[d] = term1 - term2

    return float(np.mean(crps_days))


def evaluate_curve_target(
    name: str,
    observed: np.ndarray,
    replicates: np.ndarray,
    max_peak_error_days: int = 5,
    min_peak_ratio: float = 0.75,
    max_peak_ratio: float = 1.25,
    max_cumulative_error: float = 0.25
) -> CurveValidationTarget:
    """Evaluate simulated ensemble against an observed time series."""
    obs_peak_day = int(np.argmax(observed))
    obs_peak_val = float(np.max(observed))

    mean_sim = np.mean(replicates, axis=0)
    sim_peak_day = int(np.argmax(mean_sim))
    sim_peak_val = float(np.max(mean_sim))

    timing_err = abs(sim_peak_day - obs_peak_day)
    peak_ratio = sim_peak_val / max(1e-6, obs_peak_val)

    cum_obs = float(np.sum(observed))
    cum_sim = float(np.sum(mean_sim))
    cum_err = abs(cum_sim - cum_obs) / max(1.0, cum_obs)

    # Prediction interval coverage
    p25 = np.percentile(replicates, 25, axis=0)
    p75 = np.percentile(replicates, 75, axis=0)
    p05 = np.percentile(replicates, 5, axis=0)
    p95 = np.percentile(replicates, 95, axis=0)

    in_50 = (observed >= p25) & (observed <= p75)
    in_90 = (observed >= p05) & (observed <= p95)

    cov_50 = float(np.mean(in_50))
    cov_90 = float(np.mean(in_90))
    crps = compute_crps(observed, replicates)

    passed = (
        (timing_err <= max_peak_error_days) and
        (min_peak_ratio <= peak_ratio <= max_peak_ratio) and
        (cum_err <= max_cumulative_error)
    )

    notes = "Within pre-registered tolerance" if passed else "Tolerance exceeded"
    return CurveValidationTarget(
        name=name,
        observed_peak_day=obs_peak_day,
        simulated_peak_day=sim_peak_day,
        peak_timing_error_days=timing_err,
        observed_peak_value=obs_peak_val,
        simulated_peak_value=sim_peak_val,
        peak_ratio=peak_ratio,
        cumulative_observed=cum_obs,
        cumulative_simulated=cum_sim,
        cumulative_relative_error=cum_err,
        pi_50_coverage=cov_50,
        pi_90_coverage=cov_90,
        crps_score=crps,
        passed=passed,
        notes=notes
    )


def evaluate_spatial_arrival_rank_correlation(
    observed_arrival_days: np.ndarray,
    simulated_arrival_days: np.ndarray
) -> Tuple[float, float, bool]:
    """Compute Spearman rank correlation of arrival dates across geographic units."""
    if len(observed_arrival_days) < 3 or np.all(observed_arrival_days == observed_arrival_days[0]):
        return 0.0, 1.0, False

    corr, pval = stats.spearmanr(observed_arrival_days, simulated_arrival_days)
    rho = float(corr) if not np.isnan(corr) else 0.0
    p = float(pval) if not np.isnan(pval) else 1.0
    passed = (rho >= 0.60)
    return rho, p, passed

