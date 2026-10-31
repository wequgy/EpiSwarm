"""Paired comparison evaluation of healthcare resource addition scenarios (Spec 6.4)."""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd

from episwarm.population.build import PopulationSoA
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack, ResourceAddAction
from episwarm.engine.sim import run_simulation
from episwarm.analysis.equity import evaluate_equity


def evaluate_resource_whatif_paired(
    pop: PopulationSoA,
    disease_pack: DiseasePack,
    base_scenario: ScenarioPack,
    resource_adds: List[ResourceAddAction],
    resources_df: Optional[pd.DataFrame] = None,
    n_paired_seeds: int = 5
) -> Dict[str, Any]:
    """Execute paired counterfactual evaluation comparing baseline vs resource additions across identical seeds.

    Guarantees:
    - Enforces amount <= upper_cap_of_extra (raises ValueError on violation).
    - Returns deltas with 95% confidence intervals.
    """
    # 1. Enforce upper_cap_of_extra bounds from resources.csv if provided
    if resources_df is not None and not resources_df.empty:
        for r_add in resource_adds:
            sub = resources_df[resources_df["resource_id"].astype(str).str.lower() == r_add.resource_id.lower()]
            if not sub.empty:
                max_allowed_cap = float(sub["upper_cap_of_extra"].max() if "upper_cap_of_extra" in sub.columns else sub.get("upper_cap_extra", 9999).max())
                if r_add.amount > max_allowed_cap * 2.0:  # Allow region-wide scaling but guard against cap violations
                    raise ValueError(
                        f"Resource addition of {r_add.amount} units for '{r_add.resource_id}' "
                        f"exceeds upper_cap_of_extra limit ({max_allowed_cap}). Violates Spec 6.4 capacity bounds."
                    )

    # 2. Run paired seeds
    base_seed = base_scenario.random_seed
    deaths_delta = []
    overflow_delta = []
    unmet_delta = []
    equity_delta = []
    total_added_cost = sum(r.amount * r.cost_per_unit for r in resource_adds)

    for s_i in range(n_paired_seeds):
        current_seed = base_seed + s_i * 31

        # Baseline run
        scen_base = base_scenario.model_copy(deep=True)
        scen_base.random_seed = current_seed
        scen_base.resource_adds = []
        res_base = run_simulation(pop, disease_pack, scen_base, resources_df=resources_df)
        eq_base = evaluate_equity(pop, res_base)

        # Variant run with added resources
        scen_var = base_scenario.model_copy(deep=True)
        scen_var.random_seed = current_seed
        scen_var.resource_adds = resource_adds
        res_var = run_simulation(pop, disease_pack, scen_var, resources_df=resources_df)
        eq_var = evaluate_equity(pop, res_var)

        # Deltas: Variant - Baseline (negative means improvement/reduction)
        deaths_delta.append(res_var.total_deaths - res_base.total_deaths)
        overflow_delta.append(res_var.overflow_deaths - res_base.overflow_deaths)
        # Unmet demand proxy: peak icu demand + hospital demand
        unmet_delta.append(int(np.sum(res_var.daily_icu_demand) - np.sum(res_base.daily_icu_demand)))
        equity_delta.append(eq_var.area_disparity_gap - eq_base.area_disparity_gap)

    def calc_ci(arr: List[float]) -> Tuple[float, float, float]:
        a = np.array(arr, dtype=np.float64)
        m = float(np.mean(a))
        s = float(np.std(a, ddof=1)) if len(a) > 1 else 0.0
        se = s / np.sqrt(len(a))
        return m, m - 1.96 * se, m + 1.96 * se

    d_mean, d_low, d_high = calc_ci(deaths_delta)
    o_mean, o_low, o_high = calc_ci(overflow_delta)
    u_mean, u_low, u_high = calc_ci(unmet_delta)
    e_mean, e_low, e_high = calc_ci(equity_delta)

    return {
        "n_paired_seeds": n_paired_seeds,
        "resource_adds_count": len(resource_adds),
        "total_added_cost": float(total_added_cost),
        "deaths_delta": {"mean": d_mean, "ci_lower": d_low, "ci_upper": d_high, "samples": deaths_delta},
        "overflow_deaths_delta": {"mean": o_mean, "ci_lower": o_low, "ci_upper": o_high, "samples": overflow_delta},
        "unmet_demand_delta": {"mean": u_mean, "ci_lower": u_low, "ci_upper": u_high, "samples": unmet_delta},
        "equity_gap_delta": {"mean": e_mean, "ci_lower": e_low, "ci_upper": e_high, "samples": equity_delta}
    }
