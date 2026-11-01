"""Free local logprob-based decision policy implementing section 10.2b of spec."""

import itertools
import math
import os
import random
from typing import Dict, List, Optional, Tuple
import numpy as np
import requests

from episwarm.packs.behavior import DecisionQuestion, QuestionType
from episwarm.behavior.buckets import AgentBucket, SituationBucket
from episwarm.behavior.policy_base import DecisionPolicy
from episwarm.behavior.policy_rules import RulePolicy


LABEL_SETS = {
    "alphabet": ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"],
    "binary": ["Y", "N"],
    "score": ["0", "1", "2", "3", "4"]
}


class LocalLogprobPolicy(DecisionPolicy):
    """Decision model utilizing local LLM logprobs over single-token option labels with position-bias removal."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        engine: str = "auto",  # 'ollama', 'openai_compat', 'transformers', or 'auto'
        shuffles: int = 2,
        cache=None,
        fallback_policy: Optional[DecisionPolicy] = None
    ):
        super().__init__(cache)
        self.base_url = (base_url or os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or os.getenv("LOCAL_LLM_MODEL", "llama3.2:1b")
        self.engine = engine
        self.shuffles = max(1, shuffles)
        self.fallback = fallback_policy or RulePolicy(cache=self.cache)

        # Track model call stats
        self.model_calls_count: int = 0
        self.cache_hits_count: int = 0

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

        # 1. Check cache
        cached = self.cache.get("local_logprob", question.id, sit_hash, buck_hash)
        if cached:
            self.cache_hits_count += 1
            return cached

        # 2. Assign label set
        opts = question.options
        n_opts = len(opts)
        if question.type == QuestionType.NOUL and n_opts == 2:
            labels = LABEL_SETS["binary"]
        elif question.type == QuestionType.SCORE and n_opts <= 5:
            labels = LABEL_SETS["score"][:n_opts]
        else:
            labels = LABEL_SETS["alphabet"][:n_opts]

        # 3. Position bias removal via option order shuffling
        # Generate permutation orders
        permutations = []
        base_indices = list(range(n_opts))
        permutations.append(base_indices)
        if self.shuffles > 1:
            reversed_indices = list(reversed(base_indices))
            permutations.append(reversed_indices)
            for _ in range(self.shuffles - 2):
                shuffled = base_indices.copy()
                random.shuffle(shuffled)
                permutations.append(shuffled)

        accumulated_probs: Dict[str, float] = {opt: 0.0 for opt in opts}

        # Query model across permutations
        success = False
        for perm in permutations:
            perm_opts = [opts[idx] for idx in perm]
            # Construct single-token label prompt
            prompt = self._build_prompt(question, situation, bucket, perm_opts, labels, context)
            perm_logprobs = self._query_next_token_logprobs(prompt, labels)

            if perm_logprobs is None:
                # Engine failed or unreachable
                break

            success = True
            self.model_calls_count += 1

            # Convert logprobs to probabilities
            unnorm_probs = [math.exp(perm_logprobs.get(lbl, -15.0)) for lbl in labels]
            total_mass = sum(unnorm_probs)
            if total_mass <= 0:
                total_mass = 1e-12

            for i, opt_name in enumerate(perm_opts):
                p_norm = unnorm_probs[i] / total_mass
                accumulated_probs[opt_name] += p_norm

        if not success:
            # Fall back to RulePolicy
            self.fallback_count += 1
            res = self.fallback.decide(question, situation, bucket, context)
            return res

        # Average across permutations
        n_perms = len(permutations)
        averaged_probs = {opt: round(accumulated_probs[opt] / n_perms, 4) for opt in opts}

        # Normalize to exactly 1.0
        tot = sum(averaged_probs.values())
        if tot > 0:
            averaged_probs = {opt: round(v / tot, 4) for opt, v in averaged_probs.items()}
            # Adjust rounding error on first option
            diff = 1.0 - sum(averaged_probs.values())
            averaged_probs[opts[0]] = round(averaged_probs[opts[0]] + diff, 4)

        # Store in cache
        self.cache.put("local_logprob", question.id, sit_hash, buck_hash, averaged_probs)
        return averaged_probs

    def _build_prompt(
        self,
        question: DecisionQuestion,
        situation: SituationBucket,
        bucket: AgentBucket,
        options: List[str],
        labels: List[str],
        context: str
    ) -> str:
        options_text = "\n".join([f"{labels[i]}. {options[i]}" for i in range(len(options))])
        prompt = (
            f"Context: {context}\n"
            f"Resident Profile: Age {bucket.age_band}, occupation {bucket.occupation_class}, "
            f"comorbidity: {'yes' if bucket.has_comorbidity else 'no'}, trust: {bucket.trust_band}, risk tolerance: {bucket.risk_tolerance_band}.\n"
            f"Situation: Health: {situation.health_state_group}, local outbreak: {situation.local_risk_level}, "
            f"measures: {situation.active_measures}, household member ill: {'yes' if situation.household_member_sick else 'no'}.\n\n"
            f"Task: {question.plain_instructions}\n\n"
            f"Choices:\n{options_text}\n\n"
            f"Choose exactly one label ({', '.join(labels)}) that best describes the decision. Respond ONLY with the single uppercase label:"
        )
        return prompt

    def _query_next_token_logprobs(self, prompt: str, target_labels: List[str]) -> Optional[Dict[str, float]]:
        """Query local engine (Ollama or OpenAI-compatible) for next-token top_logprobs."""
        # 1. Try OpenAI-compatible endpoint (vLLM / llama.cpp / local server)
        logprobs = self._query_openai_compat(prompt, target_labels)
        if logprobs is not None:
            return logprobs

        # 2. Try Ollama generate/chat API
        logprobs = self._query_ollama(prompt, target_labels)
        if logprobs is not None:
            return logprobs

        return None

    def _query_openai_compat(self, prompt: str, target_labels: List[str]) -> Optional[Dict[str, float]]:
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1,
            "temperature": 0.0,
            "logprobs": True,
            "top_logprobs": max(5, len(target_labels))
        }
        try:
            resp = requests.post(url, json=payload, timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                choice = data["choices"][0]
                logprob_content = choice.get("logprobs", {}).get("content", [])
                if logprob_content:
                    top_list = logprob_content[0].get("top_logprobs", [])
                    label_map: Dict[str, float] = {}
                    for item in top_list:
                        token_str = item.get("token", "").strip().upper()
                        if token_str in target_labels:
                            label_map[token_str] = float(item.get("logprob", -15.0))
                    # Assign small floor for missing target labels
                    for lbl in target_labels:
                        if lbl not in label_map:
                            label_map[lbl] = -15.0
                    return label_map
        except Exception:
            pass
        return None

    def _query_ollama(self, prompt: str, target_labels: List[str]) -> Optional[Dict[str, float]]:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "options": {
                "num_predict": 1,
                "temperature": 0.0
            },
            "stream": False
        }
        try:
            resp = requests.post(url, json=payload, timeout=2)
            if resp.status_code == 200:
                # If Ollama returns response token
                data = resp.json()
                token = data.get("response", "").strip().upper()
                label_map = {lbl: -15.0 for lbl in target_labels}
                if token in target_labels:
                    label_map[token] = 0.0  # Logprob 0 => prob 1.0
                return label_map
        except Exception:
            pass
        return None


# Backward-compatible and intuitive alias
LocalLLMPolicy = LocalLogprobPolicy
