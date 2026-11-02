"""Layered transmission engine utilizing numpy.bincount with Prem-style age-structured mixing (Spec 4.1 & 5.2)."""

from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
import pandas as pd

from episwarm.population.build import PopulationSoA
from episwarm.engine.state_graph import CompiledStateGraph


def compute_age_structured_layer_lambda(
    venue_assignments: np.ndarray,      # int32 array of venue IDs (-1 = not present)
    agent_loads: np.ndarray,            # float32 array of infectious loads
    agent_age_bands: np.ndarray,        # int8 array of age band indices (0..n_bands-1)
    M_layer: np.ndarray,                # (n_bands, n_bands) contact matrix for this layer
    beta: float,
    active_scaling: Union[float, np.ndarray] = 1.0,  # Intervention closure multiplier [0.0, 1.0] or per-agent array
    n_bands: int = 4
) -> np.ndarray:
    """Compute per-agent infection pressure lambda from a venue layer using Prem age-structured mixing (Spec 4.1).

    Uses numpy.bincount on (venue_id * n_bands + age_band) for O(N) vectorized aggregation.
    """
    if beta <= 0.0 or (isinstance(active_scaling, (int, float)) and active_scaling <= 0.0):
        return np.zeros(len(venue_assignments), dtype=np.float32)

    n_bands = M_layer.shape[0] if M_layer.size > 0 else n_bands
    valid_mask = (venue_assignments >= 0)
    if not np.any(valid_mask):
        return np.zeros(len(venue_assignments), dtype=np.float32)

    valid_venues = venue_assignments[valid_mask]
    valid_ages = agent_age_bands[valid_mask]
    valid_loads = agent_loads[valid_mask].astype(np.float64)

    max_vid = int(np.max(valid_venues))
    total_bins = (max_vid + 1) * n_bands

    combined_idx = valid_venues * n_bands + valid_ages

    # Aggregate counts and infectious loads per (venue, age_band)
    N_vb = np.bincount(combined_idx, minlength=total_bins).reshape((max_vid + 1, n_bands))
    I_vb = np.bincount(combined_idx, weights=valid_loads, minlength=total_bins).reshape((max_vid + 1, n_bands))

    safe_sizes = np.maximum(1, N_vb)
    prev_vb = I_vb / safe_sizes
    present_vb = (N_vb > 0)

    # c_l(a) = sum_b M^l[a, b]
    c_l = np.sum(M_layer, axis=1)

    # Precompute lambda table per venue and age band: shape (max_vid + 1, n_bands)
    lambda_table = np.zeros((max_vid + 1, n_bands), dtype=np.float32)

    for a in range(n_bands):
        # Contacts distributed over present age bands with weights proportional to M^l[a, b]
        W_v_a = present_vb * M_layer[a, :]
        sum_W = np.sum(W_v_a, axis=1, keepdims=True)
        safe_sum = np.maximum(1e-9, sum_W)
        norm_W = np.where(sum_W > 0, W_v_a / safe_sum, 0.0)

        # sum_b w_b * (I_{v, b} / N_{v, b})
        effective_exposure = np.sum(norm_W * prev_vb, axis=1)
        lambda_table[:, a] = (beta * c_l[a] * effective_exposure).astype(np.float32)

    agent_lambdas = np.zeros(len(venue_assignments), dtype=np.float32)
    raw_lambdas = lambda_table[valid_venues, valid_ages]
    if isinstance(active_scaling, np.ndarray):
        agent_lambdas[valid_mask] = raw_lambdas * active_scaling[valid_mask]
    else:
        agent_lambdas[valid_mask] = raw_lambdas * active_scaling
    return agent_lambdas


def compute_venue_layer_lambda_legacy(
    venue_assignments: np.ndarray,
    agent_infectious_load: np.ndarray,
    beta_layer: float,
    active_scaling: float = 1.0
) -> np.ndarray:
    """Legacy uniform-mixing venue infection pressure (labeled legacy per Phase 15)."""
    if beta_layer <= 0.0 or active_scaling <= 0.0:
        return np.zeros(len(venue_assignments), dtype=np.float32)

    valid_mask = (venue_assignments >= 0)
    if not np.any(valid_mask):
        return np.zeros(len(venue_assignments), dtype=np.float32)

    valid_venues = venue_assignments[valid_mask]
    max_vid = int(np.max(valid_venues))

    venue_sizes = np.bincount(valid_venues, minlength=max_vid + 1)
    valid_loads = agent_infectious_load[valid_mask].astype(np.float64)
    venue_loads = np.bincount(valid_venues, weights=valid_loads, minlength=max_vid + 1)

    safe_sizes = np.maximum(1, venue_sizes)
    venue_lambdas = (beta_layer * active_scaling) * (venue_loads / safe_sizes)

    agent_lambdas = np.zeros(len(venue_assignments), dtype=np.float32)
    agent_lambdas[valid_mask] = venue_lambdas[valid_venues].astype(np.float32)
    return agent_lambdas


def compute_community_layer_lambda_legacy(
    agent_areas: np.ndarray,
    agent_infectious_load: np.ndarray,
    beta_community: float,
    active_scaling: float = 1.0
) -> np.ndarray:
    """Legacy area-level community infection pressure."""
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
    layer_weights: Union[Dict[str, float], Dict[str, np.ndarray]],
    layer_scalings: Union[Dict[str, float], Dict[str, np.ndarray]],   # Active intervention multipliers (global or per-area)
    individual_infectiousness_k: np.ndarray, # Overdispersion gamma draws
    rng: np.random.Generator,
    susceptibility_multipliers: Optional[np.ndarray] = None,
    area_crowding_multipliers: Optional[np.ndarray] = None,
    agent_age_bands: Optional[np.ndarray] = None,
    legacy_uniform_mixing: bool = False,
    agent_masking: Optional[np.ndarray] = None,
    agent_vaccinated: Optional[np.ndarray] = None,
    agent_isolating: Optional[np.ndarray] = None,
    mask_inward_efficacy: float = 0.50,
    mask_outward_efficacy: float = 0.50,
    vaccine_efficacy_acquisition: float = 0.80,
    compliance_acquisition_reduction: float = 0.30,
    age_band_labels: Optional[List[str]] = None
) -> np.ndarray:
    """Determine which susceptible agents contract infection on the current simulation day (Spec 4.1, 5.1, 5.2)."""
    susceptible_mask = (current_states == state_graph.idx_S)
    if not np.any(susceptible_mask):
        return np.zeros(pop.n_agents, dtype=bool)

    # 1. Compute infectious load per agent: rel_infectiousness * individual_k * (1 - mask_outward_eff)
    agent_is_inf = state_graph.is_infectious[current_states]
    agent_loads = np.zeros(pop.n_agents, dtype=np.float32)
    base_load = (
        state_graph.rel_infectiousness[current_states[agent_is_inf]] *
        individual_infectiousness_k[agent_is_inf]
    )
    if agent_masking is not None:
        mask_out_factor = 1.0 - (mask_outward_efficacy * agent_masking[agent_is_inf].astype(np.float32))
        agent_loads[agent_is_inf] = base_load * mask_out_factor
    else:
        agent_loads[agent_is_inf] = base_load

    if not np.any(agent_is_inf):
        return np.zeros(pop.n_agents, dtype=bool)

    # 2. Derive agent age bands dynamically if not supplied
    if agent_age_bands is None:
        from episwarm.population.age_bands import assign_age_bands
        bands = age_band_labels or ["0-4", "5-18", "19-64", "65+"]
        agent_age_bands = assign_age_bands(pop.age, bands)

    # Resolve per-agent layer scalings from float or per-area arrays
    resolved_scalings: Dict[str, Union[float, np.ndarray]] = {}
    for l_key in ("home", "school", "work", "community"):
        val = layer_scalings.get(l_key, 1.0)
        if isinstance(val, np.ndarray):
            if len(val) == len(pop.int_to_area_id):
                resolved_scalings[l_key] = val[pop.area_id]
            else:
                resolved_scalings[l_key] = val
        else:
            resolved_scalings[l_key] = float(val)

    # Resolve effective venues with isolation
    effective_schools = np.copy(pop.school_id)
    effective_workplaces = np.copy(pop.workplace_id)
    effective_workplaces[pop.wfh_possible] = -1
    effective_comm = np.copy(pop.commute_area)

    if agent_isolating is not None:
        iso_b = agent_isolating.astype(bool)
        effective_schools[iso_b] = -1
        effective_workplaces[iso_b] = -1
        effective_comm[iso_b] = -1

    # Check whether matrices or legacy scalar weights are provided
    is_matrix_dict = isinstance(next(iter(layer_weights.values())), np.ndarray) and not legacy_uniform_mixing

    if is_matrix_dict:
        # Age-structured mixing per Spec 4.1
        M_home = layer_weights.get("home", np.eye(4) * 2.0)
        M_school = layer_weights.get("school", np.eye(4) * 2.0)
        M_work = layer_weights.get("work", np.eye(4) * 2.0)
        M_comm = layer_weights.get("community", layer_weights.get("comm", np.eye(4) * 2.0))

        lambda_home = compute_age_structured_layer_lambda(
            pop.household_id, agent_loads, agent_age_bands, M_home, beta,
            resolved_scalings.get("home", 1.0)
        )
        if area_crowding_multipliers is not None:
            lambda_home *= area_crowding_multipliers[pop.area_id]

        lambda_school = compute_age_structured_layer_lambda(
            effective_schools, agent_loads, agent_age_bands, M_school, beta,
            resolved_scalings.get("school", 1.0)
        )

        lambda_work = compute_age_structured_layer_lambda(
            effective_workplaces, agent_loads, agent_age_bands, M_work, beta,
            resolved_scalings.get("work", 1.0)
        )

        lambda_comm = compute_age_structured_layer_lambda(
            effective_comm, agent_loads, agent_age_bands, M_comm, beta,
            resolved_scalings.get("community", 1.0)
        )

    else:
        # Legacy uniform mixing mode
        lw = layer_weights  # type: ignore
        lambda_home = compute_venue_layer_lambda_legacy(
            pop.household_id, agent_loads, beta * float(lw.get("home", 0.35)),
            resolved_scalings.get("home", 1.0) if isinstance(resolved_scalings.get("home", 1.0), float) else 1.0
        )
        if area_crowding_multipliers is not None:
            lambda_home *= area_crowding_multipliers[pop.area_id]

        lambda_school = compute_venue_layer_lambda_legacy(
            effective_schools, agent_loads, beta * float(lw.get("school", 0.25)),
            resolved_scalings.get("school", 1.0) if isinstance(resolved_scalings.get("school", 1.0), float) else 1.0
        )

        lambda_work = compute_venue_layer_lambda_legacy(
            effective_workplaces, agent_loads, beta * float(lw.get("work", 0.25)),
            resolved_scalings.get("work", 1.0) if isinstance(resolved_scalings.get("work", 1.0), float) else 1.0
        )

        lambda_comm = compute_community_layer_lambda_legacy(
            effective_comm, agent_loads, beta * float(lw.get("community", 0.15)),
            resolved_scalings.get("community", 1.0) if isinstance(resolved_scalings.get("community", 1.0), float) else 1.0
        )

    # 3. Total lambda per susceptible agent
    total_lambda = lambda_home + lambda_school + lambda_work + lambda_comm

    # Individual behavioral compliance reduction
    compliance_factor = 1.0 - (compliance_acquisition_reduction * pop.compliance)
    effective_lambda = total_lambda * compliance_factor

    # Inward protections: mask wearing and vaccination
    inward_protection = np.ones(pop.n_agents, dtype=np.float32)
    if agent_masking is not None:
        inward_protection *= (1.0 - mask_inward_efficacy * agent_masking.astype(np.float32))
    if agent_vaccinated is not None:
        inward_protection *= (1.0 - vaccine_efficacy_acquisition * agent_vaccinated.astype(np.float32))

    effective_lambda *= inward_protection

    # Individual susceptibility multiplier (Spec 5.1 vulnerability factors)
    if susceptibility_multipliers is not None:
        effective_lambda *= susceptibility_multipliers

    # 4. Poisson transmission probability: P = 1 - exp(-lambda)
    p_infection = 1.0 - np.exp(-effective_lambda[susceptible_mask])

    # 5. Stochastic transmission trial
    random_draws = rng.random(size=int(np.sum(susceptible_mask)))
    infected_subset = random_draws < p_infection

    newly_exposed = np.zeros(pop.n_agents, dtype=bool)
    newly_exposed[susceptible_mask] = infected_subset
    return newly_exposed
