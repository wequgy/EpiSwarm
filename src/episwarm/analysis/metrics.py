"""Multi-objective evaluation vector, economic cost proxies, and confidence intervals."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np

from episwarm.packs.scenario import ScenarioPack
from episwarm.engine.sim import SimulationResults
from episwarm.analysis.equity import evaluate_equity
from episwarm.population.build import PopulationSoA


@dataclass
class ObjectiveVector:
    """Quantitative performance vector across public health and economic dimensions."""
    cumulative_deaths: float
    peak_icu_occupancy: float
    days_icu_overflow: float
    unmet_hospital_demand: float
    economic_cost_proxy: float
    equity_disparity_gap: float


@dataclass
class MultiSeedMetricsReport:
    """Mean and 95% confidence intervals across multiple stochastic simulation seeds."""
    n_seeds: int
    mean_objectives: ObjectiveVector
    ci_lower: ObjectiveVector
    ci_upper: ObjectiveVector

    def summary(self) -> str:
        lines = [
            f"============== Multi-Seed Evaluation Report (N={self.n_seeds}) ==============",
            f"Cumulative Fatalities:   {self.mean_objectives.cumulative_deaths:.1f} (95% CI: [{self.ci_lower.cumulative_deaths:.1f}, {self.ci_upper.cumulative_deaths:.1f}])",
            f"Peak ICU Occupancy:      {self.mean_objectives.peak_icu_occupancy:.1f} beds (95% CI: [{self.ci_lower.peak_icu_occupancy:.1f}, {self.ci_upper.peak_icu_occupancy:.1f}])",
            f"ICU Overflow Days:       {self.mean_objectives.days_icu_overflow:.1f} days (95% CI: [{self.ci_lower.days_icu_overflow:.1f}, {self.ci_upper.days_icu_overflow:.1f}])",
            f"Economic Cost Proxy:     {self.mean_objectives.economic_cost_proxy:.1f} units (95% CI: [{self.ci_lower.economic_cost_proxy:.1f}, {self.ci_upper.economic_cost_proxy:.1f}])",
            f"Equity Disparity Gap:    {self.mean_objectives.equity_disparity_gap*100:.2f}% (95% CI: [{self.ci_lower.equity_disparity_gap*100:.2f}%, {self.ci_upper.equity_disparity_gap*100:.2f}%])",
            "=========================================================================="
        ]
        return "\n".join(lines)


def evaluate_single_run_objectives(
    pop: PopulationSoA,
    res: SimulationResults,
    scenario: ScenarioPack,
    icu_capacity_threshold: int = 25
) -> ObjectiveVector:
    """Compute the multi-dimensional objective vector for a single simulation result."""
    # 1. Fatalities
    deaths = float(res.total_deaths)

    # 2. Peak ICU and Overflow Days
    peak_icu = float(np.max(res.daily_icu_demand))
    overflow_days = float(np.sum(res.daily_icu_demand > icu_capacity_threshold))

    # 3. Unmet demand
    unmet = float(np.sum(np.maximum(0, res.daily_icu_demand - icu_capacity_threshold)))

    # 4. Economic cost proxy: sum of active intervention days * cost_per_day * stringency
    econ_cost = 0.0
    for iv in scenario.interventions:
        dur = max(0, iv.end_day - iv.start_day + 1)
        econ_cost += dur * iv.cost_per_day * iv.stringency

    # Lost productivity: agent days in severe illness or hospital
    hosp_days = float(np.sum(res.daily_hospital_demand))
    econ_cost += hosp_days * 0.1  # lost work proxy per hospital day

    # 5. Equity gap
    equity = evaluate_equity(pop, res)
    gap = equity.area_disparity_gap

    return ObjectiveVector(
        cumulative_deaths=deaths,
        peak_icu_occupancy=peak_icu,
        days_icu_overflow=overflow_days,
        unmet_hospital_demand=unmet,
        economic_cost_proxy=round(econ_cost, 2),
        equity_disparity_gap=gap
    )


def aggregate_multi_seed_metrics(
    objective_runs: List[ObjectiveVector]
) -> MultiSeedMetricsReport:
    """Calculate mean and bootstrap/normal 95% confidence intervals across seeds."""
    n = len(objective_runs)
    if n == 0:
        raise ValueError("Must provide at least 1 objective run")

    keys = [
        "cumulative_deaths", "peak_icu_occupancy", "days_icu_overflow",
        "unmet_hospital_demand", "economic_cost_proxy", "equity_disparity_gap"
    ]

    means: Dict[str, float] = {}
    ci_low: Dict[str, float] = {}
    ci_high: Dict[str, float] = {}

    for k in keys:
        vals = np.array([getattr(o, k) for o in objective_runs], dtype=np.float64)
        m = float(np.mean(vals))
        means[k] = m
        if n > 1:
            sem = float(np.std(vals, ddof=1) / np.sqrt(n))
            ci_low[k] = max(0.0, m - 1.96 * sem)
            ci_high[k] = m + 1.96 * sem
        else:
            ci_low[k] = m
            ci_high[k] = m

    return MultiSeedMetricsReport(
        n_seeds=n,
        mean_objectives=ObjectiveVector(**means),
        ci_lower=ObjectiveVector(**ci_low),
        ci_upper=ObjectiveVector(**ci_high)
    )
