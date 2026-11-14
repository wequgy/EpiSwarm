"""Tests for Stage A2: Contact network, calendar schedules, expectation-based R0, and generality."""

import pytest
import numpy as np
import pandas as pd
import yaml

from episwarm.population.build import build_synthetic_population
from episwarm.population.network import (
    ContactNetwork,
    CalendarSchedule,
    build_persistent_contact_network,
    compute_network_edge_lambda,
    LAYER_HOME,
    LAYER_SCHOOL,
    LAYER_WORK,
    LAYER_COMMUNITY
)
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack, SeedingConfig
from episwarm.engine.sim import (
    run_simulation,
    calibrate_beta_expectation
)
from episwarm.engine.state_graph import CompiledStateGraph


def test_contact_network_structure_and_edge_arrays():
    """Verify explicit persistent edge arrays in ContactNetwork with degree controls."""
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=1000, random_seed=42)
    net = build_persistent_contact_network(
        pop,
        max_school_degree=10,
        max_work_degree=8,
        max_community_degree=6,
        random_seed=42
    )

    assert isinstance(net, ContactNetwork)
    assert net.n_agents == 1000
    assert net.n_edges > 0
    assert len(net.edge_u) == net.n_edges
    assert len(net.edge_v) == net.n_edges
    assert len(net.edge_weight) == net.n_edges
    assert len(net.edge_layer) == net.n_edges

    # Edge indices must be valid agent indices
    assert np.all((net.edge_u >= 0) & (net.edge_u < 1000))
    assert np.all((net.edge_v >= 0) & (net.edge_v < 1000))
    # Undirected pairs: u < v
    assert np.all(net.edge_u < net.edge_v)

    # All 4 layers represented
    layers_present = set(np.unique(net.edge_layer))
    assert LAYER_HOME in layers_present
    assert LAYER_WORK in layers_present


def test_calendar_schedule_shifts():
    """Verify weekday/weekend and holiday transmission multipliers."""
    cal = CalendarSchedule(
        start_date="2020-03-01",
        school_holiday_intervals=((10, 20),),
        weekend_work_fraction=0.15,
        weekend_school_multiplier=0.0
    )

    # 2020-03-01 is Day 0 (Sunday) -> weekend
    m_weekend = cal.get_layer_multipliers(0)
    assert m_weekend[LAYER_SCHOOL] == 0.0
    assert m_weekend[LAYER_WORK] == 0.15
    assert m_weekend[LAYER_HOME] > 1.0

    # Day 1 is Monday -> regular weekday
    m_weekday = cal.get_layer_multipliers(1)
    assert m_weekday[LAYER_SCHOOL] == 1.0
    assert m_weekday[LAYER_WORK] == 1.0

    # Day 12 is within school holiday -> school closed
    m_holiday = cal.get_layer_multipliers(12)
    assert m_holiday[LAYER_SCHOOL] == 0.0


def test_vectorized_edge_transmission():
    """Verify vectorized compute_network_edge_lambda produces non-zero pressure on contacts."""
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=500, random_seed=42)
    net = build_persistent_contact_network(pop, random_seed=42)

    loads = np.zeros(500, dtype=np.float32)
    # Seed 5 infectious agents
    seeds = [10, 25, 50, 100, 200]
    loads[seeds] = 1.0

    lambdas = compute_network_edge_lambda(net, loads, beta=0.05)
    assert len(lambdas) == 500
    assert np.any(lambdas > 0)
    # Contact partners of seeds must receive infection pressure
    seed_contacts = set(net.edge_v[np.isin(net.edge_u, seeds)]).union(
        set(net.edge_u[np.isin(net.edge_v, seeds)])
    )
    for c in list(seed_contacts)[:10]:
        assert lambdas[c] > 0.0


def test_expectation_based_r0_verification_2000_trials():
    """Verify expectation-based calibration with 2,000 Monte Carlo trials per Stage A2."""
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=5000, random_seed=42)
    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        dp = DiseasePack(**yaml.safe_load(f))
    contacts_df = pd.read_csv("regions/example_synthetic/contacts.csv")

    state_graph = CompiledStateGraph(dp, ["0-4", "5-18", "19-64", "65+"])
    layer_matrices = {
        "home": np.eye(4) * 2.0,
        "school": np.eye(4) * 1.5,
        "work": np.eye(4) * 1.5,
        "community": np.eye(4) * 1.0
    }

    target_r0 = 2.5
    rng = np.random.default_rng(42)
    calib_beta, empirical_r0 = calibrate_beta_expectation(
        pop=pop,
        state_graph=state_graph,
        layer_matrices=layer_matrices,
        target_r0=target_r0,
        rng=rng,
        mc_trials=2000
    )

    assert calib_beta > 0.0
    # Expected empirical R0 from 2,000 trials must agree with target R0 within 12%
    rel_error = abs(empirical_r0 - target_r0) / target_r0
    assert rel_error < 0.12, f"R0 error {rel_error:.3f} too high (empirical={empirical_r0}, target={target_r0})"


def test_simulation_with_contact_network_and_calendar():
    """Verify end-to-end simulation runs cleanly with explicit ContactNetwork and CalendarSchedule."""
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=1000, random_seed=42)
    net = build_persistent_contact_network(pop, random_seed=42)
    cal = CalendarSchedule(start_date="2020-03-01")

    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        dp = DiseasePack(**yaml.safe_load(f))
    with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
        s_dict = yaml.safe_load(f)
    s_dict["horizon_days"] = 30
    s_dict["seeding"]["initial_cases_per_area"] = 20
    sc = ScenarioPack(**s_dict)

    res = run_simulation(pop, dp, sc, contact_network=net, calendar_schedule=cal)
    assert res.attack_rate > 0.10
    assert res.total_infections > 0
    assert len(res.daily_area_infections) == 30
