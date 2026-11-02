"""Generality tests for Phase 17: Renamed states, dynamic age bands, and diseases without symptomatic role."""

import numpy as np
import pandas as pd
import pytest

from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack, DiseaseState, StateTransition
from episwarm.packs.scenario import ScenarioPack, SeedingConfig
from episwarm.engine.sim import run_simulation
from episwarm.analysis.equity import evaluate_equity
from episwarm.population.age_bands import resolve_age_bands_from_contacts, assign_age_bands


def test_generality_renamed_states():
    """Verify simulation runs with non-standard compartment names mapped purely by semantic roles."""
    # Disease graph with completely renamed states
    dp_dict = {
        "name": "renamed_state_pathogen",
        "version": "1.0.0",
        "provenance": {"status": "synthetic", "source": "test_generality"},
        "states": [
            {"name": "Naïve_Cohort", "role": "susceptible", "infectious": False},
            {"name": "Incubation_Phase", "role": "exposed", "infectious": False},
            {"name": "Clinical_Transmitter", "role": "symptomatic", "infectious": True, "relative_infectiousness": 1.0},
            {"name": "Convalescent_Immune", "role": "recovered", "infectious": False, "absorbing": True}
        ],
        "transitions": [
            {"from_state": "Incubation_Phase", "to_state": "Clinical_Transmitter", "base_probability": 1.0, "duration": {"type": "constant", "mean_days": 2.0}},
            {"from_state": "Clinical_Transmitter", "to_state": "Convalescent_Immune", "base_probability": 1.0, "duration": {"type": "constant", "mean_days": 5.0}}
        ],
        "transmission": {"mode": "person_to_person", "r0": 2.5, "overdispersion_k": 1000.0}
    }
    dp = DiseasePack(**dp_dict)

    pop = build_synthetic_population("regions/example_synthetic", scale_agents=3000, random_seed=42)

    sc_dict = {
        "name": "renamed_states_test",
        "horizon_days": 40,
        "scale_agents": 3000,
        "random_seed": 42,
        "behavior_mode": "none",
        "seeding": {
            "initial_cases_per_area": 30,
            "seeded_state": "Clinical_Transmitter"
        },
        "interventions": [],
        "provenance": {"status": "synthetic", "source": "test"}
    }
    sc = ScenarioPack(**sc_dict)

    res = run_simulation(pop, dp, sc)

    # Epidemic must successfully propagate through renamed states
    assert res.attack_rate > 0.40, f"Outbreak did not take off with renamed states: attack_rate={res.attack_rate:.3f}"
    assert "Clinical_Transmitter" in res.state_names
    assert "Convalescent_Immune" in res.state_names
    # Verify no legacy S or E strings needed
    assert "S" not in res.state_names


def test_generality_10_year_age_bands():
    """Verify simulation and equity analysis with non-standard 10-year age bands (8 bands)."""
    eight_bands = ["0-9", "10-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70+"]

    # Synthesize contact matrix for 8 age bands
    contact_rows = []
    for bi in eight_bands:
        for bj in eight_bands:
            rate = 5.0 if bi == bj else 0.8
            contact_rows.append({
                "layer": "all",
                "age_band_i": bi,
                "age_band_j": bj,
                "contacts_per_day": rate,
                "source": "syn",
                "status": "synthetic"
            })
    contacts_df = pd.DataFrame(contact_rows)

    resolved_bands = resolve_age_bands_from_contacts(contacts_df)
    assert len(resolved_bands) == 8
    assert resolved_bands[0] == "0-9"
    assert resolved_bands[-1] == "70+"

    pop = build_synthetic_population("regions/example_synthetic", scale_agents=3000, random_seed=42)
    assigned = assign_age_bands(pop.age, resolved_bands)
    assert np.all((assigned >= 0) & (assigned < 8))

    dp_dict = {
        "name": "multiband_pathogen",
        "version": "1.0.0",
        "provenance": {"status": "synthetic", "source": "test_generality"},
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

    sc_dict = {
        "name": "multiband_test",
        "horizon_days": 35,
        "scale_agents": 3000,
        "random_seed": 42,
        "behavior_mode": "none",
        "seeding": {"initial_cases_per_area": 20, "seeded_state": "I"},
        "interventions": [],
        "provenance": {"status": "synthetic", "source": "test"}
    }
    sc = ScenarioPack(**sc_dict)

    res = run_simulation(pop, dp, sc, contacts_df=contacts_df)
    assert res.attack_rate > 0.30

    # Equity evaluation across all 8 bands
    eq = evaluate_equity(pop, res, age_bands=resolved_bands)
    assert len(eq.age_attack_rates) == 8
    assert "0-9" in eq.age_attack_rates
    assert "70+" in eq.age_attack_rates


def test_generality_disease_without_symptomatic_role():
    """Verify simulation handles an asymptomatic pathogen with no symptomatic role declared."""
    dp_dict = {
        "name": "silent_pathogen",
        "version": "1.0.0",
        "provenance": {"status": "synthetic", "source": "test_generality"},
        "states": [
            {"name": "Susceptible", "role": "susceptible", "infectious": False},
            {"name": "Infected_Silent", "role": "infectious", "infectious": True, "relative_infectiousness": 1.0},
            {"name": "Clearance", "role": "recovered", "infectious": False, "absorbing": True}
        ],
        "transitions": [
            {"from_state": "Infected_Silent", "to_state": "Clearance", "base_probability": 1.0, "duration": {"type": "constant", "mean_days": 4.0}}
        ],
        "transmission": {"mode": "person_to_person", "r0": 2.2, "overdispersion_k": 100.0}
    }
    dp = DiseasePack(**dp_dict)

    pop = build_synthetic_population("regions/example_synthetic", scale_agents=3000, random_seed=42)

    sc_dict = {
        "name": "silent_test",
        "horizon_days": 30,
        "scale_agents": 3000,
        "random_seed": 42,
        "behavior_mode": "rule",  # Behavior enabled: should not crash on missing symptomatic state
        "seeding": {"initial_cases_per_area": 25, "seeded_state": "Infected_Silent"},
        "interventions": [],
        "provenance": {"status": "synthetic", "source": "test"}
    }
    sc = ScenarioPack(**sc_dict)

    # Should run to completion without error
    res = run_simulation(pop, dp, sc)
    assert res.attack_rate > 0.20
    assert res.total_infections > 0
