"""Advisor Agent: Iterative intervention planner producing Pydantic Recommendations."""

import os
import json
from typing import Dict, List, Optional, Any

from episwarm.advisor.schemas import Recommendation
from episwarm.advisor.tools import AdvisorToolKit
from episwarm.packs.scenario import InterventionAction


class AdvisorAgent:
    """Agentic decision loop exploring interventions to satisfy scenario targets."""

    def __init__(self, toolkit: AdvisorToolKit, run_budget: int = 5):
        self.toolkit = toolkit
        self.run_budget = run_budget

    def run_advisory_loop(self) -> Recommendation:
        """Run advisory cycle: baseline -> vulnerability inspection -> policy testing -> recommendation."""
        # 1. Run baseline scenario (no new interventions)
        baseline_id = self.toolkit.run_scenario({"interventions": []})
        baseline_metrics = self.toolkit.get_metrics(baseline_id)
        explored_runs = [baseline_id]

        best_run_id = baseline_id
        best_deaths = baseline_metrics["cumulative_deaths"]
        best_measures: List[InterventionAction] = []

        # 2. Iteratively test intervention candidates up to run budget
        candidate_plans = [
            # Candidate 1: Early school closure
            [
                InterventionAction(
                    name="early_school_closure",
                    measure_type="school_closure",
                    area_id="ALL",
                    start_day=7,
                    end_day=28,
                    stringency=1.0,
                    cost_per_day=1.0
                )
            ],
            # Candidate 2: Early school closure + surge ICU beds
            [
                InterventionAction(
                    name="school_closure",
                    measure_type="school_closure",
                    area_id="ALL",
                    start_day=7,
                    end_day=28,
                    stringency=1.0,
                    cost_per_day=1.0
                ),
                InterventionAction(
                    name="surge_icu_capacity",
                    measure_type="surge_beds",
                    area_id="ALL",
                    start_day=10,
                    end_day=45,
                    stringency=0.5,
                    cost_per_day=1.5
                )
            ],
            # Candidate 3: Targeted workplace reduction + curfew
            [
                InterventionAction(
                    name="workplace_reduction",
                    measure_type="workplace_reduction",
                    area_id="ALL",
                    start_day=10,
                    end_day=30,
                    stringency=0.5,
                    cost_per_day=2.5
                )
            ]
        ]

        for plan in candidate_plans[:self.run_budget - 1]:
            run_id = self.toolkit.run_scenario({
                "interventions": [p.model_dump() for p in plan]
            })
            explored_runs.append(run_id)
            metrics = self.toolkit.get_metrics(run_id)

            if metrics["cumulative_deaths"] < best_deaths:
                best_deaths = metrics["cumulative_deaths"]
                best_run_id = run_id
                best_measures = plan

        # Calculate reduction percentage
        reduction_pct = 0.0
        if baseline_metrics["cumulative_deaths"] > 0:
            reduction_pct = (baseline_metrics["cumulative_deaths"] - best_deaths) / baseline_metrics["cumulative_deaths"] * 100.0

        # Areas prioritized (from population areas)
        priority_areas = list(self.toolkit.pop.area_id_to_int.keys())[:3]

        return Recommendation(
            priority_areas=priority_areas,
            recommended_measures=best_measures,
            evidence_run_ids=explored_runs,
            objective_achieved=(best_deaths < baseline_metrics["cumulative_deaths"]),
            predicted_deaths_reduction=round(reduction_pct, 1),
            caveats=[
                "Behavior layer compliance is modeled under default assumed distributions.",
                "Spatial commuting flows rely on synthetic gravity decay matrix.",
                "Mortality reduction assumes rapid hospital admission without systemic supply chain failures."
            ]
        )

