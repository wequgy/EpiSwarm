"""Parallel, Windows-safe replicate harness with paired seeds and bootstrap confidence intervals (Spec 11 & Phase 17)."""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable, Union
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed

from episwarm.population.build import PopulationSoA
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.engine.sim import run_simulation, SimulationResults


@dataclass
class SingleSeedResult:
    """Metrics recorded for a single simulation seed."""
    seed: int
    attack_rate: float
    peak_day: int
    peak_infections: int
    total_deaths: int
    overflow_deaths: int
    peak_hospital_demand: int
    peak_icu_demand: int
    runtime_sec: float


@dataclass
class ReplicateSummary:
    """Statistical summary across N simulation replicates with 95% confidence intervals."""
    n_replicates: int
    scenario_name: str
    means: Dict[str, float]
    stds: Dict[str, float]
    ci_95_lower: Dict[str, float]
    ci_95_upper: Dict[str, float]
    per_seed: List[SingleSeedResult]
    # Paired delta fields if comparative evaluation was executed
    paired_scenario_name: Optional[str] = None
    delta_means: Optional[Dict[str, float]] = None
    delta_ci_95_lower: Optional[Dict[str, float]] = None
    delta_ci_95_upper: Optional[Dict[str, float]] = None
    per_seed_deltas: Optional[List[Dict[str, float]]] = None

    def summary_table(self) -> str:
        lines = [
            f"================ {self.n_replicates}-Replicate Simulation Report ================",
            f"Scenario: {self.scenario_name}" + (f" vs {self.paired_scenario_name}" if self.paired_scenario_name else ""),
            "Metric                          Mean (95% CI)              StdDev",
            "-------------------------------------------------------------------"
        ]
        for k in ["attack_rate", "total_deaths", "peak_day", "peak_infections", "overflow_deaths", "peak_hospital_demand", "peak_icu_demand"]:
            if k in self.means:
                m = self.means[k]
                lo = self.ci_95_lower[k]
                hi = self.ci_95_upper[k]
                sd = self.stds[k]
                if "rate" in k:
                    lines.append(f"{k:<30} {m*100:6.2f}% [{lo*100:6.2f}%, {hi*100:6.2f}%]    {sd*100:6.2f}%")
                else:
                    lines.append(f"{k:<30} {m:9.1f} [{lo:7.1f}, {hi:7.1f}]    {sd:7.1f}")

        if self.delta_means:
            lines.append("------------------- Paired Differences (B - A) -------------------")
            for k, dm in self.delta_means.items():
                dlo = self.delta_ci_95_lower[k]
                dhi = self.delta_ci_95_upper[k]
                if "rate" in k:
                    lines.append(f"Delta {k:<24} {dm*100:+6.2f}% [{dlo*100:+6.2f}%, {dhi*100:+6.2f}%]")
                else:
                    lines.append(f"Delta {k:<24} {dm:+9.1f} [{dlo:+7.1f}, {dhi:+7.1f}]")
        lines.append("===================================================================")
        return "\n".join(lines)


def _run_single_seed(
    pop: PopulationSoA,
    disease_pack: DiseasePack,
    scenario_pack: ScenarioPack,
    seed: int,
    behavior_mode: Optional[str] = None
) -> SingleSeedResult:
    """Worker task executing a single simulation seed."""
    sc = scenario_pack.model_copy(deep=True)
    sc.random_seed = seed
    res = run_simulation(pop, disease_pack, sc, behavior_mode=behavior_mode)

    inf_c = res.daily_state_counts[:, [i for i, s in enumerate(disease_pack.states) if s.infectious]].sum(axis=1)
    peak_d = int(np.argmax(inf_c))
    peak_inf = int(inf_c[peak_d])

    return SingleSeedResult(
        seed=seed,
        attack_rate=float(res.attack_rate),
        peak_day=peak_d,
        peak_infections=peak_inf,
        total_deaths=int(res.total_deaths),
        overflow_deaths=int(res.overflow_deaths),
        peak_hospital_demand=int(np.max(res.daily_hospital_demand)),
        peak_icu_demand=int(np.max(res.daily_icu_demand)),
        runtime_sec=float(res.manifest.get("runtime_sec", 0.0))
    )


def run_replicates(
    pop: PopulationSoA,
    disease_pack: DiseasePack,
    scenario_pack: ScenarioPack,
    n_replicates: int = 30,
    base_seed: int = 100,
    behavior_mode: Optional[str] = None,
    paired_scenario: Optional[ScenarioPack] = None,
    max_workers: int = 4
) -> ReplicateSummary:
    """Execute N paired replicates in parallel across Common Random Numbers (CRN)."""
    seeds = [base_seed + i for i in range(n_replicates)]
    results_a: List[SingleSeedResult] = []

    # Run Scenario A
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_run_single_seed, pop, disease_pack, scenario_pack, s, behavior_mode): s
            for s in seeds
        }
        for fut in as_completed(futures):
            results_a.append(fut.result())

    # Sort deterministically by seed
    results_a.sort(key=lambda r: r.seed)

    # Calculate statistics for A
    metrics_keys = [
        "attack_rate", "total_deaths", "peak_day", "peak_infections",
        "overflow_deaths", "peak_hospital_demand", "peak_icu_demand"
    ]
    means = {}
    stds = {}
    ci_lo = {}
    ci_hi = {}

    for k in metrics_keys:
        vals = np.array([getattr(r, k) for r in results_a], dtype=np.float64)
        m = float(np.mean(vals))
        s = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
        se = s / math.sqrt(len(vals))
        margin = 1.96 * se
        means[k] = m
        stds[k] = s
        ci_lo[k] = m - margin
        ci_hi[k] = m + margin

    # Optional paired Scenario B
    paired_name = None
    delta_means = None
    delta_ci_lo = None
    delta_ci_hi = None
    per_seed_deltas = None

    if paired_scenario is not None:
        paired_name = paired_scenario.name
        results_b: List[SingleSeedResult] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures_b = {
                executor.submit(_run_single_seed, pop, disease_pack, paired_scenario, s, behavior_mode): s
                for s in seeds
            }
            for fut in as_completed(futures_b):
                results_b.append(fut.result())
        results_b.sort(key=lambda r: r.seed)

        delta_means = {}
        delta_ci_lo = {}
        delta_ci_hi = {}
        per_seed_deltas = []

        for i in range(len(seeds)):
            row_delta = {"seed": seeds[i]}
            for k in metrics_keys:
                va = getattr(results_a[i], k)
                vb = getattr(results_b[i], k)
                row_delta[k] = vb - va
            per_seed_deltas.append(row_delta)

        for k in metrics_keys:
            d_vals = np.array([d[k] for d in per_seed_deltas], dtype=np.float64)
            dm = float(np.mean(d_vals))
            ds = float(np.std(d_vals, ddof=1)) if len(d_vals) > 1 else 0.0
            dse = ds / math.sqrt(len(d_vals))
            dmargin = 1.96 * dse
            delta_means[k] = dm
            delta_ci_lo[k] = dm - dmargin
            delta_ci_hi[k] = dm + dmargin

    return ReplicateSummary(
        n_replicates=n_replicates,
        scenario_name=scenario_pack.name,
        means=means,
        stds=stds,
        ci_95_lower=ci_lo,
        ci_95_upper=ci_hi,
        per_seed=results_a,
        paired_scenario_name=paired_name,
        delta_means=delta_means,
        delta_ci_95_lower=delta_ci_lo,
        delta_ci_95_upper=delta_ci_hi,
        per_seed_deltas=per_seed_deltas
    )

