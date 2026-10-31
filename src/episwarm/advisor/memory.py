"""Structured memory log of explored scenarios and multi-objective evaluations."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

from episwarm.analysis.metrics import ObjectiveVector
from episwarm.engine.sim import SimulationResults


@dataclass
class ScenarioRecord:
    run_id: str
    scenario_dict: Dict[str, Any]
    objectives: ObjectiveVector
    timestamp: float


class AdvisorMemory:
    """Stores history of scenario evaluations performed during an advisory session."""

    def __init__(self):
        self.records: Dict[str, ScenarioRecord] = {}

    def log_run(
        self,
        run_id: str,
        scenario_dict: Dict[str, Any],
        objectives: ObjectiveVector,
        timestamp: float
    ) -> None:
        self.records[run_id] = ScenarioRecord(
            run_id=run_id,
            scenario_dict=scenario_dict,
            objectives=objectives,
            timestamp=timestamp
        )

    def get_run(self, run_id: str) -> Optional[ScenarioRecord]:
        return self.records.get(run_id)

    def compare_runs(self, run_id_a: str, run_id_b: str) -> Dict[str, Any]:
        rec_a = self.get_run(run_id_a)
        rec_b = self.get_run(run_id_b)
        if not rec_a or not rec_b:
            raise ValueError(f"One or both run IDs not found in memory: {run_id_a}, {run_id_b}")

        obj_a = rec_a.objectives
        obj_b = rec_b.objectives

        return {
            "run_a": run_id_a,
            "run_b": run_id_b,
            "deaths_delta": obj_b.cumulative_deaths - obj_a.cumulative_deaths,
            "peak_icu_delta": obj_b.peak_icu_occupancy - obj_a.peak_icu_occupancy,
            "cost_delta": obj_b.economic_cost_proxy - obj_a.economic_cost_proxy,
            "equity_gap_delta": obj_b.equity_disparity_gap - obj_a.equity_disparity_gap
        }
