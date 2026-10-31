"""Unit and invariant tests for Phase 4: behavior policies, caching, variance, and ablation harness."""

from pathlib import Path
import numpy as np
import pytest

from episwarm.packs.behavior import DecisionQuestion, QuestionType
from episwarm.behavior.buckets import AgentBucket, SituationBucket
from episwarm.behavior.cache import DecisionCache
from episwarm.behavior.policy_rules import RulePolicy
from episwarm.behavior.policy_jev import JevPolicy
from episwarm.analysis.variance_check import evaluate_policy_variance, run_behavior_ablation, generate_benchmark_archetypes


@pytest.fixture
def test_cache(tmp_path):
    return DecisionCache(tmp_path / "test_cache.sqlite")


@pytest.fixture
def sample_question():
    return DecisionQuestion(
        id="workplace_attendance",
        type=QuestionType.CHOICE,
        options=["usual", "reduced", "avoid"],
        plain_instructions="Decide your workplace attendance based on current outbreak conditions."
    )


def test_rule_policy_decisions(test_cache, sample_question):
    policy = RulePolicy(cache=test_cache)
    bucket = AgentBucket(
        age_band="19-64",
        occupation_class="service",
        has_comorbidity=False,
        trust_band="medium",
        risk_tolerance_band="medium"
    )
    # Low risk situation
    sit_low = SituationBucket(
        health_state_group="susceptible",
        local_risk_level="low",
        active_measures="none",
        household_member_sick=False
    )
    probs_low = policy.decide(sample_question, sit_low, bucket)
    assert sum(probs_low.values()) == pytest.approx(1.0, abs=1e-3)
    assert probs_low["usual"] > probs_low["avoid"]

    # Critical risk situation
    sit_crit = SituationBucket(
        health_state_group="symptomatic",
        local_risk_level="critical",
        active_measures="lockdown",
        household_member_sick=True
    )
    probs_crit = policy.decide(sample_question, sit_crit, bucket)
    assert sum(probs_crit.values()) == pytest.approx(1.0, abs=1e-3)
    # In critical situation, avoid attendance probability must be higher than usual
    assert probs_crit["avoid"] > probs_crit["usual"]


def test_decision_cache_persistence(test_cache):
    test_cache.put("test_pol", "q1", "sit1", "buck1", {"optA": 0.6, "optB": 0.4})
    retrieved = test_cache.get("test_pol", "q1", "sit1", "buck1")
    assert retrieved is not None
    assert retrieved["optA"] == 0.6
    assert retrieved["optB"] == 0.4

    # Miss
    assert test_cache.get("test_pol", "q2", "sit1", "buck1") is None


def test_jev_policy_fallback_when_unconfigured(test_cache, sample_question):
    # No API key provided -> should fall back to RulePolicy
    jev_pol = JevPolicy(api_key=None, cache=test_cache)
    sit = SituationBucket("susceptible", "medium", "none", False)
    buck = AgentBucket("19-64", "service", False, "high", "low")

    probs = jev_pol.decide(sample_question, sit, buck)
    assert sum(probs.values()) == pytest.approx(1.0, abs=1e-3)
    assert jev_pol.fallback_count > 0
    assert jev_pol.fallback_rate == 1.0


def test_action_sampling_never_strict_argmax():
    """Verify stochastic action sampling with trait noise produces diverse actions."""
    probs = {"optA": 0.70, "optB": 0.30}
    rng = np.random.default_rng(42)

    samples = [
        RulePolicy.sample_action(probs, individual_noise=0.1, rng=rng)
        for _ in range(500)
    ]
    unique_choices, counts = np.unique(samples, return_counts=True)
    assert len(unique_choices) == 2, "Both options must be sampled; never lock to argmax!"
    # optA was 70%, so should be majority but not 100%
    p_a = counts[unique_choices == "optA"][0] / 500.0
    assert 0.55 < p_a < 0.85


def test_variance_and_ablation(test_cache, sample_question):
    rule_pol = RulePolicy(cache=test_cache)
    jev_pol = JevPolicy(api_key=None, cache=test_cache)

    policies = {"Rule": rule_pol, "Jev_Fallback": jev_pol}
    ablation_df = run_behavior_ablation(policies, sample_question)

    assert len(ablation_df) == 2
    assert "mean_variance" in ablation_df.columns
    # Ensure mean variance across diverse archetypes > 0
    assert ablation_df["mean_variance"].iloc[0] > 0.001
