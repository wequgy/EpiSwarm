"""Google Gemini behavioral decision policy with structured probability extraction."""

import json
import os
import requests
from typing import Dict, List, Optional

from episwarm.packs.behavior import DecisionQuestion
from episwarm.behavior.buckets import AgentBucket, SituationBucket
from episwarm.behavior.policy_base import DecisionPolicy
from episwarm.behavior.policy_rules import RulePolicy


class GeminiPolicy(DecisionPolicy):
    """Google Gemini policy implementation with rate-limiting and RulePolicy fallback."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        cache=None,
        fallback_policy: Optional[DecisionPolicy] = None
    ):
        super().__init__(cache)
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
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

        cached = self.cache.get("gemini", question.id, sit_hash, buck_hash)
        if cached:
            return cached

        if not self.api_key:
            self.fallback_count += 1
            return self.fallback.decide(question, situation, bucket, context)

        prompt_text = (
            f"You are evaluating a population behavioral response model.\n"
            f"Context: {context}\n"
            f"Profile: Age {bucket.age_band}, occupation {bucket.occupation_class}, "
            f"comorbidity: {bucket.has_comorbidity}, trust: {bucket.trust_band}, risk tolerance: {bucket.risk_tolerance_band}.\n"
            f"Situation: Health: {situation.health_state_group}, local risk: {situation.local_risk_level}, "
            f"measures: {situation.active_measures}, household sick: {situation.household_member_sick}.\n"
            f"Question: {question.plain_instructions}\n"
            f"Options: {question.options}\n\n"
            f"Return ONLY valid JSON mapping each option to its probability (0.0 to 1.0, summing to 1.0). "
            f"Example format: {json.dumps({opt: round(1.0/len(question.options), 2) for opt in question.options})}"
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt_text}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
        }

        try:
            resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                text_out = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text_out)
                if isinstance(parsed, dict) and all(opt in parsed for opt in question.options):
                    tot = sum(float(parsed[opt]) for opt in question.options)
                    if tot > 0:
                        probs = {opt: round(float(parsed[opt]) / tot, 4) for opt in question.options}
                        self.cache.put("gemini", question.id, sit_hash, buck_hash, probs)
                        return probs

            self.fallback_count += 1
            return self.fallback.decide(question, situation, bucket, context)
        except Exception:
            self.fallback_count += 1
            return self.fallback.decide(question, situation, bucket, context)
