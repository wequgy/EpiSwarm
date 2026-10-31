"""Layered transmission engine utilizing numpy.bincount for high-speed venue infection."""

from typing import Dict, Optional, Tuple
import numpy as np

from episwarm.population.build import PopulationSoA
from episwarm.engine.state_graph import CompiledStateGraph


def compute_venue_layer_lambda(
    venue_assignments: np.ndarray,      # int32 array of venue IDs (-1 = not present)
    agent_infectious_load: np.ndarray,  # float32 array of infectious loads
    beta_layer: float,
    active_scaling: float = 1.0         # Intervention closure multiplier [0.0, 1.0]
) -> np.ndarray:
    """Compute per-agent infection pressure lambda from a specific physical venue layer.

    Uses numpy.bincount for O(N) vectorized aggregation.
    """
    if beta_layer <= 0.0 or active_scaling <= 0.0:
        return np.zeros(len(venue_assignments), dtype=np.float32)

    valid_mask = (venue_assignments >= 0)
    if not np.any(valid_mask):
        return np.zeros(len(venue_assignments), dtype=np.float32)

    valid_venues = venue_assignments[valid_mask]
    max_vid = int(np.max(valid_venues))

    # 1. Calculate venue size (number of agents present)
    venue_sizes = np.bincount(valid_venues, minlength=max_vid + 1)

    # 2. Calculate infectious load per venue (sum of relative infectiousness)
    valid_loads = agent_infectious_load[valid_mask].astype(np.float64)
    venue_loads = np.bincount(valid_venues, weights=valid_loads, minlength=max_vid + 1)

    # 3. Venue force of infection: beta * scaling * (load / size)
    safe_sizes = np.maximum(1, venue_sizes)
    venue_lambdas = (beta_layer * active_scaling) * (venue_loads / safe_sizes)

    # 4. Map back to each agent
    agent_lambdas = np.zeros(len(venue_assignments), dtype=np.float32)
    agent_lambdas[valid_mask] = venue_lambdas[valid_venues].astype(np.float32)
    return agent_lambdas


def compute_community_layer_lambda(
    agent_areas: np.ndarray,            # int16 array of area locations
    agent_infectious_load: np.ndarray,  # float32 array of infectious loads
    beta_community: float,
    active_scaling: float = 1.0
) -> np.ndarray:
    """Compute area-level community infection pressure from mixing and mobility."""
    if beta_community <= 0.0 or active_scaling <= 0.0:
        return np.zeros(len(agent_areas), dtype=np.float32)

    max_aid = int(np.max(agent_areas))
    area_sizes = np.bincount(agent_areas, minlength=max_aid + 1)
    area_loads = np.bincount(agent_areas, weights=agent_infectious_load.astype(np.float64), minlength=max_aid + 1)

    safe_sizes = np.maximum(1, area_sizes)
    area_lambdas = (beta_community * active_scaling) * (area_loads / safe_sizes)

    return area_lambdas[agent_areas].astype(np.float32)


def evaluate_daily_infections(
    pop: PopulationSoA,
    state_graph: CompiledStateGraph,
    current_states: np.ndarray,         # int16 array of state indices
    beta: float,
    layer_weights: Dict[str, float],    # {"home": 0.35, "school": 0.25, "work": 0.25, "community": 0.15}
    layer_scalings: Dict[str, float],   # Active intervention multipliers
    individual_infectiousness_k: np.ndarray, # Overdispersion gamma draws
    rng: np.random.Generator
) -> np.ndarray:
    """Determine which susceptible agents contract infection on the current simulation day.

    Returns:
        newly_exposed_mask: Boolean array indicating new transmissions (S -> E)
    """
    susceptible_mask = (current_states == state_graph.idx_S)
    if not np.any(susceptible_mask):
        return np.zeros(pop.n_agents, dtype=bool)

    # 1. Compute infectious load per agent: rel_infectiousness * individual_k
    agent_is_inf = state_graph.is_infectious[current_states]
    agent_loads = np.zeros(pop.n_agents, dtype=np.float32)
    agent_loads[agent_is_inf] = (
        state_graph.rel_infectiousness[current_states[agent_is_inf]] *
        individual_infectiousness_k[agent_is_inf]
    )

    if not np.any(agent_is_inf):
        return np.zeros(pop.n_agents, dtype=bool)

    # 2. Accumulate transmission lambda across venue layers
    # Household layer
    lambda_home = compute_venue_layer_lambda(
        pop.household_id, agent_loads,
        beta * layer_weights.get("home", 0.35),
        layer_scalings.get("home", 1.0)
    )

    # School layer
    lambda_school = compute_venue_layer_lambda(
        pop.school_id, agent_loads,
        beta * layer_weights.get("school", 0.25),
        layer_scalings.get("school", 1.0)
    )

    # Workplace layer (accounting for WFH)
    effective_workplaces = np.copy(pop.workplace_id)
    # WFH workers have workplace nullified
    effective_workplaces[pop.wfh_possible] = -1
    lambda_work = compute_venue_layer_lambda(
        effective_workplaces, agent_loads,
        beta * layer_weights.get("work", 0.25),
        layer_scalings.get("work", 1.0)
    )

    # Community / Commute layer (uses commute destination area)
    lambda_comm = compute_community_layer_lambda(
        pop.commute_area, agent_loads,
        beta * layer_weights.get("community", 0.15),
        layer_scalings.get("community", 1.0)
    )

    # 3. Total lambda per susceptible agent
    total_lambda = lambda_home + lambda_school + lambda_work + lambda_comm

    # Individual behavioral compliance reduction (e.g. hygiene/masking reduces exposure probability)
    compliance_factor = 1.0 - (0.30 * pop.compliance)
    effective_lambda = total_lambda * compliance_factor

    # 4. Poisson transmission probability: P = 1 - exp(-lambda)
    p_infection = 1.0 - np.exp(-effective_lambda[susceptible_mask])

    # 5. Stochastic transmission trial
    random_draws = rng.random(size=int(np.sum(susceptible_mask)))
    infected_subset = random_draws < p_infection

    newly_exposed = np.zeros(pop.n_agents, dtype=bool)
    newly_exposed[susceptible_mask] = infected_subset
    return newly_exposed
