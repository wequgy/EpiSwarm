"""Unit and acceptance tests for Phase 11: Rumor, Misinformation, and Compliance Layer.

Acceptance criteria (Roadmap Section 5 & Spec 7, 8):
1. No seeds means no spread; beliefs stay strictly bounded in [0, 1].
2. More correction reach lowers mean belief.
3. Higher belief lowers compliance and increases behavioral transmission.
4. Counterfactual (rumor off) paired-seed evaluation outputs deaths attributable to rumor with confidence intervals.
5. Decision policy bucketing: belief appears only as a band ("low", "moderate", "high").
"""

from pathlib import Path
import pytest
import numpy as np
import pandas as pd
import yaml

from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack, InterventionAction
from episwarm.packs.behavior import BehaviorPack, RumorTopic, RumorBehaviorEffects, ComplianceWeights
from episwarm.behavior.network import build_social_network
from episwarm.behavior.rumor import RumorDynamicsEngine, get_belief_band
from episwarm.behavior.compliance import DynamicComplianceEngine
from episwarm.engine.sim import run_simulation, run_counterfactual_rumor_analysis


def test_rumor_no_seeds_no_spread_bounds():
    """Acceptance criterion 1: No initial seeds implies no spread; beliefs stay in [0, 1]."""
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=1000, random_seed=42)
    adj = build_social_network(pop, rng=np.random.default_rng(42))

    topic_no_seeds = RumorTopic(
        id="zero_seed_claim",
        label="Zero seed claim",
        seed_day=0,
        num_seeds=0,
        credibility=1.0
    )
    engine = RumorDynamicsEngine(pop, [topic_no_seeds], adj)
    rng = np.random.default_rng(42)

    for day in range(15):
        tele = engine.step_day(day, active_corrections={}, rng=rng)
        assert tele["zero_seed_claim"]["mean_belief"] == 0.0
        assert tele["zero_seed_claim"]["believers_count"] == 0
        assert np.all((engine.beliefs >= 0.0) & (engine.beliefs <= 1.0))


def test_correction_reach_lowers_mean_belief():
    """Acceptance criterion 2: More correction reach statistically lowers mean belief."""
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=2000, random_seed=101)
    adj = build_social_network(pop, rng=np.random.default_rng(101))

    topic = RumorTopic(
        id="test_rumor",
        label="Test Rumor",
        seed_day=0,
        num_seeds=50,
        credibility=1.2
    )

    # Run A: No correction
    engine_no_corr = RumorDynamicsEngine(pop, [topic], adj)
    rng_a = np.random.default_rng(202)
    for day in range(12):
        engine_no_corr.step_day(day, active_corrections={}, rng=rng_a)
    final_belief_no_corr = float(np.mean(engine_no_corr.beliefs[0]))

    # Run B: High correction campaign active from day 3
    engine_with_corr = RumorDynamicsEngine(pop, [topic], adj)
    rng_b = np.random.default_rng(202)
    for day in range(12):
        corrections = {"test_rumor": 0.50} if day >= 3 else {}
        engine_with_corr.step_day(day, active_corrections=corrections, rng=rng_b)
    final_belief_with_corr = float(np.mean(engine_with_corr.beliefs[0]))

    assert final_belief_no_corr > 0.10, "Rumor should spread without correction"
    assert final_belief_with_corr < final_belief_no_corr, "Correction must lower mean belief"
    assert final_belief_with_corr <= 0.60 * final_belief_no_corr, "Active correction should reduce belief substantially"


def test_higher_belief_lowers_compliance_and_distorts_behavior():
    """Acceptance criterion 3: Higher rumor belief lowers dynamic compliance via kappa and reduces masking."""
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=1500, random_seed=42)
    adj = build_social_network(pop, rng=np.random.default_rng(42))

    weights = ComplianceWeights(w_risk=0.2, w_norm=0.2, w_enf=0.2, w_fat=0.1, kappa=0.4)
    comp_engine = DynamicComplianceEngine(pop, weights, adj)

    n_areas = len(pop.int_to_area_id)
    enforcements = np.zeros(n_areas, dtype=np.float32)
    incident_rates = np.full(n_areas, 0.02, dtype=np.float32)

    # 1. Compliance under zero belief
    zero_beliefs = np.zeros((1, pop.n_agents), dtype=np.float32)
    comp_zero = comp_engine.step_day(enforcements, incident_rates, rumor_beliefs=zero_beliefs)
    mean_comp_zero = float(np.mean(comp_zero))

    # 2. Compliance under high rumor belief (0.8)
    high_beliefs = np.full((1, pop.n_agents), 0.80, dtype=np.float32)
    comp_high = comp_engine.step_day(enforcements, incident_rates, rumor_beliefs=high_beliefs)
    mean_comp_high = float(np.mean(comp_high))

    assert mean_comp_high < mean_comp_zero
    expected_drop = weights.kappa * 0.80
    actual_drop = mean_comp_zero - mean_comp_high
    assert actual_drop >= 0.70 * expected_drop

    # Behavioral distortions
    topic = RumorTopic(
        id="t1",
        label="t1",
        behavior_effects=RumorBehaviorEffects(mask_reduction=0.40, isolation_reduction=0.30)
    )
    rumor_eng = RumorDynamicsEngine(pop, [topic], adj)
    rumor_eng.beliefs[0] = 0.75
    mask_red, iso_red = rumor_eng.compute_behavior_distortions()
    assert np.all(mask_red >= 0.25)
    assert np.all(iso_red >= 0.20)


def test_counterfactual_rumor_analysis_with_ci():
    """Acceptance criterion 4: Paired-seed counterfactual evaluation with confidence intervals."""
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=3000, random_seed=42)

    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        d_pack = DiseasePack(**yaml.safe_load(f))

    with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
        s_pack = ScenarioPack(**yaml.safe_load(f))
        s_pack.horizon_days = 20

    with open("behavior/default.yaml", "r", encoding="utf-8") as f:
        b_pack = BehaviorPack(**yaml.safe_load(f))

    # Run paired counterfactual evaluation
    report = run_counterfactual_rumor_analysis(pop, d_pack, s_pack, b_pack, n_seeds=3)

    assert "deltas" in report
    assert "mean_delta_deaths" in report
    assert "ci_lower" in report
    assert "ci_upper" in report
    assert len(report["deltas"]) == 3
    # Check bounds consistency
    assert report["ci_lower"] <= report["mean_delta_deaths"] <= report["ci_upper"]


def test_belief_band_bucketing_for_policies():
    """Acceptance criterion 5: Decision policy bucketing; belief appears strictly as a band."""
    assert get_belief_band(0.0) == "low"
    assert get_belief_band(0.20) == "low"
    assert get_belief_band(0.25) == "moderate"
    assert get_belief_band(0.50) == "moderate"
    assert get_belief_band(0.64) == "moderate"
    assert get_belief_band(0.65) == "high"
    assert get_belief_band(1.0) == "high"

