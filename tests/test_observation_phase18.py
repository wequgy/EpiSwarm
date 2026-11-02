"""Unit tests and verification for Phase 18: Observation Model and Parameter Recovery."""

import numpy as np
import pytest
import yaml

from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.engine.sim import run_simulation
from episwarm.observation.config import (
    ObservationConfig,
    DelayDistribution,
    DayOfWeekEffect,
    AscertainmentModel,
    HospitalObservationConfig,
    MortalityObservationConfig,
    SerologyObservationConfig
)
from episwarm.observation.engine import generate_observations, convolve_delay
from episwarm.observation.twin import run_twin_experiment, fit_observation_parameters


@pytest.fixture(scope="module")
def sim_run():
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=3000, random_seed=42)
    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        disease = DiseasePack(**yaml.safe_load(f))
    with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
        scen = ScenarioPack(**yaml.safe_load(f))
    scen.horizon_days = 60
    scen.random_seed = 101

    results = run_simulation(pop, disease, scen, enable_behavior=False)
    return pop, disease, scen, results


def test_delay_distribution_properties():
    """Verify delay distribution discretization, normalization, and mean recovery."""
    # 1. Gamma distribution
    gamma_dist = DelayDistribution(dist_type="gamma", mean=5.0, std=2.0, max_days=30)
    pmf_gamma = gamma_dist.to_pmf()
    assert len(pmf_gamma) == 31
    assert np.isclose(np.sum(pmf_gamma), 1.0, atol=1e-5)
    calc_mean_gamma = np.sum(np.arange(len(pmf_gamma)) * pmf_gamma)
    assert abs(calc_mean_gamma - 5.0) < 0.25, f"Expected mean ~5.0, got {calc_mean_gamma}"

    # 2. Lognormal distribution
    lognorm_dist = DelayDistribution(dist_type="lognormal", mean=6.0, std=3.0, max_days=35)
    pmf_lognorm = lognorm_dist.to_pmf()
    assert np.isclose(np.sum(pmf_lognorm), 1.0, atol=1e-5)
    calc_mean_log = np.sum(np.arange(len(pmf_lognorm)) * pmf_lognorm)
    assert abs(calc_mean_log - 6.0) < 0.35, f"Expected mean ~6.0, got {calc_mean_log}"

    # 3. Fixed delay
    fixed_dist = DelayDistribution(dist_type="fixed", mean=4.0, std=0.0, max_days=10)
    pmf_fixed = fixed_dist.to_pmf()
    assert pmf_fixed[4] == 1.0
    assert np.sum(pmf_fixed) == 1.0


def test_day_of_week_effect():
    """Verify day-of-week cycling and normalization to mean 1.0."""
    dow = DayOfWeekEffect(weights=[1.4, 1.2, 1.0, 0.9, 0.9, 0.8, 0.8], start_day_of_week=0)
    assert np.isclose(np.mean(dow.weights), 1.0, atol=1e-5)
    # Day 0 = Mon -> factor is weights[0]
    assert np.isclose(dow.get_factor(0), dow.weights[0])
    # Day 6 = Sun -> factor is weights[6]
    assert np.isclose(dow.get_factor(6), dow.weights[6])
    # Day 7 = Mon -> factor cycles back to weights[0]
    assert np.isclose(dow.get_factor(7), dow.weights[0])


def test_ascertainment_models():
    """Verify constant, sigmoid, and piecewise linear ascertainment bounds."""
    # Constant
    m_const = AscertainmentModel(model_type="constant", base_fraction=0.30)
    assert m_const.get_fraction(0, 100) == 0.30
    assert m_const.get_fraction(50, 100) == 0.30

    # Sigmoid transition
    m_sig = AscertainmentModel(
        model_type="sigmoid",
        base_fraction=0.20,
        max_fraction=0.50,
        transition_day=30.0,
        transition_speed=5.0
    )
    val_early = m_sig.get_fraction(5, 100)
    val_mid = m_sig.get_fraction(30, 100)
    val_late = m_sig.get_fraction(60, 100)

    assert 0.19 <= val_early <= 0.22
    assert 0.34 <= val_mid <= 0.36  # exact midpoint ~ (0.2 + 0.5)/2 = 0.35
    assert 0.48 <= val_late <= 0.50
    assert val_early < val_mid < val_late


def test_observation_generation_and_mass_conservation(sim_run):
    """Verify observation model convolution and mass conservation."""
    pop, disease, scen, results = sim_run

    # Zero noise, flat day-of-week, constant ascertainment
    cfg = ObservationConfig(
        ascertainment=AscertainmentModel(model_type="constant", base_fraction=0.40),
        day_of_week=DayOfWeekEffect(weights=[1.0] * 7, start_day_of_week=0),
        case_delay=DelayDistribution(dist_type="gamma", mean=4.0, std=1.5, max_days=15),
        reporting_noise="none"
    )

    obs = generate_observations(results, cfg)

    assert obs.horizon_days == results.horizon_days
    assert len(obs.reported_cases) == results.horizon_days
    assert len(obs.hospital_admissions) == results.horizon_days
    assert len(obs.acute_bed_occupancy) == results.horizon_days
    assert len(obs.reported_deaths) == results.horizon_days

    # Mass conservation over complete wave: sum of reported cases
    # should be close to 0.40 * sum of symptomatic
    total_symp = np.sum(obs.true_incident_symptomatic)
    total_rep = np.sum(obs.reported_cases)
    effective_ratio = total_rep / max(1.0, total_symp)
    assert 0.35 <= effective_ratio <= 0.45, f"Expected ratio ~0.40, got {effective_ratio:.3f}"


def test_serology_rogan_gladen(sim_run):
    """Verify Rogan-Gladen apparent seroprevalence calculation."""
    pop, disease, scen, results = sim_run

    se = 0.95
    sp = 0.98
    cfg = ObservationConfig(
        serology=SerologyObservationConfig(
            test_sensitivity=se,
            test_specificity=sp,
            seroconversion_delay_days=10,
            waning_half_life_days=None
        )
    )

    obs = generate_observations(results, cfg, survey_days=[20, 50])
    assert len(obs.apparent_seroprevalence) == 2
    assert len(obs.true_cumulative_attack) == 2

    # Rogan-Gladen check for each survey day
    for app, true_prev in zip(obs.apparent_seroprevalence, obs.true_cumulative_attack):
        expected_app = se * true_prev + (1.0 - sp) * (1.0 - true_prev)
        assert np.isclose(app, expected_app, atol=1e-3)


def test_parameter_recovery_twin_experiment(sim_run):
    """Twin experiment: show parameter recovery of rho, case delay, and acute LoS within intervals."""
    pop, disease, scen, results = sim_run

    true_rho = 0.35
    true_delay = 5.0
    true_los = 8.0

    # Run 10 paired replicates for fast test verification
    res_twin = run_twin_experiment(
        results,
        n_replicates=10,
        random_seed=42,
        true_rho=true_rho,
        true_case_delay=true_delay,
        true_acute_los=true_los
    )

    stat_rho = res_twin.parameters["ascertainment_rho"]
    stat_delay = res_twin.parameters["case_delay_mean"]
    stat_los = res_twin.parameters["acute_los_mean"]

    print("\n" + res_twin.summary_table())

    # Verify that true parameters fall within the recovered 95% confidence intervals or small tolerance
    assert abs(stat_rho.mean_estimate - true_rho) < 0.08, f"Ascertainment recovery error: true={true_rho}, est={stat_rho.mean_estimate}"
    assert abs(stat_delay.mean_estimate - true_delay) < 1.0, f"Delay recovery error: true={true_delay}, est={stat_delay.mean_estimate}"
    assert abs(stat_los.mean_estimate - true_los) < 1.5, f"LoS recovery error: true={true_los}, est={stat_los.mean_estimate}"

    # Verify identifiability documentation
    assert len(res_twin.unidentifiable_pairs) >= 2
