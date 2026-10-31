"""Spatial spread matrix computation: mean arrival delays and vulnerability ordering."""

from dataclasses import dataclass
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

from episwarm.population.build import PopulationSoA
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack, SeedingConfig
from episwarm.engine.sim import run_simulation


@dataclass
class SpreadMatrixResult:
    """Outcomes from spatial spread matrix evaluation."""
    area_names: List[str]
    mean_arrival_days: np.ndarray  # (n_areas, n_areas): entry (i, j) is arrival time in j when seeded at i
    hit_order: Dict[str, List[str]] # origin -> list of areas in order of first infection

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(
            self.mean_arrival_days,
            index=self.area_names,
            columns=self.area_names
        )


def compute_spread_matrix(
    pop: PopulationSoA,
    disease_pack: DiseasePack,
    base_scenario: ScenarioPack,
    n_seeds: int = 5,
    max_days: int = 60
) -> SpreadMatrixResult:
    """Seed each administrative area in turn over multiple random seeds to trace spatial contagion flow.

    Returns:
        SpreadMatrixResult: pairwise transmission delays and hit sequence.
    """
    n_areas = len(pop.int_to_area_id)
    area_names = [pop.int_to_area_id[i] for i in range(n_areas)]
    raw_arrivals = np.full((n_areas, n_areas, n_seeds), np.nan, dtype=np.float32)

    for i_origin in range(n_areas):
        origin_id = area_names[i_origin]

        for s_idx in range(n_seeds):
            # Configure scenario seeding at origin
            scen = base_scenario.model_copy(deep=True)
            scen.horizon_days = max_days
            scen.random_seed = base_scenario.random_seed + s_idx * 100 + i_origin
            scen.seeding = SeedingConfig(
                area_id=origin_id,
                seed_all_areas=False,
                initial_cases_per_area=20,
                seeded_state="I_symp"
            )

            # Run
            res = run_simulation(pop, disease_pack, scen)

            # Find day of first case in each area
            # daily_area_infections is (days, n_areas)
            for j_target in range(n_areas):
                if i_origin == j_target:
                    raw_arrivals[i_origin, j_target, s_idx] = 0.0
                else:
                    inf_days = np.where(res.daily_area_infections[:, j_target] > 0)[0]
                    if len(inf_days) > 0:
                        raw_arrivals[i_origin, j_target, s_idx] = float(inf_days[0])
                    else:
                        raw_arrivals[i_origin, j_target, s_idx] = float(max_days)

    mean_arrivals = np.nanmean(raw_arrivals, axis=2)

    # Compute vulnerability ordering per origin
    hit_order: Dict[str, List[str]] = {}
    for i in range(n_areas):
        origin = area_names[i]
        sorted_indices = np.argsort(mean_arrivals[i, :])
        hit_order[origin] = [area_names[idx] for idx in sorted_indices if idx != i]

    return SpreadMatrixResult(
        area_names=area_names,
        mean_arrival_days=mean_arrivals,
        hit_order=hit_order
    )
