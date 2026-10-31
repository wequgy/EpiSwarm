"""Sensitivity analysis across epidemiological, capacity, and behavioral parameters."""

from typing import Dict, List, Tuple
import pandas as pd
import numpy as np

from episwarm.population.build import PopulationSoA
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.engine.sim import run_simulation
from episwarm.analysis.metrics import evaluate_single_run_objectives


def run_oat_sensitivity(
    pop: PopulationSoA,
    disease_pack: DiseasePack,
    base_scenario: ScenarioPack,
    param_variations: Dict[str, List[float]] = None
) -> pd.DataFrame:
    """One-at-a-time (OAT) sensitivity analysis across key parameters."""
    if param_variations is None:
        param_variations = {
            "r0": [1.8, 2.5, 3.2],
            "overflow_multiplier": [1.5, 2.5, 4.0],
            "compliance_scaling": [0.5, 1.0, 1.5]
        }

    records = []

    # Baseline run
    base_res = run_simulation(pop, disease_pack, base_scenario)
    base_objs = evaluate_single_run_objectives(pop, base_res, base_scenario)
    base_deaths = base_objs.cumulative_deaths

    records.append({
        "parameter": "baseline",
        "value": 1.0,
        "deaths": base_deaths,
        "delta_deaths": 0.0,
        "attack_rate": round(base_res.attack_rate * 100, 1)
    })

    # Vary R0
    for val in param_variations.get("r0", []):
        if val == (disease_pack.transmission.r0 or 2.5):
            continue
        d_mod = disease_pack.model_copy(deep=True)
        d_mod.transmission.r0 = val
        res = run_simulation(pop, d_mod, base_scenario)
        objs = evaluate_single_run_objectives(pop, res, base_scenario)
        records.append({
            "parameter": "r0",
            "value": val,
            "deaths": objs.cumulative_deaths,
            "delta_deaths": objs.cumulative_deaths - base_deaths,
            "attack_rate": round(res.attack_rate * 100, 1)
        })

    # Vary Overflow Multiplier
    for val in param_variations.get("overflow_multiplier", []):
        d_mod = disease_pack.model_copy(deep=True)
        d_mod.overflow.bed_unavailable_mortality_multiplier = val
        d_mod.overflow.icu_unavailable_mortality_multiplier = val * 1.5
        res = run_simulation(pop, d_mod, base_scenario)
        objs = evaluate_single_run_objectives(pop, res, base_scenario)
        records.append({
            "parameter": "overflow_multiplier",
            "value": val,
            "deaths": objs.cumulative_deaths,
            "delta_deaths": objs.cumulative_deaths - base_deaths,
            "attack_rate": round(res.attack_rate * 100, 1)
        })

    return pd.DataFrame(records)
