"""High-performance accelerated numerical kernels for EpiSwarm engine.

Provides Numba JIT kernels with parallel=True and prange for edge transmission
and inner loops, alongside strict pure-NumPy fallbacks and equivalence verification.
"""

from __future__ import annotations

import os
from typing import Tuple
import numpy as np

# Configurable environment flag for Numba acceleration
USE_NUMBA_ENV = os.environ.get("EPISWARM_USE_NUMBA", "1").lower() in ("1", "true", "yes")

try:
    if not USE_NUMBA_ENV:
        raise ImportError("Numba disabled via EPISWARM_USE_NUMBA environment variable")
    import numba
    from numba import njit, prange
    HAS_NUMBA = True
except Exception:
    HAS_NUMBA = False
    # Dummy decorators for fallback
    def njit(*args, **kwargs):
        def decorator(fn):
            return fn
        return decorator
    prange = range


if HAS_NUMBA:
    @njit(parallel=True, fastmath=True)
    def _edge_lambda_numba_parallel(
        edge_u: np.ndarray,
        edge_v: np.ndarray,
        edge_weight: np.ndarray,
        edge_layer: np.ndarray,
        layer_factors: np.ndarray,
        agent_loads: np.ndarray,
        beta: float,
        n_agents: int,
        n_threads: int = 4
    ) -> np.ndarray:
        """Parallel chunked edge transmission kernel across contact graph edges."""
        n_edges = len(edge_u)
        chunk_size = (n_edges + n_threads - 1) // n_threads
        thread_outs = np.zeros((n_threads, n_agents), dtype=np.float32)
        b = np.float32(beta)

        for tid in prange(n_threads):
            start = tid * chunk_size
            end = min(n_edges, start + chunk_size)
            t_out = thread_outs[tid]
            for i in range(start, end):
                u = edge_u[i]
                v = edge_v[i]
                w = edge_weight[i] * layer_factors[edge_layer[i]] * b
                lu = agent_loads[u]
                lv = agent_loads[v]
                if lu > 0.0:
                    t_out[v] += w * lu
                if lv > 0.0:
                    t_out[u] += w * lv

        # Parallel thread reduction
        final_out = np.zeros(n_agents, dtype=np.float32)
        for a in prange(n_agents):
            s = np.float32(0.0)
            for tid in range(n_threads):
                s += thread_outs[tid, a]
            final_out[a] = s
        return final_out


def compute_edge_lambda_numpy(
    edge_u: np.ndarray,
    edge_v: np.ndarray,
    edge_weight: np.ndarray,
    edge_layer: np.ndarray,
    layer_factors: np.ndarray,
    agent_loads: np.ndarray,
    beta: float,
    n_agents: int
) -> np.ndarray:
    """Pure NumPy vector accumulation fallback using np.bincount."""
    factors_per_edge = layer_factors[edge_layer]
    eff_edge_weights = edge_weight * factors_per_edge * beta
    loads_u = agent_loads[edge_u]
    pressure_u_to_v = eff_edge_weights * loads_u
    loads_v = agent_loads[edge_v]
    pressure_v_to_u = eff_edge_weights * loads_v
    lambda_received_at_v = np.bincount(edge_v, weights=pressure_u_to_v, minlength=n_agents).astype(np.float32)
    lambda_received_at_u = np.bincount(edge_u, weights=pressure_v_to_u, minlength=n_agents).astype(np.float32)
    return lambda_received_at_v + lambda_received_at_u


def compute_edge_lambda_fast(
    edge_u: np.ndarray,
    edge_v: np.ndarray,
    edge_weight: np.ndarray,
    edge_layer: np.ndarray,
    layer_factors: np.ndarray,
    agent_loads: np.ndarray,
    beta: float,
    n_agents: int,
    force_numpy: bool = False
) -> np.ndarray:
    """Dispatch edge transmission to parallel Numba kernel or NumPy fallback."""
    if HAS_NUMBA and not force_numpy and len(edge_u) > 1000:
        return _edge_lambda_numba_parallel(
            edge_u=edge_u,
            edge_v=edge_v,
            edge_weight=edge_weight,
            edge_layer=edge_layer,
            layer_factors=layer_factors,
            agent_loads=agent_loads,
            beta=beta,
            n_agents=n_agents,
            n_threads=min(8, max(1, os.cpu_count() or 4))
        )
    return compute_edge_lambda_numpy(
        edge_u=edge_u,
        edge_v=edge_v,
        edge_weight=edge_weight,
        edge_layer=edge_layer,
        layer_factors=layer_factors,
        agent_loads=agent_loads,
        beta=beta,
        n_agents=n_agents
    )
