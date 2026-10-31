"""Rumor and misinformation dynamic transmission engine (Spec 7).

Implements vectorized sparse social exposure, sharing dynamics, belief updates,
correction campaigns, and behavioral distortion effects.
"""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import scipy.sparse as sp

from episwarm.packs.behavior import RumorTopic, RumorBehaviorEffects
from episwarm.population.build import PopulationSoA


def get_belief_band(belief_value: float) -> str:
    """Bucket continuous belief into discrete band for policy prompt caching (Spec 7.2)."""
    if belief_value < 0.25:
        return "low"
    elif belief_value < 0.65:
        return "moderate"
    else:
        return "high"


class RumorDynamicsEngine:
    """Vectorized state machine simulating misinformation transmission across a sparse social network."""

    def __init__(
        self,
        pop: PopulationSoA,
        topics: List[RumorTopic],
        social_network: sp.csr_matrix,
        tau: float = 0.50,  # Trust modulation parameter
        g_params: Tuple[float, float, float, float] = (-2.0, 3.0, 1.0, 0.5)  # (g0, g1, g2, g3)
    ):
        self.pop = pop
        self.topics = topics
        self.adj = social_network
        self.tau = tau
        self.g0, self.g1, self.g2, self.g3 = g_params

        self.n_agents = pop.n_agents
        self.n_topics = len(topics)

        # Belief matrix: (n_topics, n_agents) in [0.0, 1.0]
        self.beliefs = np.zeros((self.n_topics, self.n_agents), dtype=np.float32)

        # Precompute agent gullibility from rumor_susceptibility trait
        self.gullibility = pop.rumor_susceptibility
        self.trust_factor = np.clip(1.0 - pop.trust * self.tau, 0.05, 1.0).astype(np.float32)

    def step_day(
        self,
        day: int,
        active_corrections: Dict[str, float],  # topic_id -> reach * efficacy
        rng: np.random.Generator
    ) -> Dict[str, Any]:
        """Execute daily transmission, sharing, belief revision, and correction.

        Returns telemetry dictionary for tracking rumor prevalence.
        """
        telemetry: Dict[str, Any] = {}

        for k, topic in enumerate(self.topics):
            # 1. Seeding initial believers
            if day == topic.seed_day:
                if topic.seed_area == "ALL":
                    eligible = np.arange(self.n_agents)
                else:
                    target_aid = self.pop.area_id_to_int.get(topic.seed_area, -1)
                    eligible = np.where(self.pop.area_id == target_aid)[0] if target_aid >= 0 else np.arange(self.n_agents)

                n_seed = min(len(eligible), topic.num_seeds)
                if n_seed > 0:
                    chosen = rng.choice(eligible, size=n_seed, replace=False)
                    self.beliefs[k, chosen] = np.maximum(self.beliefs[k, chosen], 0.85)

            current_b = self.beliefs[k]

            # 2. Sharing trial: Agents with zero knowledge/belief do not originate shares
            has_knowledge = current_b > 0.01
            p_share = np.zeros(self.n_agents, dtype=np.float32)
            if np.any(has_knowledge):
                fear = 1.0 - self.pop.trust[has_knowledge]
                logits = (
                    self.g0
                    + self.g1 * current_b[has_knowledge]
                    + self.g2 * self.gullibility[has_knowledge]
                    + self.g3 * fear
                )
                p_share[has_knowledge] = 1.0 / (1.0 + np.exp(-np.clip(logits, -10.0, 10.0)))
            shared = (rng.random(size=self.n_agents) < p_share).astype(np.float32)

            # 3. Sparse exposure calculation: exposure = (A @ share) * credibility
            raw_exposure = np.array(self.adj.dot(shared)).flatten()
            exposure = raw_exposure * float(topic.credibility)

            # 4. Belief update with saturating function f(exposure) = 1 - exp(-exposure)
            f_exp = 1.0 - np.exp(-exposure)
            delta_belief = self.gullibility * self.trust_factor * (1.0 - current_b) * f_exp

            # 5. Official correction campaigns
            corr_intensity = active_corrections.get(topic.id, 0.0)
            if corr_intensity > 0.0:
                correction_impact = corr_intensity * current_b
                delta_belief -= correction_impact

            # Update and clamp
            self.beliefs[k] = np.clip(current_b + delta_belief, 0.0, 1.0)

            telemetry[topic.id] = {
                "mean_belief": float(np.mean(self.beliefs[k])),
                "believers_count": int(np.sum(self.beliefs[k] > 0.50)),
                "sharing_count": int(np.sum(shared))
            }

        return telemetry

    def compute_behavior_distortions(self) -> Tuple[np.ndarray, np.ndarray]:
        """Compute net behavioral reductions across active topics (Spec 7.4).

        Returns:
            mask_reduction: float32 array in [0.0, 1.0] per agent
            isolation_reduction: float32 array in [0.0, 1.0] per agent
        """
        mask_red = np.zeros(self.n_agents, dtype=np.float32)
        iso_red = np.zeros(self.n_agents, dtype=np.float32)

        for k, topic in enumerate(self.topics):
            b = self.beliefs[k]
            mask_red += b * float(topic.behavior_effects.mask_reduction)
            iso_red += b * float(topic.behavior_effects.isolation_reduction)

        return np.clip(mask_red, 0.0, 0.90), np.clip(iso_red, 0.0, 0.90)
