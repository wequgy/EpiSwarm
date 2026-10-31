"""Area-level Metapopulation Engine (Libin et al. 2020, arXiv:2003.13676).

Implements:
1. Intra-area age-structured SEIR with Binomial chain (or deterministic equivalent).
2. Inter-area infection via non-homogeneous Poisson process (Libin et al. Algorithm 2)
   using time-scale transformation.
3. Disease multi-state collapsing to SEIR with documented mapping.
4. Calibration of spatial scaling parameter mu = log(R0) * s fitted per region and pathogen.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from scipy.optimize import minimize_scalar

from episwarm.packs.disease import DiseasePack
from episwarm.packs.region import RegionPack
from episwarm.packs.scenario import ScenarioPack, InterventionAction


@dataclass
class MetaSimResult:
    """Outcomes from a metapopulation simulation run."""
    horizon_days: int
    n_areas: int
    n_age_bands: int
    area_ids: List[str]
    age_band_names: List[str]

    # Trajectories (shape: days x areas x age_bands)
    S: np.ndarray
    E: np.ndarray
    I: np.ndarray
    R: np.ndarray

    # Aggregate summaries
    daily_new_infections: np.ndarray  # shape: days x areas
    daily_active_infections: np.ndarray  # shape: days (all areas combined)
    peak_day: int
    peak_infections: float
    attack_rate: float
    total_infections: float
    initial_population: float

    # Spatial contagion telemetry
    infected_day_per_area: Dict[str, Optional[int]]
    stochastic_mode: str  # "binomial_chain" or "deterministic"
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetapopulationEngine:
    """Fast, area-level metapopulation epidemiological engine (Libin et al. 2020).

    Uses:
    (a) Cross-validation of the agent-based micro-simulation engine.
    (b) Fast screening of intervention measures.
    (c) Deterministic or stochastic surrogate for policy search and optimization.
    """

    def __init__(
        self,
        area_populations: Dict[str, int],
        contact_matrix: np.ndarray,
        beta: float,
        latent_period_days: float = 3.0,
        infectious_period_days: float = 5.0,
        mobility_matrix: Optional[np.ndarray] = None,
        area_ids: Optional[List[str]] = None,
        age_proportions: Optional[np.ndarray] = None,
        mu: float = 0.5,
        adult_age_idx: int = 1,
        stochastic: bool = True,
        seed: int = 42
    ):
        """Initialize metapopulation engine.

        Stochastic Choice:
        Per Spec 11.1 and Libin et al. (2020), this engine implements the Binomial-chain
        formulation:
            new_E ~ Bin(S, 1 - exp(-phi))
            new_I ~ Bin(E, 1 - exp(-zeta))
            new_R ~ Bin(I, 1 - exp(-gamma))
        When stochastic=False, expected rates are evaluated deterministically:
            new_E = S * (1 - exp(-phi))
            new_I = E * (1 - exp(-zeta))
            new_R = I * (1 - exp(-gamma))

        Multi-State Disease Collapsing:
        Multi-state compartments are collapsed to standard SEIR:
            S: Susceptible
            E: Latent / Presymptomatic
            I: All active infectious states combined
            R: Recovered + Fatalities (absorbing)
        """
        self.area_ids = area_ids or list(area_populations.keys())
        self.n_areas = len(self.area_ids)
        self.area_to_idx = {aid: i for i, aid in enumerate(self.area_ids)}

        # Age bands
        self.contact_matrix = np.asarray(contact_matrix, dtype=np.float64)
        self.n_age_bands = self.contact_matrix.shape[0]
        if age_proportions is None:
            # Equal distribution across age bands if unspecified
            self.age_proportions = np.ones(self.n_age_bands, dtype=np.float64) / self.n_age_bands
        else:
            p = np.asarray(age_proportions, dtype=np.float64)
            self.age_proportions = p / np.sum(p)

        self.beta = float(beta)
        self.zeta = 1.0 / max(0.1, float(latent_period_days))   # Latency rate
        self.gamma = 1.0 / max(0.1, float(infectious_period_days)) # Recovery rate
        self.mu = float(mu)
        self.adult_age_idx = min(adult_age_idx, self.n_age_bands - 1)
        self.stochastic = stochastic
        self.rng = np.random.default_rng(seed)

        # Build population array (shape: n_areas x n_age_bands)
        self.N_area = np.array([area_populations[aid] for aid in self.area_ids], dtype=np.float64)
        self.N = np.outer(self.N_area, self.age_proportions)

        # Mobility matrix Mob[p_from, p_to]
        if mobility_matrix is not None:
            self.Mob = np.asarray(mobility_matrix, dtype=np.float64)
            assert self.Mob.shape == (self.n_areas, self.n_areas), (
                f"Mobility matrix shape {self.Mob.shape} != ({self.n_areas}, {self.n_areas})"
            )
        else:
            # Default: identity (no cross-area commuting)
            self.Mob = np.eye(self.n_areas, dtype=np.float64)

        # Adult-adult contact rate M_AA
        self.M_AA = float(self.contact_matrix[self.adult_age_idx, self.adult_age_idx])

    @classmethod
    def from_packs(
        cls,
        region_pack: RegionPack,
        disease_pack: DiseasePack,
        area_populations: Optional[Dict[str, int]] = None,
        mobility_matrix: Optional[np.ndarray] = None,
        mu: Optional[float] = None,
        stochastic: bool = True,
        seed: int = 42
    ) -> "MetapopulationEngine":
        """Factory method to construct engine directly from RegionPack and DiseasePack."""
        # 1. Age contact matrix
        c_mat = np.array(disease_pack.contacts.setting_matrices.get("all", np.eye(4) * 5.0), dtype=np.float64)
        n_bands = c_mat.shape[0]

        # 2. Derive latency and infectious periods by collapsing disease states
        latent_days = 3.0
        infectious_days = 5.0
        for s in disease_pack.states:
            s_name = s.name.lower()
            if "latent" in s_name or "presymptomatic" in s_name or "exposed" in s_name:
                latent_days = float(s.dwell_time_days)
            elif "infectious" in s_name or "symptomatic" in s_name:
                infectious_days = float(s.dwell_time_days)

        # 3. Areas and population
        if area_populations is None:
            # Fallback area populations
            area_populations = {"A01": 25000, "A02": 25000}
        area_ids = list(area_populations.keys())
        n_areas = len(area_ids)

        if mobility_matrix is None:
            # Build symmetric commuting if unsupplied
            mobility_matrix = np.eye(n_areas, dtype=np.float64) * 0.8
            if n_areas > 1:
                off_diag = 0.2 / (n_areas - 1)
                mobility_matrix += off_diag
                np.fill_diagonal(mobility_matrix, 0.8)

        # 4. Calibrated beta
        beta = float(disease_pack.r0 * (1.0 / infectious_days) / max(1.0, float(np.max(np.linalg.eigvals(c_mat).real))))

        # 5. mu parameter
        if mu is None:
            # Libin et al. mu = log(R0) * s; default baseline s=0.5
            mu = float(np.clip(np.log(max(1.01, disease_pack.r0)) * 0.5, 0.05, 0.95))

        return cls(
            area_populations=area_populations,
            contact_matrix=c_mat,
            beta=beta,
            latent_period_days=latent_days,
            infectious_period_days=infectious_days,
            mobility_matrix=mobility_matrix,
            area_ids=area_ids,
            mu=mu,
            stochastic=stochastic,
            seed=seed
        )

    def run(
        self,
        horizon_days: int = 90,
        initial_infected_area: str = "A01",
        n_initial_seeds: int = 10,
        interventions: Optional[List[InterventionAction]] = None
    ) -> MetaSimResult:
        """Execute metapopulation simulation run over specified horizon."""
        P = self.n_areas
        A = self.n_age_bands

        # Initialize compartments (P x A)
        S = np.copy(self.N)
        E = np.zeros((P, A), dtype=np.float64)
        I = np.zeros((P, A), dtype=np.float64)
        R = np.zeros((P, A), dtype=np.float64)

        # Spatial infection tracking
        is_area_infected = np.zeros(P, dtype=bool)
        infected_day: Dict[str, Optional[int]] = {aid: None for aid in self.area_ids}

        # Seed initial infected area
        seed_idx = self.area_to_idx.get(initial_infected_area, 0)
        seed_count = min(float(n_initial_seeds), S[seed_idx, self.adult_age_idx])
        S[seed_idx, self.adult_age_idx] -= seed_count
        I[seed_idx, self.adult_age_idx] += seed_count
        is_area_infected[seed_idx] = True
        infected_day[self.area_ids[seed_idx]] = 0

        # Time-scale transformation (Algorithm 2 in Libin et al.):
        # Draw threshold X_p ~ Exp(1) for each area
        X_threshold = self.rng.exponential(scale=1.0, size=P)
        cumulative_lambda = np.zeros(P, dtype=np.float64)

        # Output histories
        hist_S = np.zeros((horizon_days, P, A), dtype=np.float64)
        hist_E = np.zeros((horizon_days, P, A), dtype=np.float64)
        hist_I = np.zeros((horizon_days, P, A), dtype=np.float64)
        hist_R = np.zeros((horizon_days, P, A), dtype=np.float64)
        hist_new_inf = np.zeros((horizon_days, P), dtype=np.float64)

        for day in range(horizon_days):
            # Record state at start of day
            hist_S[day] = S
            hist_E[day] = E
            hist_I[day] = I
            hist_R[day] = R

            # Calculate active intervention multipliers
            contact_multiplier = 1.0
            if interventions:
                for act in interventions:
                    if act.start_day <= day <= act.end_day:
                        if act.measure_type in ("school_closure", "social_distancing", "lockdown"):
                            contact_multiplier *= (1.0 - 0.5 * act.stringency)

            current_M = self.contact_matrix * contact_multiplier

            # -------------------------------------------------------------
            # 1. Inter-area infection process (Libin et al. Algorithm 2)
            # -------------------------------------------------------------
            uninfected_mask = ~is_area_infected
            if np.any(uninfected_mask) and np.any(is_area_infected):
                # Infectious adults per area
                I_adults = I[:, self.adult_age_idx]  # shape (P,)
                # Susceptible adults per area
                S_adults = S[:, self.adult_age_idx]  # shape (P,)
                N_adults = np.maximum(1.0, self.N[:, self.adult_age_idx])

                # Spec 11.2 & Libin et al. (2020) Eq S3.E4, S3.E5:
                # phi_p(t) = sum_{p'} Mob[p', p] * beta * (S^A_p(t) / N^A_p)^mu * Iinf_{p'}(t)
                # Iinf_{p'}(t) = I^A_{p'}(t) * M_AA
                norm_S_mu = (S_adults / N_adults) ** self.mu
                I_inf = I_adults * self.M_AA

                # Matrix-vector product over infected patches
                flux_in = np.dot(self.Mob.T, I_inf)

                phi_patch = flux_in * self.beta * norm_S_mu

                # Accumulate intensity for uninfected areas
                for p in np.where(uninfected_mask)[0]:
                    daily_intensity = phi_patch[p]
                    cumulative_lambda[p] += daily_intensity

                    # Check infection arrival event
                    if cumulative_lambda[p] >= X_threshold[p]:
                        is_area_infected[p] = True
                        infected_day[self.area_ids[p]] = day
                        # Seed infection in area p
                        seed_p = min(float(n_initial_seeds), S[p, self.adult_age_idx])
                        S[p, self.adult_age_idx] -= seed_p
                        I[p, self.adult_age_idx] += seed_p

            # -------------------------------------------------------------
            # 2. Intra-area SEIR stepping (Spec 11.1)
            # -------------------------------------------------------------
            for p in range(P):
                # Total population in area p per age band
                N_p = np.maximum(1.0, self.N[p, :])
                I_p = I[p, :]

                # Force of infection per age band i:
                # phi_i = sum_j beta * M_ij * I_j / N_j
                phi_i = np.dot(current_M, (I_p / N_p)) * self.beta

                p_inf = 1.0 - np.exp(-phi_i)
                p_inc = 1.0 - np.exp(-self.zeta)
                p_rec = 1.0 - np.exp(-self.gamma)

                if self.stochastic:
                    # Binomial-chain stochastic sampling
                    new_E = self.rng.binomial(S[p, :].astype(np.int64), np.clip(p_inf, 0.0, 1.0)).astype(np.float64)
                    new_I = self.rng.binomial(E[p, :].astype(np.int64), np.clip(p_inc, 0.0, 1.0)).astype(np.float64)
                    new_R = self.rng.binomial(I[p, :].astype(np.int64), np.clip(p_rec, 0.0, 1.0)).astype(np.float64)
                else:
                    # Deterministic expected continuous values
                    new_E = S[p, :] * p_inf
                    new_I = E[p, :] * p_inc
                    new_R = I[p, :] * p_rec

                # Update compartments
                S[p, :] -= new_E
                E[p, :] += (new_E - new_I)
                I[p, :] += (new_I - new_R)
                R[p, :] += new_R

                hist_new_inf[day, p] = np.sum(new_E)

        # Compute summary metrics
        daily_active = np.sum(hist_I, axis=(1, 2))
        peak_day = int(np.argmax(daily_active))
        peak_inf = float(daily_active[peak_day])
        total_inf = float(np.sum(hist_R[-1]) + np.sum(hist_I[-1]) + np.sum(hist_E[-1]))
        total_pop = float(np.sum(self.N))
        attack_rate = float(total_inf / total_pop) if total_pop > 0 else 0.0

        return MetaSimResult(
            horizon_days=horizon_days,
            n_areas=P,
            n_age_bands=A,
            area_ids=self.area_ids,
            age_band_names=[f"Age_{i}" for i in range(A)],
            S=hist_S,
            E=hist_E,
            I=hist_I,
            R=hist_R,
            daily_new_infections=hist_new_inf,
            daily_active_infections=daily_active,
            peak_day=peak_day,
            peak_infections=peak_inf,
            attack_rate=attack_rate,
            total_infections=total_inf,
            initial_population=total_pop,
            infected_day_per_area=infected_day,
            stochastic_mode="binomial_chain" if self.stochastic else "deterministic",
            metadata={
                "beta": self.beta,
                "mu": self.mu,
                "zeta": self.zeta,
                "gamma": self.gamma
            }
        )


def fit_mu(
    area_populations: Dict[str, int],
    contact_matrix: np.ndarray,
    infectious_period_days: float = 5.0,
    latent_period_days: float = 3.0,
    r0_targets: Tuple[float, ...] = (1.5, 2.0, 2.5),
    horizon_days: int = 90
) -> Tuple[float, Dict[str, Any]]:
    """Fit spatial scaling parameter mu = log(R0) * s per Libin et al. 2020 (Spec 11.3).

    Fits scaling constant 's' such that the peak day of the spatial patch model
    best matches the aggregate homogeneous mixing age-structured SEIR.
    Returns:
        (fitted_s, calibration_report_dict)
    """
    total_pop = sum(area_populations.values())
    single_area_pop = {"ALL": total_pop}
    gamma = 1.0 / infectious_period_days
    dom_eig = max(1.0, float(np.max(np.linalg.eigvals(contact_matrix).real)))

    def loss(s_cand: float) -> float:
        sq_err = 0.0
        for r0 in r0_targets:
            beta = float(r0 * gamma / dom_eig)
            mu_val = float(np.clip(np.log(max(1.01, r0)) * s_cand, 0.01, 1.0))

            # 1. Homogeneous baseline
            eng_homog = MetapopulationEngine(
                area_populations=single_area_pop,
                contact_matrix=contact_matrix,
                beta=beta,
                latent_period_days=latent_period_days,
                infectious_period_days=infectious_period_days,
                stochastic=False
            )
            res_homog = eng_homog.run(horizon_days=horizon_days, n_initial_seeds=20)

            # 2. Patch model with candidate s
            eng_patch = MetapopulationEngine(
                area_populations=area_populations,
                contact_matrix=contact_matrix,
                beta=beta,
                latent_period_days=latent_period_days,
                infectious_period_days=infectious_period_days,
                mu=mu_val,
                stochastic=False
            )
            res_patch = eng_patch.run(horizon_days=horizon_days, n_initial_seeds=20)

            diff_peak = res_patch.peak_day - res_homog.peak_day
            diff_attack = res_patch.attack_rate - res_homog.attack_rate
            sq_err += (diff_peak ** 2) + 100.0 * (diff_attack ** 2)
        return float(sq_err)

    # Minimize loss over s in [0.05, 3.0]
    res = minimize_scalar(loss, bounds=(0.05, 3.0), method="bounded")
    fitted_s = float(res.x)

    # Generate calibration report
    report: Dict[str, Any] = {
        "fitted_s": round(fitted_s, 4),
        "loss": round(float(res.fun), 4),
        "r0_evaluations": []
    }

    for r0 in r0_targets:
        beta = float(r0 * gamma / dom_eig)
        mu_val = float(np.clip(np.log(max(1.01, r0)) * fitted_s, 0.01, 1.0))

        eng_homog = MetapopulationEngine(
            area_populations=single_area_pop,
            contact_matrix=contact_matrix,
            beta=beta,
            latent_period_days=latent_period_days,
            infectious_period_days=infectious_period_days,
            stochastic=False
        )
        res_homog = eng_homog.run(horizon_days=horizon_days, n_initial_seeds=20)

        eng_patch = MetapopulationEngine(
            area_populations=area_populations,
            contact_matrix=contact_matrix,
            beta=beta,
            latent_period_days=latent_period_days,
            infectious_period_days=infectious_period_days,
            mu=mu_val,
            stochastic=False
        )
        res_patch = eng_patch.run(horizon_days=horizon_days, n_initial_seeds=20)

        report["r0_evaluations"].append({
            "R0": r0,
            "mu": round(mu_val, 4),
            "peak_day_homog": res_homog.peak_day,
            "peak_day_patch": res_patch.peak_day,
            "peak_day_diff": res_patch.peak_day - res_homog.peak_day,
            "attack_rate_homog": round(res_homog.attack_rate, 4),
            "attack_rate_patch": round(res_patch.attack_rate, 4),
            "attack_rate_diff": round(res_patch.attack_rate - res_homog.attack_rate, 4)
        })

    return fitted_s, report
