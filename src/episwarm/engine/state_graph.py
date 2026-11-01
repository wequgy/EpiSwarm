"""Compiled disease state graph for Structure-of-Arrays (SoA) simulation."""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np

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

        # 4. Compute expected infectious duration weighted by relative infectiousness (Spec 4.2)
        # Compute DAG traversal visit probabilities and expected infectious duration
        # D = sum_s P(s | infection) * rel_inf_s * E[duration_s]
        visits = np.zeros(self.n_states, dtype=np.float64)
        visits[self.idx_E] = 1.0
        inflow = np.zeros(self.n_states, dtype=np.float64)
        inflow[self.idx_E] = 1.0

        for _ in range(self.n_states + 2):
            for u in range(self.n_states):
                if inflow[u] <= 0 or self.is_absorbing[u]:
                    continue
                trans = self.transitions_by_from.get(u, [])
                if not trans:
                    continue
                base_sum = sum(t.base_probability for t in trans)
                cur_inflow = inflow[u]
                inflow[u] = 0.0
                for t in trans:
                    v = self.name_to_idx[t.to_state]
                    p_uv = t.base_probability / base_sum if base_sum > 0 else 1.0 / len(trans)
                    inflow[v] += cur_inflow * p_uv
                    visits[v] += cur_inflow * p_uv

        total_d = 0.0
        for s_idx in range(self.n_states):
            if self.is_infectious[s_idx]:
                trans = self.transitions_by_from.get(s_idx, [])
                if trans:
                    mean_dwell = float(np.mean([t.duration.mean_days for t in trans]))
                else:
                    mean_dwell = 5.0
                total_d += visits[s_idx] * float(self.rel_infectiousness[s_idx]) * mean_dwell

        self.mean_infectious_days = float(max(1.0, total_d))

    def get_served_adverse_prob(self, state_idx: int) -> float:
        """Derive the baseline served adverse/fatality probability from outgoing graph transitions (Spec 6.3)."""
        transitions = self.transitions_by_from.get(state_idx, [])
        if not transitions:
            return 0.05
        adverse_prob = 0.0
        for t in transitions:
            to_idx = self.name_to_idx.get(t.to_state, -1)
            is_worse = (to_idx == self.idx_D) or (to_idx >= 0 and self.severity_level[to_idx] > self.severity_level[state_idx])
            if is_worse:
                adverse_prob += float(t.base_probability)
        return float(np.clip(adverse_prob, 0.01, 0.99)) if adverse_prob > 0 else 0.05

    def sample_state_dwell_time(
        self,
        state_idx: int,
        n_samples: int,
        rng: np.random.Generator
    ) -> np.ndarray:
        """Sample dwell durations in days for agents entering/residing in state_idx."""
        if n_samples == 0:
            return np.empty(0, dtype=np.float32)

        if self.is_absorbing[state_idx]:
            return np.full(n_samples, 99999.0, dtype=np.float32)

        transitions = self.transitions_by_from.get(state_idx, [])
        if not transitions:
            return np.full(n_samples, 5.0, dtype=np.float32)

        probs = np.array([t.base_probability for t in transitions], dtype=np.float64)
        if probs.sum() > 0:
            probs = probs / probs.sum()
        else:
            probs = np.ones(len(transitions)) / len(transitions)

        chosen_t = rng.choice(len(transitions), size=n_samples, p=probs)
        dwells = np.zeros(n_samples, dtype=np.float32)

        for t_idx, trans in enumerate(transitions):
            mask = (chosen_t == t_idx)
            count = int(np.sum(mask))
            if count == 0:
                continue

            dur = trans.duration
            if dur.type == "constant":
                dwells[mask] = np.full(count, dur.mean_days, dtype=np.float32)
            elif dur.type == "exponential":
                scale = max(0.1, dur.mean_days)
                dwells[mask] = np.clip(rng.exponential(scale, size=count), 0.5, None).astype(np.float32)
            elif dur.type == "gamma":
                sd = dur.sd_days or (0.3 * dur.mean_days)
                k = max(0.1, (dur.mean_days / max(0.01, sd)) ** 2)
                theta = max(0.1, (sd ** 2) / max(0.01, dur.mean_days))
                dwells[mask] = np.clip(rng.gamma(k, theta, size=count), 0.5, None).astype(np.float32)
            elif dur.type == "lognormal":
                mean = max(0.1, dur.mean_days)
                sd = dur.sd_days or (0.3 * mean)
                sigma2 = np.log(1.0 + (sd / mean) ** 2)
                mu = np.log(mean) - 0.5 * sigma2
                dwells[mask] = np.clip(rng.lognormal(mu, np.sqrt(sigma2), size=count), 0.5, None).astype(np.float32)
            else:
                dwells[mask] = np.full(count, dur.mean_days, dtype=np.float32)

        return dwells

    def sample_dwell_time(
        self,
        from_state_idx: int,
        target_state_idx: int,
        n_samples: int,
        rng: np.random.Generator
    ) -> np.ndarray:
        """Sample dwell durations in days for agents transitioning into target_state_idx."""
        transitions = self.transitions_by_from.get(from_state_idx, [])
        matched = [t for t in transitions if self.name_to_idx[t.to_state] == target_state_idx]
        if matched:
            dur = matched[0].duration
            if dur.type == "constant":
                return np.full(n_samples, dur.mean_days, dtype=np.float32)
            elif dur.type == "exponential":
                scale = max(0.1, dur.mean_days)
                return np.clip(rng.exponential(scale, size=n_samples), 0.5, None).astype(np.float32)
            elif dur.type == "gamma":
                sd = dur.sd_days or (0.3 * dur.mean_days)
                k = max(0.1, (dur.mean_days / max(0.01, sd)) ** 2)
                theta = max(0.1, (sd ** 2) / max(0.01, dur.mean_days))
                return np.clip(rng.gamma(k, theta, size=n_samples), 0.5, None).astype(np.float32)
            elif dur.type == "lognormal":
                mean = max(0.1, dur.mean_days)
                sd = dur.sd_days or (0.3 * mean)
                sigma2 = np.log(1.0 + (sd / mean) ** 2)
                mu = np.log(mean) - 0.5 * sigma2
                return np.clip(rng.lognormal(mu, np.sqrt(sigma2), size=n_samples), 0.5, None).astype(np.float32)

        # Fall back to target state's dwell time
        return self.sample_state_dwell_time(target_state_idx, n_samples, rng)

    def resolve_next_state(
        self,
        current_state_idx: int,
        agent_age_bands: np.ndarray,
        comorbidity_multipliers: np.ndarray,
        rng: np.random.Generator,
        vulnerability_odds: Optional[np.ndarray] = None,
        adverse_prob_override: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Determine next states and dwell times for agents whose dwell time in current_state has expired."""
        n_agents = len(agent_age_bands)
        if n_agents == 0:
            return np.empty(0, dtype=np.int16), np.empty(0, dtype=np.float32)

        transitions = self.transitions_by_from.get(current_state_idx, [])
        if not transitions:
            return np.full(n_agents, current_state_idx, dtype=np.int16), np.full(n_agents, 99999.0, dtype=np.float32)

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

                if is_worse and v_odds != 1.0 and adj_probs[t_idx] > 0:
                    p = np.clip(adj_probs[t_idx], 1e-5, 1.0 - 1e-5)
                    logit_p = np.log(p / (1.0 - p)) + np.log(max(1e-4, float(v_odds)))
                    adj_probs[t_idx] = 1.0 / (1.0 + np.exp(-logit_p))

                if is_worse and adv_override is not None:
                    adj_probs[t_idx] = float(adv_override)

            p_sum = adj_probs.sum()
            if p_sum > 0:
                p_norm = adj_probs / p_sum
                chosen_idx = rng.choice(to_indices, p=p_norm)
            else:
                chosen_idx = to_indices[0]

            next_states[i] = chosen_idx

        # Dwell times in the NEW state are sampled from that state's duration distribution
        for to_idx in to_indices:
            mask = (next_states == to_idx)
            count = int(np.sum(mask))
            if count > 0:
                dwell_times[mask] = self.sample_state_dwell_time(to_idx, count, rng)

        return next_states, dwell_times
