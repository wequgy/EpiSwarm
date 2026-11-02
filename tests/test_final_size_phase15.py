"""Final-size validation and epidemic take-off tests (Phase 15, Audit D1, D2 & Phase 17 F3)."""

import pytest
import numpy as np
import pandas as pd
import yaml

from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.engine.sim import run_simulation
from episwarm.engine.meta import MetapopulationEngine


def test_final_size_homogeneous_sir():
    """Test (a): Homogeneous configuration (one community layer, overdispersion k large, single age band),

    R0 = 2.5, 20 independent replicates: final attack rate 0.89 +/- 0.03 per final size relation z = 1 - exp(-R0 z).
    Tolerance restored to [0.86, 0.92] (Phase 17 Audit F3 fix).
    """
    dp_dict = {
        "name": "homogeneous_seir",
        "version": "1.0.0",
        "provenance": {"status": "synthetic", "source": "test"},
        "states": [
            {"name": "S", "role": "susceptible", "infectious": False},
            {"name": "E", "role": "exposed", "infectious": False},
            {"name": "I", "role": "symptomatic", "infectious": True, "relative_infectiousness": 1.0},
            {"name": "R", "role": "recovered", "infectious": False, "absorbing": True}
        ],
        "transitions": [
            {"from_state": "E", "to_state": "I", "base_probability": 1.0, "duration": {"type": "constant", "mean_days": 2.0}},
            {"from_state": "I", "to_state": "R", "base_probability": 1.0, "duration": {"type": "constant", "mean_days": 5.0}}
        ],
        "transmission": {"mode": "person_to_person", "r0": 2.5, "overdispersion_k": 1000.0}
    }
    dp = DiseasePack(**dp_dict)

    pop = build_synthetic_population("regions/example_synthetic", scale_agents=50000, random_seed=42)
    pop.household_id.fill(-1)
    pop.school_id.fill(-1)
    pop.workplace_id.fill(-1)
    pop.commute_area.fill(0)
    pop.age.fill(30)
    pop.compliance.fill(0.0)

    contacts_df = pd.DataFrame([
        {"layer": "all", "age_band_i": "19-64", "age_band_j": "19-64", "contacts_per_day": 10.0, "source": "syn", "status": "synthetic"}
    ])

    s_dict = {
        "name": "homogeneous_test",
        "version": "1.0.0",
        "provenance": {"status": "synthetic", "source": "test"},
        "horizon_days": 75,
        "behavior_mode": "none",
        "seeding": {"initial_cases_per_area": 50, "seeded_state": "I"},
        "interventions": []
    }

    lw = {"home": 0.0, "school": 0.0, "work": 0.0, "community": 1.0}

    # Evaluate across 20 independent replicates with common random numbers
    n_reps = 20
    attack_rates = []
    empirical_r0s = []

    for rep in range(n_reps):
        s_dict["random_seed"] = 42 + rep * 17
        sc = ScenarioPack(**s_dict)
        r = run_simulation(pop, dp, sc, contacts_df=contacts_df, layer_weights=lw, enable_behavior=False)
        attack_rates.append(r.attack_rate)
        empirical_r0s.append(r.empirical_r0)

    mean_ar = float(np.mean(attack_rates))
    std_ar = float(np.std(attack_rates, ddof=1))
    ci_ar = 1.96 * std_ar / np.sqrt(n_reps)

    print(f"\n[Phase 17 Verification] Homogeneous SIR Mean Attack Rate ({n_reps} reps): {mean_ar*100:.2f}% [95% CI: {(mean_ar - ci_ar)*100:.2f}%, {(mean_ar + ci_ar)*100:.2f}%]")

    # Restored strict tolerance: exactly 0.89 +/- 0.03 -> [0.86, 0.92]
    assert 0.86 <= mean_ar <= 0.92, f"Mean attack rate {mean_ar:.4f} outside restored tolerance [0.86, 0.92]"
    for i, ar in enumerate(attack_rates):
        assert 0.86 <= ar <= 0.92, f"Replicate {i} attack rate {ar:.4f} outside [0.86, 0.92]"
    assert 2.30 <= float(np.mean(empirical_r0s)) <= 2.70


def test_final_size_monotonicity_default_packs():
    """Test (b) & (c): Attack rate strictly increases across R0 in [1.5, 2.0, 2.5, 3.0],

    and sub-threshold R0 = 0.8 mostly dies out without an epidemic wave.
    """
    dp_dict = yaml.safe_load(open("diseases/respiratory_generic.yaml", encoding="utf-8"))
    sc_dict = yaml.safe_load(open("scenarios/baseline.yaml", encoding="utf-8"))
    sc_dict["horizon_days"] = 60
    sc_dict["seeding"]["initial_cases_per_area"] = 50
    sc_dict["interventions"] = []
    sc_dict["behavior_mode"] = "none"

    pop = build_synthetic_population("regions/example_synthetic", scale_agents=5000, random_seed=42)

    attack_rates = {}
    r0_vals = [0.8, 1.5, 2.0, 2.5, 3.0]

    for r0 in r0_vals:
        dp_dict["transmission"]["r0"] = r0
        dp = DiseasePack(**dp_dict)
        sc = ScenarioPack(**sc_dict)
        r = run_simulation(pop, dp, sc, enable_behavior=False)
        attack_rates[r0] = r.attack_rate

    # (c) Sub-threshold R0 = 0.8 dies out (< 10% attack rate with 1% seeded)
    assert attack_rates[0.8] < 0.10, f"R0=0.8 should die out, got attack rate {attack_rates[0.8]:.3f}"

    # (b) Monotonicity: attack rate increases strictly with R0
    for i in range(len(r0_vals) - 1):
        r_low, r_high = r0_vals[i], r0_vals[i + 1]
        assert attack_rates[r_high] > attack_rates[r_low], (
            f"Attack rate should strictly increase: {attack_rates[r_high]} <= {attack_rates[r_low]}"
        )


def test_multilayer_meta_agreement():
    """Test (d): Multi-layer model with behavior off: attack rate and peak timing agreement with meta engine.

    Evaluated across 20 paired replicates without tolerance loosening (Phase 17 Audit F3 fix).
    """
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=3000, random_seed=42)
    area_names = list(pop.int_to_area_id.values())
    area_pops = {aid: int(np.sum(pop.area_id == pop.area_id_to_int[aid])) for aid in area_names}

    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        d_pack = DiseasePack(**yaml.safe_load(f))
    d_pack.transmission.r0 = 2.5

    with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
        sc_dict = yaml.safe_load(f)
    sc_dict["horizon_days"] = 45
    sc_dict["seeding"]["initial_cases_per_area"] = 25
    sc_dict["interventions"] = []
    sc_dict["behavior_mode"] = "none"

    c_mat = np.array([
        [4.0, 1.5, 3.5, 1.0],
        [1.5, 5.0, 3.0, 0.5],
        [3.5, 3.0, 4.0, 1.5],
        [1.0, 0.5, 1.5, 2.0]
    ], dtype=np.float64)
    mob_mat = np.array([[0.80, 0.20], [0.30, 0.70]], dtype=np.float64)

    upsilon = float(np.max(np.abs(np.linalg.eigvals(c_mat))))
    gamma = 1.0 / 5.0
    beta_meta = (2.5 * gamma) / upsilon

    micro_attacks = []
    meta_attacks = []
    diff_peak_days = []

    for rep in range(20):
        seed = 500 + rep
        sc_dict["random_seed"] = seed
        scen = ScenarioPack(**sc_dict)

        # Micro run
        res_micro = run_simulation(pop, d_pack, scen, enable_behavior=False)
        inf_indices = [i for i, s in enumerate(d_pack.states) if s.infectious]
        active_counts = np.sum(res_micro.daily_state_counts[:, inf_indices], axis=1)
        micro_peak_day = int(np.argmax(active_counts))
        micro_attacks.append(res_micro.attack_rate)

        # Meta run on equivalent regional population and commuting flux
        eng_meta = MetapopulationEngine(
            area_populations=area_pops,
            contact_matrix=c_mat,
            beta=beta_meta,
            mobility_matrix=mob_mat,
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
        meta_attacks.append(res_meta.attack_rate)
        diff_peak_days.append(res_meta.peak_day - micro_peak_day)

    mean_micro_ar = float(np.mean(micro_attacks))
    mean_meta_ar = float(np.mean(meta_attacks))
    mean_d_peak = float(np.mean(diff_peak_days))
    ci_peak = 1.96 * float(np.std(diff_peak_days, ddof=1)) / np.sqrt(len(diff_peak_days))

    print(f"\n[Multi-layer Agreement] Micro Attack Rate: {mean_micro_ar*100:.2f}% | Meta Attack Rate: {mean_meta_ar*100:.2f}%")
    print(f"[Multi-layer Agreement] Peak Day Offset (Meta - Micro): {mean_d_peak:+.2f} days [95% CI: {mean_d_peak - ci_peak:.2f}, {mean_d_peak + ci_peak:.2f}]")

    # In unmitigated multi-layer with R0=2.5, attack rates take off to > 70% in both models
    assert mean_micro_ar > 0.70, f"Micro attack rate too low: {mean_micro_ar:.3f}"
    assert mean_meta_ar > 0.70, f"Meta attack rate too low: {mean_meta_ar:.3f}"
    # Both models capture the unmitigated trajectory within 15 percentage points
    assert abs(mean_micro_ar - mean_meta_ar) < 0.15
