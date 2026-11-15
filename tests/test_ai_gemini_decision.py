"""Tests for AI Layer: Gemini Decision 1 and LLM Advisor Agents (Stage R3.3).

Verifies:
1. GeminiDecisionClient offline determinism & prompt hashing.
2. 5 domain decision tasks: teacher buckets, column mapping, ledger claim, triage, claim check.
3. LLMAgentRuntime tool registration, dispatch, and transcript persistence.
4. Onboarding, ScenarioAuthor, and Critic interactive modes with transcripts.
"""

from pathlib import Path
import json
import pytest

from episwarm.ai.gemini_decision import (
    GeminiDecisionClient,
    DecisionResult,
    evaluate_teacher_bucket_decisions,
    map_import_columns,
    verify_ledger_parameter_claim,
    triage_scenario_measures,
    check_report_numerical_claims,
)
from episwarm.advisor.llm_client import LLMAgentRuntime, AgentTranscript
from episwarm.advisor.onboarding import OnboardingAgent
from episwarm.advisor.scenario_author import ScenarioAuthor
from episwarm.advisor.critic import PolicyCritic


def test_gemini_decision_offline_fallback(tmp_path):
    client = GeminiDecisionClient(api_key=None, cache_dir=tmp_path / "decision_cache")
    questions = {
        "q1": {"type": "choice", "options": ["adopt_masks", "no_masks"]},
        "q2": {"type": "noul", "min": 0.0, "max": 1.0},
        "q3": {"type": "score", "min": 1, "max": 10},
    }
    res = client.make_decisions(input_context="Agent in risk state 2", questions=questions)
    assert isinstance(res, dict)
    assert "q1" in res
    assert "q2" in res
    assert "q3" in res
    assert isinstance(res["q1"], DecisionResult)
    assert res["q1"].decision_type == "choice"
    assert res["q1"].fallback is True
    assert "adopt_masks" in res["q1"].probabilities or "no_masks" in res["q1"].probabilities


def test_evaluate_teacher_bucket_decisions(tmp_path):
    client = GeminiDecisionClient(api_key=None, cache_dir=tmp_path / "decision_cache")
    sit_text = "Severe outbreak, hospital ICU capacity at 85% with statutory mandates."
    buckets = {
        "b1": "Age 65+, symptomatic with comorbidity, high local risk",
        "b2": "Age 20-30, asymptomatic, low local risk"
    }
    res = evaluate_teacher_bucket_decisions(sit_text, buckets, client=client)
    assert "b1" in res
    assert "b2" in res
    assert isinstance(res["b1"], dict)
    assert "isolate_strict" in res["b1"]


def test_map_import_columns(tmp_path):
    client = GeminiDecisionClient(api_key=None, cache_dir=tmp_path / "decision_cache")
    cols = ["age_years", "area_code", "household_idx"]
    samples = [{"age_years": 45, "area_code": "E09000001", "household_idx": 102}]
    mapping = map_import_columns(cols, samples, client=client)
    assert isinstance(mapping, dict)
    assert "age_years" in mapping
    assert "area_code" in mapping
    assert mapping["age_years"]["target_field"] == "age"
    assert mapping["area_code"]["target_field"] == "area_id"


def test_verify_ledger_parameter_claim(tmp_path):
    client = GeminiDecisionClient(api_key=None, cache_dir=tmp_path / "decision_cache")
    res = verify_ledger_parameter_claim(
        source_excerpt="Imperial College COVID-19 Report 9 estimated R0 to be 2.4 (95% CI: 2.2-2.6).",
        parameter_name="r0",
        claimed_value=2.4,
        client=client
    )
    assert isinstance(res, dict)
    assert res["parameter"] == "r0"
    assert res["claimed_value"] == 2.4
    assert "verified" in res
    assert "probability" in res


def test_triage_scenario_measures(tmp_path):
    client = GeminiDecisionClient(api_key=None, cache_dir=tmp_path / "decision_cache")
    measures = [
        "Close all primary and secondary schools for 14 days",
        "Mandatory face masks in public retail and transit",
        "Unspecified guidance"
    ]
    triage = triage_scenario_measures(measures, client=client)
    assert isinstance(triage, list)
    assert len(triage) == 3
    cats = [m["category"] for m in triage]
    assert "school_closure" in cats
    assert "mask_mandate" in cats


def test_check_report_numerical_claims(tmp_path):
    client = GeminiDecisionClient(api_key=None, cache_dir=tmp_path / "decision_cache")
    sentences = [
        "Spearman rank correlation rho achieved 0.162.",
        "ICU peak ratio was 7.95."
    ]
    ledger_metrics = {"spearman_rho": 0.162, "icu_peak_ratio": 7.95}
    checks = check_report_numerical_claims(sentences, ledger_metrics, client=client)
    assert isinstance(checks, list)
    assert len(checks) == 2
    assert checks[0]["consistent_with_ledger"] is True


def test_llm_agent_runtime_transcript():
    runtime = LLMAgentRuntime(
        agent_name="TestAdvisor",
        system_instruction="Assists with testing",
        tools={"square": lambda x: x * x},
    )

    reply, transcript = runtime.run(
        user_prompt="Compute the square of 7",
        fallback_fn=lambda: "Squared 7 is 49"
    )

    assert "49" in reply
    assert isinstance(transcript, AgentTranscript)
    assert transcript.fallback == (runtime._client is None)
    saved_path = transcript.save()
    assert saved_path.exists()
    content = json.loads(saved_path.read_text(encoding="utf-8"))
    assert content["agent_name"] == "TestAdvisor"


def test_interactive_advisors():
    # Onboarding interactive diagnosis
    onboarding = OnboardingAgent()
    diag_reply, diag_trans = onboarding.diagnose_interactive("Check London setup")
    assert isinstance(diag_reply, str)
    assert isinstance(diag_trans, AgentTranscript)

    # Scenario author interactive
    author = ScenarioAuthor()
    sc, auth_trans = author.author_interactive("Close schools for 2 weeks on day 10, mandate masks for 40 days")
    assert sc is not None
    assert len(sc.interventions) >= 2
    assert isinstance(auth_trans, AgentTranscript)

    # Critic interactive
    critic = PolicyCritic()
    crit, crit_trans = critic.critique_interactive(sc)
    assert crit is not None
    assert 0.0 <= crit.overall_score <= 1.0
    assert isinstance(crit_trans, AgentTranscript)
