"""Dynamic compliance engine modeling social norms, policy fatigue, and rumor erosion (Spec 8)."""

from typing import Dict, List, Optional, Tuple
import numpy as np
import scipy.sparse as sp

from episwarm.packs.behavior import ComplianceWeights
from episwarm.population.build import PopulationSoA


class DynamicComplianceEngine:
    """Calculates agent compliance day-by-day incorporating social peer norms, fatigue, and rumors."""

    def __init__(
        self,
        pop: PopulationSoA,
        weights: ComplianceWeights,
        social_network: sp.csr_matrix
    ):
        self.pop = pop
        self.weights = weights
        self.adj = social_network
        self.n_agents = pop.n_agents

        # Base compliance derived from personality traits and life history
        self.base_compliance = np.clip(
            0.50 * pop.compliance +
            0.30 * pop.trust +
            0.20 * pop.prior_authority_experience,
            0.05, 0.95
        ).astype(np.float32)

        # Dynamic state arrays
        self.current_compliance = np.copy(self.base_compliance)
        self.fatigue = np.zeros(self.n_agents, dtype=np.float32)

    def step_day(
        self,
        area_enforcements: np.ndarray,      # float32 array of policy stringency per area
        area_incident_rates: np.ndarray,    # float32 array of incident case rates per area
        rumor_beliefs: Optional[np.ndarray] = None  # (n_topics, n_agents)
    ) -> np.ndarray:
        """Update daily compliance and fatigue across all synthetic agents.

        Returns:
            updated_compliance: float32 array in [0.0, 1.0]
        """
        # 1. Local risk perception from area incident rate
        agent_areas = self.pop.area_id
        agent_risk_perception = np.clip(area_incident_rates[agent_areas] * 10.0, 0.0, 1.0)

        # 2. Peer network norm: (A @ compliance)_i
        peer_norm = np.array(self.adj.dot(self.current_compliance)).flatten().astype(np.float32)

        # 3. Area policy enforcement
        agent_enforcement = area_enforcements[agent_areas]

        # 4. Misinformation erosion: sum_k kappa_k * belief_ik
        rumor_erosion = np.zeros(self.n_agents, dtype=np.float32)
        if rumor_beliefs is not None and rumor_beliefs.shape[0] > 0:
            total_belief = np.sum(rumor_beliefs, axis=0)
            rumor_erosion = self.weights.kappa * total_belief

        # 5. Dynamic compliance equation (Spec 8)
        new_compliance = (
            self.base_compliance
            + self.weights.w_risk * agent_risk_perception
            + self.weights.w_norm * peer_norm
            + self.weights.w_enf * agent_enforcement
            - self.weights.w_fat * self.fatigue
            - rumor_erosion
        )
        self.current_compliance = np.clip(new_compliance, 0.0, 1.0).astype(np.float32)

        # 6. Fatigue update
        measure_active = agent_enforcement > 0.05
        self.fatigue[measure_active] = np.clip(
            self.fatigue[measure_active] + self.weights.fatigue_rate,
            0.0, 1.0
        )
        self.fatigue[~measure_active] = np.clip(
            self.fatigue[~measure_active] - self.weights.fatigue_recovery,
            0.0, 1.0
        )

        return self.current_compliance

