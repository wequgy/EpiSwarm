"""Twin experiment parameter recovery harness and identifiability evaluation (Phase 18)."""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
from scipy.optimize import minimize

from episwarm.engine.sim import SimulationResults
from episwarm.observation.config import (
    ObservationConfig,
    DelayDistribution,
    AscertainmentModel,
    HospitalObservationConfig
)
from episwarm.observation.engine import generate_observations, convolve_delay


@dataclass
class ParameterRecoveryStats:
    """Statistical summary for a recovered parameter across replicates."""
    name: str
    true_value: float
    estimates: List[float]
    mean_estimate: float = 0.0
    bias: float = 0.0
    relative_bias_pct: float = 0.0
    std_error: float = 0.0
    ci_95_lower: float = 0.0
    ci_95_upper: float = 0.0
    is_identifiable: bool = True
    identifiability_notes: str = ""

    def compute(self) -> None:
        arr = np.array(self.estimates, dtype=np.float64)
        if len(arr) == 0:
            return
        self.mean_estimate = float(np.mean(arr))
        self.bias = float(self.mean_estimate - self.true_value)
        self.relative_bias_pct = float((self.bias / max(1e-6, abs(self.true_value))) * 100.0)
        self.std_error = float(np.std(arr, ddof=1) if len(arr) > 1 else 0.0)
        margin = 1.96 * (self.std_error / np.sqrt(len(arr))) if len(arr) > 1 else 0.0
        self.ci_95_lower = float(self.mean_estimate - margin)
        self.ci_95_upper = float(self.mean_estimate + margin)


@dataclass
class TwinExperimentResult:
    """Summary of twin experiment parameter recovery across N replicates."""
    n_replicates: int
    parameters: Dict[str, ParameterRecoveryStats] = field(default_factory=dict)
    unidentifiable_pairs: List[Dict[str, str]] = field(default_factory=list)
    replicate_losses: List[float] = field(default_factory=list)

    def summary_table(self) -> str:
        lines = [
            "==========================================================================================",
            "TWIN EXPERIMENT: PARAMETER RECOVERY REPORT (Phase 18)",
            f"Evaluated across {self.n_replicates} paired stochastic observation replicates",
            "------------------------------------------------------------------------------------------",
            f"{'Parameter':<25} | {'True':>8} | {'Recovered':>10} | {'95% CI':>18} | {'Bias %':>8} | {'Identifiable':>12}",
            "------------------------------------------------------------------------------------------"
        ]
        for name, stat in self.parameters.items():
            ci_str = f"[{stat.ci_95_lower:.3f}, {stat.ci_95_upper:.3f}]"
            ident_str = "YES" if stat.is_identifiable else "NO (Confounded)"
            lines.append(
                f"{stat.name:<25} | {stat.true_value:>8.3f} | {stat.mean_estimate:>10.3f} | {ci_str:>18} | {stat.relative_bias_pct:>+7.2f}% | {ident_str:>12}"
            )
        lines.append("==========================================================================================")

        if self.unidentifiable_pairs:
            lines.append("\nSTRUCTURAL UNIDENTIFIABILITY ANALYSIS:")
            for pair in self.unidentifiable_pairs:
                lines.append(f"  * {pair['parameters']}: {pair['mechanism']}")
            lines.append("==========================================================================================")

        return "\n".join(lines)


def fit_observation_parameters(
    observed_cases: np.ndarray,
    observed_admissions: np.ndarray,
    observed_occupancy: np.ndarray,
    latent_symptomatic: np.ndarray,
    dow_weights: np.ndarray,
    initial_guess: Tuple[float, float, float] = (0.20, 3.5, 6.0)
) -> Tuple[float, float, float, float]:
    """Recover (ascertainment_rho, case_delay_mean, acute_los_mean) via bounded least-squares loss.

    Returns:
        (rho_hat, delay_hat, los_hat, loss)
    """
    horizon = len(observed_cases)
    dow_cycle = np.tile(dow_weights, int(np.ceil(horizon / 7.0)))[:horizon]

    def objective(params: np.ndarray) -> float:
        rho, delay_mean, los_mean = params
        # 1. Model expected cases: delay convolution + ascertainment + day-of-week
        dist = DelayDistribution(dist_type="gamma", mean=delay_mean, std=max(1.0, delay_mean * 0.45), max_days=25)
        pmf_case = dist.to_pmf(max_days=25)
        pred_cases = convolve_delay(latent_symptomatic, pmf_case) * rho * dow_cycle

        # 2. Model expected Acute Bed Occupancy: survival renewal from admissions
        los_dist = DelayDistribution(dist_type="gamma", mean=los_mean, std=max(1.0, los_mean * 0.50), max_days=40)
        los_pmf = los_dist.to_pmf(max_days=40)
        los_survival = np.maximum(0.0, 1.0 - np.cumsum(los_pmf))
        pred_occupancy = convolve_delay(observed_admissions.astype(np.float64), los_survival)

        case_scale = max(1.0, float(np.mean(observed_cases)))
        occ_scale = max(1.0, float(np.mean(observed_occupancy)))

        loss_cases = np.mean(((observed_cases - pred_cases) / case_scale) ** 2)
        loss_occ = np.mean(((observed_occupancy - pred_occupancy) / occ_scale) ** 2)

        return float(loss_cases + loss_occ)

    bounds = [
        (0.05, 0.80),    # rho
        (1.0, 15.0),     # delay_mean
        (2.0, 25.0)      # los_mean
    ]

    res = minimize(
        objective,
        x0=np.array(initial_guess, dtype=np.float64),
        method="L-BFGS-B",
        bounds=bounds
    )

    rho_hat, delay_hat, los_hat = res.x
    return float(rho_hat), float(delay_hat), float(los_hat), float(res.fun)


def run_twin_experiment(
    sim_results: SimulationResults,
    n_replicates: int = 30,
    random_seed: int = 42,
    true_rho: float = 0.35,
    true_case_delay: float = 5.0,
    true_acute_los: float = 8.0
) -> TwinExperimentResult:
    """Execute parameter recovery twin experiment across N paired stochastic replicates (Phase 18)."""
    # 1. Ground truth observation configuration
    true_obs_config = ObservationConfig(
        name="ground_truth_twin",
        ascertainment=AscertainmentModel(model_type="constant", base_fraction=true_rho),
        case_delay=DelayDistribution(dist_type="gamma", mean=true_case_delay, std=2.2, max_days=25),
        hospital=HospitalObservationConfig(
            acute_los=DelayDistribution(dist_type="gamma", mean=true_acute_los, std=3.5, max_days=40)
        ),
        reporting_noise="negbin",
        negbin_dispersion=25.0
    )

    dow_weights = np.array(true_obs_config.day_of_week.weights, dtype=np.float64)

    recovered_rho = []
    recovered_delay = []
    recovered_los = []
    losses = []

    # 2. Iterate across N stochastic observation draws
    for rep in range(n_replicates):
        sub_rng = np.random.default_rng(random_seed + rep * 101)
        obs = generate_observations(sim_results, true_obs_config, rng=sub_rng)

        # Estimate parameters
        r_hat, d_hat, los_hat, loss = fit_observation_parameters(
            obs.reported_cases,
            obs.hospital_admissions,
            obs.acute_bed_occupancy,
            obs.true_incident_symptomatic,
            dow_weights,
            initial_guess=(0.20, 3.5, 5.0)
        )

        recovered_rho.append(r_hat)
        recovered_delay.append(d_hat)
        recovered_los.append(los_hat)
        losses.append(loss)

    # 3. Compile statistical metrics
    stat_rho = ParameterRecoveryStats(
        name="Ascertainment (rho)",
        true_value=true_rho,
        estimates=recovered_rho,
        is_identifiable=True,
        identifiability_notes="Identifiable when serological anchor or latent symptomatic incidence shape is known."
    )
    stat_rho.compute()

    stat_delay = ParameterRecoveryStats(
        name="Case Delay Mean (days)",
        true_value=true_case_delay,
        estimates=recovered_delay,
        is_identifiable=True,
        identifiability_notes="Identifiable via time lag between onset incidence and reported peak timing."
    )
    stat_delay.compute()

    stat_los = ParameterRecoveryStats(
        name="Hospital Acute LoS (days)",
        true_value=true_acute_los,
        estimates=recovered_los,
        is_identifiable=True,
        identifiability_notes="Identifiable from the ratio of peak occupancy to admission velocity and clearance tail."
    )
    stat_los.compute()

    # 4. Structural Unidentifiability Analysis
    unidentifiable_pairs = [
        {
            "parameters": "(Ascertainment rho, Transmission beta / Initial Seeds)",
            "mechanism": "Without seroprevalence, a large epidemic with low ascertainment produces mathematically indistinguishable case curves from a smaller epidemic with high ascertainment (scale-transmission confounding)."
        },
        {
            "parameters": "(Onset-to-Test Delay, Test-to-Report Delay)",
            "mechanism": "When only the final public notification date is recorded, the internal partition between test-seeking delay and laboratory turnaround is non-identifiable without explicit sample collection timestamps."
        }
    ]

    return TwinExperimentResult(
        n_replicates=n_replicates,
        parameters={
            "ascertainment_rho": stat_rho,
            "case_delay_mean": stat_delay,
            "acute_los_mean": stat_los
        },
        unidentifiable_pairs=unidentifiable_pairs,
        replicate_losses=losses
    )
