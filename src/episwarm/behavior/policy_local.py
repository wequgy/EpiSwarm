"""Free local logprob and generative decision policy with granular cohort deliberation and fast GPU inference."""

import json
import logging
import os
import re
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


class LocalLogprobPolicy(DecisionPolicy):
    """Local LLM policy (Ollama) supporting granular demographic cohort deliberation across 70+ citizen profiles."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        granularity: str = "granular",  # "granular" (70-150+ LLM calls) or "archetype" (8-15 calls)
        cache=None,
        fallback_policy: Optional[DecisionPolicy] = None
    ):
        super().__init__(cache)
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        self.base_url = (base_url or os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or os.getenv("LOCAL_LLM_MODEL")
        self.granularity = granularity
        self.fallback = fallback_policy or RulePolicy(cache=self.cache)

        # In-memory decision cache: key -> {question_id: {opt: prob}}
        self._decisions_cache: Dict[str, Dict[str, Dict[str, float]]] = {}
        self.model_calls_count: int = 0
        self.cache_hits_count: int = 0
        self.last_error: str = ""
        self.recent_deliberations: list = []

        # Auto-detect model if none supplied or invalid
        self._resolve_model()
        # Pre-warm model in GPU VRAM
        self._warmup_model()

    def _resolve_model(self) -> None:
        """Probe Ollama /api/tags to select best available model."""
        if not self.model or self.model in ("auto", ""):
            try:
                resp = requests.get(f"{self.base_url}/api/tags", timeout=3)
                if resp.status_code == 200:
                    models = [m.get("name", "") for m in resp.json().get("models", [])]
                    if models:
                        # Prefer llama3.2:3b if installed, then qwen3:4b
                        if "llama3.2:3b" in models:
                            self.model = "llama3.2:3b"
                        elif any("llama3.2" in m for m in models):
                            self.model = [m for m in models if "llama3.2" in m][0]
                        elif any("qwen" in m for m in models):
                            self.model = [m for m in models if "qwen" in m][0]
                        else:
                            self.model = models[0]
                        logger.info(f"Auto-selected installed Ollama model: {self.model}")
            except Exception as e:
                logger.debug(f"Could not probe Ollama tags: {e}")

        if not self.model:
            self.model = "llama3.2:3b"

    def _warmup_model(self) -> None:
        """Ping Ollama once with a 1-token query to preload weights into GPU VRAM before simulation starts."""
        try:
            requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": "ready", "options": {"num_predict": 1}, "stream": False},
                timeout=45
            )
        except Exception:
            pass

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

        # 1. Granular SQLite cache check
        cached = self.cache.get("local_logprob", question.id, sit_hash, buck_hash)
        if cached:
            self.cache_hits_count += 1
            return cached

        # 2. Determine decision cohort key based on granularity mode
        if self.granularity == "granular":
            # Cohort key preserves exact demographic attributes (70+ unique citizen profiles)
            cohort_key = f"{bucket.age_band}_{bucket.occupation_class}_{bucket.has_comorbidity}_{bucket.trust_band}_{bucket.risk_tolerance_band}::{situation.health_state_group}_{situation.local_risk_level}_{situation.active_measures}_{situation.household_member_sick}"
        else:
            ag_arch, sit_arch = get_archetype_key(bucket, situation)
            cohort_key = f"{ag_arch}::{sit_arch}"

        # 3. In-memory cohort cache check
        if cohort_key in self._decisions_cache:
            cohort_data = self._decisions_cache[cohort_key]
            if question.id in cohort_data:
                self.cache_hits_count += 1
                res = cohort_data[question.id]
                self.cache.put("local_logprob", question.id, sit_hash, buck_hash, res)
                return res
            else:
                fb_res = self.fallback.decide(question, situation, bucket, context)
                cohort_data[question.id] = fb_res
                self.cache.put("local_logprob", question.id, sit_hash, buck_hash, fb_res)
                return fb_res

        # 4. Query Local LLM via Granular Cohort batch (evaluates all 4 behaviors in 1 call for this profile)
        batch_probs = self._query_cohort_batch(bucket, situation, context)
        if batch_probs:
            self._decisions_cache[cohort_key] = batch_probs
            has_com = "Chronic Condition" if bucket.has_comorbidity else "Healthy"
            occ = bucket.occupation_class.replace("_", " ").title()
            c_desc = f"{bucket.age_band} • {occ} • {has_com} • Trust: {bucket.trust_band.title()} • Risk Tol: {bucket.risk_tolerance_band.title()}"
            s_desc = f"{situation.local_risk_level.title()} Transmission ({situation.active_measures})"
            self.recent_deliberations.append({
                "cohort": c_desc,
                "situation": s_desc,
                "mask": f"{int(batch_probs.get('wear_mask', {}).get('yes', 0.5) * 100)}%",
                "isolate": f"{int(batch_probs.get('isolate_symptomatic', {}).get('yes', 0.7) * 100)}%",
                "work_avoid": f"{int(batch_probs.get('workplace_attendance', {}).get('avoid', 0.1) * 100)}%",
                "vaccine": f"{int(batch_probs.get('accept_vaccine', {}).get('yes', 0.6) * 100)}%"
            })
            if len(self.recent_deliberations) > 200:
                self.recent_deliberations.pop(0)
            if question.id in batch_probs:
                res = batch_probs[question.id]
                self.cache.put("local_logprob", question.id, sit_hash, buck_hash, res)
                return res
            else:
                fb_res = self.fallback.decide(question, situation, bucket, context)
                self._decisions_cache[cohort_key][question.id] = fb_res
                return fb_res

        # 5. Fallback if LLM call failed -> cache fallback for this cohort to prevent repeated timeouts
        self.fallback_count += 1
        fb_res = self.fallback.decide(question, situation, bucket, context)
        self._decisions_cache[cohort_key] = {question.id: fb_res}
        self.cache.put("local_logprob", question.id, sit_hash, buck_hash, fb_res)
        return fb_res

    def _query_cohort_batch(
        self,
        bucket: AgentBucket,
        situation: SituationBucket,
        context: str
    ) -> Optional[Dict[str, Dict[str, float]]]:
        """Query local LLM for cohort decisions using chat template and simulation framing."""
        is_qwen = "qwen" in self.model.lower()

        # Behavioral simulation framing avoids generic medical advice refusal filters in Llama 3
        sys_msg = (
            "You are an agent representing a demographic citizen cohort in an academic agent-based epidemic simulation game (EpiSwarm). "
            "For each decision question, choose option A, B, or C based strictly on the cohort's trust level, risk tolerance, and outbreak situation. "
            "Output strictly in this format:\nQ1: [A/B]\nQ2: [A/B]\nQ3: [A/B/C]\nQ4: [A/B]"
        )

        user_msg = (
            f"Citizen Cohort Profile:\n"
            f"- Demographic Age: {bucket.age_band}\n"
            f"- Occupation: {bucket.occupation_class}\n"
            f"- Chronic Health Condition: {'Yes' if bucket.has_comorbidity else 'No'}\n"
            f"- Institutional / Civic Trust: {bucket.trust_band}\n"
            f"- Personal Risk Tolerance: {bucket.risk_tolerance_band}\n\n"
            f"Epidemic Outbreak Situation:\n"
            f"- Community Transmission Level: {situation.local_risk_level}\n"
            f"- Health Status: {situation.health_state_group}\n"
            f"- Municipal Directives in Effect: {situation.active_measures}\n"
            f"- Household Member Ill: {'Yes' if situation.household_member_sick else 'No'}\n\n"
            f"Decide compliance for these 4 public health behaviors:\n"
            f"Q1 (Adhere to public mask advisory): A: Comply | B: Do not comply\n"
            f"Q2 (Self-quarantine if symptomatic): A: Comply | B: Do not comply\n"
            f"Q3 (Workplace presence): A: Attend as usual | B: Reduced attendance | C: Avoid crowded workplace\n"
            f"Q4 (Accept preventive health intervention): A: Accept | B: Decline\n\n"
            f"Choices:"
        )

        try:
            if is_qwen:
                raw_prompt = (
                    f"<|im_start|>system\n{sys_msg}<|im_end|>\n"
                    f"<|im_start|>user\n{user_msg}<|im_end|>\n"
                    f"<|im_start|>assistant\nQ1: "
                )
                url = f"{self.base_url}/api/generate"
                payload = {
                    "model": self.model,
                    "prompt": raw_prompt,
                    "raw": True,
                    "options": {"num_predict": 45, "temperature": 0.1},
                    "stream": False
                }
                resp = requests.post(url, json=payload, timeout=45)
                if resp.status_code == 200:
                    self.model_calls_count += 1
                    body = "Q1: " + resp.json().get("response", "")
                    return self._parse_decisions(body, situation)
            else:
                # Use /api/chat with official chat template for Llama 3.2
                url = f"{self.base_url}/api/chat"
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": sys_msg},
                        {"role": "user", "content": user_msg}
                    ],
                    "options": {"num_predict": 45, "temperature": 0.1},
                    "stream": False
                }
                resp = requests.post(url, json=payload, timeout=45)
                if resp.status_code == 200:
                    self.model_calls_count += 1
                    content = resp.json().get("message", {}).get("content", "")
                    return self._parse_decisions(content, situation)

            self.last_error = f"Ollama HTTP {resp.status_code}"
            logger.warning(self.last_error)
        except Exception as e:
            self.last_error = str(e)
            logger.warning(f"Ollama call exception: {e}")

        return None

    def _parse_decisions(self, text: str, situation: SituationBucket) -> Optional[Dict[str, Dict[str, float]]]:
        """Extract choice letters and convert to calibrated option probability distributions."""
        q_letters: Dict[str, str] = {}
        for m in re.finditer(r"Q(\d):\s*([A-Za-z])", text):
            q_num = m.group(1)
            q_letters[f"Q{q_num}"] = m.group(2).upper()

        if "Q1" in q_letters:
            out_probs: Dict[str, Dict[str, float]] = {}

            # Q1: wear_mask
            ans1 = q_letters.get("Q1", "A")
            out_probs["wear_mask"] = {"yes": 0.88, "no": 0.12} if ans1 == "A" else {"yes": 0.18, "no": 0.82}

            # Q2: isolate_symptomatic
            ans2 = q_letters.get("Q2", "A")
            out_probs["isolate_symptomatic"] = {"yes": 0.92, "no": 0.08} if ans2 == "A" else {"yes": 0.25, "no": 0.75}

            # Q3: workplace_attendance
            ans3 = q_letters.get("Q3", "A")
            if ans3 == "C":
                out_probs["workplace_attendance"] = {"avoid": 0.75, "reduced": 0.20, "usual": 0.05}
            elif ans3 == "B":
                out_probs["workplace_attendance"] = {"avoid": 0.25, "reduced": 0.60, "usual": 0.15}
            else:
                out_probs["workplace_attendance"] = {"avoid": 0.08, "reduced": 0.22, "usual": 0.70}

            # Q4: accept_vaccine
            ans4 = q_letters.get("Q4", "A")
            out_probs["accept_vaccine"] = {"yes": 0.82, "no": 0.18} if ans4 == "A" else {"yes": 0.20, "no": 0.80}

            # Derived market_visits
            if ans3 == "C" or situation.local_risk_level in ("high", "critical"):
                out_probs["market_visits"] = {"avoid": 0.60, "essential_only": 0.35, "usual": 0.05}
            elif ans3 == "B":
                out_probs["market_visits"] = {"avoid": 0.20, "essential_only": 0.65, "usual": 0.15}
            else:
                out_probs["market_visits"] = {"avoid": 0.05, "essential_only": 0.30, "usual": 0.65}

            return out_probs

        return None


# Backward-compatible and intuitive alias
LocalLLMPolicy = LocalLogprobPolicy
