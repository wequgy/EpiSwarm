"""Advisor tool functions for running counterfactual scenarios and comparing outcomes."""

import time
from typing import Dict, List, Optional, Any
import numpy as np

from episwarm.population.build import PopulationSoA
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack, InterventionAction
from episwarm.engine.sim import run_simulation
from episwarm.analysis.metrics import evaluate_single_run_objectives, ObjectiveVector
from episwarm.advisor.memory import AdvisorMemory


AVAILABLE_MEASURES = [
    {
        "type": "school_closure",
        "description": "Closes schools in target area or region-wide.",
        "typical_cost_per_day": 1.0,
        "default_stringency": 1.0
    },
    {
        "type": "workplace_reduction",
        "description": "Reduces in-person workplace occupancy and mandates work-from-home.",
        "typical_cost_per_day": 2.5,
        "default_stringency": 0.50
    },
    {
        "type": "curfew",
        "description": "Restricts evening mobility and social community mixing.",
        "typical_cost_per_day": 3.0,
        "default_stringency": 0.60
    },
    {
        "type": "surge_beds",
        "description": "Provisions emergency ICU beds and oxygen buffers.",
        "typical_cost_per_day": 1.5,
        "default_stringency": 0.30
    }
]


class AdvisorToolKit:
    """Execution environment for Advisor agent tool calls."""

    def __init__(
        self,
        pop: PopulationSoA,
        disease_pack: DiseasePack,
        base_scenario: ScenarioPack,
        memory: Optional[AdvisorMemory] = None
    ):
        self.pop = pop
        self.disease_pack = disease_pack
        self.base_scenario = base_scenario
        self.memory = memory or AdvisorMemory()

    def list_measures(self) -> List[Dict[str, Any]]:
        """Return library of available intervention types, parameters, and economic costs."""
        return AVAILABLE_MEASURES

    def run_scenario(self, scenario_dict: Dict[str, Any]) -> str:
        """Run a counterfactual scenario with specified interventions and record in memory."""
        # Merge scenario dictionary with base
        data = self.base_scenario.model_dump()
        data.update(scenario_dict)
        scen = ScenarioPack(**data)

        res = run_simulation(self.pop, self.disease_pack, scen)
        objs = evaluate_single_run_objectives(self.pop, res, scen)

        self.memory.log_run(res.run_id, scen.model_dump(), objs, time.time())
        return res.run_id

    def get_metrics(self, run_id: str, by: str = "summary") -> Dict[str, Any]:
        """Retrieve evaluated objective metrics for a specific run ID."""
        rec = self.memory.get_run(run_id)
        if not rec:
            return {"error": f"Run ID '{run_id}' not found in memory"}

        objs = rec.objectives
        return {
            "run_id": run_id,
            "cumulative_deaths": objs.cumulative_deaths,
            "peak_icu_occupancy": objs.peak_icu_occupancy,
            "days_icu_overflow": objs.days_icu_overflow,
            "economic_cost_proxy": objs.economic_cost_proxy,
            "equity_disparity_gap": objs.equity_disparity_gap
        }

    def compare(self, run_id_a: str, run_id_b: str) -> Dict[str, Any]:
        """Compare the objective vectors between two runs."""
        return self.memory.compare_runs(run_id_a, run_id_b)

