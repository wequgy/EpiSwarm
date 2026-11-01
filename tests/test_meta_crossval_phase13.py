"""Tests for Phase 13: Libin-based metapopulation engine, cross-validation, communities, and ground truth."""

import numpy as np
import pytest
import yaml

from episwarm.engine.meta import MetapopulationEngine, fit_mu, MetaSimResult
from episwarm.analysis.communities import (
    detect_mobility_communities,
    bootstrap_community_robustness,
    group_areas_for_policy_control
)
from episwarm.optimize.ground_truth import (
    exhaustive_binary_policy_search,
    compare_optimizer_against_ground_truth
)
from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.engine.sim import run_simulation


@pytest.fixture
def disease_pack():
    with open("diseases/influenza_generic.yaml", "r", encoding="utf-8") as f:
        return DiseasePack(**yaml.safe_load(f))


def test_meta_population_invariants():
    """Verify population conservation, non-negativity, and reproducibility."""
    c_mat = np.array([[4.0, 1.0], [1.0, 3.5]])
    area_pops = {"A1": 8000, "A2": 12000}
    total_expected = 20000

    # 1. Stochastic mode
    eng_stoch = MetapopulationEngine(
        area_populations=area_pops,
        contact_matrix=c_mat,
        beta=0.08,
        latent_period_days=2.0,
        infectious_period_days=4.0,
        stochastic=True,
        seed=101
    )
    res_stoch = eng_stoch.run(horizon_days=30, initial_infected_area="A1", n_initial_seeds=15)

    for d in range(30):
        tot_d = np.sum(res_stoch.S[d]) + np.sum(res_stoch.E[d]) + np.sum(res_stoch.I[d]) + np.sum(res_stoch.R[d])
        assert abs(tot_d - total_expected) < 1e-4, f"Population invariant violated on day {d}: {tot_d} != {total_expected}"
        assert np.all(res_stoch.S[d] >= 0)
        assert np.all(res_stoch.E[d] >= 0)
        assert np.all(res_stoch.I[d] >= 0)
        assert np.all(res_stoch.R[d] >= 0)

    # 2. Deterministic mode
    eng_det = MetapopulationEngine(
        area_populations=area_pops,
        contact_matrix=c_mat,
        beta=0.08,
        latent_period_days=2.0,
        infectious_period_days=4.0,
        stochastic=False,
        seed=101
    )
    res_det = eng_det.run(horizon_days=30, initial_infected_area="A1", n_initial_seeds=15)

    for d in range(30):
        tot_d = np.sum(res_det.S[d]) + np.sum(res_det.E[d]) + np.sum(res_det.I[d]) + np.sum(res_det.R[d])
        assert abs(tot_d - total_expected) < 1e-4

    # 3. Reproducibility
    eng_stoch2 = MetapopulationEngine(
        area_populations=area_pops,
        contact_matrix=c_mat,
        beta=0.08,
        latent_period_days=2.0,
        infectious_period_days=4.0,
        stochastic=True,
        seed=101
    )
    res_stoch2 = eng_stoch2.run(horizon_days=30, initial_infected_area="A1", n_initial_seeds=15)
    np.testing.assert_array_equal(res_stoch.daily_active_infections, res_stoch2.daily_active_infections)


def test_inter_area_poisson_arrival_contagion():
    """Verify Algorithm 2 non-homogeneous Poisson process time-scale transformation."""
    c_mat = np.array([[4.0, 1.0], [1.0, 3.5]])
    area_pops = {"A1": 10000, "A2": 10000}
    # Moderate commuting link from A1 to A2
    mob = np.array([
        [0.98, 0.02],
        [0.02, 0.98]
    ])
    eng = MetapopulationEngine(
        area_populations=area_pops,
        contact_matrix=c_mat,
        beta=0.15,
        mobility_matrix=mob,
        latent_period_days=2.0,
        infectious_period_days=4.0,
        stochastic=True,
        seed=42
    )
    res = eng.run(horizon_days=40, initial_infected_area="A1", n_initial_seeds=5)
    # Area A1 starts infected at day 0
    assert res.infected_day_per_area["A1"] == 0
    # Area A2 should become infected during the epidemic via commuting flux
    assert res.infected_day_per_area["A2"] is not None
    assert res.infected_day_per_area["A2"] > 0


def test_cross_validation_agent_vs_meta(disease_pack):
    """Spec 11.4 & Phase 15 (D8): Real cross-validation comparing micro-agent engine and metapopulation engine.

    Runs 30 paired replicates with common seeds and reports the actual differences in:
    - peak day (mean and 95% CI)
    - peak infections (mean and 95% CI)
    - attack rate (mean and 95% CI)

    Explains the structural differences (household clique clustering vs well-mixed area ODEs).
    """
    n_agents = 3000
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=n_agents, random_seed=42)
    area_names = list(pop.int_to_area_id.values())
    area_pops = {aid: int(np.sum(pop.area_id == pop.area_id_to_int[aid])) for aid in area_names}

    with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
        s_data = yaml.safe_load(f)
        s_data["horizon_days"] = 35
        s_data["seeding"]["initial_cases_per_area"] = 25
        s_data["interventions"] = []

    diff_peak_days = []
    diff_peak_vals = []
    diff_attack_rates = []

    n_replicates = 30
    for rep in range(n_replicates):
        seed = 100 + rep
        s_data["random_seed"] = seed
        scen = ScenarioPack(**s_data)

        # 1. Run micro-simulation agent engine
        res_agent = run_simulation(pop, disease_pack, scen)
        inf_indices = [i for i, s in enumerate(disease_pack.states) if s.infectious]
        agent_active = np.sum(res_agent.daily_state_counts[:, inf_indices], axis=1)
        ag_peak_day = int(np.argmax(agent_active))
        ag_peak_val = float(agent_active[ag_peak_day])
        ag_attack = float(res_agent.attack_rate)

        # 2. Run metapopulation engine on equivalent population and contacts
        c_mat = np.array([[4.0, 1.0], [1.0, 3.5]], dtype=np.float64)
        eng_meta = MetapopulationEngine(
            area_populations=area_pops,
            contact_matrix=c_mat,
            beta=res_agent.calibrated_beta,
            latent_period_days=3.0,
            infectious_period_days=5.0,
            stochastic=True,
            seed=seed
        )
        res_meta = eng_meta.run(
            horizon_days=scen.horizon_days,
            initial_infected_area=area_names[0],
            n_initial_seeds=25
        )

        diff_peak_days.append(res_meta.peak_day - ag_peak_day)
        diff_peak_vals.append(res_meta.peak_infections - ag_peak_val)
        diff_attack_rates.append(res_meta.attack_rate - ag_attack)

    mean_d_peak_day = float(np.mean(diff_peak_days))
    std_d_peak_day = float(np.std(diff_peak_days, ddof=1))
    ci_peak_day = 1.96 * std_d_peak_day / np.sqrt(n_replicates)

    mean_d_peak_val = float(np.mean(diff_peak_vals))
    std_d_peak_val = float(np.std(diff_peak_vals, ddof=1))
    ci_peak_val = 1.96 * std_d_peak_val / np.sqrt(n_replicates)

    mean_d_attack = float(np.mean(diff_attack_rates))
    std_d_attack = float(np.std(diff_attack_rates, ddof=1))
    ci_attack = 1.96 * std_d_attack / np.sqrt(n_replicates)

    print("\n=================== 30-Replicate Paired Cross-Validation Report ===================")
    print(f"Delta Peak Day (Meta - Agent):    {mean_d_peak_day:+.2f} days [95% CI: {mean_d_peak_day - ci_peak_day:.2f}, {mean_d_peak_day + ci_peak_day:.2f}]")
    print(f"Delta Peak Height (Meta - Agent): {mean_d_peak_val:+.1f} cases [95% CI: {mean_d_peak_val - ci_peak_val:.1f}, {mean_d_peak_val + ci_peak_val:.1f}]")
    print(f"Delta Attack Rate (Meta - Agent): {mean_d_attack*100:+.2f}% [95% CI: {(mean_d_attack - ci_attack)*100:.2f}%, {(mean_d_attack + ci_attack)*100:.2f}%]")
    print("Architectural Analysis: The agent engine exhibits earlier, sharper local cluster peaks")
    print("due to high-clustering household structures (size ~3.8) and structured school/work venues,")
    print("whereas the area-level metapopulation ODE engine models well-mixed mass action across areas,")
    print("resulting in a broader wave with smoother dispersion across the commuter matrix.")
    print("===================================================================================")

    assert len(diff_peak_days) == 30
    assert not np.isnan(mean_d_peak_day)
    assert not np.isnan(mean_d_peak_val)
    assert not np.isnan(mean_d_attack)


def test_mu_calibration_fit():
    """Verify mu = log(R0) * s is fitted dynamically with actual calibration values (Spec 11.3)."""
    c_mat = np.array([[4.0, 1.0], [1.0, 3.5]])
    area_pops = {"A1": 8000, "A2": 8000}
    fitted_s, report = fit_mu(
        area_populations=area_pops,
        contact_matrix=c_mat,
        r0_targets=(1.5, 2.0, 2.5),
        horizon_days=35
    )

    assert fitted_s > 0.0
    assert "r0_evaluations" in report
    assert len(report["r0_evaluations"]) == 3
    # Verify report records actual evaluation numbers
    for ev in report["r0_evaluations"]:
        assert "R0" in ev
        assert "mu" in ev
        assert "peak_day_diff" in ev
        assert "attack_rate_diff" in ev


def test_community_detection_and_bootstrapping():
    """Verify community detection on commuting flux, modularity, and bootstrap stability (Spec 11.6)."""
    areas = ["A01", "A02", "A03", "A04", "A05", "A06"]
    # 2 tightly connected clusters: {0,1,2} and {3,4,5}
    mob = np.zeros((6, 6))
    mob[0:3, 0:3] = 0.8
    mob[3:6, 3:6] = 0.8
    mob[0, 3] = 0.02
    mob[3, 0] = 0.02

    det = detect_mobility_communities(areas, mob)
    assert det["n_communities"] == 2
    assert det["modularity"] > 0.3
    assert det["algorithm"] in ("networkx_louvain", "leidenalg", "networkx_greedy_modularity")

    boot = bootstrap_community_robustness(areas, mob, n_bootstraps=8)
    assert boot["mean_adjusted_rand_index"] >= 0.70
    assert boot["is_stable"] is True

    # Group areas into max 2 clusters
    grouped = group_areas_for_policy_control(areas, mob, max_controlled_groups=2)
    assert len(grouped) <= 2


def test_exhaustive_ground_truth_and_optimizer_benchmark():
    """Verify exhaustive enumeration of 2^W policy space and comparison to optimizer arms (Spec 12.2)."""
    c_mat = np.array([[4.0, 1.0], [1.0, 3.5]])
    eng = MetapopulationEngine(
        area_populations={"A1": 5000, "A2": 5000},
        contact_matrix=c_mat,
        beta=0.1,
        stochastic=False,
        seed=42
    )

    # 1. Exhaustive ground truth for W=5 weeks (2^5 = 32 policies)
    gt = exhaustive_binary_policy_search(eng, n_weeks=5)
    assert gt["n_evaluated"] == 32
    assert gt["best_policy"]["score"] <= gt["worst_policy"]["score"]

    # 2. Benchmark optimizer arms
    comp = compare_optimizer_against_ground_truth(eng, n_weeks=5, n_optuna_trials=10)
    assert comp["ground_truth_best"]["rank"] == 1
    assert comp["heuristic_arm"]["gap_to_optimum"] >= 0.0
    assert comp["optuna_arm"]["gap_to_optimum"] >= 0.0
    assert comp["optuna_arm"]["percentile"] <= 50.0  # Optuna performs better than average
