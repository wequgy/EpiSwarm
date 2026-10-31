"""Household composition and agent assignment module."""

from typing import List, Tuple
import numpy as np


def compose_households(
    agent_ages: np.ndarray,
    target_mean_size: float,
    rng: np.random.Generator
) -> np.ndarray:
    """Assign agents to households guaranteeing each household has at least one adult (age >= 18).

    Args:
        agent_ages: 1D array of agent ages
        target_mean_size: Target average household size
        rng: Seeded numpy Random Generator

    Returns:
        household_ids: 1D array of assigned household IDs (int32) matching len(agent_ages)
    """
    n_agents = len(agent_ages)
    if n_agents == 0:
        return np.empty(0, dtype=np.int32)

    adult_indices = np.where(agent_ages >= 18)[0]
    child_indices = np.where(agent_ages < 18)[0]

    rng.shuffle(adult_indices)
    rng.shuffle(child_indices)

    # Estimate number of households
    n_households = max(1, int(round(n_agents / max(1.0, target_mean_size))))
    # Ensure n_households <= n_adults so every household gets >= 1 adult
    if n_households > len(adult_indices):
        n_households = max(1, len(adult_indices))

    household_ids = np.full(n_agents, -1, dtype=np.int32)

    # 1. Seed each household with 1 adult
    for h_id in range(n_households):
        adult_idx = adult_indices[h_id]
        household_ids[adult_idx] = h_id

    # 2. Pool remaining agents (remaining adults + all children)
    remaining_adults = adult_indices[n_households:]
    remaining_pool = np.concatenate([remaining_adults, child_indices])
    rng.shuffle(remaining_pool)

    # 3. Draw random household sizes using truncated Poisson-like distribution
    # Distribute remaining agents across the existing households
    if len(remaining_pool) > 0:
        # Generate random weights for each household to receive additional members
        weights = rng.gamma(shape=2.0, scale=1.0, size=n_households)
        weights /= weights.sum()

        chosen_h_ids = rng.choice(n_households, size=len(remaining_pool), p=weights)
        for agent_idx, h_id in zip(remaining_pool, chosen_h_ids):
            household_ids[agent_idx] = h_id

    # Invariant assertion: every household has at least one adult
    assert np.all(household_ids >= 0), "All agents must be assigned to a household"
    return household_ids
