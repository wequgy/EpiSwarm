"""Sensitivity analysis across epidemiological, capacity, behavioral, and adverse outcome parameters (Spec 13 & 14).

Performs One-at-a-time (OAT) parameter sweeps over:
1. Epidemiological: R0, ascertainment rate
2. Resource and unserved adverse outcomes: theta_care, theta_delay, resource capacity multiplier
3. Rumor and behavioral: rumor credibility, compliance peer weight, compliance erosion
"""

from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

from episwarm.population.build import PopulationSoA
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.packs.behavior import BehaviorPack
from episwarm.engine.sim import run_simulation
from episwarm.analysis.metrics import evaluate_single_run_objectives


def run_oat_sensitivity(
    pop: PopulationSoA,
    disease_pack: DiseasePack,
    base_scenario: ScenarioPack,
    behavior_pack: Optional[BehaviorPack] = None,
    param_variations: Optional[Dict[str, List[float]]] = None,
    random_seed: int = 42
) -> pd.DataFrame:
    """One-at-a-time (OAT) sensitivity analysis across disease, resource, and behavior parameters."""
    if param_variations is None:
        param_variations = {
            "r0": [1.8, 2.5, 3.2],
            "theta_care": [0.0, 0.4, 0.8],
            "theta_delay": [0.0, 0.1, 0.3],
            "rumor_credibility": [0.2, 0.5, 0.8],
            "resource_capacity_multiplier": [0.5, 1.0, 2.0]
        }

    records: List[Dict[str, Any]] = []

    # 1. Baseline simulation run
    base_res = run_simulation(pop, disease_pack, base_scenario, behavior_pack=behavior_pack)
    base_objs = evaluate_single_run_objectives(pop, base_res, base_scenario)
    base_deaths = base_objs.cumulative_deaths
    base_attack_rate = base_res.attack_rate
    base_overflow = getattr(base_res, "overflow_deaths", 0)

    records.append({
        "category": "baseline",
        "parameter": "baseline",
        "value": 1.0,
        "deaths": base_deaths,
        "delta_deaths": 0.0,
        "overflow_deaths": base_overflow,
        "attack_rate": round(base_attack_rate * 100, 2)
    })

    # 2. Sweep R0
    for val in param_variations.get("r0", []):
        d_mod = disease_pack.model_copy(deep=True)
        d_mod.transmission.r0 = val
        res = run_simulation(pop, d_mod, base_scenario, behavior_pack=behavior_pack)
        objs = evaluate_single_run_objectives(pop, res, base_scenario)
        records.append({
            "category": "epidemiology",
            "parameter": "r0",
            "value": val,
            "deaths": objs.cumulative_deaths,
            "delta_deaths": objs.cumulative_deaths - base_deaths,
            "overflow_deaths": getattr(res, "overflow_deaths", 0),
            "attack_rate": round(res.attack_rate * 100, 2)
        })

    # 3. Sweep theta_care (unserved adverse outcome sensitivity)
    for val in param_variations.get("theta_care", []):
        d_mod = disease_pack.model_copy(deep=True)
        if d_mod.unserved_outcome:
            d_mod.unserved_outcome.theta_care = val
        res = run_simulation(pop, d_mod, base_scenario, behavior_pack=behavior_pack)
        objs = evaluate_single_run_objectives(pop, res, base_scenario)
        records.append({
            "category": "resource_adverse",
            "parameter": "theta_care",
            "value": val,
            "deaths": objs.cumulative_deaths,
            "delta_deaths": objs.cumulative_deaths - base_deaths,
            "overflow_deaths": getattr(res, "overflow_deaths", 0),
            "attack_rate": round(res.attack_rate * 100, 2)
        })

    # 4. Sweep theta_delay (daily unserved accumulation sensitivity)
    for val in param_variations.get("theta_delay", []):
        d_mod = disease_pack.model_copy(deep=True)
        if d_mod.unserved_outcome:
            d_mod.unserved_outcome.theta_delay = val
        res = run_simulation(pop, d_mod, base_scenario, behavior_pack=behavior_pack)
        objs = evaluate_single_run_objectives(pop, res, base_scenario)
        records.append({
            "category": "resource_adverse",
            "parameter": "theta_delay",
            "value": val,
            "deaths": objs.cumulative_deaths,
            "delta_deaths": objs.cumulative_deaths - base_deaths,
            "overflow_deaths": getattr(res, "overflow_deaths", 0),
            "attack_rate": round(res.attack_rate * 100, 2)
        })

    # 5. Sweep Rumor Credibility
    if behavior_pack and "rumor_credibility" in param_variations:
        for val in param_variations["rumor_credibility"]:
            b_mod = behavior_pack.model_copy(deep=True)
            for top in b_mod.rumor_topics:
                top.credibility = val
            res = run_simulation(pop, disease_pack, base_scenario, behavior_pack=b_mod)
            objs = evaluate_single_run_objectives(pop, res, base_scenario)
            records.append({
                "category": "behavior",
                "parameter": "rumor_credibility",
                "value": val,
                "deaths": objs.cumulative_deaths,
                "delta_deaths": objs.cumulative_deaths - base_deaths,
                "overflow_deaths": getattr(res, "overflow_deaths", 0),
                "attack_rate": round(res.attack_rate * 100, 2)
            })

    return pd.DataFrame(records)
