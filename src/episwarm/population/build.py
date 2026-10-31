"""Structure-of-Arrays (SoA) synthetic population synthesizer with structured life histories (Spec 9 & 5)."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
import numpy as np
import pandas as pd
import yaml

from episwarm.packs.region import RegionPack, RegionMeta
from episwarm.packs.behavior import BehaviorPack
from episwarm.population.ipf import run_ipf_2d
from episwarm.population.households import compose_households
from episwarm.population.venues import instantiate_venues, assign_venues_and_commute, assign_social_venues
from episwarm.population.traits import sample_traits, assign_comorbidity_multipliers


@dataclass
class PopulationSoA:
    """Structure-of-Arrays contiguous memory block representing all synthetic agents."""
    n_agents: int
    total_population_represented: int
    sampling_ratio: float  # real people represented per 1 agent

    # Core demographic SoA fields
    agent_id: np.ndarray          # int32
    area_id: np.ndarray           # int16
    household_id: np.ndarray      # int32
    age: np.ndarray               # int8
    sex: np.ndarray               # int8 (0=M, 1=F)
    occupation_class: np.ndarray  # int8 (0=none/child, 1=service, 2=manufacturing/other)
    workplace_id: np.ndarray      # int32 (-1 if none)
    school_id: np.ndarray         # int32 (-1 if none)
    commute_area: np.ndarray      # int16
    wfh_possible: np.ndarray      # bool
    comorbidity_multiplier: np.ndarray  # float32
    compliance: np.ndarray        # float32
    rumor_susceptibility: np.ndarray  # float32
    trust: np.ndarray             # float32
    risk_tolerance: np.ndarray    # float32

    # Spec 9: Structured life history facts
    income_band: np.ndarray       # int8 (0=low, 1=middle, 2=high)
    household_role: np.ndarray    # int8 (0=child, 1=primary_earner, 2=caregiver_adult, 3=elder)
    caregiver: np.ndarray         # bool
    financial_buffer: np.ndarray  # float32 [0, 1] (ability to sustain quarantine/isolation)
    past_bereavement: np.ndarray  # bool (experienced loss in prior waves)
    prior_authority_experience: np.ndarray  # float32 [0, 1]
    routine_template: np.ndarray  # int8 (0=student, 1=office_worker, 2=shift_worker, 3=informal_worker, 4=homemaker, 5=retired)

    # Persistent preferred social venues (Spec 9)
    pref_market_id: np.ndarray    # int32
    pref_leisure_id: np.ndarray   # int32

    # Disease-specific vulnerability & healthcare factors (Spec 5.1 & 6.3)
    risk_factor_bits: np.ndarray  # uint32 bitmask of declared vulnerability factors
    self_care: np.ndarray         # float32 [0, 1]
    support: np.ndarray           # float32 [0, 1]
    alt_care_access: np.ndarray   # float32 [0, 1]
    unserved_days: np.ndarray     # int16

    # Lookups
    int_to_area_id: Dict[int, str]
    area_id_to_int: Dict[str, int]

    def get_showcase_profile(self, index: int) -> Dict[str, Any]:
        """Generate a structured, non-hallucinatory narrative profile for a showcase agent (Spec 9)."""
        idx = int(index)
        role_map = {0: "Child/Dependent", 1: "Primary Earner", 2: "Caregiver Adult", 3: "Elder Resident"}
        routine_map = {
            0: "Student / Youth Schedule",
            1: "Standard Office / Commercial Worker",
            2: "Shift / Industrial Worker",
            3: "Informal Market Worker",
            4: "Homemaker / Family Caregiver",
            5: "Retired / Home-based"
        }
        income_map = {0: "Low", 1: "Middle", 2: "High"}

        area_str = self.int_to_area_id.get(int(self.area_id[idx]), str(self.area_id[idx]))

        narrative = (
            f"[GENERATED NARRATIVE - SYNTHETIC DATA ONLY]\n"
            f"Agent #{int(self.agent_id[idx])} is a {int(self.age[idx])}-year-old "
            f"{'female' if self.sex[idx] == 1 else 'male'} residing in {area_str}. "
            f"Within their household (ID: {int(self.household_id[idx])}), their primary role is {role_map.get(int(self.household_role[idx]), 'Member')}. "
            f"They follow a {routine_map.get(int(self.routine_template[idx]), 'Daily Routine')} with an estimated "
            f"{income_map.get(int(self.income_band[idx]), 'Middle')} income buffer (financial reserve score: {self.financial_buffer[idx]:.2f}). "
            f"{'They have prior family bereavement experience from earlier outbreaks. ' if self.past_bereavement[idx] else ''}"
            f"Healthcare self-care capacity: {self.self_care[idx]:.2f}, household support score: {self.support[idx]:.2f}."
        )

        return {
            "agent_id": int(self.agent_id[idx]),
            "area": area_str,
            "age": int(self.age[idx]),
            "sex": "Female" if self.sex[idx] == 1 else "Male",
            "role": role_map.get(int(self.household_role[idx]), "Member"),
            "routine": routine_map.get(int(self.routine_template[idx]), "General"),
            "income_band": income_map.get(int(self.income_band[idx]), "Middle"),
            "financial_buffer": float(self.financial_buffer[idx]),
            "compliance": float(self.compliance[idx]),
            "self_care": float(self.self_care[idx]),
            "support": float(self.support[idx]),
            "alt_care_access": float(self.alt_care_access[idx]),
            "caregiver": bool(self.caregiver[idx]),
            "past_bereavement": bool(self.past_bereavement[idx]),
            "narrative": narrative
        }

    def summary(self) -> str:
        """Generate human-readable audit summary of the synthetic population."""
        lines = [
            "================ Synthetic Population Summary ================",
            f"Total Agents Simulated:        {self.n_agents:,}",
            f"Real Population Represented:   {self.total_population_represented:,}",
            f"Sampling Ratio:                1 agent = {self.sampling_ratio:.2f} persons",
            f"Number of Households:          {len(np.unique(self.household_id)):,}",
            f"Employed Workers:              {np.sum(self.workplace_id >= 0):,} ({np.mean(self.workplace_id >= 0)*100:.1f}%)",
            f"Students in School:            {np.sum(self.school_id >= 0):,} ({np.mean(self.school_id >= 0)*100:.1f}%)",
            f"Active Caregivers:             {np.sum(self.caregiver):,} ({np.mean(self.caregiver)*100:.1f}%)",
            f"Mean Compliance Trait:         {np.mean(self.compliance):.3f}",
            f"Mean Self-Care Score:          {np.mean(self.self_care):.3f}",
            f"Mean Household Support:        {np.mean(self.support):.3f}",
            f"Mean Comorbidity Multiplier:   {np.mean(self.comorbidity_multiplier):.3f}",
            "---------------- Area Distribution ----------------",
            f"{'Area Code':<12} {'Agent Count':<14} {'Estimated Pop':<16}"
        ]
        unique_areas, counts = np.unique(self.area_id, return_counts=True)
        for u_aid, cnt in zip(unique_areas, counts):
            name = self.int_to_area_id.get(u_aid, str(u_aid))
            lines.append(f"{name:<12} {cnt:<14,} {int(round(cnt * self.sampling_ratio)):<16,}")
        lines.append("==============================================================")
        return "\n".join(lines)


def build_synthetic_population(
    region_dir: Union[str, Path],
    scale_agents: int = 50000,
    random_seed: int = 42,
    behavior_pack: Optional[BehaviorPack] = None
) -> PopulationSoA:
    """Build a Structure-of-Arrays synthetic population with life histories and disease vulnerability."""
    region_dir = Path(region_dir)
    rng = np.random.default_rng(random_seed)

    # 1. Load region metadata
    yaml_path = region_dir / "region.yaml"
    with open(yaml_path, "r", encoding="utf-8") as f:
        meta_dict = yaml.safe_load(f)
    pack = RegionPack(**meta_dict)

    # 2. Load areas.csv
    areas_df = pd.read_csv(region_dir / "areas.csv")
    area_ids = areas_df["area_id"].astype(str).tolist()
    int_to_area_id = {i: aid for i, aid in enumerate(area_ids)}
    area_id_to_int = {aid: i for i, aid in enumerate(area_ids)}

    total_real_pop = int(areas_df["population"].sum())
    sampling_ratio = total_real_pop / float(scale_agents)

    # Area population allocation in proportion to marginals (Hamilton-Hare / Largest Remainder method)
    pop_shares = areas_df["population"].values.astype(np.float64) / total_real_pop
    exact_agents = pop_shares * scale_agents
    base_allocated = np.floor(exact_agents).astype(np.int32)
    remainder = scale_agents - base_allocated.sum()
    fractional = exact_agents - base_allocated
    top_remainder_indices = np.argsort(-fractional)[:remainder]
    base_allocated[top_remainder_indices] += 1
    area_agent_counts = base_allocated

    assert area_agent_counts.sum() == scale_agents

    # 3. Demographic attribution (age, sex, occupation)
    age_df = pd.read_csv(region_dir / "age_structure.csv")
    age_bands = age_df["age_band"].unique().tolist()
    age_probs = []
    age_ranges: Dict[str, Tuple[int, int]] = {
        "0-4": (0, 4),
        "5-18": (5, 18),
        "19-64": (19, 64),
        "65+": (65, 85)
    }
    for b in age_bands:
        share = float(age_df[age_df["age_band"] == b]["share"].sum())
        age_probs.append(share)
    age_probs = np.array(age_probs, dtype=np.float64)
    age_probs /= age_probs.sum()

    agent_age_bands = rng.choice(len(age_bands), size=scale_agents, p=age_probs)
    agent_ages = np.zeros(scale_agents, dtype=np.int8)
    for b_idx, b_name in enumerate(age_bands):
        mask = (agent_age_bands == b_idx)
        n_band = int(np.sum(mask))
        if n_band > 0:
            low, high = age_ranges.get(b_name, (20, 60))
            agent_ages[mask] = rng.integers(low, high + 1, size=n_band, dtype=np.int8)

    agent_sexes = rng.integers(0, 2, size=scale_agents, dtype=np.int8)

    agent_occupations = np.zeros(scale_agents, dtype=np.int8)
    workable_mask = (agent_ages >= 18) & (agent_ages < 65)
    emp_rate = 0.60
    if pack.quick_inputs:
        emp_rate = pack.quick_inputs.employment_rate
    elif (region_dir / "employment.csv").exists():
        emp_df = pd.read_csv(region_dir / "employment.csv")
        emp_rate = float(emp_df["employment_rate"].mean())

    work_indices = np.where(workable_mask)[0]
    is_employed = rng.random(size=len(work_indices)) < emp_rate
    employed_indices = work_indices[is_employed]
    agent_occupations[employed_indices] = rng.choice([1, 2], size=len(employed_indices), p=[0.75, 0.25]).astype(np.int8)

    agent_areas = np.empty(scale_agents, dtype=np.int16)
    curr_idx = 0
    for a_int, count in enumerate(area_agent_counts):
        agent_areas[curr_idx:curr_idx + count] = a_int
        curr_idx += count

    # 4. Household composition
    target_hh_size = 3.5
    if pack.quick_inputs:
        target_hh_size = pack.quick_inputs.avg_household_size
    elif "households" in areas_df.columns:
        target_hh_size = float(areas_df["population"].sum() / max(1.0, areas_df["households"].sum()))

    household_ids = compose_households(agent_ages, target_hh_size, rng)

    # 5. Venues & Commute & Social Spaces (Spec 9)
    venues_path = region_dir / "venues.csv"
    venues_df = pd.read_csv(venues_path) if venues_path.exists() else pd.DataFrame()

    commute_path = region_dir / "commute_od.csv"
    commute_df = pd.read_csv(commute_path) if commute_path.exists() else None

    registry, schools_by_area, workplaces_by_area, all_venues_by_type = instantiate_venues(venues_df, area_id_to_int, rng)
    workplace_ids, school_ids, commute_areas = assign_venues_and_commute(
        agent_ages, agent_areas, agent_occupations, commute_df,
        area_id_to_int, schools_by_area, workplaces_by_area, rng
    )
    pref_market_ids, pref_leisure_ids = assign_social_venues(agent_areas, all_venues_by_type, rng)

    # 6. Traits and baseline comorbidity
    traits = sample_traits(scale_agents, behavior_pack, rng)

    # Risk factors / vulnerability (Spec 5.1)
    risk_factors_path = region_dir / "risk_factors.csv"
    comorb_path = region_dir / "comorbidity.csv"

    risk_bits = np.zeros(scale_agents, dtype=np.uint32)
    comorb_mults = np.ones(scale_agents, dtype=np.float32)

    if risk_factors_path.exists():
        rf_df = pd.read_csv(risk_factors_path)
        factor_ids = rf_df["factor_id"].unique().tolist()
        for f_idx, fid in enumerate(factor_ids[:32]):
            bit_mask = 1 << f_idx
            sub = rf_df[rf_df["factor_id"] == fid]
            prev = float(sub["prevalence"].mean()) if not sub.empty else 0.10
            has_factor = rng.random(size=scale_agents) < prev
            risk_bits[has_factor] |= np.uint32(bit_mask)
            comorb_mults[has_factor] *= 1.35
    elif comorb_path.exists():
        comorb_df = pd.read_csv(comorb_path)
        comorb_mults = assign_comorbidity_multipliers(agent_ages, agent_sexes, comorb_df, rng)
        has_cond = comorb_mults > 1.05
        risk_bits[has_cond] |= np.uint32(1)

    # 7. Structured life histories (Spec 9)
    # Income band (0=low, 1=middle, 2=high): conditional on occupation
    income_band = np.ones(scale_agents, dtype=np.int8)  # default middle
    income_band[agent_occupations == 0] = rng.choice([0, 1], size=np.sum(agent_occupations == 0), p=[0.7, 0.3])
    income_band[agent_occupations == 1] = rng.choice([0, 1, 2], size=np.sum(agent_occupations == 1), p=[0.25, 0.55, 0.20])
    income_band[agent_occupations == 2] = rng.choice([0, 1, 2], size=np.sum(agent_occupations == 2), p=[0.35, 0.55, 0.10])

    # Financial buffer in [0, 1]
    financial_buffer = np.clip(
        0.25 * income_band + rng.normal(0.4, 0.15, size=scale_agents),
        0.05, 0.98
    ).astype(np.float32)

    # Household role: 0=child (<18), 1=primary_earner, 2=caregiver_adult, 3=elder (65+)
    household_role = np.ones(scale_agents, dtype=np.int8)
    household_role[agent_ages < 18] = 0
    household_role[agent_ages >= 65] = 3
    # Among adults 18-64:
    adult_mask = (agent_ages >= 18) & (agent_ages < 65)
    employed_adult = adult_mask & (agent_occupations > 0)
    household_role[employed_adult] = 1
    non_emp_adult = adult_mask & (agent_occupations == 0)
    household_role[non_emp_adult] = 2

    # Caregiver status: designated caregiver adults
    caregiver = (household_role == 2) | ((agent_sexes == 1) & adult_mask & (rng.random(size=scale_agents) < 0.20))

    # Past bereavement (15% baseline experience)
    past_bereavement = rng.random(size=scale_agents) < 0.15

    # Prior authority experience (correlated with institutional trust)
    prior_authority_exp = np.clip(
        0.6 * traits["institutional_trust"] + rng.normal(0.2, 0.1, size=scale_agents),
        0.0, 1.0
    ).astype(np.float32)

    # Routine template:
    # 0=student, 1=office_worker, 2=shift_worker, 3=informal_worker, 4=homemaker, 5=retired
    routine_template = np.zeros(scale_agents, dtype=np.int8)
    routine_template[agent_ages < 18] = 0
    routine_template[agent_ages >= 65] = 5
    routine_template[employed_adult & (agent_occupations == 1)] = 1
    routine_template[employed_adult & (agent_occupations == 2)] = 2
    routine_template[non_emp_adult & caregiver] = 4
    routine_template[non_emp_adult & ~caregiver] = 3

    # Self-care score (Spec 6.3): derived from education/income proxy, compliance, caregiver, and financial buffer
    self_care = np.clip(
        0.35 * traits["compliance"] +
        0.30 * (income_band / 2.0) +
        0.20 * financial_buffer +
        0.15 * (1.0 - 0.5 * (household_role == 0)),
        0.05, 0.99
    ).astype(np.float32)

    # Household support score: household size and caregiver in household
    support = np.full(scale_agents, 0.65, dtype=np.float32)
    # Give boost to agents residing in households with an active caregiver
    hh_with_caregiver = np.unique(household_ids[caregiver])
    in_caregiver_hh = np.isin(household_ids, hh_with_caregiver)
    support[in_caregiver_hh] = np.clip(support[in_caregiver_hh] + 0.25, 0.1, 0.98)
    support[household_role == 0] = np.clip(support[household_role == 0] + 0.15, 0.1, 0.99)

    # Alternative care access (distance/urban proxy)
    alt_care_access = np.clip(
        0.50 + 0.25 * (income_band / 2.0) + rng.normal(0.0, 0.1, size=scale_agents),
        0.10, 0.95
    ).astype(np.float32)

    unserved_days = np.zeros(scale_agents, dtype=np.int16)

    # WFH possibility for service workers
    wfh_possible = (agent_occupations == 1) & (rng.random(size=scale_agents) < 0.40)

    return PopulationSoA(
        n_agents=scale_agents,
        total_population_represented=total_real_pop,
        sampling_ratio=sampling_ratio,
        agent_id=np.arange(scale_agents, dtype=np.int32),
        area_id=agent_areas,
        household_id=household_ids,
        age=agent_ages,
        sex=agent_sexes,
        occupation_class=agent_occupations,
        workplace_id=workplace_ids,
        school_id=school_ids,
        commute_area=commute_areas,
        wfh_possible=wfh_possible,
        comorbidity_multiplier=comorb_mults,
        compliance=traits["compliance"],
        rumor_susceptibility=traits["rumor_susceptibility"],
        trust=traits["institutional_trust"],
        risk_tolerance=traits["risk_tolerance"],
        income_band=income_band,
        household_role=household_role,
        caregiver=caregiver,
        financial_buffer=financial_buffer,
        past_bereavement=past_bereavement,
        prior_authority_experience=prior_authority_exp,
        routine_template=routine_template,
        pref_market_id=pref_market_ids,
        pref_leisure_id=pref_leisure_ids,
        risk_factor_bits=risk_bits,
        self_care=self_care,
        support=support,
        alt_care_access=alt_care_access,
        unserved_days=unserved_days,
        int_to_area_id=int_to_area_id,
        area_id_to_int=area_id_to_int
    )
