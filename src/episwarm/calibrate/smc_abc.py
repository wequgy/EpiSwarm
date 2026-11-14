"""Sequential Monte Carlo Approximate Bayesian Computation (SMC-ABC) for EpiSwarm (Stage A3).

Implements adaptive SMC-ABC algorithm following Toni et al. (2009) and Beaumont et al. (2009)
for calibrating epidemic parameters (R0, initial seed volume I0, policy effectiveness kappa)
against empirical clinical trajectories with rigorous uncertainty quantification.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Callable
import numpy as np
import pandas as pd
from scipy.stats import norm, uniform

from episwarm.population.build import PopulationSoA
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack, SeedingConfig
from episwarm.engine.sim import run_simulation


@dataclass
class SMCABCConfig:
    n_particles: int = 200
    n_generations: int = 3
    quantile_schedule: Tuple[float, ...] = (0.50, 0.25, 0.10)
    priors: Dict[str, Tuple[float, float]] = field(default_factory=lambda: {
        "r0": (2.2, 3.8),
        "i0": (15.0, 60.0),
        "kappa": (0.40, 0.85)
    })
    random_seed: int = 42


@dataclass
class Particle:
    params: Dict[str, float]
    weight: float
    distance: float
    sim_peak_day: int
    sim_peak_val: float
    sim_total: float


@dataclass
class PosteriorEnsemble:
    particles: List[Particle]
    generation: int
    tolerance: float
    parameter_names: List[str]

    def get_parameter_array(self, param_name: str) -> np.ndarray:
        return np.array([p.params[param_name] for p in self.particles])

    def get_weights(self) -> np.ndarray:
        w = np.array([p.weight for p in self.particles])
        return w / np.sum(w)

    def summary(self) -> Dict[str, Dict[str, float]]:
        weights = self.get_weights()
        stats = {}
        for p_name in self.parameter_names:
            vals = self.get_parameter_array(p_name)
            # Weighted mean
            w_mean = float(np.sum(vals * weights))
            # Weighted variance
            w_var = float(np.sum(weights * (vals - w_mean) ** 2))
            w_std = float(np.sqrt(w_var))

            # Weighted quantiles via sorting
            sort_idx = np.argsort(vals)
            sorted_vals = vals[sort_idx]
            cum_w = np.cumsum(weights[sort_idx])

            q025 = float(sorted_vals[np.searchsorted(cum_w, 0.025)])
            q50 = float(sorted_vals[np.searchsorted(cum_w, 0.50)])
            q975 = float(sorted_vals[np.searchsorted(cum_w, 0.975)])

            stats[p_name] = {
                "mean": round(w_mean, 3),
                "std": round(w_std, 3),
                "median": round(q50, 3),
                "ci_95_lower": round(q025, 3),
                "ci_95_upper": round(q975, 3)
            }
        return stats


def compute_trajectory_distance(
    sim_curve: np.ndarray,
    obs_curve: np.ndarray,
    obs_peak_day: int,
    obs_peak_val: float
) -> Tuple[float, int, float, float]:
    """Compute composite distance metric balancing timing, peak amplitude, and trajectory error."""
    min_len = min(len(sim_curve), len(obs_curve))
    sim_c = sim_curve[:min_len]
    obs_c = obs_curve[:min_len]

    sim_peak_day = int(np.argmax(sim_c))
    sim_peak_val = float(np.max(sim_c))
    sim_total = float(np.sum(sim_c))
    obs_total = max(1e-3, float(np.sum(obs_c)))

    day_err = abs(sim_peak_day - obs_peak_day)
    peak_err = abs(sim_peak_val - obs_peak_val) / max(1e-3, obs_peak_val)
    cum_err = abs(sim_total - obs_total) / obs_total
    mse = float(np.mean((sim_c - obs_c) ** 2)) / max(1e-3, obs_peak_val ** 2)

    dist = float(2.0 * day_err + 5.0 * peak_err + 3.0 * cum_err + 10.0 * np.sqrt(mse))
    return dist, sim_peak_day, sim_peak_val, sim_total


def run_smc_abc(
    simulate_fn: Callable[[Dict[str, float]], np.ndarray],
    observed_curve: np.ndarray,
    config: Optional[SMCABCConfig] = None
) -> PosteriorEnsemble:
    """Execute Sequential Monte Carlo ABC across specified generation schedule."""
    if config is None:
        config = SMCABCConfig()

    rng = np.random.default_rng(config.random_seed)
    priors = config.priors
    param_names = list(priors.keys())
    n_particles = config.n_particles

    obs_peak_day = int(np.argmax(observed_curve))
    obs_peak_val = float(np.max(observed_curve))

    print(f"Starting SMC-ABC Calibration ({n_particles} particles, {config.n_generations} generations)...")
    print(f"Target Observations: Peak Day {obs_peak_day}, Peak Val {obs_peak_val:.1f}")

    # Generation 0: Initial rejection sampling from prior
    current_particles: List[Particle] = []
    initial_distances: List[float] = []

    n_samples_g0 = max(n_particles * 2, 400)
    print(f"Generation 1/{config.n_generations}: Sampling {n_samples_g0} candidates from prior...")

    for i in range(n_samples_g0):
        cand_params = {
            p: float(rng.uniform(bounds[0], bounds[1]))
            for p, bounds in priors.items()
        }
        sim_c = simulate_fn(cand_params)
        dist, p_day, p_val, s_tot = compute_trajectory_distance(sim_c, observed_curve, obs_peak_day, obs_peak_val)

        p = Particle(
            params=cand_params,
            weight=1.0,
            distance=dist,
            sim_peak_day=p_day,
            sim_peak_val=p_val,
            sim_total=s_tot
        )
        current_particles.append(p)
        initial_distances.append(dist)

    # Sort and take top particles based on first tolerance quantile
    current_particles.sort(key=lambda p: p.distance)
    current_particles = current_particles[:n_particles]
    # Normalize weights
    for p in current_particles:
        p.weight = 1.0 / n_particles

    tolerance = current_particles[-1].distance
    print(f"Generation 1 Accepted: Tolerance epsilon = {tolerance:.3f}, Median Dist = {np.median([p.distance for p in current_particles]):.3f}")

    # Subsequent Generations
    for gen in range(1, config.n_generations):
        prev_particles = current_particles
        prev_weights = np.array([p.weight for p in prev_particles])
        prev_weights /= np.sum(prev_weights)

        # Compute perturbation covariance matrix
        param_mat = np.array([[p.params[name] for name in param_names] for p in prev_particles])
        cov_mat = np.cov(param_mat, rowvar=False, aweights=prev_weights) * 2.0
        # Ensure positive-definite diagonal regularization
        cov_mat += np.eye(len(param_names)) * 1e-4

        prev_distances = [p.distance for p in prev_particles]
        q_target = config.quantile_schedule[min(gen, len(config.quantile_schedule) - 1)]
        tolerance = float(np.quantile(prev_distances, q_target))

        print(f"\nGeneration {gen + 1}/{config.n_generations}: Target Tolerance epsilon = {tolerance:.3f}")

        new_particles: List[Particle] = []
        attempts = 0
        max_attempts = n_particles * 30

        while len(new_particles) < n_particles and attempts < max_attempts:
            attempts += 1
            # Sample index from previous generation according to weights
            parent_idx = rng.choice(len(prev_particles), p=prev_weights)
            parent_p = prev_particles[parent_idx]
            parent_vec = np.array([parent_p.params[name] for name in param_names])

            # Perturb via multivariate normal
            perturbed_vec = rng.multivariate_normal(parent_vec, cov_mat)
            cand_params = {}
            in_prior = True
            for idx, p_name in enumerate(param_names):
                b_min, b_max = priors[p_name]
                val = float(perturbed_vec[idx])
                if not (b_min <= val <= b_max):
                    in_prior = False
                    break
                cand_params[p_name] = val

            if not in_prior:
                continue

            sim_c = simulate_fn(cand_params)
            dist, p_day, p_val, s_tot = compute_trajectory_distance(sim_c, observed_curve, obs_peak_day, obs_peak_val)

            if dist <= tolerance:
                # Calculate importance weight: prior(theta) / sum(w_j * K(theta | theta_j))
                # Uniform prior is constant over support
                prior_val = 1.0
                kernel_sum = 0.0
                for prev_idx, prev_p in enumerate(prev_particles):
                    p_vec = np.array([prev_p.params[name] for name in param_names])
                    diff = perturbed_vec - p_vec
                    # Multivariate normal pdf
                    try:
                        k_val = float(np.exp(-0.5 * diff.T @ np.linalg.solve(cov_mat, diff)))
                    except np.linalg.LinAlgError:
                        k_val = 1.0
                    kernel_sum += prev_weights[prev_idx] * k_val

                weight = prior_val / max(1e-12, kernel_sum)
                new_particles.append(Particle(
                    params=cand_params,
                    weight=weight,
                    distance=dist,
                    sim_peak_day=p_day,
                    sim_peak_val=p_val,
                    sim_total=s_tot
                ))

        if len(new_particles) < n_particles:
            print(f"  Warning: Reached max attempts ({attempts}). Retained {len(new_particles)} particles.")
        else:
            print(f"  Accepted {n_particles} particles in {attempts} trials (Acceptance rate: {n_particles/attempts*100:.1f}%)")

        current_particles = new_particles if new_particles else prev_particles
        # Normalize weights
        tot_w = sum(p.weight for p in current_particles)
        for p in current_particles:
            p.weight /= max(1e-12, tot_w)

    ensemble = PosteriorEnsemble(
        particles=current_particles,
        generation=config.n_generations,
        tolerance=tolerance,
        parameter_names=param_names
    )
    return ensemble


def run_twin_experiment(
    true_params: Optional[Dict[str, float]] = None,
    n_particles: int = 100,
    random_seed: int = 42
) -> Dict[str, Any]:
    """Execute a rigorous Twin Experiment verifying parameter identification and recovery."""
    if true_params is None:
        true_params = {"r0": 2.75, "i0": 32.0, "kappa": 0.60}

    print("=== Running Stage A3 Twin Experiment ===")
    print(f"True Synthetic Parameters: {true_params}")

    t = np.arange(92)
    def synthetic_forward(params: Dict[str, float]) -> np.ndarray:
        r0 = params["r0"]
        i0 = params["i0"]
        kappa = params["kappa"]
        # Analytical transmission model with statutory intervention reduction
        r = np.where(t < 23, r0, r0 * (1.0 - kappa * 0.75))
        growth = (r - 1.0) / 4.5
        cum_g = np.cumsum(growth)
        infections = i0 * np.exp(cum_g)
        kernel = (t ** 2) * np.exp(-t / 5.0)
        kernel /= np.sum(kernel)
        curve = np.convolve(infections, kernel)[:92]
        return curve

    # Generate ground truth observation with Poisson observation noise
    rng = np.random.default_rng(random_seed)
    ground_truth = synthetic_forward(true_params)
    noisy_observation = rng.poisson(np.maximum(0, ground_truth)).astype(np.float64)

    cfg = SMCABCConfig(
        n_particles=n_particles,
        n_generations=3,
        quantile_schedule=(0.50, 0.25, 0.10),
        priors={
            "r0": (2.0, 3.6),
            "i0": (15.0, 50.0),
            "kappa": (0.35, 0.85)
        },
        random_seed=random_seed
    )

    ensemble = run_smc_abc(synthetic_forward, noisy_observation, config=cfg)
    summary = ensemble.summary()

    recovery_success = True
    recovery_report = {}
    for p_name, true_val in true_params.items():
        est = summary[p_name]["mean"]
        ci_l = summary[p_name]["ci_95_lower"]
        ci_u = summary[p_name]["ci_95_upper"]
        rel_err = abs(est - true_val) / true_val
        covered = (ci_l <= true_val <= ci_u)
        # R0 and kappa have sharp likelihood surfaces; I0 has exponential co-linearity with R0
        max_rel_err = 0.25 if p_name == "i0" else 0.15
        passed = (covered and rel_err <= max_rel_err)
        if not passed:
            recovery_success = False
        recovery_report[p_name] = {
            "true": true_val,
            "estimate": est,
            "ci_95": (ci_l, ci_u),
            "rel_error_pct": round(rel_err * 100, 2),
            "covered_95_ci": covered,
            "status": "PASS" if passed else "FAIL"
        }
        print(f"  [{'PASS' if passed else 'FAIL'}] Parameter '{p_name}': True={true_val:.2f}, Est={est:.2f} [95% CI: {ci_l:.2f}, {ci_u:.2f}], Rel Error={rel_err*100:.1f}%")

    return {
        "success": recovery_success,
        "true_params": true_params,
        "recovery_report": recovery_report,
        "ensemble": ensemble
    }
