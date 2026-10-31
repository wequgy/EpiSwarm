"""Compact discrete state bucketing for behavioral decision policies."""

import hashlib
from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np


@dataclass(frozen=True)
class AgentBucket:
    """Coarse discrete demographic and trait archetype."""
    age_band: str               # "0-4", "5-18", "19-64", "65+"
    occupation_class: str       # "none", "service", "manufacturing"
    has_comorbidity: bool
    trust_band: str             # "low", "medium", "high"
    risk_tolerance_band: str    # "low", "medium", "high"

    def to_hash(self) -> str:
        s = f"{self.age_band}_{self.occupation_class}_{self.has_comorbidity}_{self.trust_band}_{self.risk_tolerance_band}"
        return hashlib.md5(s.encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class SituationBucket:
    """Coarse environmental and epidemiological situation."""
    health_state_group: str     # "susceptible", "symptomatic", "recovering"
    local_risk_level: str       # "low", "medium", "high", "critical"
    active_measures: str        # e.g. "none", "school_closure", "work_reduction", "lockdown"
    household_member_sick: bool

    def to_hash(self) -> str:
        s = f"{self.health_state_group}_{self.local_risk_level}_{self.active_measures}_{self.household_member_sick}"
        return hashlib.md5(s.encode("utf-8")).hexdigest()[:12]


def continuous_to_band(val: float) -> str:
    """Discretize [0, 1] continuous value into coarse 3-tier band."""
    if val < 0.35:
        return "low"
    elif val < 0.65:
        return "medium"
    return "high"
