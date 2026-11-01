"""Archetype collapsing and risk grouping for behavioral decision policies.

Reduces hundreds of discrete bucket combinations to core demographic/situational archetypes,
enabling cloud and local LLMs to simulate city populations within rate quotas (e.g. Gemini 15 RPM).
"""

from typing import Dict, Tuple
from episwarm.behavior.buckets import AgentBucket, SituationBucket


def get_archetype_key(bucket: AgentBucket, situation: SituationBucket) -> Tuple[str, str]:
    """Map granular AgentBucket and SituationBucket to coarse population archetypes.

    Returns:
        (agent_archetype, situation_archetype)
    """
    # 1. Demographic & Risk Tolerance Archetype
    if bucket.age_band == "65+" or bucket.has_comorbidity:
        ag_arch = "elderly_vulnerable"
    elif bucket.trust_band == "low" and bucket.risk_tolerance_band in ("medium", "high"):
        ag_arch = "skeptical_risk_tolerant"
    elif bucket.occupation_class in ("service", "manufacturing"):
        ag_arch = "essential_worker"
    else:
        ag_arch = "cautious_resident"

    # 2. Situational Outbreak Context
    if situation.health_state_group == "symptomatic" or situation.household_member_sick:
        sit_arch = "personal_exposure"
    elif situation.local_risk_level in ("high", "critical") or situation.active_measures not in ("none", ""):
        sit_arch = "high_risk_mandates"
    else:
        sit_arch = "low_risk_baseline"

    return ag_arch, sit_arch


ARCHETYPE_DESCRIPTIONS: Dict[str, str] = {
    "elderly_vulnerable": "Senior citizen (65+) or clinically vulnerable individual with pre-existing health conditions.",
    "skeptical_risk_tolerant": "Younger/working resident with low trust in official health advisories and high risk tolerance.",
    "essential_worker": "Frontline or service/manufacturing employee requiring in-person commute, moderate trust.",
    "cautious_resident": "Working-age urban resident with high civic trust, capable of remote adherence.",
}

SITUATION_DESCRIPTIONS: Dict[str, str] = {
    "personal_exposure": "Resident has developed respiratory symptoms or a direct household member is confirmed ill.",
    "high_risk_mandates": "Local area is experiencing an active outbreak surge with government advisories/mandates in place.",
    "low_risk_baseline": "Low community transmission; routine baseline monitoring with no active restrictions.",
}
