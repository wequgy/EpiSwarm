"""Free local logprob and generative decision policy with archetype aggregation and fast inference."""

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
    """Local LLM policy (Ollama / OpenAI-compat) with archetype batching for fast, reliable city simulations."""

    def __init__(
        self,
        base_url: Optional[str] = None,
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

        self.base_url = (base_url or os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or os.getenv("LOCAL_LLM_MODEL")
        self.fallback = fallback_policy or RulePolicy(cache=self.cache)

        # In-memory archetype decisions: (ag_arch, sit_arch) -> {question_id: {opt: prob}}
        self._archetype_decisions: Dict[Tuple[str, str], Dict[str, Dict[str, float]]] = {}
        self.model_calls_count: int = 0
        self.cache_hits_count: int = 0
        self.last_error: str = ""

        # Auto-detect model if none supplied or invalid
        self._resolve_model()

    def _resolve_model(self) -> None:
        """Probe Ollama /api/tags to verify model or select first available model."""
        if not self.model or self.model in ("llama3.2:1b", "auto"):
            try:
                resp = requests.get(f"{self.base_url}/api/tags", timeout=2)
                if resp.status_code == 200:
                    models = [m.get("name", "") for m in resp.json().get("models", [])]
                    if models:
                        # Prefer qwen3:4b or qwen models for fast inference
                        qwen_models = [m for m in models if "qwen" in m]
                        if qwen_models:
                            preferred = [m for m in qwen_models if "4b" in m]
                            self.model = preferred[0] if preferred else qwen_models[0]
                        else:
                            self.model = models[0]
                        logger.info(f"Auto-selected installed Ollama model: {self.model}")
            except Exception as e:
                logger.debug(f"Could not probe Ollama tags: {e}")

        if not self.model:
            self.model = "qwen3:4b"

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

        # 2. Archetype in-memory cache check
        arch_key = get_archetype_key(bucket, situation)
        if arch_key in self._archetype_decisions:
            arch_data = self._archetype_decisions[arch_key]
            if question.id in arch_data:
                self.cache_hits_count += 1
                res = arch_data[question.id]
                self.cache.put("local_logprob", question.id, sit_hash, buck_hash, res)
                return res
            else:
                # Question not explicitly returned in batch -> fallback and cache in archetype
                fb_res = self.fallback.decide(question, situation, bucket, context)
                arch_data[question.id] = fb_res
                self.cache.put("local_logprob", question.id, sit_hash, buck_hash, fb_res)
                return fb_res

        # 3. Query Local LLM via Archetype batch (resolves all decisions for this archetype at once)
        batch_probs = self._query_archetype_batch(arch_key, context)
        if batch_probs:
            self._archetype_decisions[arch_key] = batch_probs
            if question.id in batch_probs:
                res = batch_probs[question.id]
                self.cache.put("local_logprob", question.id, sit_hash, buck_hash, res)
                return res
            else:
                fb_res = self.fallback.decide(question, situation, bucket, context)
                self._archetype_decisions[arch_key][question.id] = fb_res
                return fb_res

        # 4. Fallback if LLM call failed -> cache fallback for this archetype to avoid repeated timeouts
        self.fallback_count += 1
        fb_res = self.fallback.decide(question, situation, bucket, context)
        self._archetype_decisions[arch_key] = {question.id: fb_res}
        self.cache.put("local_logprob", question.id, sit_hash, buck_hash, fb_res)
        return fb_res

    def _query_archetype_batch(
        self,
        arch_key: Tuple[str, str],
        context: str
    ) -> Optional[Dict[str, Dict[str, float]]]:
        """Query local LLM for archetype decisions across all behaviors in one fast request."""
        ag_arch, sit_arch = arch_key
        ag_desc = ARCHETYPE_DESCRIPTIONS.get(ag_arch, ag_arch)
        sit_desc = SITUATION_DESCRIPTIONS.get(sit_arch, sit_arch)

        is_qwen = "qwen" in self.model.lower()
        url = f"{self.base_url}/api/generate"

        if is_qwen:
            # High-speed prefill syntax bypassing thinking tokens in Qwen3
            raw_prompt = (
                f"<|im_start|>system\n"
                f"You are an epidemiological behavioral decision agent in a city simulation. "
                f"When presented with choices, output only the letter of your choice for each question.<|im_end|>\n"
                f"<|im_start|>user\n"
                f"Archetype ({ag_arch}): {ag_desc}\n"
                f"Context ({sit_arch}): {sit_desc}\n\n"
                f"Decide these 4 behaviors:\n"
                f"Q1 (wear_mask): A: Yes | B: No\n"
                f"Q2 (isolate_symptomatic): A: Yes | B: No\n"
                f"Q3 (workplace_attendance): A: Usual | B: Reduced | C: Avoid\n"
                f"Q4 (accept_vaccine): A: Yes | B: No\n\n"
                f"Output format:\n"
                f"Q1: [A/B]\n"
                f"Q2: [A/B]\n"
                f"Q3: [A/B/C]\n"
                f"Q4: [A/B]<|im_end|>\n"
                f"<|im_start|>assistant\n"
                f"Q1: "
            )
            payload = {
                "model": self.model,
                "prompt": raw_prompt,
                "raw": True,
                "options": {"num_predict": 45, "temperature": 0.1},
                "stream": False
            }
        else:
            prompt = (
                f"Archetype: {ag_desc}\n"
                f"Situation: {sit_desc}\n\n"
                f"Choose decisions for:\n"
                f"Q1 (wear_mask): A: Yes, B: No\n"
                f"Q2 (isolate_symptomatic): A: Yes, B: No\n"
                f"Q3 (workplace_attendance): A: Usual, B: Reduced, C: Avoid\n"
                f"Q4 (accept_vaccine): A: Yes, B: No\n\n"
                f"Respond ONLY in format:\n"
                f"Q1: [A/B]\nQ2: [A/B]\nQ3: [A/B/C]\nQ4: [A/B]"
            )
            payload = {
                "model": self.model,
                "prompt": prompt,
                "options": {"num_predict": 45, "temperature": 0.1},
                "stream": False
            }

        try:
            resp = requests.post(url, json=payload, timeout=12)
            if resp.status_code == 200:
                self.model_calls_count += 1
                body = resp.json().get("response", "")
                full_text = ("Q1: " + body) if is_qwen else body

                # Extract Q1-Q4 letters
                q_letters: Dict[str, str] = {}
                for m in re.finditer(r"Q(\d):\s*([A-Za-z])", full_text):
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

                    # Q3: workplace_attendance (A: usual, B: reduced, C: avoid)
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

                    # Derive market_visits from workplace attendance & situation
                    if ans3 == "C" or sit_arch in ("personal_exposure", "high_risk_mandates"):
                        out_probs["market_visits"] = {"avoid": 0.60, "essential_only": 0.35, "usual": 0.05}
                    elif ans3 == "B":
                        out_probs["market_visits"] = {"avoid": 0.20, "essential_only": 0.65, "usual": 0.15}
                    else:
                        out_probs["market_visits"] = {"avoid": 0.05, "essential_only": 0.30, "usual": 0.65}

                    return out_probs
            else:
                self.last_error = f"Ollama HTTP {resp.status_code}"
                logger.warning(self.last_error)
        except Exception as e:
            self.last_error = str(e)
            logger.warning(f"Ollama call exception: {e}")

        return None


# Backward-compatible and intuitive alias
LocalLLMPolicy = LocalLogprobPolicy
