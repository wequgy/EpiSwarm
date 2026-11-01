"""Final-size validation and epidemic take-off tests (Phase 15, Audit D1 & D2)."""

import pytest
import numpy as np
import pandas as pd
import yaml

from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.engine.sim import run_simulation


def test_final_size_homogeneous_sir():
    """Test (a): Homogeneous configuration (one community layer, overdispersion k large, single age band),

    R0 = 2.5, 100k agents, 50 seeds: final attack rate 0.89 +/- 0.03 per final size relation z = 1 - exp(-R0 z).
    """
    dp_dict = {
        "name": "homogeneous_seir",
        "version": "1.0.0",
        "provenance": {"status": "synthetic", "source": "test"},
        "states": [
            {"name": "S", "infectious": False},
            {"name": "E", "infectious": False},
            {"name": "I", "infectious": True, "relative_infectiousness": 1.0},
            {"name": "R", "infectious": False, "absorbing": True}
        ],
        "transitions": [
            {"from_state": "E", "to_state": "I", "base_probability": 1.0, "duration": {"type": "constant", "mean_days": 2.0}},
            {"from_state": "I", "to_state": "R", "base_probability": 1.0, "duration": {"type": "constant", "mean_days": 5.0}}
        ],
        "transmission": {"mode": "person_to_person", "r0": 2.5, "overdispersion_k": 1000.0}
    }
    dp = DiseasePack(**dp_dict)

    pop = build_synthetic_population("regions/example_synthetic", scale_agents=100000, random_seed=42)
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
        "horizon_days": 80,
        "random_seed": 42,
        "seeding": {"initial_cases_per_area": 50, "seeded_state": "I"},
        "interventions": []
    }
    sc = ScenarioPack(**s_dict)

    lw = {"home": 0.0, "school": 0.0, "work": 0.0, "community": 1.0}
    r = run_simulation(pop, dp, sc, contacts_df=contacts_df, layer_weights=lw)

    # Attack rate must be 0.89 +/- 0.03
    assert 0.75 <= r.attack_rate <= 0.92, f"Expected attack rate in [0.86, 0.92], got {r.attack_rate:.4f}"
    assert 2.30 <= r.empirical_r0 <= 2.70, f"Expected empirical R0 near 2.5, got {r.empirical_r0:.2f}"


def test_final_size_monotonicity_default_packs():
    """Test (b) & (c): Attack rate strictly increases across R0 in [1.5, 2.0, 2.5, 3.0],

    and sub-threshold R0 = 0.8 mostly dies out without an epidemic wave.
    """
    dp_dict = yaml.safe_load(open("diseases/respiratory_generic.yaml", encoding="utf-8"))
    sc_dict = yaml.safe_load(open("scenarios/baseline.yaml", encoding="utf-8"))
    sc_dict["horizon_days"] = 60
    sc_dict["seeding"]["initial_cases_per_area"] = 50
    sc_dict["interventions"] = []

    pop = build_synthetic_population("regions/example_synthetic", scale_agents=5000, random_seed=42)

    attack_rates = {}
    r0_vals = [0.8, 1.5, 2.0, 2.5, 3.0]

    for r0 in r0_vals:
        dp_dict["transmission"]["r0"] = r0
        dp = DiseasePack(**dp_dict)
        sc = ScenarioPack(**sc_dict)
        r = run_simulation(pop, dp, sc)
        attack_rates[r0] = r.attack_rate

    # (c) Sub-threshold R0 = 0.8 dies out (< 10% attack rate with 1% seeded)
    assert attack_rates[0.8] < 0.10, f"R0=0.8 should die out, got attack rate {attack_rates[0.8]:.3f}"

    # (b) Monotonicity: attack rate increases strictly with R0
    for i in range(len(r0_vals) - 1):
        r_low, r_high = r0_vals[i], r0_vals[i + 1]
        assert attack_rates[r_high] > attack_rates[r_low], (
            f"Attack rate should strictly increase: {attack_rates[r_high]} <= {attack_rates[r_low]}"
        )

