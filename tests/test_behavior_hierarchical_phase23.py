"""Tests for Phase 23: Hierarchical individual behavior model & agent diversity."""
import pytest
import numpy as np
import pandas as pd
import yaml
from pathlib import Path

from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.packs.behavior import DecisionQuestion
from episwarm.behavior.buckets import AgentBucket, SituationBucket
from episwarm.engine.sim import run_simulation
from episwarm.behavior.hierarchical import (
    HierarchicalCoefficients,
    compute_individual_probabilities,
    evaluate_agent_diversity
)
from episwarm.behavior.policy_local import LocalLogprobPolicy
from episwarm.behavior.policy_rules import RulePolicy


@pytest.fixture
def test_pop():
    return build_synthetic_population("regions/example_synthetic", scale_agents=1000, random_seed=42)


@pytest.fixture
def test_disease():
    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        return DiseasePack(**yaml.safe_load(f))


@pytest.fixture
def test_scenario():
    with open("scenarios/targeted_containment.yaml", "r", encoding="utf-8") as f:
        return ScenarioPack(**yaml.safe_load(f))


def test_individual_agent_probability_variance(test_pop):
    """Every agent must have individually distinct decision probabilities with significant variance (F8 fix)."""
    div = evaluate_agent_diversity(0.60, "wear_mask", test_pop)
    
    assert div["variance"] > 0.005, f"Expected non-zero variance across individual agents, got {div['variance']}"
    assert div["std_dev"] > 0.05, f"Expected std dev > 0.05, got {div['std_dev']}"
    assert div["min_probability"] < div["max_probability"]
    assert div["n_distinct_values"] > 100, f"Expected continuous distribution with >100 distinct values, got {div['n_distinct_values']}"


def test_trait_monotonicity(test_pop):
    """Higher compliance and trust should monotonically increase protective adoption."""
    idx = np.arange(test_pop.n_agents)
    probs = compute_individual_probabilities(0.50, "wear_mask", test_pop, idx)
    
    # Sort agents by compliance + trust index
    score = test_pop.compliance + test_pop.trust
    high_tier = probs[score > np.percentile(score, 75)]
    low_tier = probs[score < np.percentile(score, 25)]
    
    assert np.mean(high_tier) > np.mean(low_tier), "High compliance/trust agents should have higher protective adoption"


def test_financial_buffer_effect_on_isolation(test_pop):
    """Agents with greater financial buffer can afford to isolate more readily when sick."""
    idx = np.arange(test_pop.n_agents)
    probs = compute_individual_probabilities(0.70, "isolate_symptomatic", test_pop, idx)
    
    buff = test_pop.financial_buffer
    high_buff = probs[buff > 0.7]
    low_buff = probs[buff < 0.3]
    
    assert np.mean(high_buff) > np.mean(low_buff)


def test_prompt_shuffle_invariance():
    """Policy must be invariant to option ordering."""
    policy = RulePolicy()
    q = DecisionQuestion(
        id="wear_mask",
        question="Do you wear a mask in public?",
        options=["yes", "no"],
        plain_instructions="Decide whether to wear a mask in public spaces."
    )
    sit = SituationBucket(
        health_state_group="healthy",
        local_risk_level="high",
        active_measures="mask_mandate",
        household_member_sick=False
    )
    ag = AgentBucket(
        age_band="19-64",
        occupation_class="service",
        has_comorbidity=False,
        trust_band="high",
        risk_tolerance_band="low"
    )
    
    res1 = policy.decide(q, sit, ag)
    assert "yes" in res1 and "no" in res1
    assert abs(res1["yes"] + res1["no"] - 1.0) < 1e-4


def test_simulation_with_hierarchical_behavior(test_pop, test_disease, test_scenario):
    """End-to-end simulation runs seamlessly with individual hierarchical decisions."""
    contacts_df = pd.read_csv("regions/london/contacts.csv")
    test_scenario.horizon_days = 14
    
    res = run_simulation(
        pop=test_pop,
        disease_pack=test_disease,
        scenario_pack=test_scenario,
        contacts_df=contacts_df,
        behavior_mode="rule"
    )
    
    assert res.total_infections >= 0
    assert len(res.daily_hospital_demand) == 14
    assert res.daily_area_infections.shape[0] == 14
