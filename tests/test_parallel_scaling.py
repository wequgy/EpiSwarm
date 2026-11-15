"""Equivalence and scaling tests for ProcessPoolExecutor with shared memory (Stage R3.2)."""

import pytest
import yaml
from pathlib import Path

from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.population.build import build_synthetic_population
from episwarm.analysis.replicates import run_replicates
from episwarm.engine.kernels import compute_edge_lambda_fast, compute_edge_lambda_numpy, HAS_NUMBA
import numpy as np


@pytest.fixture(scope="module")
def setup_env():
    root = Path(__file__).resolve().parent.parent
    region_dir = root / "regions" / "example_synthetic"
    with open(root / "diseases" / "respiratory_generic.yaml", "r", encoding="utf-8") as f:
        disease = DiseasePack(**yaml.safe_load(f))
    with open(root / "scenarios" / "baseline.yaml", "r", encoding="utf-8") as f:
        scenario = ScenarioPack(**yaml.safe_load(f))
    scenario.horizon_days = 20
    pop = build_synthetic_population(region_dir=region_dir, scale_agents=5000, random_seed=42)
    return pop, disease, scenario


def test_replicates_process_vs_thread_equivalence(setup_env):
    """Verify ProcessPoolExecutor with shared memory produces identical results to single/thread runs for same seeds."""
    pop, disease, scenario = setup_env

    # 1. Thread execution (single process)
    rep_thread = run_replicates(
        pop=pop,
        disease_pack=disease,
        scenario_pack=scenario,
        n_replicates=3,
        base_seed=101,
        use_processes=False,
        max_workers=1
    )

    # 2. ProcessPoolExecutor execution with shared memory
    rep_proc = run_replicates(
        pop=pop,
        disease_pack=disease,
        scenario_pack=scenario,
        n_replicates=3,
        base_seed=101,
        use_processes=True,
        max_workers=2
    )

    assert len(rep_thread.per_seed) == len(rep_proc.per_seed)
    for res_t, res_p in zip(rep_thread.per_seed, rep_proc.per_seed):
        assert res_t.seed == res_p.seed
        assert res_t.peak_day == res_p.peak_day
        assert res_t.peak_infections == res_p.peak_infections
        assert res_t.total_deaths == res_p.total_deaths
        assert pytest.approx(res_t.attack_rate, rel=1e-5) == res_p.attack_rate


def test_kernel_equivalence():
    """Verify Numba accelerated edge lambda matches pure NumPy fallback within float32 precision."""
    n_agents = 5000
    n_edges = 20000
    rng = np.random.default_rng(42)

    edge_u = rng.integers(0, n_agents, size=n_edges, dtype=np.int32)
    edge_v = rng.integers(0, n_agents, size=n_edges, dtype=np.int32)
    edge_weight = rng.uniform(0.5, 1.5, size=n_edges).astype(np.float32)
    edge_layer = rng.integers(0, 4, size=n_edges, dtype=np.int8)
    layer_factors = np.array([1.0, 0.8, 0.9, 1.1], dtype=np.float32)

    agent_loads = np.zeros(n_agents, dtype=np.float32)
    inf_idx = rng.choice(n_agents, size=150, replace=False)
    agent_loads[inf_idx] = rng.uniform(0.5, 2.0, size=len(inf_idx)).astype(np.float32)

    res_numpy = compute_edge_lambda_numpy(
        edge_u=edge_u,
        edge_v=edge_v,
        edge_weight=edge_weight,
        edge_layer=edge_layer,
        layer_factors=layer_factors,
        agent_loads=agent_loads,
        beta=0.08,
        n_agents=n_agents
    )

    res_fast = compute_edge_lambda_fast(
        edge_u=edge_u,
        edge_v=edge_v,
        edge_weight=edge_weight,
        edge_layer=edge_layer,
        layer_factors=layer_factors,
        agent_loads=agent_loads,
        beta=0.08,
        n_agents=n_agents
    )

    np.testing.assert_allclose(res_fast, res_numpy, rtol=1e-5, atol=1e-6)
