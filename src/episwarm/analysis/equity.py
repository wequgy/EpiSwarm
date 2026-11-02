"""Equity analysis: outcome disparities across geography and demographic cohorts."""

from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

from episwarm.population.build import PopulationSoA
from episwarm.engine.sim import SimulationResults


@dataclass
class EquityReport:
    """Disparity metrics across demographic strata."""
    area_attack_rates: Dict[str, float]
    age_attack_rates: Dict[str, float]
    worst_off_area: str
    best_off_area: str
    area_disparity_gap: float  # worst_off - best_off attack rate
    age_disparity_gap: float   # highest - lowest age attack rate

    def summary(self) -> str:
        lines = [
            "---------------- Equity & Disparity Audit ----------------",
            f"Worst-Off Area:      {self.worst_off_area} ({self.area_attack_rates.get(self.worst_off_area, 0.0)*100:.1f}% attack rate)",
            f"Best-Off Area:       {self.best_off_area} ({self.area_attack_rates.get(self.best_off_area, 0.0)*100:.1f}% attack rate)",
            f"Geographic Equity Gap: {self.area_disparity_gap*100:.2f} percentage points",
            f"Age Cohort Equity Gap: {self.age_disparity_gap*100:.2f} percentage points",
            "----------------------------------------------------------"
        ]
        return "\n".join(lines)


def evaluate_equity(
    pop: PopulationSoA,
    sim_results: SimulationResults,
    age_bands: Optional[List[str]] = None
) -> EquityReport:
    """Evaluate outbreak outcome equity across areas and age cohorts."""
    # 1. By Area
    area_totals = np.bincount(pop.area_id, minlength=len(pop.int_to_area_id))
    # Sum daily infections per area
    area_cases = sim_results.daily_area_infections.sum(axis=0)

    area_rates: Dict[str, float] = {}
    for i in range(len(area_totals)):
        aid_str = pop.int_to_area_id.get(i, f"A{i:02d}")
        pop_sz = max(1, area_totals[i])
        rate = float(area_cases[i] / pop_sz)
        area_rates[aid_str] = round(rate, 4)

    worst_aid = max(area_rates, key=area_rates.get) if area_rates else "none"
    best_aid = min(area_rates, key=area_rates.get) if area_rates else "none"
    geo_gap = (area_rates[worst_aid] - area_rates[best_aid]) if area_rates else 0.0

    # 2. By Age Cohort (Dynamic bands per Phase 17 Generality)
    if not age_bands:
        age_bands = ["0-4", "5-18", "19-64", "65+"]

    from episwarm.population.age_bands import assign_age_bands
    band_indices = assign_age_bands(pop.age, age_bands)

    # Approximate age cases using relative population shares
    age_rates: Dict[str, float] = {}
    for idx, b_name in enumerate(age_bands):
        sub_pop = int(np.sum(band_indices == idx))
        if sub_pop > 0:
            frac = sub_pop / float(pop.n_agents)
            cases_est = sim_results.total_infections * frac
            age_rates[b_name] = round(float(cases_est / sub_pop), 4)

    worst_age = max(age_rates, key=age_rates.get) if age_rates else "none"
    best_age = min(age_rates, key=age_rates.get) if age_rates else "none"
    age_gap = age_rates[worst_age] - age_rates[best_age]

    return EquityReport(
        area_attack_rates=area_rates,
        age_attack_rates=age_rates,
        worst_off_area=worst_aid,
        best_off_area=best_aid,
        area_disparity_gap=round(geo_gap, 4),
        age_disparity_gap=round(age_gap, 4)
    )

