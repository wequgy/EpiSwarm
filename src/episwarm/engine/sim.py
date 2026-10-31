"""Simulation engine stepping through epidemic progression day by day (Spec 5, 6 & 9)."""

import time
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd

from episwarm.population.build import PopulationSoA
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack, InterventionAction, ResourceAddAction
from episwarm.engine.state_graph import CompiledStateGraph
from episwarm.engine.infection import evaluate_daily_infections
from episwarm.engine.contacts import parse_contact_matrix, analytical_beta_from_r0
from episwarm.engine.resources import RegionalResourceSystem


@dataclass
class SimulationResults:
    """Outcomes and time-series telemetry from a simulation run."""
    run_id: str
    scenario_name: str
    disease_name: str
    horizon_days: int
    n_agents: int
    sampling_ratio: float
    calibrated_beta: float
    target_r0: float
    empirical_r0: float

    # Time-series aggregates (days x n_states)
    daily_state_counts: np.ndarray
    state_names: List[str]

    # Daily area incident cases (days x n_areas)
    daily_area_infections: np.ndarray

    # Daily healthcare metrics
    daily_hospital_demand: np.ndarray
    daily_icu_demand: np.ndarray

    # Final summary statistics
    total_infections: int
    total_deaths: int
    attack_rate: float
    overflow_deaths: int = 0
    daily_unmet_demand: Dict[str, int] = field(default_factory=dict)
    manifest: Dict[str, Any] = field(default_factory=dict)

    def summary_table(self) -> str:
        lines = [
            "================ Simulation Outcome Summary ================",
            f"Scenario:             {self.scenario_name}",
            f"Pathogen:             {self.disease_name}",
            f"Simulated Days:       {self.horizon_days}",
            f"Total Agents:         {self.n_agents:,} (Represents {int(self.n_agents * self.sampling_ratio):,} persons)",
            f"Target R0:            {self.target_r0:.2f} | Calibrated Beta: {self.calibrated_beta:.4f} (Empirical R0: {self.empirical_r0:.2f})",
            f"Total Infections:     {self.total_infections:,} ({self.attack_rate*100:.1f}% Attack Rate)",
            f"Cumulative Fatalities:{self.total_deaths:,} ({self.total_deaths / max(1, self.total_infections)*100:.2f}% CFR)",
            f"Overflow Deaths:      {self.overflow_deaths:,}",
            f"Peak Hospital Demand: {int(np.max(self.daily_hospital_demand)):,} beds",
            f"Peak ICU Demand:      {int(np.max(self.daily_icu_demand)):,} beds",
            "============================================================"
        ]
        return "\n".join(lines)


def calibrate_beta_numerical(
    pop: PopulationSoA,
    state_graph: CompiledStateGraph,
    initial_beta: float,
    target_r0: float,
    layer_weights: Dict[str, float],
    rng: np.random.Generator,
    trials: int = 50
) -> Tuple[float, float]:
    """Numerically calibrate beta so a single seeded case in a fully susceptible population produces target R0 on average."""
    current_beta = initial_beta
    best_beta = current_beta
    best_err = float("inf")
    measured_r0 = target_r0

    for iteration in range(3):
        secondary_counts = []
        for _ in range(trials):
            states = np.full(pop.n_agents, state_graph.idx_S, dtype=np.int16)
            index_agent = rng.integers(0, pop.n_agents)
            states[index_agent] = state_graph.name_to_idx.get("I_symp", 1)

            k_draws = rng.gamma(shape=state_graph.pack.transmission.overdispersion_k, scale=1.0, size=pop.n_agents)
            k_draws /= max(1e-6, np.mean(k_draws))

            total_secondaries = 0
            inf_days = int(round(state_graph.mean_infectious_days))
            for _ in range(inf_days):
                new_inf = evaluate_daily_infections(
                    pop, state_graph, states, current_beta,
                    layer_weights, {"home": 1.0, "school": 1.0, "work": 1.0, "community": 1.0},
                    k_draws, rng
                )
                total_secondaries += int(np.sum(new_inf))
                states[new_inf] = state_graph.idx_S

            secondary_counts.append(total_secondaries)

        measured_r0 = float(np.mean(secondary_counts))
        err = abs(measured_r0 - target_r0)
        if err < best_err:
            best_err = err
            best_beta = current_beta

        if measured_r0 > 0.01:
            current_beta = current_beta * (target_r0 / measured_r0)
        else:
            current_beta *= 1.5

    return best_beta, measured_r0


def run_simulation(
    pop: PopulationSoA,
    disease_pack: DiseasePack,
    scenario_pack: ScenarioPack,
    contacts_df: Optional[pd.DataFrame] = None,
    layer_weights: Optional[Dict[str, float]] = None,
    resources_df: Optional[pd.DataFrame] = None,
    environment_df: Optional[pd.DataFrame] = None,
    areas_df: Optional[pd.DataFrame] = None
) -> SimulationResults:
    """Execute complete multi-day epidemic simulation with generic resources and vulnerability factors."""
    rng = np.random.default_rng(scenario_pack.random_seed)
    age_bands = ["0-4", "5-18", "19-64", "65+"]
    state_graph = CompiledStateGraph(disease_pack, age_bands)

    if layer_weights is None:
        layer_weights = {"home": 0.35, "school": 0.25, "work": 0.25, "community": 0.15}

    # 1. Contact matrix & beta calibration
    if contacts_df is not None:
        c_matrix = parse_contact_matrix(contacts_df, age_bands)
    else:
        c_matrix = np.eye(4) * 5.0

    target_r0 = disease_pack.transmission.r0 or 2.5
    init_beta, upsilon = analytical_beta_from_r0(target_r0, state_graph.mean_infectious_days, c_matrix)
    calib_beta, empirical_r0 = calibrate_beta_numerical(pop, state_graph, init_beta, target_r0, layer_weights, rng)

    # 2. Disease-specific vulnerability factors (Spec 5.1)
    susceptibility_mult = np.ones(pop.n_agents, dtype=np.float32)
    severity_odds = np.ones(pop.n_agents, dtype=np.float32)

    for f_idx, vf in enumerate(disease_pack.vulnerability_factors):
        bit = 1 << f_idx
        has_bit = (pop.risk_factor_bits & bit) > 0
        if np.any(has_bit):
            susceptibility_mult[has_bit] *= float(vf.effects.susceptibility)
            severity_odds[has_bit] *= float(vf.effects.severity_odds)

    # 3. Environment & Sanitation modifiers (Spec 5.2)
    n_areas = len(pop.int_to_area_id)
    area_crowding = np.ones(n_areas, dtype=np.float32)

    if environment_df is not None and not environment_df.empty and disease_pack.environment_modifiers:
        env_mods = disease_pack.environment_modifiers
        home_crowd_mod = env_mods.get("household_transmission", {}).get("persons_per_room", 0.0)
        if home_crowd_mod != 0.0 and "persons_per_room" in environment_df.columns:
            for _, r in environment_df.iterrows():
                aid_s = str(r.get("area_id", ""))
                if aid_s in pop.area_id_to_int:
                    aid_idx = pop.area_id_to_int[aid_s]
                    ppr = float(r.get("persons_per_room", 1.5))
                    # Scale factor centered around baseline 1.5 persons/room
                    area_crowding[aid_idx] = float(np.clip(1.0 + home_crowd_mod * (ppr - 1.5), 0.5, 3.0))

    # 4. Regional Healthcare Resource System (Spec 6.1, 6.2, 6.3, 6.4)
    if areas_df is None:
        areas_df = pd.DataFrame([{"area_id": aid} for aid in pop.area_id_to_int.keys()])

    resource_system = RegionalResourceSystem(
        resources_df=resources_df,
        areas_df=areas_df,
        area_id_to_int=pop.area_id_to_int,
        unserved_config=disease_pack.unserved_outcome
    )

    # Apply scenario resource additions (Spec 6.4)
    for res_add in scenario_pack.resource_adds:
        if res_add.start_day == 0:
            resource_system.apply_resource_addition(res_add)

    # 5. Initialize agent states & dwell times
    states = np.full(pop.n_agents, state_graph.idx_S, dtype=np.int16)
    dwell_remaining = np.zeros(pop.n_agents, dtype=np.float32)
    unserved_days = np.zeros(pop.n_agents, dtype=np.int16)

    k_param = disease_pack.transmission.overdispersion_k
    individual_k = rng.gamma(shape=k_param, scale=1.0, size=pop.n_agents).astype(np.float32)
    individual_k /= max(1e-6, np.mean(individual_k))

    # 6. Seeding
    seeding = scenario_pack.seeding
    seeded_state_idx = state_graph.name_to_idx.get(seeding.seeded_state, state_graph.name_to_idx.get("I_symp", 1))

    if seeding.area_id and seeding.area_id in pop.area_id_to_int:
        target_aid_int = pop.area_id_to_int[seeding.area_id]
        eligible = np.where(pop.area_id == target_aid_int)[0]
    else:
        eligible = np.arange(pop.n_agents)

    n_seed = min(len(eligible), seeding.initial_cases_per_area)
    seed_chosen = rng.choice(eligible, size=n_seed, replace=False)
    states[seed_chosen] = seeded_state_idx
    dwell_remaining[seed_chosen] = state_graph.sample_dwell_time(
        state_graph.idx_S, seeded_state_idx, n_seed, rng
    )

    horizon = scenario_pack.horizon_days
    n_states = state_graph.n_states

    daily_state_counts = np.zeros((horizon, n_states), dtype=np.int32)
    daily_area_infections = np.zeros((horizon, n_areas), dtype=np.int32)
    daily_hospital_demand = np.zeros(horizon, dtype=np.int32)
    daily_icu_demand = np.zeros(horizon, dtype=np.int32)

    agent_age_bands = np.empty(pop.n_agents, dtype=object)
    agent_age_bands[pop.age < 5] = "0-4"
    agent_age_bands[(pop.age >= 5) & (pop.age <= 18)] = "5-18"
    agent_age_bands[(pop.age >= 19) & (pop.age <= 64)] = "19-64"
    agent_age_bands[pop.age >= 65] = "65+"

    total_overflow_deaths = 0

    # 7. Day-by-day stepping loop
    for day in range(horizon):
        # A. Resolve active interventions and resource additions for the day
        layer_scalings = {"home": 1.0, "school": 1.0, "work": 1.0, "community": 1.0}
        for iv in scenario_pack.interventions:
            if iv.start_day <= day <= iv.end_day:
                scale_val = max(0.0, 1.0 - iv.stringency)
                if iv.measure_type == "school_closure":
                    layer_scalings["school"] = min(layer_scalings["school"], scale_val)
                elif iv.measure_type == "workplace_reduction":
                    layer_scalings["work"] = min(layer_scalings["work"], scale_val)
                elif iv.measure_type in ("curfew", "market_closure"):
                    layer_scalings["community"] = min(layer_scalings["community"], scale_val)

        for res_add in scenario_pack.resource_adds:
            if res_add.start_day == day and day > 0:
                resource_system.apply_resource_addition(res_add)

        # B. Healthcare allocation & unserved outcomes (Spec 6.2 & 6.3)
        care_mask = state_graph.needs_care[states]
        agent_adverse_probs: Optional[np.ndarray] = None

        if np.any(care_mask):
            care_indices = np.where(care_mask)[0]
            n_care = len(care_indices)

            patient_needs = [state_graph.state_needs[states[idx]] for idx in care_indices]
            p_served_ref = np.full(n_care, 0.05, dtype=np.float32)

            service_levels, adverse_probs, unmet_counts = resource_system.route_and_allocate(
                patient_areas=pop.area_id[care_indices],
                resource_needs=patient_needs,
                self_care=pop.self_care[care_indices],
                support=pop.support[care_indices],
                alt_care=pop.alt_care_access[care_indices],
                unserved_days=unserved_days[care_indices],
                severity_levels=state_graph.severity_level[states[care_indices]],
                p_served_adverse=p_served_ref
            )

            # Accumulate unserved days
            unserved_now = (service_levels == 0.0)
            unserved_days[care_indices[unserved_now]] += 1
            unserved_days[care_indices[~unserved_now]] = 0

            agent_adverse_probs = np.full(pop.n_agents, 0.05, dtype=np.float32)
            agent_adverse_probs[care_indices] = adverse_probs

            # Track excess deaths due to unserved overflow
            excess_adverse = np.maximum(0.0, adverse_probs - p_served_ref)
            total_overflow_deaths += int(np.sum(excess_adverse > 0.05))

        # C. Dwell time countdown and state transitions
        non_absorbing = ~state_graph.is_absorbing[states] & (states != state_graph.idx_S)
        dwell_remaining[non_absorbing] -= 1.0
        expired_mask = non_absorbing & (dwell_remaining <= 0.0)

        if np.any(expired_mask):
            expired_indices = np.where(expired_mask)[0]
            for s_idx in np.unique(states[expired_indices]):
                group_mask = expired_indices[states[expired_indices] == s_idx]
                adv_override = agent_adverse_probs[group_mask] if agent_adverse_probs is not None else None

                next_st, new_dwell = state_graph.resolve_next_state(
                    s_idx,
                    agent_age_bands[group_mask],
                    pop.comorbidity_multiplier[group_mask],
                    rng,
                    vulnerability_odds=severity_odds[group_mask],
                    adverse_prob_override=adv_override
                )
                states[group_mask] = next_st
                dwell_remaining[group_mask] = new_dwell

        # D. Evaluate new infections (S -> E)
        newly_infected = evaluate_daily_infections(
            pop, state_graph, states, calib_beta,
            layer_weights, layer_scalings, individual_k, rng,
            susceptibility_multipliers=susceptibility_mult,
            area_crowding_multipliers=area_crowding
        )

        if np.any(newly_infected):
            n_new = int(np.sum(newly_infected))
            states[newly_infected] = state_graph.idx_E
            dwell_remaining[newly_infected] = state_graph.sample_dwell_time(
                state_graph.idx_S, state_graph.idx_E, n_new, rng
            )

            inf_areas = pop.area_id[newly_infected]
            counts_by_aid = np.bincount(inf_areas, minlength=n_areas)
            daily_area_infections[day, :] = counts_by_aid[:n_areas]

        # E. Record daily telemetry
        daily_state_counts[day, :] = np.bincount(states, minlength=n_states)[:n_states]
        daily_hospital_demand[day] = int(np.sum(state_graph.needs_bed[states] == 1))
        daily_icu_demand[day] = int(np.sum(state_graph.needs_bed[states] == 3))

    init_s = pop.n_agents - n_seed
    final_s = daily_state_counts[-1, state_graph.idx_S]
    total_infections = max(0, init_s - final_s) + n_seed
    attack_rate = total_infections / float(pop.n_agents)

    total_deaths = 0
    if state_graph.idx_D >= 0:
        total_deaths = int(daily_state_counts[-1, state_graph.idx_D])

    manifest = {
        "timestamp": time.time(),
        "random_seed": scenario_pack.random_seed,
        "n_agents": pop.n_agents,
        "calibrated_beta": calib_beta,
        "target_r0": target_r0,
        "provenance_flags": ["synthetic" if "synthetic" in disease_pack.provenance.status else "assumed"]
    }

    return SimulationResults(
        run_id=f"run_{int(time.time()*1000)}",
        scenario_name=scenario_pack.name,
        disease_name=disease_pack.name,
        horizon_days=horizon,
        n_agents=pop.n_agents,
        sampling_ratio=pop.sampling_ratio,
        calibrated_beta=calib_beta,
        target_r0=target_r0,
        empirical_r0=empirical_r0,
        daily_state_counts=daily_state_counts,
        state_names=state_graph.state_names,
        daily_area_infections=daily_area_infections,
        daily_hospital_demand=daily_hospital_demand,
        daily_icu_demand=daily_icu_demand,
        total_infections=total_infections,
        total_deaths=total_deaths,
        attack_rate=attack_rate,
        overflow_deaths=total_overflow_deaths,
        manifest=manifest
    )
