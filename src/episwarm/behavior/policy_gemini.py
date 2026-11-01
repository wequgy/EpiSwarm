"""Google Gemini behavioral decision policy with archetype aggregation, 15 RPM rate-limiting, and circuit breaker."""

import json
import logging
import os
import time
import requests
from typing import Dict, List, Optional, Tuple

from episwarm.packs.behavior import DecisionQuestion
from episwarm.behavior.buckets import AgentBucket, SituationBucket
from episwarm.behavior.policy_base import DecisionPolicy
from episwarm.behavior.policy_rules import RulePolicy
from episwarm.behavior.archetypes import (
    get_archetype_key,
    ARCHETYPE_DESCRIPTIONS,
    SITUATION_DESCRIPTIONS
)

logger = logging.getLogger(__name__)


class GeminiPolicy(DecisionPolicy):
    """Google Gemini policy with archetype batching, 15 RPM quota compliance, and circuit breaker."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        cache=None,
        fallback_policy: Optional[DecisionPolicy] = None
    ):
        super().__init__(cache)
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        self.api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or ""
        ).strip()
        # Default to gemini-3.1-flash-lite
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        self.fallback = fallback_policy or RulePolicy(cache=self.cache)

        # In-memory archetype cache: (ag_arch, sit_arch) -> {question_id: {opt: prob}}
        self._archetype_decisions: Dict[Tuple[str, str], Dict[str, Dict[str, float]]] = {}
        self.model_calls_count: int = 0
        self.cache_hits_count: int = 0
        self.last_error: str = ""
        self._circuit_broken: bool = False
        self._last_call_time: float = 0.0

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

        # 1. Check exact granular cache first
        cached = self.cache.get("gemini", question.id, sit_hash, buck_hash)
        if cached:
            self.cache_hits_count += 1
            return cached

        # 2. Map to Archetype & check archetype in-memory cache
        arch_key = get_archetype_key(bucket, situation)
        if arch_key in self._archetype_decisions:
            arch_data = self._archetype_decisions[arch_key]
            if question.id in arch_data:
                self.cache_hits_count += 1
                res = arch_data[question.id]
                self.cache.put("gemini", question.id, sit_hash, buck_hash, res)
                return res
            else:
                fb_res = self.fallback.decide(question, situation, bucket, context)
                arch_data[question.id] = fb_res
                self.cache.put("gemini", question.id, sit_hash, buck_hash, fb_res)
                return fb_res

        # 3. If no API key or circuit broken (e.g. 429 quota exhaustion), use fallback immediately
        if not self.api_key or self._circuit_broken:
            self.fallback_count += 1
            fb_res = self.fallback.decide(question, situation, bucket, context)
            self._archetype_decisions[arch_key] = {question.id: fb_res}
            self.cache.put("gemini", question.id, sit_hash, buck_hash, fb_res)
            return fb_res

        # 4. Enforce 2-second rate-limiting interval between uncached calls (preserves 15 RPM quota)
        elapsed = time.time() - self._last_call_time
        if elapsed < 2.0:
            time.sleep(2.0 - elapsed)

        # 5. Query Gemini with Archetype Batch prompt
        batch_probs = self._query_gemini_archetype_batch(arch_key, context)
        self._last_call_time = time.time()

        if batch_probs:
            self._archetype_decisions[arch_key] = batch_probs
            if question.id in batch_probs:
                res = batch_probs[question.id]
                self.cache.put("gemini", question.id, sit_hash, buck_hash, res)
                return res
            else:
                fb_res = self.fallback.decide(question, situation, bucket, context)
                self._archetype_decisions[arch_key][question.id] = fb_res
                return fb_res

        # 6. Fallback if call failed or was throttled -> cache fallback for this archetype
        self.fallback_count += 1
        fb_res = self.fallback.decide(question, situation, bucket, context)
        self._archetype_decisions[arch_key] = {question.id: fb_res}
        self.cache.put("gemini", question.id, sit_hash, buck_hash, fb_res)
        return fb_res

    def _query_gemini_archetype_batch(
        self,
        arch_key: Tuple[str, str],
        context: str
    ) -> Optional[Dict[str, Dict[str, float]]]:
        """Query Gemini once for an archetype to get all behavioral probabilities simultaneously."""
        ag_arch, sit_arch = arch_key
        ag_desc = ARCHETYPE_DESCRIPTIONS.get(ag_arch, ag_arch)
        sit_desc = SITUATION_DESCRIPTIONS.get(sit_arch, sit_arch)

        prompt_text = (
            f"You are an epidemiological behavioral response model for an urban simulation.\n"
            f"Resident Archetype ({ag_arch}): {ag_desc}\n"
            f"Outbreak Situation ({sit_arch}): {sit_desc}\n"
            f"Context: {context or 'Urban center during respiratory pathogen outbreak.'}\n\n"
            f"Estimate the compliance probability (0.0 to 1.0) for this resident archetype across 4 decisions:\n"
            f"1. wear_mask: probability of consistently wearing a mask in public (yes / no)\n"
            f"2. isolate_symptomatic: probability of isolating at home if symptomatic (yes / no)\n"
            f"3. workplace_attendance: probability of avoiding crowded workplace (avoid / usual)\n"
            f"4. accept_vaccine: probability of accepting vaccination if available (yes / no)\n\n"
            f"Return ONLY valid JSON matching this schema:\n"
            f"{{\n"
            f'  "wear_mask": {{"yes": 0.85, "no": 0.15}},\n'
            f'  "isolate_symptomatic": {{"yes": 0.90, "no": 0.10}},\n'
            f'  "workplace_attendance": {{"avoid": 0.40, "usual": 0.60}},\n'
            f'  "accept_vaccine": {{"yes": 0.75, "no": 0.25}}\n'
            f"}}"
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt_text}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
        }

        try:
            resp = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            if resp.status_code == 200:
                self.model_calls_count += 1
                data = resp.json()
                text_out = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text_out)

                formatted: Dict[str, Dict[str, float]] = {}
                for qid in ["wear_mask", "isolate_symptomatic", "workplace_attendance", "accept_vaccine"]:
                    val = parsed.get(qid)
                    if isinstance(val, dict):
                        tot = sum(float(v) for v in val.values())
                        if tot > 0:
                            formatted[qid] = {k: round(float(v) / tot, 4) for k, v in val.items()}
                    elif isinstance(val, (int, float)):
                        p = float(val)
                        if qid == "workplace_attendance":
                            formatted[qid] = {"avoid": round(p, 4), "usual": round(1.0 - p, 4)}
                        else:
                            formatted[qid] = {"yes": round(p, 4), "no": round(1.0 - p, 4)}

                # Derive market_visits
                wp_avoid = formatted.get("workplace_attendance", {}).get("avoid", 0.3)
                if wp_avoid > 0.5 or sit_arch in ("personal_exposure", "high_risk_mandates"):
                    formatted["market_visits"] = {"avoid": 0.60, "essential_only": 0.35, "usual": 0.05}
                else:
                    formatted["market_visits"] = {"avoid": 0.10, "essential_only": 0.35, "usual": 0.55}

                if "wear_mask" in formatted:
                    return formatted
            else:
                self._circuit_broken = True
                err_data = resp.json().get("error", {})
                self.last_error = f"Gemini HTTP {resp.status_code}: {err_data.get('message', resp.text)[:120]}"
                logger.warning(self.last_error)
        except Exception as e:
            self._circuit_broken = True
            self.last_error = f"Gemini connection timeout/error ({e}). Auto-tripped circuit breaker."
            logger.warning(self.last_error)

        return None
