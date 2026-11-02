"""Epidemiological observation engine: transforms latent simulated states into real-world observables (Phase 18)."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

from episwarm.engine.sim import SimulationResults
from episwarm.population.build import PopulationSoA
from episwarm.observation.config import ObservationConfig


@dataclass
class ObservationData:
    """Observed epidemiological time series and surveillance data."""
    horizon_days: int
    reported_cases: np.ndarray             # Daily confirmed cases reported
    hospital_admissions: np.ndarray        # Daily reported hospital admissions
    acute_bed_occupancy: np.ndarray        # Daily reported acute ward occupancy
    icu_bed_occupancy: np.ndarray          # Daily reported ICU bed occupancy
    ventilated_bed_occupancy: np.ndarray   # Daily ventilated bed occupancy
    reported_deaths: np.ndarray            # Daily confirmed deaths reported

    # Serological surveillance
    seroprevalence_dates: List[int] = field(default_factory=list)
    apparent_seroprevalence: List[float] = field(default_factory=list)
    true_cumulative_attack: List[float] = field(default_factory=list)

    # Ground-truth latent counterparts for validation & error analysis
    true_incident_infections: Optional[np.ndarray] = None
    true_incident_symptomatic: Optional[np.ndarray] = None
    true_hospital_demand: Optional[np.ndarray] = None
    true_icu_demand: Optional[np.ndarray] = None
    true_daily_deaths: Optional[np.ndarray] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dataframe(self) -> pd.DataFrame:
        """Export core observation series to a pandas DataFrame."""
        return pd.DataFrame({
            "day": np.arange(self.horizon_days),
            "reported_cases": self.reported_cases,
            "hospital_admissions": self.hospital_admissions,
            "acute_bed_occupancy": self.acute_bed_occupancy,
            "icu_bed_occupancy": self.icu_bed_occupancy,
            "ventilated_bed_occupancy": self.ventilated_bed_occupancy,
            "reported_deaths": self.reported_deaths
        })


def convolve_delay(events: np.ndarray, pmf: np.ndarray) -> np.ndarray:
    """Convolve an event series with a discrete delay PMF, truncating at original length."""
    if len(events) == 0 or len(pmf) == 0:
        return np.zeros_like(events, dtype=np.float64)
    conv = np.convolve(events.astype(np.float64), pmf.astype(np.float64))
    return conv[:len(events)]


def sample_observation_noise(
    mean_series: np.ndarray,
    noise_type: str,
    phi: float,
    rng: np.random.Generator
) -> np.ndarray:
    """Sample noisy integer observations from expected means via Poisson or Negative Binomial."""
    means = np.maximum(0.0, mean_series.astype(np.float64))
    if noise_type == "none":
        return np.round(means).astype(np.int64)
    elif noise_type == "poisson":
        return rng.poisson(lam=means).astype(np.int64)
    elif noise_type == "negbin":
        # NegBin parameterization: mean = mu, variance = mu + mu^2 / phi
        # Scipy / NumPy parameterization: number of failures r = phi, probability p = phi / (phi + mu)
        out = np.zeros(len(means), dtype=np.int64)
        pos = (means > 1e-6)
        if np.any(pos):
            mu_pos = means[pos]
            r = max(0.1, float(phi))
            p = r / (r + mu_pos)
            out[pos] = rng.negative_binomial(n=r, p=p)
        return out
    return np.round(means).astype(np.int64)


def generate_observations(
    sim_results: SimulationResults,
    obs_config: ObservationConfig,
    rng: Optional[np.random.Generator] = None,
    pop: Optional[PopulationSoA] = None,
    survey_days: Optional[List[int]] = None
) -> ObservationData:
    """Transform latent simulation results into realistic reported surveillance metrics (Phase 18)."""
    if rng is None:
        rng = np.random.default_rng(42)

    horizon = sim_results.horizon_days

    # 1. Derive true latent incident events
    # Incident infections: sum across areas
    true_infections = np.sum(sim_results.daily_area_infections, axis=1).astype(np.float64)

    # Incident symptomatic: use recorded or infer from state changes
    if getattr(sim_results, "daily_incident_symptomatic", None) is not None:
        true_symptomatic = sim_results.daily_incident_symptomatic.astype(np.float64)
    else:
        # Approximate from incident infections delayed by ~3 days incubation
        inc_pmf = np.array([0.05, 0.15, 0.35, 0.25, 0.15, 0.05])
        true_symptomatic = convolve_delay(true_infections, inc_pmf)

    # True daily deaths: from cumulative deaths or states
    if getattr(sim_results, "daily_incident_deaths", None) is not None:
        true_deaths = sim_results.daily_incident_deaths.astype(np.float64)
    else:
        # Find dead state index if present
        d_idx = -1
        for i, s_name in enumerate(sim_results.state_names):
            if s_name in ("D", "Dead", "dead"):
                d_idx = i
                break
        if d_idx >= 0:
            cum_deaths = sim_results.daily_state_counts[:, d_idx].astype(np.float64)
            true_deaths = np.diff(np.concatenate(([0.0], cum_deaths)))
            true_deaths = np.maximum(0.0, true_deaths)
        else:
            true_deaths = np.zeros(horizon, dtype=np.float64)

    true_hosp_demand = sim_results.daily_hospital_demand.astype(np.float64)
    true_icu_demand = sim_results.daily_icu_demand.astype(np.float64)

    # 2. Case Observation Model:
    # Onset-to-report delay convolution
    case_pmf = obs_config.case_delay.to_pmf(max_days=obs_config.case_delay.max_days)
    delayed_symptomatic = convolve_delay(true_symptomatic, case_pmf)

    # Time-varying ascertainment fraction
    ascertainment_factors = np.array([
        obs_config.ascertainment.get_fraction(d, horizon) for d in range(horizon)
    ], dtype=np.float64)
    ascertained_cases = delayed_symptomatic * ascertainment_factors

    # Day-of-week reporting modulation
    dow_factors = np.array([
        obs_config.day_of_week.get_factor(d) for d in range(horizon)
    ], dtype=np.float64)
    expected_reported_cases = ascertained_cases * dow_factors

    # Stochastic observation noise
    reported_cases = sample_observation_noise(
        expected_reported_cases,
        obs_config.reporting_noise,
        obs_config.negbin_dispersion,
        rng
    )

    # 3. Hospital Observation Model:
    # Onset-to-admission delay
    adm_pmf = obs_config.hospital.admission_delay.to_pmf(max_days=obs_config.hospital.admission_delay.max_days)

    # Infer admissions: rate of new arrivals needed to sustain hospital demand
    # New admissions ~ convolve severe demand derivative or scale symptomatic
    # More robustly: acute admissions derived from newly severe cases
    acute_los_pmf = obs_config.hospital.acute_los.to_pmf(max_days=obs_config.hospital.acute_los.max_days)
    mean_los = max(1.0, obs_config.hospital.acute_los.mean)

    # Admissions expected per day ~ demand / mean_los
    expected_admissions = (true_hosp_demand / mean_los) * obs_config.hospital.admission_reporting_fraction
    admissions_delayed = convolve_delay(expected_admissions, adm_pmf)
    hospital_admissions = sample_observation_noise(
        admissions_delayed,
        obs_config.reporting_noise,
        obs_config.negbin_dispersion,
        rng
    )

    # Occupancy via survival renewal: S(t) = 1 - CDF(t)
    # Occupancy(t) = sum_k Admissions(t - k) * S(k)
    acute_cdf = np.cumsum(acute_los_pmf)
    acute_survival = np.maximum(0.0, 1.0 - acute_cdf)
    acute_occupancy_mean = convolve_delay(hospital_admissions.astype(np.float64), acute_survival)
    acute_bed_occupancy = sample_observation_noise(
        acute_occupancy_mean,
        obs_config.reporting_noise,
        obs_config.negbin_dispersion * 2.0,  # occupancy has less daily fluctuation than flow
        rng
    )

    # ICU occupancy and ventilated bed occupancy
    icu_los_pmf = obs_config.hospital.icu_los.to_pmf(max_days=obs_config.hospital.icu_los.max_days)
    icu_cdf = np.cumsum(icu_los_pmf)
    icu_survival = np.maximum(0.0, 1.0 - icu_cdf)
    mean_icu_los = max(1.0, obs_config.hospital.icu_los.mean)
    expected_icu_admissions = true_icu_demand / mean_icu_los
    icu_occupancy_mean = convolve_delay(expected_icu_admissions, icu_survival)
    icu_bed_occupancy = sample_observation_noise(
        icu_occupancy_mean,
        obs_config.reporting_noise,
        obs_config.negbin_dispersion * 2.0,
        rng
    )

    vent_occupancy_mean = icu_bed_occupancy.astype(np.float64) * obs_config.hospital.ventilated_fraction
    ventilated_bed_occupancy = sample_observation_noise(
        vent_occupancy_mean,
        obs_config.reporting_noise,
        obs_config.negbin_dispersion * 2.0,
        rng
    )

    # 4. Mortality Observation Model:
    # Death registration delay
    death_pmf = obs_config.mortality.registration_delay.to_pmf(max_days=obs_config.mortality.registration_delay.max_days)
    delayed_deaths = convolve_delay(true_deaths, death_pmf) * obs_config.mortality.reporting_completeness

    if obs_config.mortality.day_of_week is not None:
        death_dow = np.array([
            obs_config.mortality.day_of_week.get_factor(d) for d in range(horizon)
        ], dtype=np.float64)
        delayed_deaths *= death_dow

    reported_deaths = sample_observation_noise(
        delayed_deaths,
        obs_config.reporting_noise,
        obs_config.negbin_dispersion,
        rng
    )

    # 5. Serological Surveillance:
    seroprevalence_dates = survey_days or [int(horizon * 0.33), int(horizon * 0.66), horizon - 1]
    apparent_sero = []
    true_attack_rates = []

    total_pop = float(sim_results.n_agents)
    cum_infections = np.cumsum(true_infections)

    for s_day in seroprevalence_dates:
        s_day = min(horizon - 1, max(0, s_day))
        # Account for seroconversion delay
        eff_day = max(0, s_day - obs_config.serology.seroconversion_delay_days)
        true_prev = float(cum_infections[eff_day] / max(1.0, total_pop))
        true_prev = min(1.0, true_prev)

        # Rogan-Gladen relation: Apparent = Se * True + (1 - Sp) * (1 - True)
        se = obs_config.serology.test_sensitivity
        sp = obs_config.serology.test_specificity
        apparent = se * true_prev + (1.0 - sp) * (1.0 - true_prev)

        # Antibody waning if configured
        if obs_config.serology.waning_half_life_days is not None and s_day > 60:
            waning_rate = np.log(2.0) / obs_config.serology.waning_half_life_days
            apparent *= np.exp(-waning_rate * (s_day - 60))

        apparent_sero.append(float(np.clip(apparent, 0.0, 1.0)))
        true_attack_rates.append(true_prev)

    return ObservationData(
        horizon_days=horizon,
        reported_cases=reported_cases,
        hospital_admissions=hospital_admissions,
        acute_bed_occupancy=acute_bed_occupancy,
        icu_bed_occupancy=icu_bed_occupancy,
        ventilated_bed_occupancy=ventilated_bed_occupancy,
        reported_deaths=reported_deaths,
        seroprevalence_dates=seroprevalence_dates,
        apparent_seroprevalence=apparent_sero,
        true_cumulative_attack=true_attack_rates,
        true_incident_infections=true_infections,
        true_incident_symptomatic=true_symptomatic,
        true_hospital_demand=true_hosp_demand,
        true_icu_demand=true_icu_demand,
        true_daily_deaths=true_deaths,
        metadata={
            "observation_config_name": obs_config.name,
            "provenance": obs_config.provenance.model_dump(),
            "noise_model": obs_config.reporting_noise
        }
    )

