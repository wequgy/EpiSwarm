"""Fast deterministic rule-based decision policy based on demographic traits and epidemiological triggers."""

from typing import Dict, List, Optional
import numpy as np

from episwarm.packs.behavior import DecisionQuestion
from episwarm.behavior.buckets import AgentBucket, SituationBucket
from episwarm.behavior.policy_base import DecisionPolicy


class RulePolicy(DecisionPolicy):
    """Deterministic, trait- and symptom-driven baseline policy with instant in-memory evaluation."""

    def __init__(self, cache=None):
        super().__init__(cache)
        self._rule_mem_cache: Dict[str, Dict[str, float]] = {}

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
        key = f"{question.id}::{sit_hash}::{buck_hash}"

        # 1. Instant in-memory tier
        if key in self._rule_mem_cache:
            return self._rule_mem_cache[key]

        # 2. Check persistent cache
        cached = self.cache.get("rule", question.id, sit_hash, buck_hash)
        if cached:
            self._rule_mem_cache[key] = cached
            return cached

        # 3. Fast deterministic evaluation
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
        elif bucket.trust_band == "low":
            risk_score -= 0.15

        risk_score = float(np.clip(risk_score, 0.05, 0.95))

        out_probs = {}
        if question.id == "wear_mask":
            out_probs = {"yes": risk_score, "no": 1.0 - risk_score}
        elif question.id == "isolate_symptomatic":
            iso_p = float(np.clip(risk_score + 0.20, 0.10, 0.99))
            out_probs = {"yes": iso_p, "no": 1.0 - iso_p}
        elif question.id == "workplace_attendance":
            if bucket.occupation_class == "essential":
                out_probs = {"usual": 0.70, "reduced": 0.20, "avoid": 0.10}
            else:
                p_avoid = float(np.clip(risk_score * 0.8, 0.05, 0.80))
                p_red = float(np.clip(risk_score * 0.4, 0.10, 0.40))
                p_usual = max(0.05, 1.0 - p_avoid - p_red)
                tot = p_avoid + p_red + p_usual
                out_probs = {"avoid": p_avoid / tot, "reduced": p_red / tot, "usual": p_usual / tot}
        elif question.id == "accept_vaccine":
            vax_p = float(np.clip(risk_score + 0.10, 0.10, 0.95))
            out_probs = {"yes": vax_p, "no": 1.0 - vax_p}
        else:
            n_opts = len(question.options)
            out_probs = {opt: 1.0 / n_opts for opt in question.options}

        self._rule_mem_cache[key] = out_probs
        self.cache.put("rule", question.id, sit_hash, buck_hash, out_probs)
        return out_probs
