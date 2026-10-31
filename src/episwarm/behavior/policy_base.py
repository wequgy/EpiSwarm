"""Abstract base class and sampling logic for behavioral decision policies."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import numpy as np

from episwarm.packs.behavior import DecisionQuestion
from episwarm.behavior.buckets import AgentBucket, SituationBucket
from episwarm.behavior.cache import DecisionCache


class DecisionPolicy(ABC):
    """Abstract interface for all behavioral decision models."""

    def __init__(self, cache: Optional[DecisionCache] = None):
        self.cache = cache or DecisionCache()
        self.total_queries: int = 0
        self.fallback_count: int = 0

    @property
    def fallback_rate(self) -> float:
        if self.total_queries == 0:
            return 0.0
        return self.fallback_count / float(self.total_queries)

    @abstractmethod
    def decide(
        self,
        question: DecisionQuestion,
        situation: SituationBucket,
        bucket: AgentBucket,
        context: str = ""
    ) -> Dict[str, float]:
        """Compute probability distribution over question options.

        Returns:
            Dict mapping option name -> probability (summing to 1.0).
        """
        pass

    @staticmethod
    def sample_action(
        probabilities: Dict[str, float],
        individual_noise: float,
        rng: np.random.Generator
    ) -> str:
        """Sample an action probabilistically.

        RULE: NEVER take the argmax! Add individual trait-based perturbation to avoid artificial uniformity.
        """
        options = list(probabilities.keys())
        probs = np.array([probabilities[opt] for opt in options], dtype=np.float64)

        # Inject bounded trait noise
        if individual_noise != 0.0 and len(options) > 1:
            noise = rng.normal(0.0, abs(individual_noise), size=len(options))
            probs = np.clip(probs + noise, 0.01, None)

        # Re-normalize
        probs /= probs.sum()
        chosen = rng.choice(options, p=probs)
        return str(chosen)
