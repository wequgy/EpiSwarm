"""Compiled disease state graph for Structure-of-Arrays (SoA) simulation."""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from scipy import stats

from episwarm.packs.disease import DiseasePack, DiseaseState, StateTransition


class CompiledStateGraph:
    """Pre-compiled numerical tables and dispatchers for high-performance agent state transitions."""

    def __init__(self, disease_pack: DiseasePack, age_bands: List[str]):
        self.pack = disease_pack
        self.age_bands = age_bands

        # 1. State mappings
        self.state_names = [s.name for s in disease_pack.states]
        self.n_states = len(self.state_names)
        self.name_to_idx = {name: i for i, name in enumerate(self.state_names)}
        self.idx_to_name = {i: name for i, name in enumerate(self.state_names)}

        # Key state indices
        self.idx_S = self.name_to_idx.get("S", 0)
        self.idx_E = self.name_to_idx.get("E", 1 if self.n_states > 1 else 0)
        self.idx_R = self.name_to_idx.get("R", -1)
        self.idx_D = self.name_to_idx.get("D", -1)

        # 2. State property vectors
        self.is_infectious = np.zeros(self.n_states, dtype=bool)
        self.rel_infectiousness = np.zeros(self.n_states, dtype=np.float32)
        self.is_absorbing = np.zeros(self.n_states, dtype=bool)
        self.needs_care = np.zeros(self.n_states, dtype=bool)
        self.severity_level = np.zeros(self.n_states, dtype=np.float32)
        self.state_needs: List[Dict[str, float]] = []

        # Backward compatibility vector
        self.needs_bed = np.zeros(self.n_states, dtype=np.int8)

        for i, s in enumerate(disease_pack.states):
            self.is_infectious[i] = s.infectious
            self.rel_infectiousness[i] = s.relative_infectiousness
            self.is_absorbing[i] = s.absorbing
            self.needs_care[i] = s.needs_care or bool(s.needs)
            self.severity_level[i] = s.severity_level
            self.state_needs.append(dict(s.needs))

            # Approximate bed requirement for backward compatibility
            needs_keys = [k.lower() for k in s.needs.keys()]
            if any("icu" in k for k in needs_keys):
                self.needs_bed[i] = 3
            elif any("bed" in k or "general" in k for k in needs_keys) or s.needs_care:
                self.needs_bed[i] = 1

        # 3. Transitions by source state
        self.transitions_by_from: Dict[int, List[StateTransition]] = {i: [] for i in range(self.n_states)}
        for t in disease_pack.transitions:
            from_idx = self.name_to_idx[t.from_state]
            self.transitions_by_from[from_idx].append(t)

        # Calculate mean infectious period for R0 calibration
        inf_durations = []
        for i in range(self.n_states):
            if self.is_infectious[i]:
                for t in self.transitions_by_from[i]:
                    inf_durations.append(t.duration.mean_days)
        self.mean_infectious_days = float(np.mean(inf_durations)) if inf_durations else 5.0

    def sample_dwell_time(
        self,
        from_state_idx: int,
        target_state_idx: int,
        n_samples: int,
        rng: np.random.Generator
    ) -> np.ndarray:
        """Sample dwell durations in days for agents entering a compartment."""
        transitions = self.transitions_by_from.get(from_state_idx, [])
        matched = [t for t in transitions if self.name_to_idx[t.to_state] == target_state_idx]
        if not matched:
            return np.ones(n_samples, dtype=np.float32)

        dur = matched[0].duration
        if dur.type == "constant":
            return np.full(n_samples, dur.mean_days, dtype=np.float32)
        elif dur.type == "exponential":
            scale = dur.mean_days
            return np.clip(rng.exponential(scale, size=n_samples), 0.5, None).astype(np.float32)
        elif dur.type == "gamma":
            sd = dur.sd_days or (0.3 * dur.mean_days)
            k = max(0.1, (dur.mean_days / sd) ** 2)
            theta = max(0.1, (sd ** 2) / dur.mean_days)
            return np.clip(rng.gamma(k, theta, size=n_samples), 0.5, None).astype(np.float32)
        elif dur.type == "lognormal":
            mean = dur.mean_days
            sd = dur.sd_days or (0.3 * mean)
            sigma2 = np.log(1.0 + (sd / mean) ** 2)
            mu = np.log(mean) - 0.5 * sigma2
            return np.clip(rng.lognormal(mu, np.sqrt(sigma2), size=n_samples), 0.5, None).astype(np.float32)

        return np.full(n_samples, dur.mean_days, dtype=np.float32)

    def resolve_next_state(
        self,
        current_state_idx: int,
        agent_age_bands: np.ndarray,
        comorbidity_multipliers: np.ndarray,
        rng: np.random.Generator,
        vulnerability_odds: Optional[np.ndarray] = None,
        adverse_prob_override: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Determine next states and dwell times for agents whose dwell time in current_state has expired.

        Supports:
        - Age multipliers
        - Comorbidity multipliers
        - Logit-scale vulnerability odds (Spec 5.1)
        - Individual unserved adverse probability overrides (Spec 6.3)
        """
        n_agents = len(agent_age_bands)
        if n_agents == 0:
            return np.empty(0, dtype=np.int16), np.empty(0, dtype=np.float32)

        transitions = self.transitions_by_from.get(current_state_idx, [])
        if not transitions:
            return np.full(n_agents, current_state_idx, dtype=np.int16), np.full(n_agents, 9999.0, dtype=np.float32)

        next_states = np.full(n_agents, current_state_idx, dtype=np.int16)
        dwell_times = np.ones(n_agents, dtype=np.float32)

        to_indices = [self.name_to_idx[t.to_state] for t in transitions]
        base_probs = np.array([t.base_probability for t in transitions], dtype=np.float64)

        for i in range(n_agents):
            band = agent_age_bands[i]
            c_mult = comorbidity_multipliers[i]
            v_odds = vulnerability_odds[i] if vulnerability_odds is not None else 1.0
            adv_override = adverse_prob_override[i] if adverse_prob_override is not None else None

            adj_probs = base_probs.copy()
            for t_idx, t in enumerate(transitions):
                to_idx = to_indices[t_idx]
                is_worse = (to_idx == self.idx_D) or (self.severity_level[to_idx] > self.severity_level[current_state_idx])

                if band in t.age_multipliers:
                    adj_probs[t_idx] *= t.age_multipliers[band]

                if t.comorbidity_multipliers:
                    adj_probs[t_idx] *= c_mult

                # Apply vulnerability odds on logit scale for severe/fatal progression (Spec 5.1)
                if is_worse and v_odds != 1.0 and adj_probs[t_idx] > 0:
                    p = np.clip(adj_probs[t_idx], 1e-5, 1.0 - 1e-5)
                    logit_p = np.log(p / (1.0 - p)) + np.log(max(1e-4, float(v_odds)))
                    adj_probs[t_idx] = 1.0 / (1.0 + np.exp(-logit_p))

                # Apply unserved overflow adverse probability override if provided (Spec 6.3)
                if is_worse and adv_override is not None:
                    adj_probs[t_idx] = float(adv_override)

            p_sum = adj_probs.sum()
            if p_sum > 0:
                p_norm = adj_probs / p_sum
                chosen_idx = rng.choice(to_indices, p=p_norm)
            else:
                chosen_idx = to_indices[0]

            next_states[i] = chosen_idx

        # Draw dwell times for chosen transitions
        for to_idx in to_indices:
            mask = (next_states == to_idx)
            count = int(np.sum(mask))
            if count > 0:
                dwell_times[mask] = self.sample_dwell_time(current_state_idx, to_idx, count, rng)

        return next_states, dwell_times
