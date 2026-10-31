"""Unit and invariant tests for Phase 6: Advisor agent, NSGA-II search, and three-arm comparison."""

import numpy as np
import pytest
import yaml

from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.advisor.tools import AdvisorToolKit
from episwarm.advisor.agent import AdvisorAgent
from episwarm.advisor.schemas import Recommendation
from episwarm.optimize.search import run_optuna_search, brute_force_best_policy
from episwarm.optimize.comparison import run_three_arm_comparison


@pytest.fixture
def test_setup():
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=3000, random_seed=42)
    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        d_pack = DiseasePack(**yaml.safe_load(f))
    with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
        s_data = yaml.safe_load(f)
        s_data["horizon_days"] = 15
        s_pack = ScenarioPack(**s_data)
    return pop, d_pack, s_pack


def test_advisor_toolkit_and_agent(test_setup):
    pop, d_pack, s_pack = test_setup
    toolkit = AdvisorToolKit(pop, d_pack, s_pack)

    measures = toolkit.list_measures()
    assert len(measures) >= 3

    agent = AdvisorAgent(toolkit, run_budget=3)
    rec = agent.run_advisory_loop()

    assert isinstance(rec, Recommendation)
    assert len(rec.priority_areas) > 0
    assert len(rec.evidence_run_ids) >= 2
    assert "stated assumptions" in rec.human_in_the_loop_advisory


def test_optuna_nsga2_search(test_setup):
    pop, d_pack, s_pack = test_setup
    df_pareto = run_optuna_search(pop, d_pack, s_pack, n_trials=4)

    assert not df_pareto.empty
    assert "deaths" in df_pareto.columns
    assert "peak_icu" in df_pareto.columns
    assert "cost" in df_pareto.columns


def test_brute_force_ground_truth(test_setup):
    pop, d_pack, s_pack = test_setup
    best = brute_force_best_policy(pop, d_pack, s_pack, [7], [14])

    assert "start_day" in best
    assert "score" in best
    assert best["start_day"] == 7


def test_three_arm_comparison(test_setup):
    pop, d_pack, s_pack = test_setup
    report = run_three_arm_comparison(pop, d_pack, s_pack)

    assert report.advisor_score >= 0.0
    assert report.search_score >= 0.0
    assert report.brute_force_best_score >= 0.0
    assert len(report.summary_df) == 4
