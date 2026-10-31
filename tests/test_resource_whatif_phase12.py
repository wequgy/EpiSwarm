"""Unit and acceptance tests for Phase 12: Resource What-If, Marginal Value Curves, and Studio Modes.

Acceptance criteria (Roadmap Section 6 & Spec 6.4):
1. Baseline vs +X units paired comparison outputs deltas with confidence intervals.
2. Adding resources never increases unmet demand across paired seeds (delta <= 0).
3. Marginal value curves identify diminishing returns thresholds and best-area rankings.
4. Upper cap validation strictly enforced with clear message.
5. Simulate and Plan modes operational in Studio.
"""

from pathlib import Path
import pytest
import numpy as np
import pandas as pd
import yaml

from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack, ResourceAddAction
from episwarm.analysis.resource_whatif import evaluate_resource_whatif_paired
from episwarm.analysis.marginal_value import compute_marginal_value_curve, rank_areas_by_marginal_benefit


def test_resource_whatif_paired_deltas_and_ci():
    """Acceptance criterion 1 & 2: Paired comparison reports deltas with CI and never increases unmet demand."""
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=3000, random_seed=42)

    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        d_pack = DiseasePack(**yaml.safe_load(f))

    with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
        s_pack = ScenarioPack(**yaml.safe_load(f))
        s_pack.horizon_days = 25

    res_df = pd.read_csv("regions/example_synthetic/resources.csv")

    action = ResourceAddAction(
        resource_id="res_bed",
        area_id="ALL",
        amount=20.0,
        start_day=0,
        cost_per_unit=2.0
    )

    report = evaluate_resource_whatif_paired(
        pop, d_pack, s_pack, [action], resources_df=res_df, n_paired_seeds=5
    )

    assert report["n_paired_seeds"] == 5
    assert report["total_added_cost"] == 40.0
    assert "deaths_delta" in report
    assert "ci_lower" in report["deaths_delta"]
    assert "ci_upper" in report["deaths_delta"]

    # Invariant: Adding clinical capacity must NEVER increase unmet demand (delta <= 0 in paired seeds)
    unmet_samples = report["unmet_demand_delta"]["samples"]
    for s_delta in unmet_samples:
        assert s_delta <= 0, f"Resource addition must never increase unmet demand! Got delta: {s_delta}"


def test_marginal_value_curve_and_diminishing_returns():
    """Acceptance criterion 3: Marginal value curve produces diminishing returns inflection point."""
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=3000, random_seed=101)

    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        d_pack = DiseasePack(**yaml.safe_load(f))

    with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
        s_pack = ScenarioPack(**yaml.safe_load(f))
        s_pack.horizon_days = 20

    curve_res = compute_marginal_value_curve(
        pop, d_pack, s_pack,
        resource_id="res_bed",
        area_id="ALL",
        step_units=10.0,
        max_units=40.0,
        n_paired_seeds=3
    )

    assert len(curve_res.curve) == 5  # 0, 10, 20, 30, 40
    assert curve_res.diminishing_returns_threshold_units > 0
    assert curve_res.resource_id == "res_bed"

    # Best area ranking
    ranking = rank_areas_by_marginal_benefit(
        pop, d_pack, s_pack, resource_id="res_bed", test_units=10.0, n_paired_seeds=3
    )
    assert len(ranking) == 2  # A01 and A02
    assert ranking[0][0] in ["A01", "A02"]


def test_resource_whatif_upper_cap_enforcement():
    """Acceptance criterion 4: Violations exceeding upper_cap_of_extra raise clear ValueError (Spec 6.4)."""
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=1000, random_seed=42)

    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        d_pack = DiseasePack(**yaml.safe_load(f))

    with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
        s_pack = ScenarioPack(**yaml.safe_load(f))

    res_df = pd.DataFrame([
        {
            "resource_id": "res_bed",
            "area_id": "A01",
            "nominal": 50,
            "upper_cap_of_extra": 15.0
        }
    ])

    # Attempting to add 100 units when cap is 15
    excess_action = ResourceAddAction(resource_id="res_bed", area_id="A01", amount=100.0)

    with pytest.raises(ValueError) as excinfo:
        evaluate_resource_whatif_paired(pop, d_pack, s_pack, [excess_action], resources_df=res_df, n_paired_seeds=2)

    assert "exceeds upper_cap_of_extra" in str(excinfo.value)
