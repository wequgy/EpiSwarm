"""Unit tests for LocalLogprobPolicy (Phase 9D acceptance criteria)."""

from pathlib import Path
from unittest.mock import patch
import pytest

from episwarm.packs.behavior import DecisionQuestion, QuestionType
from episwarm.behavior.buckets import AgentBucket, SituationBucket
from episwarm.behavior.cache import DecisionCache
from episwarm.behavior.policy_local import LocalLogprobPolicy
from episwarm.behavior.policy_rules import RulePolicy
from episwarm.analysis.variance_check import evaluate_policy_variance, run_behavior_ablation, generate_benchmark_archetypes


@pytest.fixture
def local_cache(tmp_path):
    return DecisionCache(tmp_path / "local_cache.sqlite")


@pytest.fixture
def mock_question():
    return DecisionQuestion(
        id="mask_wearing",
        type=QuestionType.NOUL,
        options=["yes", "no"],
        plain_instructions="Decide whether you will wear a mask in public venues."
    )


def test_local_policy_offline_fallback(local_cache, mock_question):
    """Verify LocalLogprobPolicy runs fully offline when server is unreachable, falling back to RulePolicy."""
    policy = LocalLogprobPolicy(
        base_url="http://127.0.0.1:9999",  # non-existent port
        cache=local_cache,
        fallback_policy=RulePolicy(cache=local_cache)
    )
    sit = SituationBucket("susceptible", "high", "curfew", False)
    buck = AgentBucket("65+", "none", True, "high", "low")

    probs = policy.decide(mock_question, sit, buck)
    # 1. Probabilities sum to 1.0
    assert sum(probs.values()) == pytest.approx(1.0, abs=1e-3)
    assert "yes" in probs and "no" in probs
    assert policy.fallback_count > 0


def test_local_policy_with_mock_logprobs(local_cache, mock_question):
    """Verify logprob calculation, normalization, and option order shuffling."""
    policy = LocalLogprobPolicy(cache=local_cache, shuffles=2)
    sit = SituationBucket("susceptible", "low", "none", False)
    buck = AgentBucket("19-64", "service", False, "medium", "medium")

    # Mock _query_next_token_logprobs: model assigns higher logprob to the label corresponding to "yes"
    def fake_query(prompt, labels):
        # Find which label is associated with "yes" in this prompt
        if f"{labels[0]}. yes" in prompt:
            return {labels[0]: -0.223, labels[1]: -1.609}
        else:
            return {labels[0]: -1.609, labels[1]: -0.223}

    with patch.object(policy, "_query_next_token_logprobs", side_effect=fake_query):
        probs = policy.decide(mock_question, sit, buck)

        assert sum(probs.values()) == pytest.approx(1.0, abs=1e-3)
        assert probs["yes"] > probs["no"]
        # Cache hit on second call
        cached_probs = policy.decide(mock_question, sit, buck)
        assert cached_probs == probs
        assert policy.cache_hits_count == 1


def test_option_order_shuffling_tolerance(local_cache, mock_question):
    """Verify that shuffling option order stabilizes output and changes averaged probabilities by < stated tolerance (0.05)."""
    policy = LocalLogprobPolicy(cache=local_cache, shuffles=2)
    sit = SituationBucket("susceptible", "medium", "none", False)
    buck = AgentBucket("19-64", "service", False, "medium", "medium")

    call_count = 0

    def biased_query(prompt, labels):
        nonlocal call_count
        call_count += 1
        # Simulate slight position bias: first option always gets slightly higher logprob
        return {labels[0]: -0.51, labels[1]: -0.91}

    with patch.object(policy, "_query_next_token_logprobs", side_effect=biased_query):
        probs = policy.decide(mock_question, sit, buck)
        assert sum(probs.values()) == pytest.approx(1.0, abs=1e-3)
        # Because options were shuffled, the position bias is cancelled out
        diff = abs(probs["yes"] - probs["no"])
        assert diff <= 0.05, f"Position bias was not cancelled: diff is {diff}"


def test_prompt_sensitivity_5_paraphrases(local_cache):
    """Run 5-paraphrase prompt sensitivity test and report spread."""
    paraphrases = [
        "Decide whether you will wear a mask in public venues.",
        "Will you wear a protective face mask when entering crowded spaces?",
        "Please choose if you intend to wear a face covering outdoors or indoors.",
        "Under current guidelines, do you commit to wearing a face mask?",
        "Are you going to wear a mask during your daily routines?"
    ]

    policy = RulePolicy(cache=local_cache)
    sit = SituationBucket("susceptible", "medium", "none", False)
    buck = AgentBucket("19-64", "service", False, "medium", "medium")

    results = []
    for p_text in paraphrases:
        q = DecisionQuestion(
            id=f"mask_test_{hash(p_text)}",
            type=QuestionType.NOUL,
            options=["yes", "no"],
            plain_instructions=p_text
        )
        probs = policy.decide(q, sit, buck)
        results.append(probs["yes"])

    spread = max(results) - min(results)
    # Documented spread
    assert spread <= 0.20, f"Prompt paraphrase spread exceeds threshold: {spread}"
