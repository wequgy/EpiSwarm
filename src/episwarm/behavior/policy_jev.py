"""TypeSafe AI Jev (SystemOne) decision policy implementation with automatic fallback."""

import os
import requests
from typing import Dict, List, Optional

from episwarm.packs.behavior import DecisionQuestion
from episwarm.behavior.buckets import AgentBucket, SituationBucket
from episwarm.behavior.policy_base import DecisionPolicy
from episwarm.behavior.policy_rules import RulePolicy


class JevPolicy(DecisionPolicy):
    """TypeSafe AI Jev decision model predicting probabilistic policy choices."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: str = "jev-latest",
        cache=None,
        fallback_policy: Optional[DecisionPolicy] = None
    ):
        super().__init__(cache)
        self.api_key = api_key or os.getenv("TYPESAFE_API_KEY")
        self.api_url = api_url or os.getenv("TYPESAFE_API_URL", "https://api.typesafe.ai/v1/systemone")
        self.model = model
        self.fallback = fallback_policy or RulePolicy(cache=self.cache)

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

        # 1. Check persistent SQLite cache
        cached = self.cache.get("jev", question.id, sit_hash, buck_hash)
        if cached:
            return cached

        # 2. If no API key configured, invoke fallback directly
        if not self.api_key:
            self.fallback_count += 1
            return self.fallback.decide(question, situation, bucket, context)

        # 3. Construct prompt (Notice: question ID is omitted per specification)
        prompt_text = (
            f"Context: {context}\n"
            f"Individual Profile: Age group {bucket.age_band}, occupation {bucket.occupation_class}, "
            f"chronic condition: {'yes' if bucket.has_comorbidity else 'no'}, trust level: {bucket.trust_band}, risk tolerance: {bucket.risk_tolerance_band}.\n"
            f"Current Situation: Health status: {situation.health_state_group}, local outbreak level: {situation.local_risk_level}, "
            f"active public health measures: {situation.active_measures}, household member ill: {'yes' if situation.household_member_sick else 'no'}.\n"
            f"Decision Instruction: {question.plain_instructions}"
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "question": prompt_text,
            "options": question.options
        }

        try:
            resp = requests.post(self.api_url, json=payload, headers=headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                # Format: {"probabilities": {"opt1": 0.7, "opt2": 0.3}} or list of weights
                probs_raw = data.get("probabilities", {})
                if isinstance(probs_raw, dict) and all(opt in probs_raw for opt in question.options):
                    probs = {opt: float(probs_raw[opt]) for opt in question.options}
                    # Normalize
                    tot = sum(probs.values())
                    if tot > 0:
                        probs = {opt: round(v / tot, 4) for opt, v in probs.items()}
                        self.cache.put("jev", question.id, sit_hash, buck_hash, probs)
                        return probs

            # Non-200 or unexpected payload: fallback
            self.fallback_count += 1
            return self.fallback.decide(question, situation, bucket, context)

        except Exception:
            # Network or timeout failure: fallback cleanly
            self.fallback_count += 1
            return self.fallback.decide(question, situation, bucket, context)
