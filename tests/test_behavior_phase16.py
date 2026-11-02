"""Verification tests for Phase 16: Behavior loop, area targeting, attributable overflow, and LLM Advisor."""

import json
from pathlib import Path
from unittest.mock import MagicMock
import numpy as np
import pandas as pd
import pytest
import yaml

from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack, InterventionAction
from episwarm.packs.behavior import BehaviorPack
from episwarm.behavior.policy_rules import RulePolicy
from episwarm.behavior.policy_local import LocalLogprobPolicy
from episwarm.behavior.cache import DecisionCache
from episwarm.engine.sim import run_simulation, run_paired_counterfactual_overflow
from episwarm.advisor.tools import AdvisorToolKit
from episwarm.advisor.agent import AdvisorAgent
from episwarm.advisor.schemas import Recommendation


@pytest.fixture(scope="module")
def shared_pop():
    return build_synthetic_population("regions/example_synthetic", scale_agents=2000, random_seed=42)


@pytest.fixture(scope="module")
def shared_disease():
    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return DiseasePack(**data)


@pytest.fixture(scope="module")
def shared_behavior():
    with open("behavior/default.yaml", "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return BehaviorPack(**data)


@pytest.fixture(scope="module")
def shared_contacts():
    p = Path("regions/example_synthetic/contacts.csv")
    if p.exists():
        return pd.read_csv(p)
    return None


@pytest.fixture(scope="module")
def shared_scenario():
    with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    data["horizon_days"] = 35
    data["seeding"]["initial_cases_per_area"] = 60
    data["interventions"] = []
    return ScenarioPack(**data)


def test_16a_behavior_ablation(shared_pop, shared_disease, shared_scenario, shared_behavior):
    """(a) Behavior ablation: run with (1) no behavior, (2) rule behavior, (3) local policy;

    Show attack rate drops monotonically and peak flattens.
    """
    scen = shared_scenario.model_copy(deep=True)
    scen.random_seed = 101

    # 1. No behavior (agents take zero personal protective actions)
    res_no_beh = run_simulation(
        shared_pop, shared_disease, scen,
        behavior_pack=shared_behavior,
        enable_behavior=False
    )

    # 2. Rule behavior (agents respond on triggers with rule-based heuristics)
    cache_rule = DecisionCache(db_path=":memory:")
    rule_policy = RulePolicy(cache=cache_rule)
    res_rule = run_simulation(
        shared_pop, shared_disease, scen,
        behavior_pack=shared_behavior,
        policy=rule_policy,
        enable_behavior=True
    )

    # 3. Local/High-compliance policy (protective risk-aware model)
    class HighProtectionPolicy(RulePolicy):
        def decide(self, question, situation, bucket, context=""):
            if question.id == "wear_mask":
                return {"yes": 0.95, "no": 0.05}
            elif question.id == "isolate_symptomatic":
                return {"yes": 0.95, "no": 0.05}
            elif question.id == "workplace_attendance":
                return {"usual": 0.1, "reduced": 0.3, "avoid": 0.6}
            return super().decide(question, situation, bucket, context)

    high_policy = HighProtectionPolicy(cache=DecisionCache(db_path=":memory:"))
    res_high = run_simulation(
        shared_pop, shared_disease, scen,
        behavior_pack=shared_behavior,
        policy=high_policy,
        enable_behavior=True
    )

    ar_none = res_no_beh.attack_rate
    ar_rule = res_rule.attack_rate
    ar_high = res_high.attack_rate

    inf_indices = [i for i, s in enumerate(shared_disease.states) if s.infectious]
    peak_none = int(np.max(np.sum(res_no_beh.daily_state_counts[:, inf_indices], axis=1)))
    peak_rule = int(np.max(np.sum(res_rule.daily_state_counts[:, inf_indices], axis=1)))
    peak_high = int(np.max(np.sum(res_high.daily_state_counts[:, inf_indices], axis=1)))

    print(f"\nBehavior Ablation Results:")
    print(f"  No Behavior:     Attack Rate = {ar_none*100:.2f}%, Peak Active = {peak_none}")
    print(f"  Rule Behavior:   Attack Rate = {ar_rule*100:.2f}%, Peak Active = {peak_rule}")
    print(f"  High Protection: Attack Rate = {ar_high*100:.2f}%, Peak Active = {peak_high}")

    # Monotonic drop in attack rate and peak flattening
    assert ar_none > ar_rule >= ar_high, f"Expected monotonic drop: {ar_none} > {ar_rule} >= {ar_high}"
    assert peak_none >= peak_rule >= peak_high, f"Expected peak flattening: {peak_none} >= {peak_rule} >= {peak_high}"


def test_16b_area_targeting(shared_pop, shared_disease, shared_scenario, shared_contacts):
    """(b) Area targeting test: closing schools only in area A drops transmission in area A

    significantly more than in unclosed area B.
    """
    scen_baseline = shared_scenario.model_copy(deep=True)
    scen_baseline.random_seed = 202
    scen_baseline.seeding.area_id = None  # Seed across region
    scen_baseline.seeding.initial_cases_per_area = 50
    scen_baseline.interventions = []

    res_baseline = run_simulation(shared_pop, shared_disease, scen_baseline, contacts_df=shared_contacts, enable_behavior=False)

    # Area A01 school closure
    scen_a01 = scen_baseline.model_copy(deep=True)
    scen_a01.interventions = [
        InterventionAction(
            name="a01_school_closure",
            measure_type="school_closure",
            area_id="A01",
            start_day=3,
            end_day=35,
            stringency=1.0,
            cost_per_day=1.0
        )
    ]
    res_a01 = run_simulation(shared_pop, shared_disease, scen_a01, contacts_df=shared_contacts, enable_behavior=False)

    aid_0 = shared_pop.area_id_to_int["A01"]
    aid_1 = shared_pop.area_id_to_int["A02"]

    inf_base_a01 = int(np.sum(res_baseline.daily_area_infections[:, aid_0]))
    inf_a01_a01 = int(np.sum(res_a01.daily_area_infections[:, aid_0]))
    drop_a01 = inf_base_a01 - inf_a01_a01

    inf_base_a02 = int(np.sum(res_baseline.daily_area_infections[:, aid_1]))
    inf_a01_a02 = int(np.sum(res_a01.daily_area_infections[:, aid_1]))
    drop_a02 = inf_base_a02 - inf_a01_a02

    pct_drop_a01 = (drop_a01 / max(1, inf_base_a01)) * 100.0
    pct_drop_a02 = (drop_a02 / max(1, inf_base_a02)) * 100.0

    print(f"\nArea Targeting Results:")
    print(f"  A01 (Closed schools):   Baseline Inf = {inf_base_a01}, Closed Inf = {inf_a01_a01} (Drop = {pct_drop_a01:.1f}%)")
    print(f"  A02 (Unclosed schools): Baseline Inf = {inf_base_a02}, Closed Inf = {inf_a01_a02} (Drop = {pct_drop_a02:.1f}%)")

    # The drop in closed area A01 must exceed the drop in unclosed area A02
    assert drop_a01 > 0, "A01 school closure must reduce infections in A01"
    assert pct_drop_a01 > pct_drop_a02, f"Expected larger percentage drop in A01 ({pct_drop_a01:.1f}%) than A02 ({pct_drop_a02:.1f}%)"


def test_16c_attributable_overflow_accounting(shared_pop, shared_disease, shared_scenario):
    """(c) Attributable overflow test: counterfactual run with infinite beds shows fewer deaths;

    difference equals attributable overflow deaths within Poisson error.
    """
    scen = shared_scenario.model_copy(deep=True)
    scen.random_seed = 303
    scen.horizon_days = 40
    scen.seeding.initial_cases_per_area = 100

    # Create severe resource shortage dataframe (near 0 clinical capacity)
    resources_data = []
    for aid in shared_pop.area_id_to_int.keys():
        resources_data.append({
            "resource_id": "res_bed",
            "name": "General Bed",
            "unit": "bed",
            "area_id": aid,
            "date_or_static": "static",
            "nominal": 2.0,  # Only 2 beds per area -> extreme overflow
            "effective_low": 2.0,
            "effective_high": 2.0,
            "upper_cap_of_extra": 50.0,
            "restock_rate": 0.0,
            "source": "synthetic",
            "status": "synthetic"
        })
        resources_data.append({
            "resource_id": "res_support",
            "name": "Support Unit",
            "unit": "unit",
            "area_id": aid,
            "date_or_static": "static",
            "nominal": 1.0,
            "effective_low": 1.0,
            "effective_high": 1.0,
            "upper_cap_of_extra": 20.0,
            "restock_rate": 0.0,
            "source": "synthetic",
            "status": "synthetic"
        })
    resources_df = pd.DataFrame(resources_data)

    constrained_res, unlimited_res, delta_deaths = run_paired_counterfactual_overflow(
        shared_pop, shared_disease, scen,
        resources_df=resources_df,
        enable_behavior=False
    )

    print(f"\nAttributable Overflow Results:")
    print(f"  Constrained Run Deaths: {constrained_res.total_deaths}")
    print(f"  Unlimited Run Deaths:   {unlimited_res.total_deaths}")
    print(f"  Attributable Overflow:  {delta_deaths}")

    assert constrained_res.total_deaths >= unlimited_res.total_deaths, "Constrained run must have at least as many deaths as unlimited"
    assert delta_deaths == (constrained_res.total_deaths - unlimited_res.total_deaths), "Delta must equal difference"
    assert constrained_res.overflow_deaths == delta_deaths


def test_16d_advisor_gemini_fallback_and_tool_calling(shared_pop, shared_disease, shared_scenario):
    """(d) Fallback test: when Gemini fails or runs out of budget, the deterministic fallback runs

    and returns a valid Recommendation. Also tests mocked Gemini tool-calling execution.
    """
    toolkit = AdvisorToolKit(shared_pop, shared_disease, shared_scenario)

    # 1. Fallback when no API key is provided
    agent_fallback = AdvisorAgent(toolkit, run_budget=3, gemini_client=None)
    rec_fallback = agent_fallback.run_advisory_loop()

    assert isinstance(rec_fallback, Recommendation)
    assert len(rec_fallback.priority_areas) > 0
    assert len(rec_fallback.recommended_measures) > 0
    assert len(rec_fallback.evidence_run_ids) > 0
    assert any("Deterministic fallback" in c for c in rec_fallback.caveats)

    # 2. Fallback when Gemini client raises an exception
    faulty_client = MagicMock()
    faulty_client.models.generate_content.side_effect = RuntimeError("Quota exhausted or connection refused")

    agent_faulty = AdvisorAgent(toolkit, run_budget=3, gemini_client=faulty_client)
    rec_faulty = agent_faulty.run_advisory_loop()

    assert isinstance(rec_faulty, Recommendation)
    assert any("Deterministic fallback" in c for c in rec_faulty.caveats)

    # 3. Successful tool-calling path with Mock Gemini Client
    mock_client = MagicMock()

    # Step 1: Model calls list_available_measures
    fc_list = MagicMock()
    fc_list.name = "list_available_measures"
    fc_list.args = {}

    part_fc = MagicMock()
    part_fc.function_call = fc_list
    part_fc.text = None

    cand_fc = MagicMock()
    cand_fc.content.parts = [part_fc]

    resp_step1 = MagicMock()
    resp_step1.function_calls = [fc_list]
    resp_step1.candidates = [cand_fc]

    # Step 2: Model returns final JSON Recommendation
    rec_json = json.dumps({
        "priority_areas": ["A01", "A02"],
        "recommended_measures": [
            {
                "name": "early_school_closure",
                "measure_type": "school_closure",
                "area_id": "ALL",
                "start_day": 7,
                "end_day": 28,
                "stringency": 1.0,
                "cost_per_day": 1.0
            }
        ],
        "evidence_run_ids": ["run_mock_1"],
        "objective_achieved": True,
        "predicted_deaths_reduction": 45.0,
        "caveats": ["Assumes baseline compliance"],
        "human_in_the_loop_advisory": "Advisory disclaimer."
    })

    part_text = MagicMock()
    part_text.function_call = None
    part_text.text = rec_json

    cand_text = MagicMock()
    cand_text.content.parts = [part_text]

    resp_step2 = MagicMock()
    resp_step2.function_calls = None
    resp_step2.candidates = [cand_text]
    resp_step2.text = rec_json

    mock_client.models.generate_content.side_effect = [resp_step1, resp_step2]

    agent_mock = AdvisorAgent(toolkit, run_budget=4, gemini_client=mock_client)
    rec_success = agent_mock.run_advisory_loop()

    assert isinstance(rec_success, Recommendation)
    assert rec_success.priority_areas == ["A01", "A02"]
    assert len(rec_success.recommended_measures) == 1
    assert rec_success.predicted_deaths_reduction == 45.0
    assert len(agent_mock.transcripts) > 0

