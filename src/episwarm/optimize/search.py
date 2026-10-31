"""Multi-objective policy optimization (Optuna NSGA-II) and discrete search."""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import optuna
import pandas as pd

from episwarm.population.build import PopulationSoA
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack, InterventionAction
from episwarm.engine.sim import run_simulation
from episwarm.analysis.metrics import evaluate_single_run_objectives, ObjectiveVector

# Suppress verbose Optuna logs
optuna.logging.set_verbosity(optuna.logging.WARNING)


def run_optuna_search(
    pop: PopulationSoA,
    disease_pack: DiseasePack,
    base_scenario: ScenarioPack,
    n_trials: int = 15
) -> pd.DataFrame:
    """Multi-objective policy search over start timing, duration, and stringency using NSGA-II.

    Objectives to minimize:
    1. Cumulative fatalities
    2. Peak ICU occupancy
    3. Economic cost proxy
    """
    def objective(trial: optuna.Trial) -> Tuple[float, float, float]:
        # Sample intervention levers
        school_start = trial.suggest_int("school_start", 5, 25)
        school_duration = trial.suggest_int("school_dur", 10, 30)
        school_stringency = trial.suggest_float("school_str", 0.3, 1.0)

        work_start = trial.suggest_int("work_start", 10, 30)
        work_duration = trial.suggest_int("work_dur", 10, 30)
        work_stringency = trial.suggest_float("work_str", 0.2, 0.8)

        scen = base_scenario.model_copy(deep=True)
        scen.interventions = [
            InterventionAction(
                name="school_closure",
                measure_type="school_closure",
                area_id="ALL",
                start_day=school_start,
                end_day=school_start + school_duration,
                stringency=school_stringency,
                cost_per_day=1.0
            ),
            InterventionAction(
                name="workplace_reduction",
                measure_type="workplace_reduction",
                area_id="ALL",
                start_day=work_start,
                end_day=work_start + work_duration,
                stringency=work_stringency,
                cost_per_day=2.5
            )
        ]

        res = run_simulation(pop, disease_pack, scen)
        objs = evaluate_single_run_objectives(pop, res, scen)
        return objs.cumulative_deaths, objs.peak_icu_occupancy, objs.economic_cost_proxy

    study = optuna.create_study(
        directions=["minimize", "minimize", "minimize"],
        sampler=optuna.samplers.NSGAIISampler(seed=42)
    )
    study.optimize(objective, n_trials=n_trials)

    # Extract Pareto front
    records = []
    for t in study.best_trials:
        records.append({
            "trial_id": t.number,
            "deaths": t.values[0],
            "peak_icu": t.values[1],
            "cost": t.values[2],
            "params": t.params
        })
    return pd.DataFrame(records)


def brute_force_best_policy(
    pop: PopulationSoA,
    disease_pack: DiseasePack,
    base_scenario: ScenarioPack,
    timing_options: List[int] = [7, 14],
    duration_options: List[int] = [14, 28]
) -> Dict[str, Any]:
    """Exhaustively evaluate all combinations on a discrete action space to find ground-truth optimum."""
    best_cost = float("inf")
    best_record: Dict[str, Any] = {}

    for start in timing_options:
        for dur in duration_options:
            scen = base_scenario.model_copy(deep=True)
            scen.interventions = [
                InterventionAction(
                    name="school_closure",
                    measure_type="school_closure",
                    area_id="ALL",
                    start_day=start,
                    end_day=start + dur,
                    stringency=1.0,
                    cost_per_day=1.0
                )
            ]
            res = run_simulation(pop, disease_pack, scen)
            objs = evaluate_single_run_objectives(pop, res, scen)

            # Combined objective score
            score = objs.cumulative_deaths * 10.0 + objs.economic_cost_proxy
            if score < best_cost:
                best_cost = score
                best_record = {
                    "start_day": start,
                    "duration": dur,
                    "deaths": objs.cumulative_deaths,
                    "cost": objs.economic_cost_proxy,
                    "score": round(score, 2)
                }

    return best_record
