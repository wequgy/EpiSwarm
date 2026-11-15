"""Gemini Decision 1 behavioral policy implementation (Stage R3.3).

Executes behavioral decision queries through the Gemini Decision 1 API (gemini-decision-1)
with zero output tokens, calibrated probabilities, prompt-hash caching, and offline fallback.
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional
import numpy as np

from episwarm.packs.behavior import DecisionQuestion
from episwarm.behavior.buckets import AgentBucket, SituationBucket
from episwarm.behavior.cache import DecisionCache
from episwarm.behavior.policy_base import DecisionPolicy
from episwarm.ai.gemini_decision import GeminiDecisionClient


class GeminiDecisionPolicy(DecisionPolicy):
    """Behavioral policy driven by Gemini Decision 1 (gemini-decision-1)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache: Optional[DecisionCache] = None,
        model: str = "gemini-decision-1",
    ):
        super().__init__(cache=cache)
        self.client = GeminiDecisionClient(api_key=api_key, model=model)
        self.model_name = model

    def decide(
        self,
        question: DecisionQuestion,
        situation: SituationBucket,
        bucket: AgentBucket,
        context: str = "",
    ) -> Dict[str, float]:
        """Compute probability distribution over question options using gemini-decision-1."""
        self.total_queries += 1

        # Check in-memory / persistent DecisionCache first
        sit_hash = situation.to_hash()
        bkt_hash = bucket.to_hash()
        cached = self.cache.get(self.model_name, question.id, sit_hash, bkt_hash)
        if cached is not None:
            return cached

        # Shared input context describes current epidemiological situation
        input_ctx = (
            f"Epidemiological Situation:\n"
            f"- Health state: {situation.health_state_group}\n"
            f"- Local risk level: {situation.local_risk_level}\n"
            f"- Active measures: {situation.active_measures}\n"
            f"- Household sick: {situation.household_member_sick}\n"
            f"- Additional context: {context}\n"
        )

        # Question specifies agent citizen cohort and choices
        opt_names = [opt if isinstance(opt, str) else getattr(opt, "name", str(opt)) for opt in question.options]
        qid = f"{question.id}_{situation.to_hash()}_{bucket.to_hash()}"

        q_spec = {
            qid: {
                "type": "choice",
                "instructions": (
                    f"Citizen Profile: Age band={bucket.age_band}, Occupation={bucket.occupation_class}, "
                    f"Comorbidity={bucket.has_comorbidity}, Trust={bucket.trust_band}, Risk tolerance={bucket.risk_tolerance_band}. "
                    f"Choose the behavioral action for this citizen under current conditions."
                ),
                "options": opt_names,
            }
        }

        decisions = self.client.make_decisions(input_context=input_ctx, questions=q_spec)
        result = decisions.get(qid)

        if result and not result.fallback and result.probabilities:
            probs = {opt: float(result.probabilities.get(opt, 1e-4)) for opt in opt_names}
            total = sum(probs.values())
            probs = {k: v / total for k, v in probs.items()}
        else:
            self.fallback_count += 1
            # Calibrated behavioral prior based on situation threat and age
            probs = self._calibrated_fallback_probs(question, situation, bucket)

        self.cache.put(self.model_name, question.id, sit_hash, bkt_hash, probs)
        return probs

    def _calibrated_fallback_probs(
        self,
        question: DecisionQuestion,
        situation: SituationBucket,
        bucket: AgentBucket,
    ) -> Dict[str, float]:
        """Empirical fallback prior based on threat level and economic vulnerability."""
        opt_names = [opt if isinstance(opt, str) else getattr(opt, "name", str(opt)) for opt in question.options]
        n_opts = len(opt_names)
        if n_opts == 0:
            return {}
        if n_opts == 1:
            return {opt_names[0]: 1.0}

        # Higher threat and higher vulnerability increase protective choices
        risk_score = 0.8 if situation.local_risk_level in ("high", "critical") else (0.4 if situation.local_risk_level == "medium" else 0.1)
        age_score = 0.7 if "65" in bucket.age_band else 0.3
        protective_weight = min(0.90, max(0.10, 0.5 * risk_score + 0.5 * age_score))

        probs = {}
        for idx, opt in enumerate(opt_names):
            if "isolate" in opt or "stay_home" in opt or "strict" in opt:
                probs[opt] = protective_weight
            elif "routine" in opt or "no" in opt or "maintain" in opt:
                probs[opt] = (1.0 - protective_weight) * 0.7
            else:
                probs[opt] = (1.0 - protective_weight) * 0.3

        total = sum(probs.values())
        if total > 0:
            return {k: v / total for k, v in probs.items()}
        return {opt: 1.0 / n_opts for opt in opt_names}
