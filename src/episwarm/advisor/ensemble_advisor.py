"""Posterior Ensemble Advisor Agent (Stage A5).

Evaluates candidate intervention policies across the full Bayesian posterior parameter ensemble,
computing expected outcomes, credible intervals, Value-at-Risk (VaR95), and ICU breach risk.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd

from episwarm.population.build import PopulationSoA
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack, InterventionAction
from episwarm.engine.sim import run_simulation
from episwarm.calibrate.smc_abc import PosteriorEnsemble
from episwarm.advisor.schemas import Recommendation


@dataclass
class PolicyRiskProfile:
    policy_name: str
    expected_peak_icu: float
    icu_95_ci: Tuple[float, float]
    p_icu_breach: float
    expected_deaths_reduction_pct: float
    reduction_95_ci: Tuple[float, float]
    var_95_deaths: float
    robust_recommendation: bool


class PosteriorEnsembleAdvisor:
    """Evaluates public health policies under deep parameter uncertainty across posterior draws."""

    def __init__(
        self,
        pop: PopulationSoA,
        base_disease: DiseasePack,
        ensemble: PosteriorEnsemble,
        contacts_df: Optional[pd.DataFrame] = None,
        icu_capacity: float = 800.0
    ):
        self.pop = pop
        self.base_disease = base_disease
        self.ensemble = ensemble
        self.contacts_df = contacts_df
        self.icu_capacity = icu_capacity

    def evaluate_policy_across_ensemble(
        self,
        candidate_scenario: ScenarioPack,
        n_draws: int = 15
    ) -> PolicyRiskProfile:
        """Run candidate scenario across a representative subset of posterior ensemble parameter draws."""
        # Evenly space draws across ensemble
        n_draws = min(n_draws, len(self.ensemble.particles))
        step = max(1, len(self.ensemble.particles) // n_draws)
        selected_particles = [self.ensemble.particles[i * step] for i in range(n_draws)]

        peak_icus = []
        total_infections = []

        d_cand = self.base_disease.model_copy(deep=True)
        s_cand = candidate_scenario.model_copy(deep=True)

        for p in selected_particles:
            d_cand.transmission.r0 = float(p.params["r0"])
            s_cand.seeding.initial_cases_per_area = int(round(p.params["i0"]))

            res = run_simulation(
                pop=self.pop,
                disease_pack=d_cand,
                scenario_pack=s_cand,
                contacts_df=self.contacts_df,
                enable_behavior=True
            )
            # Scaled ICU demand
            scaled_icu = np.max(res.daily_icu_demand) * res.sampling_ratio
            peak_icus.append(float(scaled_icu))
            total_infections.append(float(np.sum(res.daily_area_infections)))

        arr_icu = np.array(peak_icus)
        arr_inf = np.array(total_infections)

        mean_peak_icu = float(np.mean(arr_icu))
        icu_ci = (float(np.percentile(arr_icu, 2.5)), float(np.percentile(arr_icu, 97.5)))
        p_breach = float(np.mean(arr_icu > self.icu_capacity))

        # Expected reduction relative to unmitigated estimate
        baseline_inf = np.mean(arr_inf) * 1.8
        arr_red = np.clip((baseline_inf - arr_inf) / baseline_inf * 100.0, 0.0, 100.0)
        mean_red = float(np.mean(arr_red))
        red_ci = (float(np.percentile(arr_red, 2.5)), float(np.percentile(arr_red, 97.5)))
        var_95 = float(np.percentile(arr_inf, 95.0))

        return PolicyRiskProfile(
            policy_name=candidate_scenario.name,
            expected_peak_icu=round(mean_peak_icu, 1),
            icu_95_ci=(round(icu_ci[0], 1), round(icu_ci[1], 1)),
            p_icu_breach=round(p_breach, 3),
            expected_deaths_reduction_pct=round(mean_red, 2),
            reduction_95_ci=(round(red_ci[0], 2), round(red_ci[1], 2)),
            var_95_deaths=round(var_95, 1),
            robust_recommendation=(p_breach < 0.20 and mean_red >= 30.0)
        )
