"""Marginal value analysis, diminishing returns curves, and optimal resource allocation (Spec 6.4)."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd

from episwarm.population.build import PopulationSoA
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack, ResourceAddAction
from episwarm.engine.sim import run_simulation


@dataclass
class MarginalPoint:
    units_added: float
    mean_deaths: float
    mean_overflow_deaths: float
    mean_unmet_demand: float
    marginal_death_reduction: float  # Deaths saved per unit


@dataclass
class MarginalCurveResult:
    resource_id: str
    area_id: str
    curve: List[MarginalPoint]
    diminishing_returns_threshold_units: float  # Inflection point where MB flattens
    best_marginal_benefit: float


def compute_marginal_value_curve(
    pop: PopulationSoA,
    disease_pack: DiseasePack,
    base_scenario: ScenarioPack,
    resource_id: str,
    area_id: str = "ALL",
    step_units: float = 10.0,
    max_units: float = 50.0,
    n_paired_seeds: int = 5
) -> MarginalCurveResult:
    """Sweep added resource units k = 0, d, 2d, ... across paired seeds to compute diminishing returns (Spec 6.4)."""
    unit_steps = np.arange(0.0, max_units + 0.1, step_units)
    curve_points: List[MarginalPoint] = []
    base_seed = base_scenario.random_seed

    prev_deaths = 0.0
    prev_units = 0.0

    for idx, u in enumerate(unit_steps):
        deaths_list = []
        overflow_list = []
        unmet_list = []

        for s_i in range(n_paired_seeds):
            scen = base_scenario.model_copy(deep=True)
            scen.random_seed = base_seed + s_i * 23

            if u > 0.0:
                res_add = ResourceAddAction(
                    resource_id=resource_id,
                    area_id=area_id,
                    amount=float(u),
                    start_day=0
                )
                scen.resource_adds = [res_add]
            else:
                scen.resource_adds = []

            res = run_simulation(pop, disease_pack, scen)
            deaths_list.append(res.total_deaths)
            overflow_list.append(res.overflow_deaths)
            unmet_list.append(int(np.sum(res.daily_icu_demand)))

        m_deaths = float(np.mean(deaths_list))
        m_overflow = float(np.mean(overflow_list))
        m_unmet = float(np.mean(unmet_list))

        if idx == 0:
            mb = 0.0
        else:
            delta_units = u - prev_units
            delta_deaths = prev_deaths - m_deaths
            mb = max(0.0, delta_deaths / max(1e-4, delta_units))

        prev_deaths = m_deaths
        prev_units = u

        curve_points.append(MarginalPoint(
            units_added=float(u),
            mean_deaths=m_deaths,
            mean_overflow_deaths=m_overflow,
            mean_unmet_demand=m_unmet,
            marginal_death_reduction=mb
        ))

    # Detect diminishing returns: point where MB drops below 30% of peak MB
    mb_values = [p.marginal_death_reduction for p in curve_points[1:]] if len(curve_points) > 1 else [0.0]
    peak_mb = max(mb_values) if mb_values else 0.0
    dim_units = float(max_units)

    for p in curve_points[1:]:
        if peak_mb > 0 and p.marginal_death_reduction < 0.30 * peak_mb:
            dim_units = p.units_added
            break

    return MarginalCurveResult(
        resource_id=resource_id,
        area_id=area_id,
        curve=curve_points,
        diminishing_returns_threshold_units=dim_units,
        best_marginal_benefit=peak_mb
    )


def rank_areas_by_marginal_benefit(
    pop: PopulationSoA,
    disease_pack: DiseasePack,
    base_scenario: ScenarioPack,
    resource_id: str,
    test_units: float = 15.0,
    n_paired_seeds: int = 4
) -> List[Tuple[str, float]]:
    """Determine which administrative area benefits most from the next unit of resources (Spec 6.4).

    Returns:
        List of (area_id, marginal_death_reduction) sorted in descending order of benefit.
    """
    area_ids = list(pop.area_id_to_int.keys())
    ranking = []

    for aid in area_ids:
        curve_res = compute_marginal_value_curve(
            pop, disease_pack, base_scenario,
            resource_id=resource_id,
            area_id=aid,
            step_units=test_units,
            max_units=test_units,
            n_paired_seeds=n_paired_seeds
        )
        benefit = curve_res.curve[-1].marginal_death_reduction if len(curve_res.curve) > 1 else 0.0
        ranking.append((aid, benefit))

    ranking.sort(key=lambda x: x[1], reverse=True)
    return ranking
