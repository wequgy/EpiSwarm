"""Unit and integration tests for Agent Layer v3 (Stage A5)."""

from pathlib import Path
import numpy as np
import pytest
from episwarm.advisor.onboarding import OnboardingAgent, OnboardingIssue
from episwarm.advisor.scenario_author import ScenarioAuthor
from episwarm.advisor.critic import PolicyCritic
from episwarm.advisor.ensemble_advisor import PosteriorEnsembleAdvisor
from episwarm.calibrate.smc_abc import PosteriorEnsemble, Particle
from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack
import yaml


def test_onboarding_agent_valid_region():
    agent = OnboardingAgent()
    report = agent.run_onboarding_audit(
        region_dir=Path("regions/reference_london"),
        disease_yaml=Path("diseases/respiratory_generic.yaml")
    )
    assert report.valid is True
    assert report.n_areas > 0
    assert report.n_issues == 0 or all(i.severity != "ERROR" for i in report.issues)


def test_onboarding_agent_missing_region():
    agent = OnboardingAgent()
    report = agent.run_onboarding_audit(
        region_dir=Path("regions/nonexistent_region_xyz"),
        disease_yaml=Path("diseases/respiratory_generic.yaml")
    )
    assert report.valid is False
    assert any(i.severity == "ERROR" for i in report.issues)


def test_scenario_author():
    author = ScenarioAuthor()
    sc = author.parse_natural_language_brief(
        "Close schools for 3 weeks on day 14, and mandate masks for 60 days."
    )
    assert sc.horizon_days >= 60
    assert len(sc.interventions) >= 2
    types = [a.measure_type for a in sc.interventions]
    assert "school_closure" in types
    assert "mask_wearing" in types
    school_action = [a for a in sc.interventions if a.measure_type == "school_closure"][0]
    assert school_action.start_day == 14
    assert school_action.end_day == 35


def test_policy_critic():
    author = ScenarioAuthor()
    critic = PolicyCritic()

    # Good multi-layered policy
    sc_good = author.parse_natural_language_brief("Mandate masks for 40 days, and close schools for 2 weeks on day 10.")
    crit_good = critic.evaluate_scenario(sc_good)
    assert crit_good.approved is True
    assert crit_good.overall_score > 0.70

    # Excessive lockdown provoking fatigue
    sc_fatigue = author.parse_natural_language_brief("Institute stay at home lockdown for 70 days on day 5.")
    crit_fatigue = critic.evaluate_scenario(sc_fatigue)
    assert crit_fatigue.dimension_scores["fatigue_risk"].score < 0.70


def test_posterior_ensemble_advisor():
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=1000, random_seed=42)
    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        dp = DiseasePack(**yaml.safe_load(f))

    particles = [
        Particle(params={"r0": 2.4, "i0": 20.0, "kappa": 0.6}, weight=0.5, distance=1.0, sim_peak_day=30, sim_peak_val=100.0, sim_total=1000.0),
        Particle(params={"r0": 3.0, "i0": 35.0, "kappa": 0.7}, weight=0.5, distance=1.2, sim_peak_day=28, sim_peak_val=150.0, sim_total=1500.0),
    ]
    ensemble = PosteriorEnsemble(particles=particles, generation=2, tolerance=1.5, parameter_names=["r0", "i0", "kappa"])

    advisor = PosteriorEnsembleAdvisor(pop, dp, ensemble, icu_capacity=500.0)
    author = ScenarioAuthor()
    sc = author.parse_natural_language_brief("Mandate masks for 45 days starting day 5.")
    risk = advisor.evaluate_policy_across_ensemble(sc, n_draws=2)

    assert risk.expected_peak_icu > 0.0
    assert 0.0 <= risk.p_icu_breach <= 1.0
    assert len(risk.icu_95_ci) == 2
