"""Behavior policy factory supporting hierarchical selection: Jev -> Local -> Rule."""

import logging
import os
import requests
from typing import Optional, Tuple

from episwarm.behavior.policy_base import DecisionPolicy
from episwarm.behavior.policy_rules import RulePolicy
from episwarm.behavior.policy_jev import JevPolicy
from episwarm.behavior.policy_local import LocalLogprobPolicy
from episwarm.behavior.cache import DecisionCache

logger = logging.getLogger(__name__)


def create_decision_policy(preferred_mode: str = "auto", cache: Optional[DecisionCache] = None) -> Tuple[DecisionPolicy, str]:
    """Select and instantiate behavioral decision policy according to configuration hierarchy.

    Order of priority:
    0. If preferred_mode == "rule": RulePolicy (deterministic fast rule policy)
    1. JevPolicy (if TYPESAFE_API_KEY is present and non-empty)
    2. LocalLogprobPolicy (if LOCAL_LLM_BASE_URL is reachable and preferred_mode == "llm" or "auto")
    3. RulePolicy (deterministic fallback)

    Returns:
        policy: instantiated DecisionPolicy
        backend_name: string identifier of selected active backend
    """
    cache = cache or DecisionCache()

    # 0. Strict Rule Override
    if preferred_mode in ("rule", "none"):
        return RulePolicy(cache=cache), preferred_mode

    # 1. Jev Check
    jev_key = os.getenv("TYPESAFE_API_KEY", "").strip()
    if jev_key:
        logger.info("Instantiating JevPolicy as primary backend.")
        return JevPolicy(api_key=jev_key, cache=cache), "jev"

    # 2. Local LLM Check (auto-detects local Ollama/OpenAI at http://localhost:11434 by default)
    local_url = (os.getenv("LOCAL_LLM_BASE_URL", "").strip() or "http://localhost:11434").rstrip("/")
    local_reachable = False
    if local_url:
        try:
            resp = requests.get(f"{local_url}/api/tags", timeout=1)  # Ollama tags check
            if resp.status_code == 200:
                local_reachable = True
        except Exception:
            try:
                resp = requests.get(f"{local_url}/v1/models", timeout=1)  # OpenAI-compat check
                if resp.status_code == 200:
                    local_reachable = True
            except Exception:
                pass

    if local_reachable:
        logger.info("Instantiating LocalLogprobPolicy as primary backend.")
        return LocalLogprobPolicy(base_url=local_url, cache=cache), "local_logprob"

    # 3. RulePolicy Fallback
    logger.info("Instantiating RulePolicy as baseline/fallback backend.")
    return RulePolicy(cache=cache), "rule"
