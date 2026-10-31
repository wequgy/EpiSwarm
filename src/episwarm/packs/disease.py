"""Pydantic schemas for DiseasePack configuration and state-graph definitions."""

from enum import Enum
from typing import Dict, List, Literal, Optional, Set
from pydantic import BaseModel, Field, model_validator
from episwarm.packs.schema import ProvenanceRecord


class BedCategory(str, Enum):
    """Healthcare bed categories required during severe disease stages."""
    NONE = "none"
    GENERAL = "general"
    HDU = "hdu"
    ICU = "icu"
    ICU_VENT = "icu_vent"


class DiseaseState(BaseModel):
    """A compartment in the disease progression state graph."""
    name: str = Field(..., min_length=1, description="Identifier for this health state (e.g. S, E, I_asymp, I_symp, H, ICU, R, D)")
    infectious: bool = Field(default=False, description="Whether individuals in this state can transmit pathogen")
    relative_infectiousness: float = Field(
        default=0.0, ge=0.0, le=10.0,
        description="Transmission multiplier relative to reference infectious state (e.g., 0.5 for asymptomatic)"
    )
    needs_bed: BedCategory = Field(default=BedCategory.NONE, description="Bed resource requirement")
    needs_oxygen: bool = Field(default=False, description="Whether state requires supplementary medical oxygen")
    absorbing: bool = Field(default=False, description="Terminal state with no outgoing transitions (e.g. R, D)")


class DurationDistribution(BaseModel):
    """Stochastic dwell time distribution within a disease compartment."""
    type: Literal["constant", "exponential", "gamma", "lognormal"] = "gamma"
    mean_days: float = Field(..., gt=0.0, description="Mean duration in days")
    sd_days: Optional[float] = Field(default=None, gt=0.0, description="Standard deviation in days (for gamma/lognormal)")

    @model_validator(mode="after")
    def validate_sd(self):
        if self.type in ("gamma", "lognormal") and self.sd_days is None:
            # Default sd to 0.4 * mean if unspecified
            self.sd_days = max(0.1, 0.4 * self.mean_days)
        return self


class StateTransition(BaseModel):
    """Directed edge between compartments with transition probability and duration."""
    from_state: str
    to_state: str
    base_probability: float = Field(..., ge=0.0, le=1.0, description="Baseline transition probability")
    duration: DurationDistribution
    age_multipliers: Dict[str, float] = Field(
        default_factory=dict,
        description="Age-band specific multiplier on base_probability (e.g. {'65+': 2.5})"
    )
    comorbidity_multipliers: Dict[str, float] = Field(
        default_factory=dict,
        description="Comorbidity specific multiplier on base_probability"
    )


class TransmissionConfig(BaseModel):
    """Pathogen transmission characteristics."""
    mode: Literal["person_to_person"] = "person_to_person"
    r0: Optional[float] = Field(default=None, gt=0.0, le=30.0, description="Basic reproduction number R0")
    beta: Optional[float] = Field(default=None, gt=0.0, description="Per-contact transmission probability per unit time")
    overdispersion_k: float = Field(
        default=0.16, gt=0.0, le=10.0,
        description="Negative binomial dispersion parameter k for secondary transmissions (lower = more super-spreading)"
    )
    seasonality_amplitude: float = Field(default=0.0, ge=0.0, le=1.0)
    waning_immunity_days: Optional[float] = Field(default=None, gt=0.0, description="Mean days until transition from R to S")

    @model_validator(mode="after")
    def check_r0_or_beta(self):
        if self.r0 is None and self.beta is None:
            raise ValueError("At least one of 'r0' or 'beta' must be specified.")
        return self


class OverflowMortalityConfig(BaseModel):
    """Mortality amplification factors when healthcare capacity is saturated."""
    bed_unavailable_mortality_multiplier: float = Field(
        default=2.0, ge=1.0, le=10.0,
        description="Mortality multiplier for patients needing a general bed when none is available"
    )
    icu_unavailable_mortality_multiplier: float = Field(
        default=3.5, ge=1.0, le=15.0,
        description="Mortality multiplier for patients needing ICU when none is available"
    )
    oxygen_unavailable_mortality_multiplier: float = Field(
        default=2.5, ge=1.0, le=10.0,
        description="Mortality multiplier for hypoxemic patients when oxygen buffer is exhausted"
    )
    compliance_mortality_benefit: float = Field(
        default=0.85, ge=0.0, le=1.0,
        description="Mortality scaling for fully compliant individuals (better adherence to triage/care)"
    )
    non_compliance_mortality_penalty: float = Field(
        default=1.25, ge=1.0, le=3.0,
        description="Mortality scaling for non-compliant individuals (delayed presentation, refusal of care)"
    )


class DiseasePack(BaseModel):
    """Complete Disease specification bundle."""
    name: str = Field(..., min_length=1)
    description: str = ""
    provenance: ProvenanceRecord
    transmission: TransmissionConfig
    states: List[DiseaseState]
    transitions: List[StateTransition]
    overflow: OverflowMortalityConfig = Field(default_factory=OverflowMortalityConfig)
    sanitation_sensitivity: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Pathogen sensitivity to environmental sanitation deficits (0 = airborne only, 1 = fomite/contact sensitive)"
    )
    disease_specific_risks: Dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_graph_structure(self):
        state_dict = {s.name: s for s in self.states}
        state_names = set(state_dict.keys())
        absorbing_states = {s.name for s in self.states if s.absorbing}

        if not absorbing_states:
            raise ValueError("Disease graph must contain at least one absorbing state (e.g. 'R' or 'D').")

        # Verify transition edges
        for t in self.transitions:
            if t.from_state not in state_names:
                raise ValueError(f"Transition references unknown from_state '{t.from_state}'")
            if t.to_state not in state_names:
                raise ValueError(f"Transition references unknown to_state '{t.to_state}'")
            if t.from_state in absorbing_states:
                raise ValueError(f"Absorbing state '{t.from_state}' cannot have outgoing transitions")

        # Verify outgoing transition probabilities sum <= 1.0 (with small float tolerance)
        from collections import defaultdict
        out_prob: Dict[str, float] = defaultdict(float)
        for t in self.transitions:
            out_prob[t.from_state] += t.base_probability

        for s_name, prob_sum in out_prob.items():
            if prob_sum > 1.0001:
                raise ValueError(
                    f"Outgoing transition probabilities for state '{s_name}' sum to {prob_sum:.4f} > 1.0"
                )

        # Reachability check: verify that every state with transitions can eventually reach an absorbing state
        from collections import defaultdict
        adj: Dict[str, List[str]] = defaultdict(list)
        for t in self.transitions:
            adj[t.from_state].append(t.to_state)

        for source_state in list(adj.keys()):
            visited: Set[str] = set()
            queue = [source_state]
            while queue:
                curr = queue.pop(0)
                if curr not in visited:
                    visited.add(curr)
                    queue.extend(adj[curr])
            if not (visited & absorbing_states):
                raise ValueError(
                    f"No absorbing state is reachable from state '{source_state}'"
                )

        return self
