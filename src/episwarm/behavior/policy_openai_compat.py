"""OpenAI-compatible decision policy with structured JSON probability returns."""

import json
import os
import requests
from typing import Dict, List, Optional

from episwarm.packs.behavior import DecisionQuestion
from episwarm.behavior.buckets import AgentBucket, SituationBucket
from episwarm.behavior.policy_base import DecisionPolicy
from episwarm.behavior.policy_rules import RulePolicy


class OpenAICompatiblePolicy(DecisionPolicy):
    """Generic OpenAI-compatible behavioral decision policy."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        cache=None,
        fallback_policy: Optional[DecisionPolicy] = None
    ):
        super().__init__(cache)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
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

        cached = self.cache.get("openai_compat", question.id, sit_hash, buck_hash)
        if cached:
            return cached

        if not self.api_key:
            self.fallback_count += 1
            return self.fallback.decide(question, situation, bucket, context)

        prompt_text = (
            f"Context: {context}\n"
            f"Profile: Age {bucket.age_band}, occupation {bucket.occupation_class}, "
            f"comorbidity: {bucket.has_comorbidity}, trust: {bucket.trust_band}, risk tolerance: {bucket.risk_tolerance_band}.\n"
            f"Situation: Health: {situation.health_state_group}, local risk: {situation.local_risk_level}, "
            f"measures: {situation.active_measures}, household sick: {situation.household_member_sick}.\n"
            f"Question: {question.plain_instructions}\n"
            f"Options: {question.options}\n\n"
            f"Respond with JSON object mapping each option to a probability between 0 and 1, summing to 1.0."
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a public behavioral simulator. Output valid JSON only."},
                {"role": "user", "content": prompt_text}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2
        }

        try:
            resp = requests.post(f"{self.base_url}/chat/completions", json=payload, headers=headers, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                if isinstance(parsed, dict) and all(opt in parsed for opt in question.options):
                    tot = sum(float(parsed[opt]) for opt in question.options)
                    if tot > 0:
                        probs = {opt: round(float(parsed[opt]) / tot, 4) for opt in question.options}
                        self.cache.put("openai_compat", question.id, sit_hash, buck_hash, probs)
                        return probs

            self.fallback_count += 1
            return self.fallback.decide(question, situation, bucket, context)
        except Exception:
            self.fallback_count += 1
            return self.fallback.decide(question, situation, bucket, context)

