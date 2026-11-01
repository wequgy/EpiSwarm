"""Simulation engine stepping through epidemic progression, generic resources, and rumor/compliance dynamics (Spec 5-9)."""

import time
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set, Union
import numpy as np
import pandas as pd

from scipy.optimize import root_scalar
from episwarm.population.build import PopulationSoA
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack, InterventionAction, ResourceAddAction
from episwarm.packs.behavior import BehaviorPack, DecisionQuestion
from episwarm.engine.state_graph import CompiledStateGraph
from episwarm.engine.infection import evaluate_daily_infections
from episwarm.engine.contacts import parse_contact_matrix, parse_layer_contact_matrices, analytical_beta_from_r0
from episwarm.engine.resources import RegionalResourceSystem
from episwarm.behavior.network import build_social_network
from episwarm.behavior.rumor import RumorDynamicsEngine
from episwarm.behavior.compliance import DynamicComplianceEngine
from episwarm.behavior.buckets import AgentBucket, SituationBucket, continuous_to_band
from episwarm.behavior.policy_base import DecisionPolicy
from episwarm.behavior.factory import create_decision_policy


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

    # Rumor & Compliance telemetry (Spec 7 & 8)
    daily_mean_compliance: Optional[np.ndarray] = None
    daily_rumor_beliefs: Dict[str, np.ndarray] = field(default_factory=dict)
    deaths_attributable_to_rumor: int = 0

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


def calibrate_beta_expectation(
    pop: PopulationSoA,
    state_graph: CompiledStateGraph,
    layer_matrices: Dict[str, np.ndarray],
    target_r0: float,
    rng: np.random.Generator,
    sample_size: int = 1500,
    mc_trials: int = 2000
) -> Tuple[float, float]:
    """Expectation-based calibration (deterministic, scale-invariant) per Phase 15.

    Computes expected secondary infections from a typical infectious person analytically
    from venue structure and age-structured contact matrices, solves with Brent's method,
    and validates via a 2,000 index Monte Carlo trial with common random numbers.
    """
    D = state_graph.mean_infectious_days
    n_bands = 4
    agent_age_bands = np.zeros(pop.n_agents, dtype=np.int8)
    agent_age_bands[(pop.age >= 5) & (pop.age <= 18)] = 1
    agent_age_bands[(pop.age >= 19) & (pop.age <= 64)] = 2
    agent_age_bands[pop.age >= 65] = 3

    mean_susc = float(np.mean(1.0 - 0.30 * pop.compliance))

    # Representative sample of index cases
    sample_rng = np.random.default_rng(42)
    n_idx = min(pop.n_agents, sample_size)
    index_cases = sample_rng.choice(pop.n_agents, size=n_idx, replace=False)

    layer_venues = {
        "home": pop.household_id,
        "school": pop.school_id,
        "work": np.where(pop.wfh_possible, -1, pop.workplace_id),
        "community": pop.commute_area
    }

    # Precompute venue structure per layer
    layer_cache = []
    for l_name, v_ids in layer_venues.items():
        M_l = layer_matrices.get(l_name, np.eye(4) * 2.0)
        c_l = np.sum(M_l, axis=1)
        valid = (v_ids >= 0)
        if not np.any(valid):
            continue
        max_vid = int(np.max(v_ids[valid]))
        bins = (max_vid + 1) * n_bands
        combined = v_ids[valid] * n_bands + agent_age_bands[valid]
        N_vb = np.bincount(combined, minlength=bins).reshape((max_vid + 1, n_bands))
        present_vb = (N_vb > 0)

        idx_venues = v_ids[index_cases]
        idx_ages = agent_age_bands[index_cases]
        valid_idx = (idx_venues >= 0)
        if not np.any(valid_idx):
            continue

        cur_v = idx_venues[valid_idx]
        cur_b = idx_ages[valid_idx]

        W = present_vb[:, None, :] * M_l[None, :, :]
        sum_W = np.sum(W, axis=2, keepdims=True)
        safe_sum = np.maximum(1e-9, sum_W)
        norm_W = np.where(sum_W > 0, W / safe_sum, 0.0)

        w_b = norm_W[cur_v, :, cur_b]
        n_cur_b = N_vb[cur_v, cur_b][:, None]

        co_members = N_vb[cur_v, :].astype(np.float64)
        row_indices = np.arange(len(cur_v))
        co_members[row_indices, cur_b] = np.maximum(0.0, co_members[row_indices, cur_b] - 1.0)

        factor = c_l[None, :] * (w_b / np.maximum(1, n_cur_b)) * D
        layer_cache.append((co_members, factor))

    def expected_r0(b: float) -> float:
        total = 0.0
        for co_members, factor in layer_cache:
            prob_inf = (1.0 - np.exp(-b * factor)) * mean_susc
            total += np.sum(co_members * prob_inf)
        return total / n_idx

    try:
        sol = root_scalar(lambda b: expected_r0(b) - target_r0, bracket=[0.005, 2.5], method="brentq")
        best_beta = float(sol.root)
    except Exception:
        best_beta = 0.13

    # Monte Carlo validation with common random numbers (2,000 index trials)
    rng_mc = np.random.default_rng(9999)
    mc_indices = rng_mc.choice(pop.n_agents, size=mc_trials, replace=True)
    trial_secondaries = np.zeros(mc_trials, dtype=np.int32)

    for l_name, v_ids in layer_venues.items():
        M_l = layer_matrices.get(l_name, np.eye(4) * 2.0)
        c_l = np.sum(M_l, axis=1)
        valid = (v_ids >= 0)
        if not np.any(valid):
            continue
        max_vid = int(np.max(v_ids[valid]))
        bins = (max_vid + 1) * n_bands
        combined = v_ids[valid] * n_bands + agent_age_bands[valid]
        N_vb = np.bincount(combined, minlength=bins).reshape((max_vid + 1, n_bands))
        present_vb = (N_vb > 0)

        idx_venues = v_ids[mc_indices]
        idx_ages = agent_age_bands[mc_indices]
        valid_idx = (idx_venues >= 0)
        if not np.any(valid_idx):
            continue

        cur_v = idx_venues[valid_idx]
        cur_b = idx_ages[valid_idx]

        W = present_vb[:, None, :] * M_l[None, :, :]
        sum_W = np.sum(W, axis=2, keepdims=True)
        safe_sum = np.maximum(1e-9, sum_W)
        norm_W = np.where(sum_W > 0, W / safe_sum, 0.0)

        w_b = norm_W[cur_v, :, cur_b]
        n_cur_b = N_vb[cur_v, cur_b][:, None]

        lam_a = best_beta * c_l[None, :] * (w_b / np.maximum(1, n_cur_b))
        prob_inf_a = (1.0 - np.exp(-lam_a * D)) * mean_susc

        co_members = N_vb[cur_v, :].astype(np.float64)
        row_indices = np.arange(len(cur_v))
        co_members[row_indices, cur_b] = np.maximum(0.0, co_members[row_indices, cur_b] - 1.0)

        draws = rng_mc.binomial(n=co_members.astype(np.int64), p=np.clip(prob_inf_a, 0.0, 1.0))
        trial_secondaries[valid_idx] += np.sum(draws, axis=1)

    measured_r0 = float(np.mean(trial_secondaries))
    return best_beta, measured_r0


def calibrate_beta_numerical(
    pop: PopulationSoA,
    state_graph: CompiledStateGraph,
    initial_beta: float,
    target_r0: float,
    layer_weights: Dict[str, float],
    rng: np.random.Generator,
    trials: int = 50
) -> Tuple[float, float]:
    """Legacy numerical calibration (retained for backward compatibility)."""
    matrices = {l: np.eye(4) * w * 5.0 for l, w in layer_weights.items()}
    return calibrate_beta_expectation(pop, state_graph, matrices, target_r0, rng)


def run_simulation(
    pop: PopulationSoA,
    disease_pack: DiseasePack,
    scenario_pack: ScenarioPack,
    contacts_df: Optional[pd.DataFrame] = None,
    layer_weights: Optional[Dict[str, float]] = None,
    resources_df: Optional[pd.DataFrame] = None,
    environment_df: Optional[pd.DataFrame] = None,
    areas_df: Optional[pd.DataFrame] = None,
    behavior_pack: Optional[BehaviorPack] = None,
    enable_rumor: bool = True,
    policy: Optional[DecisionPolicy] = None,
    enable_behavior: bool = True,
    unlimited_resources: bool = False,
    compute_attributable_overflow: bool = False,
    step_callback: Optional[Any] = None
) -> SimulationResults:
    """Execute complete multi-day epidemic simulation with generic resources, vulnerability factors, and rumor dynamics."""
    rng = np.random.default_rng(scenario_pack.random_seed)
    age_bands = ["0-4", "5-18", "19-64", "65+"]
    state_graph = CompiledStateGraph(disease_pack, age_bands)

    if layer_weights is None:
        layer_weights = {"home": 0.35, "school": 0.25, "work": 0.25, "community": 0.15}

    # 1. Contact matrix & beta calibration
    if contacts_df is None:
        p_contacts = Path("regions/example_synthetic/contacts.csv")
        if p_contacts.exists():
            contacts_df = pd.read_csv(p_contacts)

    layer_matrices = parse_layer_contact_matrices(contacts_df, age_bands, layer_weights)
    target_r0 = disease_pack.transmission.r0 or 2.5
    calib_beta, empirical_r0 = calibrate_beta_expectation(
        pop, state_graph, layer_matrices, target_r0, rng
    )

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

    for res_add in scenario_pack.resource_adds:
        if res_add.start_day == 0:
            resource_system.apply_resource_addition(res_add)

    # 5. Social Network, Rumor Dynamics, and Compliance Engines (Spec 7 & 8)
    horizon = scenario_pack.horizon_days
    social_network = build_social_network(pop, rng=rng)

    rumor_engine: Optional[RumorDynamicsEngine] = None
    compliance_engine: Optional[DynamicComplianceEngine] = None
    daily_mean_compliance = np.zeros(horizon, dtype=np.float32)
    daily_rumor_beliefs: Dict[str, np.ndarray] = {}

    # Snapshot base compliance for isolated runs
    saved_compliance = np.copy(pop.compliance)

    if behavior_pack and behavior_pack.rumor_topics and enable_rumor:
        rumor_engine = RumorDynamicsEngine(pop, behavior_pack.rumor_topics, social_network)
        compliance_engine = DynamicComplianceEngine(pop, behavior_pack.compliance_weights, social_network)
        for t in behavior_pack.rumor_topics:
            daily_rumor_beliefs[t.id] = np.zeros(horizon, dtype=np.float32)

    # Initialize Behavior Decision Policy & Buckets (Spec 10 & Phase 16)
    active_policy = policy
    policy_backend = "none"
    if enable_behavior:
        if active_policy is None:
            active_policy, policy_backend = create_decision_policy()
        else:
            policy_backend = active_policy.__class__.__name__.lower().replace("policy", "")

    decision_questions = (behavior_pack.questions if behavior_pack and behavior_pack.questions else [
        DecisionQuestion(id="wear_mask", type="noul", options=["yes", "no"], plain_instructions="Decide whether to wear a mask in public venues."),
        DecisionQuestion(id="isolate_symptomatic", type="noul", options=["yes", "no"], plain_instructions="Decide whether to isolate at home when symptomatic."),
        DecisionQuestion(id="workplace_attendance", type="choice", options=["usual", "reduced", "avoid"], plain_instructions="Decide whether to attend workplace as usual, reduced, or avoid."),
        DecisionQuestion(id="accept_vaccine", type="noul", options=["yes", "no"], plain_instructions="Decide whether to accept vaccination if offered.")
    ])

    occ_classes = np.full(pop.n_agents, "service", dtype=object)
    occ_classes[pop.occupation_class == 0] = "none"
    occ_classes[pop.occupation_class == 2] = "manufacturing"

    trust_vals = getattr(pop, "trust_authority", getattr(pop, "trust", None))
    if trust_vals is None:
        trust_vals = np.full(pop.n_agents, 0.5, dtype=np.float32)

    agent_age_bands = np.empty(pop.n_agents, dtype=object)
    agent_age_bands[pop.age < 5] = "0-4"
    agent_age_bands[(pop.age >= 5) & (pop.age <= 18)] = "5-18"
    agent_age_bands[(pop.age >= 19) & (pop.age <= 64)] = "19-64"
    agent_age_bands[pop.age >= 65] = "65+"

    agent_age_bands_int = np.zeros(pop.n_agents, dtype=np.int8)
    agent_age_bands_int[(pop.age >= 5) & (pop.age <= 18)] = 1
    agent_age_bands_int[(pop.age >= 19) & (pop.age <= 64)] = 2
    agent_age_bands_int[pop.age >= 65] = 3

    agent_buckets = [
        AgentBucket(
            age_band=agent_age_bands[i],
            occupation_class=occ_classes[i],
            has_comorbidity=bool(pop.risk_factor_bits[i] > 0),
            trust_band=continuous_to_band(trust_vals[i]),
            risk_tolerance_band=continuous_to_band(pop.risk_tolerance[i])
        )
        for i in range(pop.n_agents)
    ]

    agent_masking = np.zeros(pop.n_agents, dtype=bool)
    agent_isolating = np.zeros(pop.n_agents, dtype=bool)
    agent_work_avoid = np.zeros(pop.n_agents, dtype=bool)
    agent_vaccinated = np.zeros(pop.n_agents, dtype=bool)
    prev_area_measures_desc = {aid: "none" for aid in range(n_areas)}
    prev_area_risk_bands = np.full(n_areas, "low", dtype=object)

    # 6. Initialize agent states & dwell times
    states = np.full(pop.n_agents, state_graph.idx_S, dtype=np.int16)
    dwell_remaining = np.zeros(pop.n_agents, dtype=np.float32)
    unserved_days = np.zeros(pop.n_agents, dtype=np.int16)

    k_param = disease_pack.transmission.overdispersion_k
    individual_k = rng.gamma(shape=k_param, scale=1.0, size=pop.n_agents).astype(np.float32)
    individual_k /= max(1e-6, np.mean(individual_k))

    # 7. Seeding
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
    dwell_remaining[seed_chosen] = state_graph.sample_state_dwell_time(
        seeded_state_idx, n_seed, rng
    )

    seed_mode = getattr(seeding, "seed_infectiousness", "mean")
    if seed_mode == "mean":
        individual_k[seed_chosen] = 1.0

    n_states = state_graph.n_states
    daily_state_counts = np.zeros((horizon, n_states), dtype=np.int32)
    daily_area_infections = np.zeros((horizon, n_areas), dtype=np.int32)
    daily_hospital_demand = np.zeros(horizon, dtype=np.int32)
    daily_icu_demand = np.zeros(horizon, dtype=np.int32)

    total_overflow_deaths = 0

    # 8. Day-by-day stepping loop
    for day in range(horizon):
        # A. Resolve active interventions, corrections, and resource additions per area (Spec 4.1 & Phase 16)
        layer_scalings = {
            "home": np.ones(n_areas, dtype=np.float32),
            "school": np.ones(n_areas, dtype=np.float32),
            "work": np.ones(n_areas, dtype=np.float32),
            "community": np.ones(n_areas, dtype=np.float32)
        }
        active_corrections: Dict[str, float] = {}
        area_enforcements = np.zeros(n_areas, dtype=np.float32)
        area_active_measures: Dict[int, List[str]] = {aid: [] for aid in range(n_areas)}
        vaccine_available_areas: Set[int] = set()

        for iv in scenario_pack.interventions:
            if iv.start_day <= day <= iv.end_day:
                scale_val = max(0.0, 1.0 - iv.stringency)
                target_aids = list(range(n_areas)) if iv.area_id == "ALL" else ([pop.area_id_to_int[iv.area_id]] if iv.area_id in pop.area_id_to_int else [])

                for aid in target_aids:
                    area_active_measures[aid].append(iv.measure_type)
                    if iv.measure_type == "school_closure":
                        layer_scalings["school"][aid] = min(layer_scalings["school"][aid], scale_val)
                    elif iv.measure_type == "workplace_reduction":
                        layer_scalings["work"][aid] = min(layer_scalings["work"][aid], scale_val)
                    elif iv.measure_type in ("curfew", "market_closure"):
                        layer_scalings["community"][aid] = min(layer_scalings["community"][aid], scale_val)
                    elif iv.measure_type == "vaccination":
                        vaccine_available_areas.add(aid)

                if iv.measure_type == "correction_campaign":
                    eff = float(iv.parameters.get("efficacy", 0.40) * iv.stringency)
                    tid = iv.parameters.get("topic_id", "all")
                    if tid == "all" and behavior_pack:
                        for top in behavior_pack.rumor_topics:
                            active_corrections[top.id] = max(active_corrections.get(top.id, 0.0), eff)
                    else:
                        active_corrections[tid] = max(active_corrections.get(tid, 0.0), eff)

                if iv.area_id == "ALL":
                    area_enforcements.fill(max(float(np.max(area_enforcements)), iv.stringency))
                else:
                    aid_int = pop.area_id_to_int.get(iv.area_id, -1)
                    if aid_int >= 0:
                        area_enforcements[aid_int] = max(area_enforcements[aid_int], iv.stringency)

        for res_add in scenario_pack.resource_adds:
            if res_add.start_day == day and day > 0:
                resource_system.apply_resource_addition(res_add)

        # B. Step Rumor and Dynamic Compliance Engines (Spec 7 & 8)
        daily_mean_compliance[day] = float(np.mean(pop.compliance))
        mask_red = np.zeros(pop.n_agents, dtype=np.float32)
        iso_red = np.zeros(pop.n_agents, dtype=np.float32)
        vax_red = np.zeros(pop.n_agents, dtype=np.float32)

        if rumor_engine and compliance_engine:
            rumor_tele = rumor_engine.step_day(day, active_corrections, rng)
            for tid, stat in rumor_tele.items():
                if tid in daily_rumor_beliefs:
                    daily_rumor_beliefs[tid][day] = stat["mean_belief"]

            recent_infections = daily_area_infections[max(0, day - 7):day + 1].sum(axis=0) if day > 0 else np.zeros(n_areas)
            area_pops = np.bincount(pop.area_id, minlength=n_areas)
            area_rates = recent_infections / np.maximum(1, area_pops)

            pop.compliance = compliance_engine.step_day(
                area_enforcements, area_rates.astype(np.float32), rumor_engine.beliefs
            )
            daily_mean_compliance[day] = float(np.mean(pop.compliance))

            m_r, i_r = rumor_engine.compute_behavior_distortions()
            mask_red = m_r
            iso_red = i_r
        else:
            recent_infections = daily_area_infections[max(0, day - 7):day + 1].sum(axis=0) if day > 0 else np.zeros(n_areas)
            area_pops = np.bincount(pop.area_id, minlength=n_areas)
            area_rates = recent_infections / np.maximum(1, area_pops)

        area_risk_bands = np.full(n_areas, "low", dtype=object)
        for aid in range(n_areas):
            rate = area_rates[aid]
            if rate > 0.05:
                area_risk_bands[aid] = "critical"
            elif rate > 0.02:
                area_risk_bands[aid] = "high"
            elif rate > 0.005:
                area_risk_bands[aid] = "medium"
            else:
                area_risk_bands[aid] = "low"

        # Step Behavioral Decision Policy on Triggers (Spec 10 & Phase 16)
        if enable_behavior and active_policy is not None:
            symp_idx = state_graph.name_to_idx.get("I_symp", -1)
            symptomatic_mask = (states == symp_idx) if symp_idx >= 0 else np.zeros(pop.n_agents, dtype=bool)
            symptomatic_households = set(pop.household_id[symptomatic_mask]) if np.any(symptomatic_mask) else set()

            area_measure_changed = np.array([
                ",".join(sorted(area_active_measures[aid])) != prev_area_measures_desc[aid]
                for aid in range(n_areas)
            ])
            area_risk_changed = (area_risk_bands != prev_area_risk_bands)

            agent_area_triggered = area_measure_changed[pop.area_id] | area_risk_changed[pop.area_id]
            agent_hh_triggered = np.isin(pop.household_id, list(symptomatic_households)) if symptomatic_households else np.zeros(pop.n_agents, dtype=bool)

            triggered_agents = (day == 0) | agent_area_triggered | symptomatic_mask | agent_hh_triggered
            if np.any(triggered_agents):
                trig_indices = np.where(triggered_agents)[0]
                bucket_groups: Dict[Tuple[AgentBucket, SituationBucket], List[int]] = {}
                for idx in trig_indices:
                    a_aid = pop.area_id[idx]
                    a_st = states[idx]
                    st_group = "symptomatic" if a_st == symp_idx else ("recovering" if a_st in (state_graph.idx_R, state_graph.idx_D) else "susceptible")
                    sit_b = SituationBucket(
                        health_state_group=st_group,
                        local_risk_level=area_risk_bands[a_aid],
                        active_measures=",".join(sorted(area_active_measures[a_aid])) or "none",
                        household_member_sick=bool(pop.household_id[idx] in symptomatic_households)
                    )
                    pair_key = (agent_buckets[idx], sit_b)
                    if pair_key not in bucket_groups:
                        bucket_groups[pair_key] = []
                    bucket_groups[pair_key].append(idx)

                for (ag_b, sit_b), idx_list in bucket_groups.items():
                    idx_arr = np.array(idx_list, dtype=np.int32)
                    c_arr = pop.compliance[idx_arr]
                    n_sub = len(idx_arr)
                    for q in decision_questions:
                        probs = active_policy.decide(q, sit_b, ag_b)
                        if q.id == "wear_mask":
                            p_yes = probs.get("yes", 0.5)
                            p_eff = np.clip(p_yes * (0.30 + 0.70 * c_arr) * (1.0 - mask_red[idx_arr]), 0.01, 0.99)
                            agent_masking[idx_arr] = (rng.random(size=n_sub) < p_eff)
                        elif q.id == "isolate_symptomatic":
                            if sit_b.health_state_group == "symptomatic":
                                p_yes = probs.get("yes", 0.7)
                                p_eff = np.clip(p_yes * (0.30 + 0.70 * c_arr) * (1.0 - iso_red[idx_arr]), 0.01, 0.99)
                                agent_isolating[idx_arr] = (rng.random(size=n_sub) < p_eff)
                            else:
                                agent_isolating[idx_arr] = False
                        elif q.id == "workplace_attendance":
                            p_avoid = probs.get("avoid", 0.1)
                            p_eff = np.clip(p_avoid * (0.30 + 0.70 * c_arr), 0.01, 0.99)
                            agent_work_avoid[idx_arr] = (rng.random(size=n_sub) < p_eff)
                        elif q.id == "accept_vaccine":
                            if vaccine_available_areas:
                                in_vax = np.isin(pop.area_id[idx_arr], list(vaccine_available_areas)) & (~agent_vaccinated[idx_arr])
                                if np.any(in_vax):
                                    vax_sub = idx_arr[in_vax]
                                    p_yes = probs.get("yes", 0.6)
                                    p_eff = np.clip(p_yes * (0.30 + 0.70 * pop.compliance[vax_sub]) * (1.0 - vax_red[vax_sub]), 0.01, 0.99)
                                    agent_vaccinated[vax_sub] = (rng.random(size=len(vax_sub)) < p_eff)

            for aid in range(n_areas):
                prev_area_measures_desc[aid] = ",".join(sorted(area_active_measures[aid]))
            prev_area_risk_bands = np.copy(area_risk_bands)

        # C. Healthcare allocation & unserved outcomes (Spec 6.2 & 6.3)
        care_mask = state_graph.needs_care[states]
        agent_adverse_probs: Optional[np.ndarray] = None

        if np.any(care_mask):
            care_indices = np.where(care_mask)[0]
            n_care = len(care_indices)

            patient_needs = [state_graph.state_needs[states[idx]] for idx in care_indices]
            p_served_ref = np.array([state_graph.get_served_adverse_prob(states[idx]) for idx in care_indices], dtype=np.float32)

            if unlimited_resources:
                service_levels = np.ones(n_care, dtype=np.float32)
                adverse_probs = p_served_ref
            else:
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

            unserved_now = (service_levels == 0.0)
            unserved_days[care_indices[unserved_now]] += 1
            unserved_days[care_indices[~unserved_now]] = 0

            agent_adverse_probs = np.full(pop.n_agents, 0.05, dtype=np.float32)
            agent_adverse_probs[care_indices] = adverse_probs

        # D. Dwell time countdown and state transitions
        non_absorbing = ~state_graph.is_absorbing[states] & (states != state_graph.idx_S)
        dwell_remaining[non_absorbing] -= 1.0
        expired_mask = non_absorbing & (dwell_remaining <= 0.0)

        if np.any(expired_mask):
            expired_indices = np.where(expired_mask)[0]
            expired_states = states[expired_indices].copy()
            for s_idx in np.unique(expired_states):
                group_mask = expired_indices[expired_states == s_idx]
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

        # E. Evaluate new infections (S -> E) with behavior actions
        effective_isolating = agent_isolating.copy()
        newly_infected = evaluate_daily_infections(
            pop, state_graph, states, calib_beta,
            layer_matrices, layer_scalings, individual_k, rng,
            susceptibility_multipliers=susceptibility_mult,
            area_crowding_multipliers=area_crowding,
            agent_age_bands=agent_age_bands_int,
            agent_masking=agent_masking if enable_behavior else None,
            agent_vaccinated=agent_vaccinated if enable_behavior else None,
            agent_isolating=effective_isolating if enable_behavior else None,
            mask_inward_efficacy=disease_pack.transmission.mask_inward_efficacy,
            mask_outward_efficacy=disease_pack.transmission.mask_outward_efficacy,
            vaccine_efficacy_acquisition=disease_pack.transmission.vaccine_efficacy_acquisition
        )

        if np.any(newly_infected):
            n_new = int(np.sum(newly_infected))
            states[newly_infected] = state_graph.idx_E
            dwell_remaining[newly_infected] = state_graph.sample_state_dwell_time(
                state_graph.idx_E, n_new, rng
            )

            inf_areas = pop.area_id[newly_infected]
            counts_by_aid = np.bincount(inf_areas, minlength=n_areas)
            daily_area_infections[day, :] = counts_by_aid[:n_areas]

        # F. Record daily telemetry
        daily_state_counts[day, :] = np.bincount(states, minlength=n_states)[:n_states]
        daily_hospital_demand[day] = int(np.sum(state_graph.needs_bed[states] == 1))
        daily_icu_demand[day] = int(np.sum(state_graph.needs_bed[states] == 3))

        if step_callback is not None:
            symp_idx = state_graph.name_to_idx.get('I_symp', -1)
            symp_c = int(np.sum(states == symp_idx)) if symp_idx >= 0 else int(np.sum(states != state_graph.idx_S))
            step_callback(day, scenario_pack.horizon_days, {
                'active_infected': symp_c,
                'llm_calls': getattr(active_policy, 'model_calls_count', 0),
                'cache_hits': getattr(active_policy, 'cache_hits_count', 0),
                'fallbacks': getattr(active_policy, 'fallback_count', 0)
            })

    # Restore pop baseline compliance to prevent mutative side effects
    pop.compliance = saved_compliance

    init_s = pop.n_agents - n_seed
    final_s = daily_state_counts[-1, state_graph.idx_S]
    total_infections = max(0, init_s - final_s) + n_seed
    attack_rate = total_infections / float(pop.n_agents)

    total_deaths = 0
    if state_graph.idx_D >= 0:
        total_deaths = int(daily_state_counts[-1, state_graph.idx_D])

    total_overflow_deaths = 0
    if compute_attributable_overflow and not unlimited_resources:
        # Paired counterfactual run with identical random seed streams
        unlim_run = run_simulation(
            pop, disease_pack, scenario_pack,
            contacts_df=contacts_df, layer_weights=layer_weights,
            resources_df=resources_df, environment_df=environment_df, areas_df=areas_df,
            behavior_pack=behavior_pack, enable_rumor=enable_rumor,
            policy=policy, enable_behavior=enable_behavior,
            unlimited_resources=True, compute_attributable_overflow=False
        )
        total_overflow_deaths = max(0, total_deaths - unlim_run.total_deaths)

    fb_rate = active_policy.fallback_rate if (enable_behavior and active_policy is not None) else 0.0

    manifest = {
        "timestamp": time.time(),
        "random_seed": scenario_pack.random_seed,
        "n_agents": pop.n_agents,
        "calibrated_beta": calib_beta,
        "target_r0": target_r0,
        "policy_backend": policy_backend,
        "policy_fallback_rate": fb_rate,
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
        daily_mean_compliance=daily_mean_compliance,
        daily_rumor_beliefs=daily_rumor_beliefs,
        manifest=manifest
    )


def run_paired_counterfactual_overflow(
    pop: PopulationSoA,
    disease_pack: DiseasePack,
    scenario_pack: ScenarioPack,
    contacts_df: Optional[pd.DataFrame] = None,
    layer_weights: Optional[Dict[str, float]] = None,
    resources_df: Optional[pd.DataFrame] = None,
    environment_df: Optional[pd.DataFrame] = None,
    areas_df: Optional[pd.DataFrame] = None,
    behavior_pack: Optional[BehaviorPack] = None,
    policy: Optional[DecisionPolicy] = None,
    enable_behavior: bool = True
) -> Tuple[SimulationResults, SimulationResults, int]:
    """Run paired constrained and unlimited-resource simulations to compute attributable overflow deaths (D6)."""
    constrained_res = run_simulation(
        pop, disease_pack, scenario_pack,
        contacts_df=contacts_df, layer_weights=layer_weights,
        resources_df=resources_df, environment_df=environment_df, areas_df=areas_df,
        behavior_pack=behavior_pack, policy=policy, enable_behavior=enable_behavior,
        unlimited_resources=False
    )
    unlimited_res = run_simulation(
        pop, disease_pack, scenario_pack,
        contacts_df=contacts_df, layer_weights=layer_weights,
        resources_df=resources_df, environment_df=environment_df, areas_df=areas_df,
        behavior_pack=behavior_pack, policy=policy, enable_behavior=enable_behavior,
        unlimited_resources=True
    )
    delta_deaths = max(0, constrained_res.total_deaths - unlimited_res.total_deaths)
    constrained_res.overflow_deaths = delta_deaths
    return constrained_res, unlimited_res, delta_deaths


def run_counterfactual_rumor_analysis(
    pop: PopulationSoA,
    disease_pack: DiseasePack,
    scenario_pack: ScenarioPack,
    behavior_pack: BehaviorPack,
    n_seeds: int = 5
) -> Dict[str, Any]:
    """Execute paired counterfactual evaluation comparing runs with and without misinformation (Spec 7.4).

    Returns:
        delta_deaths: array of (deaths_with_rumor - deaths_without_rumor)
        mean_delta_deaths: float
        ci_lower: float 95% CI
        ci_upper: float 95% CI
    """
    deltas = []
    base_seed = scenario_pack.random_seed

    for s_idx in range(n_seeds):
        scen_run = scenario_pack.model_copy(deep=True)
        scen_run.random_seed = base_seed + s_idx * 17

        # 1. Run with rumor active
        res_with = run_simulation(pop, disease_pack, scen_run, behavior_pack=behavior_pack, enable_rumor=True)

        # 2. Run counterfactual with rumor disabled (same seed)
        res_without = run_simulation(pop, disease_pack, scen_run, behavior_pack=behavior_pack, enable_rumor=False)

        diff = res_with.total_deaths - res_without.total_deaths
        deltas.append(diff)

    deltas_arr = np.array(deltas, dtype=np.float64)
    mean_diff = float(np.mean(deltas_arr))
    std_diff = float(np.std(deltas_arr, ddof=1)) if len(deltas) > 1 else 0.0
    se = std_diff / np.sqrt(len(deltas))

    return {
        "deltas": deltas,
        "mean_delta_deaths": mean_diff,
        "ci_lower": mean_diff - 1.96 * se,
        "ci_upper": mean_diff + 1.96 * se,
        "deaths_attributable_to_rumor": int(round(max(0.0, mean_diff)))
    }
