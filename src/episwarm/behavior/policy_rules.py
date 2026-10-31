"""Rule-based decision policy based on demographic traits and epidemiological triggers."""

from typing import Dict, List, Optional
import numpy as np

from episwarm.packs.behavior import DecisionQuestion
from episwarm.behavior.buckets import AgentBucket, SituationBucket
from episwarm.behavior.policy_base import DecisionPolicy


class RulePolicy(DecisionPolicy):
    """Deterministic, trait- and symptom-driven baseline policy."""

    def decide(
        self,
        question: DecisionQuestion,
        situation: SituationBucket,
        bucket: AgentBucket,
        context: str = ""
    ) -> Dict[str, float]:
        self.total_queries += 1
        sit_hash = situation.to_hash()
        buck_hash = bucket.to_hash()

        # Check cache
        cached = self.cache.get("rule", question.id, sit_hash, buck_hash)
        if cached:
            return cached

        # Calculate base risk awareness [0, 1]
        risk_score = 0.20
        if situation.local_risk_level == "medium":
            risk_score += 0.20
        elif situation.local_risk_level in ("high", "critical"):
            risk_score += 0.45

        if situation.health_state_group == "symptomatic":
            risk_score += 0.35
        if situation.household_member_sick:
            risk_score += 0.20

        # Modulate by psychographics
        if bucket.risk_tolerance_band == "low":
            risk_score += 0.15
        elif bucket.risk_tolerance_band == "high":
            risk_score -= 0.15

        if bucket.trust_band == "high":
            risk_score += 0.10

        risk_score = float(np.clip(risk_score, 0.05, 0.95))

        # Build options distribution based on question
        opts = question.options
        probs: Dict[str, float] = {}

        if question.id in ("workplace_attendance", "market_visits"):
            # Typical options: ["usual", "reduced", "avoid"] or ["usual", "essential_only", "avoid"]
            p_avoid = float(np.clip(risk_score * 0.8, 0.05, 0.80))
            p_reduced = float(np.clip(risk_score * 0.5, 0.15, 0.60))
            p_usual = max(0.05, 1.0 - (p_avoid + p_reduced))
            total = p_usual + p_reduced + p_avoid
            probs = {
                opts[0]: round(p_usual / total, 4),
                opts[1]: round(p_reduced / total, 4),
                opts[2]: round(p_avoid / total, 4)
            }
        elif question.type.value in ("noul", "score") or len(opts) == 2:
            # Binary choices like ["yes", "no"]
            p_yes = risk_score
            p_no = 1.0 - p_yes
            probs = {opts[0]: round(p_yes, 4), opts[1]: round(p_no, 4)}
        else:
            # Uniform fallback
            u = 1.0 / len(opts)
            probs = {opt: round(u, 4) for opt in opts}

        self.cache.put("rule", question.id, sit_hash, buck_hash, probs)
        return probs

