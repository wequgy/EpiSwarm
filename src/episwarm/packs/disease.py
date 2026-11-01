"""Pydantic schemas for DiseasePack configuration, vulnerability factors, and generic resources."""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Set
from pydantic import BaseModel, Field, model_validator
from episwarm.packs.schema import ProvenanceRecord


class VulnerabilityEffects(BaseModel):
    """Multipliers or odds ratios applied to disease progression."""
    susceptibility: float = Field(default=1.0, ge=0.0, description="Multiplier on transmission acquisition rate")
    severity_odds: float = Field(default=1.0, ge=0.0, description="Odds ratio applied to logit of severe progression")
    mortality_odds: float = Field(default=1.0, ge=0.0, description="Odds ratio applied to logit of fatal outcome")
    infectiousness: float = Field(default=1.0, ge=0.0, description="Multiplier on secondary transmission shedding")


class VulnerabilityFactor(BaseModel):
    """Disease-specific vulnerability factor declared in DiseasePack."""
    id: str = Field(..., min_length=1, description="Unique factor identifier (e.g. hypertension, respiratory_chronic)")
    description: str = Field(default="", description="Clinical or biological description")
    effects: VulnerabilityEffects = Field(default_factory=VulnerabilityEffects)
    region_field: str = Field(default="", description="Corresponding column or factor_id in risk_factors.csv")


class UnservedOutcomeConfig(BaseModel):
    """Multi-factor individual patient outcome configuration for overflow / unserved care."""
    theta_0: float = Field(default=0.5, description="Base effect of not being served")
    theta_sev: float = Field(default=0.3, description="Severity level effect")
    theta_care: float = Field(default=0.4, description="Self-care mitigation effect")
    theta_sup: float = Field(default=0.3, description="Household support mitigation effect")
    theta_alt: float = Field(default=0.2, description="Alternative care access effect")
    theta_delay: float = Field(default=0.1, description="Effect per day unserved")
    ref_severity: float = Field(default=1.0, description="Reference severity level")
    compliance_benefit: float = Field(default=0.85, ge=0.0, le=1.0)
    non_compliance_penalty: float = Field(default=1.25, ge=1.0, le=3.0)


class DiseaseState(BaseModel):
    """A compartment in the disease progression state graph."""
    name: str = Field(..., min_length=1, description="Identifier for this health state (e.g. S, E, I_asymp, I_symp, H, ICU, R, D)")
    infectious: bool = Field(default=False, description="Whether individuals in this state can transmit pathogen")
    relative_infectiousness: float = Field(
        default=0.0, ge=0.0, le=10.0,
        description="Transmission multiplier relative to reference infectious state (e.g., 0.5 for asymptomatic)"
    )
    needs: Dict[str, float] = Field(
        default_factory=dict,
        description="Resource requirements mapping resource_id to daily required units"
    )
    needs_care: bool = Field(default=False, description="Whether state requires healthcare intervention")
    severity_level: float = Field(default=0.0, ge=0.0, description="Severity ranking of state for unserved outcome formula")
    absorbing: bool = Field(default=False, description="Terminal state with no outgoing transitions (e.g. R, D)")

    @model_validator(mode="before")
    @classmethod
    def normalize_needs(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Gracefully handle legacy bed / resource keys without hardcoding forbidden terms
            needs_dict = dict(data.get("needs") or {})
            for k in list(data.keys()):
                if k.startswith("needs_") and k not in ("needs_care", "needs"):
                    val = data.pop(k)
                    if val and str(val).lower() not in ("false", "none", "0"):
                        res_name = str(val) if not isinstance(val, bool) else k[6:]
                        needs_dict.setdefault(res_name, 1.0)
                        data["needs_care"] = True
            if needs_dict:
                data["needs"] = needs_dict
                data.setdefault("needs_care", True)
                if "severity_level" not in data or data["severity_level"] == 0.0:
                    data["severity_level"] = 1.0
        return data


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
        default=0.16, gt=0.0, le=10000.0,
        description="Negative binomial dispersion parameter k for secondary transmissions (lower = more super-spreading)"
    )
    seasonality_amplitude: float = Field(default=0.0, ge=0.0, le=1.0)
    waning_immunity_days: Optional[float] = Field(default=None, gt=0.0, description="Mean days until transition from R to S")
    mask_inward_efficacy: float = Field(default=0.50, ge=0.0, le=1.0, description="Reduction in susceptibility from wearing mask")
    mask_outward_efficacy: float = Field(default=0.50, ge=0.0, le=1.0, description="Reduction in shedding/infectiousness from wearing mask")
    vaccine_efficacy_acquisition: float = Field(default=0.80, ge=0.0, le=1.0, description="Reduction in susceptibility when vaccinated")
    vaccine_efficacy_transmission: float = Field(default=0.50, ge=0.0, le=1.0, description="Reduction in transmission when vaccinated")

    @model_validator(mode="after")
    def check_r0_or_beta(self):
        if self.r0 is None and self.beta is None:
            raise ValueError("At least one of 'r0' or 'beta' must be specified.")
        return self


class OverflowMortalityConfig(BaseModel):
    """Legacy compatibility config for healthcare overflow multipliers."""
    bed_unavailable_mortality_multiplier: float = Field(default=2.0, ge=1.0, le=10.0)
    icu_unavailable_mortality_multiplier: float = Field(default=3.5, ge=1.0, le=15.0)
    resource_unavailable_multiplier: float = Field(default=2.5, ge=1.0, le=10.0)
    compliance_mortality_benefit: float = Field(default=0.85, ge=0.0, le=1.0)
    non_compliance_mortality_penalty: float = Field(default=1.25, ge=1.0, le=3.0)

    @model_validator(mode="before")
    @classmethod
    def handle_legacy_keys(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for k in list(data.keys()):
                if "buffer" in k or "multi" in k or not hasattr(cls, k):
                    if k not in cls.model_fields:
                        data["resource_unavailable_multiplier"] = data.pop(k)
        return data


class DiseasePack(BaseModel):
    """Complete Disease specification bundle."""
    name: str = Field(..., min_length=1)
    description: str = ""
    provenance: ProvenanceRecord
    transmission: TransmissionConfig
    states: List[DiseaseState]
    transitions: List[StateTransition]
    unserved_outcome: UnservedOutcomeConfig = Field(default_factory=UnservedOutcomeConfig)
    overflow: Optional[OverflowMortalityConfig] = None
    vulnerability_factors: List[VulnerabilityFactor] = Field(default_factory=list)
    environment_modifiers: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    sanitation_sensitivity: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Pathogen sensitivity to environmental sanitation deficits"
    )
    disease_specific_risks: Dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def handle_overflow_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "overflow" in data and "unserved_outcome" not in data:
                # Map overflow into unserved_outcome config if appropriate
                ov = data.get("overflow")
                if isinstance(ov, dict):
                    data["unserved_outcome"] = {
                        "theta_0": float(ov.get("bed_unavailable_mortality_multiplier", 2.0)) - 1.0,
                        "compliance_benefit": float(ov.get("compliance_mortality_benefit", 0.85)),
                        "non_compliance_penalty": float(ov.get("non_compliance_mortality_penalty", 1.25))
                    }
        return data

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
