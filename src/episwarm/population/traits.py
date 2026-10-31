"""Psychographic trait and comorbidity sampling for synthetic agents."""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd

from episwarm.packs.behavior import BehaviorPack, TraitDistribution


def sample_traits(
    n_agents: int,
    behavior_pack: Optional[BehaviorPack],
    rng: np.random.Generator
) -> Dict[str, np.ndarray]:
    """Sample continuous psychographic traits bounded in [0.0, 1.0]."""
    traits = {
        "compliance": np.full(n_agents, 0.70, dtype=np.float32),
        "rumor_susceptibility": np.full(n_agents, 0.30, dtype=np.float32),
        "risk_tolerance": np.full(n_agents, 0.40, dtype=np.float32),
        "institutional_trust": np.full(n_agents, 0.60, dtype=np.float32)
    }

    if behavior_pack is not None:
        for trait_name, dist in behavior_pack.traits.items():
            draws = rng.normal(dist.mean, dist.std, size=n_agents)
            traits[trait_name] = np.clip(draws, 0.0, 1.0).astype(np.float32)
    else:
        for t_name in traits:
            draws = rng.normal(traits[t_name][0], 0.15, size=n_agents)
            traits[t_name] = np.clip(draws, 0.0, 1.0).astype(np.float32)

    return traits


def assign_comorbidity_multipliers(
    agent_ages: np.ndarray,
    agent_sexes: np.ndarray,
    comorbidity_df: Optional[pd.DataFrame],
    rng: np.random.Generator
) -> np.ndarray:
    """Compute risk multipliers based on age, sex, and prevalence from comorbidity.csv.

    Returns:
        multipliers: float32 array where 1.0 = baseline healthy risk
    """
    n_agents = len(agent_ages)
    multipliers = np.ones(n_agents, dtype=np.float32)

    if comorbidity_df is None or comorbidity_df.empty:
        return multipliers

    # Map age into bands: 0-4, 5-18, 19-64, 65+
    age_bands = np.empty(n_agents, dtype=object)
    age_bands[agent_ages < 5] = "0-4"
    age_bands[(agent_ages >= 5) & (agent_ages <= 18)] = "5-18"
    age_bands[(agent_ages >= 19) & (agent_ages <= 64)] = "19-64"
    age_bands[agent_ages >= 65] = "65+"

    sex_map = {0: "M", 1: "F"}

    for _, row in comorbidity_df.iterrows():
        band = str(row["age_band"])
        c_sex = str(row["sex"]).upper()
        prev = float(row["prevalence"])

        mask = (age_bands == band)
        if c_sex in ("M", "F"):
            target_sex_code = 0 if c_sex == "M" else 1
            mask &= (agent_sexes == target_sex_code)

        matching_indices = np.where(mask)[0]
        if len(matching_indices) > 0:
            # Bernoulli draw according to prevalence
            has_condition = rng.random(size=len(matching_indices)) < prev
            affected = matching_indices[has_condition]
            # Sourced/Assumed condition penalty: +40% risk multiplier per chronic condition
            multipliers[affected] *= 1.40

    return multipliers
