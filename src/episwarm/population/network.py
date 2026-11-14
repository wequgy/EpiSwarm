"""Explicit persistent contact network and edge transmission engine (Stage A2).

Provides:
1. ContactNetwork dataclass storing explicit contiguous NumPy edge arrays:
   - edge_u, edge_v: int32 agent endpoint indices
   - edge_weight: float32 contact frequency / transmission weight
   - edge_layer: int8 layer identifier (0=home, 1=school, 2=work, 3=community)
2. Network generation from PopulationSoA venues with degree controls and persistent social ties.
3. Calendar schedule engine:
   - Weekday vs weekend contact shifts (schools/offices closed or reduced; home/community increased)
   - Term time vs school holiday calendar schedules
4. Vectorized edge-based transmission pressure using np.bincount for O(|E|) scaling.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from episwarm.population.build import PopulationSoA


LAYER_HOME = 0
LAYER_SCHOOL = 1
LAYER_WORK = 2
LAYER_COMMUNITY = 3

LAYER_NAMES = {
    LAYER_HOME: "home",
    LAYER_SCHOOL: "school",
    LAYER_WORK: "work",
    LAYER_COMMUNITY: "community"
}

LAYER_TO_INT = {v: k for k, v in LAYER_NAMES.items()}


@dataclass
class CalendarSchedule:
    """Calendar rules governing temporal shifts in layer activity."""
    start_date: str = "2020-03-01"
    weekend_days: Tuple[int, ...] = (5, 6)  # Saturday=5, Sunday=6 (assuming Day 0=Sunday for 2020-03-01: 2020-03-01 was Sunday)
    school_holiday_intervals: Tuple[Tuple[int, int], ...] = ((35, 49),)  # e.g., Easter holidays
    weekend_work_fraction: float = 0.20
    weekend_school_multiplier: float = 0.0
    weekend_home_multiplier: float = 1.30
    weekend_community_multiplier: float = 1.25

    def get_layer_multipliers(self, sim_day: int) -> Dict[int, float]:
        """Compute layer transmission multipliers for a given simulation day."""
        # Calculate day of week (0..6)
        day_of_week = (sim_day) % 7
        is_weekend = (day_of_week in (0, 6)) if self.start_date.startswith("2020-03-01") else (day_of_week in self.weekend_days)

        is_school_holiday = any(start <= sim_day <= end for start, end in self.school_holiday_intervals)

        mults = {
            LAYER_HOME: 1.0,
            LAYER_SCHOOL: 1.0,
            LAYER_WORK: 1.0,
            LAYER_COMMUNITY: 1.0
        }

        if is_weekend:
            mults[LAYER_HOME] *= self.weekend_home_multiplier
            mults[LAYER_COMMUNITY] *= self.weekend_community_multiplier
            mults[LAYER_WORK] *= self.weekend_work_fraction
            mults[LAYER_SCHOOL] *= self.weekend_school_multiplier
        elif is_school_holiday:
            mults[LAYER_SCHOOL] = 0.0
            mults[LAYER_HOME] *= 1.15
            mults[LAYER_COMMUNITY] *= 1.10

        return mults


@dataclass
class ContactNetwork:
    """Structure-of-Arrays persistent contact network representation."""
    n_agents: int
    edge_u: np.ndarray        # int32 array of source agent indices
    edge_v: np.ndarray        # int32 array of target agent indices
    edge_weight: np.ndarray   # float32 array of edge contact weights
    edge_layer: np.ndarray    # int8 array of layer IDs (0=home, 1=school, 2=work, 3=community)

    @property
    def n_edges(self) -> int:
        return len(self.edge_u)

    def filter_active_edges(self, active_layers: Optional[List[int]] = None) -> "ContactNetwork":
        if active_layers is None:
            return self
        mask = np.isin(self.edge_layer, active_layers)
        return ContactNetwork(
            n_agents=self.n_agents,
            edge_u=self.edge_u[mask],
            edge_v=self.edge_v[mask],
            edge_weight=self.edge_weight[mask],
            edge_layer=self.edge_layer[mask]
        )


def build_household_edges(pop: PopulationSoA) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate all-to-all undirected edges within each household."""
    valid_mask = pop.household_id >= 0
    valid_agents = np.where(valid_mask)[0].astype(np.int32)
    valid_hh = pop.household_id[valid_mask]

    sort_order = np.argsort(valid_hh)
    sorted_agents = valid_agents[sort_order]
    sorted_hh = valid_hh[sort_order]

    unique_hh, hh_indices, hh_counts = np.unique(sorted_hh, return_index=True, return_counts=True)

    u_list, v_list = [], []
    for idx, count in zip(hh_indices, hh_counts):
        if count > 1:
            members = sorted_agents[idx : idx + count]
            for i in range(count):
                for j in range(i + 1, count):
                    a1, a2 = members[i], members[j]
                    u_list.append(min(a1, a2))
                    v_list.append(max(a1, a2))

    if not u_list:
        return np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.float32)

    edge_u = np.array(u_list, dtype=np.int32)
    edge_v = np.array(v_list, dtype=np.int32)
    # Household contact weight normalized by household size
    edge_w = np.ones(len(edge_u), dtype=np.float32) * 1.5
    return edge_u, edge_v, edge_w


def build_venue_edges(
    venue_assignments: np.ndarray,
    max_degree: int = 15,
    layer_weight: float = 1.0,
    rng: Optional[np.random.Generator] = None
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate persistent contact edges within venues bounded by maximum degree."""
    if rng is None:
        rng = np.random.default_rng(42)

    valid_mask = venue_assignments >= 0
    valid_agents = np.where(valid_mask)[0].astype(np.int32)
    valid_venues = venue_assignments[valid_mask]

    if len(valid_agents) == 0:
        return np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.float32)

    sort_order = np.argsort(valid_venues)
    sorted_agents = valid_agents[sort_order]
    sorted_v = valid_venues[sort_order]

    unique_v, v_indices, v_counts = np.unique(sorted_v, return_index=True, return_counts=True)

    u_list, v_list = [], []
    for idx, count in zip(v_indices, v_counts):
        if count <= 1:
            continue
        members = sorted_agents[idx : idx + count]
        if count <= max_degree:
            # Full clique for small groups
            for i in range(count):
                for j in range(i + 1, count):
                    a1, a2 = members[i], members[j]
                    u_list.append(min(a1, a2))
                    v_list.append(max(a1, a2))
        else:
            # Regular ring lattice bounded by max_degree
            k_half = max(1, max_degree // 2)
            for i in range(count):
                for step in range(1, k_half + 1):
                    j = (i + step) % count
                    if i != j:
                        a1, a2 = members[i], members[j]
                        if a1 < a2:
                            u_list.append(a1)
                            v_list.append(a2)

    if not u_list:
        return np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.float32)

    edge_u = np.array(u_list, dtype=np.int32)
    edge_v = np.array(v_list, dtype=np.int32)
    edge_w = np.ones(len(edge_u), dtype=np.float32) * float(layer_weight)
    return edge_u, edge_v, edge_w


def build_persistent_contact_network(
    pop: PopulationSoA,
    max_school_degree: int = 12,
    max_work_degree: int = 10,
    max_community_degree: int = 8,
    random_seed: int = 42
) -> ContactNetwork:
    """Build unified multi-layer ContactNetwork for a population."""
    rng = np.random.default_rng(random_seed)

    # 1. Household edges (clique)
    hh_u, hh_v, hh_w = build_household_edges(pop)
    hh_layer = np.full(len(hh_u), LAYER_HOME, dtype=np.int8)

    # 2. School edges
    sc_u, sc_v, sc_w = build_venue_edges(pop.school_id, max_degree=max_school_degree, layer_weight=1.0, rng=rng)
    sc_layer = np.full(len(sc_u), LAYER_SCHOOL, dtype=np.int8)

    # 3. Work edges
    wk_u, wk_v, wk_w = build_venue_edges(pop.workplace_id, max_degree=max_work_degree, layer_weight=1.0, rng=rng)
    wk_layer = np.full(len(wk_u), LAYER_WORK, dtype=np.int8)

    # 4. Community persistent edges (preferred leisure / social ties)
    cm_venues = np.copy(pop.pref_leisure_id) if hasattr(pop, "pref_leisure_id") else np.copy(pop.commute_area)
    cm_u, cm_v, cm_w = build_venue_edges(cm_venues, max_degree=max_community_degree, layer_weight=0.8, rng=rng)
    cm_layer = np.full(len(cm_u), LAYER_COMMUNITY, dtype=np.int8)

    all_u = np.concatenate([hh_u, sc_u, wk_u, cm_u])
    all_v = np.concatenate([hh_v, sc_v, wk_v, cm_v])
    all_w = np.concatenate([hh_w, sc_w, wk_w, cm_w])
    all_layers = np.concatenate([hh_layer, sc_layer, wk_layer, cm_layer])

    return ContactNetwork(
        n_agents=pop.n_agents,
        edge_u=all_u,
        edge_v=all_v,
        edge_weight=all_w,
        edge_layer=all_layers
    )


def compute_network_edge_lambda(
    network: ContactNetwork,
    agent_loads: np.ndarray,            # float32 array of infectious loads
    beta: float,
    layer_scalings: Optional[Dict[str, Union[float, np.ndarray]]] = None,
    calendar_multipliers: Optional[Dict[int, float]] = None,
    agent_areas: Optional[np.ndarray] = None
) -> np.ndarray:
    """Compute per-agent infection pressure lambda vectorially over explicit network edges.

    Uses numpy.bincount across edge endpoints in O(|E|) time.
    Transmission on edge (u, v):
    lambda_{u -> v} = beta * edge_weight * load_u * layer_scaling * calendar_multiplier
    """
    if beta <= 0.0 or network.n_edges == 0:
        return np.zeros(network.n_agents, dtype=np.float32)

    # Layer scaling factors per layer type
    base_scalings = {
        LAYER_HOME: 1.0,
        LAYER_SCHOOL: 1.0,
        LAYER_WORK: 1.0,
        LAYER_COMMUNITY: 1.0
    }
    if layer_scalings:
        for k, v in layer_scalings.items():
            l_int = LAYER_TO_INT.get(k)
            if l_int is not None and isinstance(v, (int, float)):
                base_scalings[l_int] = float(v)

    if calendar_multipliers:
        for l_int, mult in calendar_multipliers.items():
            if l_int in base_scalings:
                base_scalings[l_int] *= mult

    # Map layer multipliers to each edge
    edge_layer_factors = np.array([base_scalings.get(int(l), 1.0) for l in range(4)], dtype=np.float32)
    factors_per_edge = edge_layer_factors[network.edge_layer]

    # Effective edge weights
    eff_edge_weights = network.edge_weight * factors_per_edge * beta

    u = network.edge_u
    v = network.edge_v

    # Edge transmission: u transmits to v
    loads_u = agent_loads[u]
    pressure_u_to_v = eff_edge_weights * loads_u

    # Edge transmission: v transmits to u (undirected contact graph)
    loads_v = agent_loads[v]
    pressure_v_to_u = eff_edge_weights * loads_v

    # Vectorized accumulation using np.bincount
    total_lambda = np.zeros(network.n_agents, dtype=np.float32)
    lambda_received_at_v = np.bincount(v, weights=pressure_u_to_v, minlength=network.n_agents).astype(np.float32)
    lambda_received_at_u = np.bincount(u, weights=pressure_v_to_u, minlength=network.n_agents).astype(np.float32)

    total_lambda = lambda_received_at_v + lambda_received_at_u
    return total_lambda
