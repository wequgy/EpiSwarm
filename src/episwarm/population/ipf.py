"""Iterative Proportional Fitting (IPF) algorithm for multi-dimensional demographic synthesis."""

from typing import List, Tuple
import numpy as np


def run_ipf_2d(
    row_marginals: np.ndarray,
    col_marginals: np.ndarray,
    seed_matrix: np.ndarray = None,
    max_iter: int = 100,
    tol: float = 1e-6
) -> np.ndarray:
    """Run 2D Iterative Proportional Fitting (Biproportional fitting / RAS algorithm).

    Args:
        row_marginals: 1D array of target row sums (sum = 1.0 or N)
        col_marginals: 1D array of target column sums (sum matching row_marginals)
        seed_matrix: Optional prior joint distribution matrix (default: uniform)
        max_iter: Maximum iterations
        tol: Convergence tolerance for absolute error

    Returns:
        Converged joint contingency table matching row and col marginals.
    """
    row_target = np.asarray(row_marginals, dtype=np.float64)
    col_target = np.asarray(col_marginals, dtype=np.float64)

    # Normalize targets to same grand sum
    col_target = col_target * (row_target.sum() / max(1e-12, col_target.sum()))

    n_rows = len(row_target)
    n_cols = len(col_target)

    if seed_matrix is None:
        table = np.ones((n_rows, n_cols), dtype=np.float64)
    else:
        table = np.array(seed_matrix, dtype=np.float64)

    for _ in range(max_iter):
        # 1. Adjust rows
        current_row_sums = table.sum(axis=1)
        row_scales = np.where(current_row_sums > 1e-12, row_target / current_row_sums, 0.0)
        table = table * row_scales[:, np.newaxis]

        # 2. Adjust columns
        current_col_sums = table.sum(axis=0)
        col_scales = np.where(current_col_sums > 1e-12, col_target / current_col_sums, 0.0)
        table = table * col_scales[np.newaxis, :]

        # Check convergence
        row_err = np.max(np.abs(table.sum(axis=1) - row_target))
        col_err = np.max(np.abs(table.sum(axis=0) - col_target))
        if max(row_err, col_err) < tol:
            break

    return table


def run_ipf_3d(
    dim0_marg: np.ndarray,
    dim1_marg: np.ndarray,
    dim2_marg: np.ndarray,
    max_iter: int = 100,
    tol: float = 1e-5
) -> np.ndarray:
    """Run 3D Iterative Proportional Fitting for (age x sex x occupation)."""
    m0 = np.asarray(dim0_marg, dtype=np.float64)
    m1 = np.asarray(dim1_marg, dtype=np.float64)
    m2 = np.asarray(dim2_marg, dtype=np.float64)

    total = m0.sum()
    m1 = m1 * (total / max(1e-12, m1.sum()))
    m2 = m2 * (total / max(1e-12, m2.sum()))

    shape = (len(m0), len(m1), len(m2))
    table = np.ones(shape, dtype=np.float64)

    for _ in range(max_iter):
        # Dim 0
        s0 = table.sum(axis=(1, 2))
        table *= np.where(s0 > 1e-12, m0 / s0, 0.0)[:, None, None]

        # Dim 1
        s1 = table.sum(axis=(0, 2))
        table *= np.where(s1 > 1e-12, m1 / s1, 0.0)[None, :, None]

        # Dim 2
        s2 = table.sum(axis=(0, 1))
        table *= np.where(s2 > 1e-12, m2 / s2, 0.0)[None, None, :]

        err0 = np.max(np.abs(table.sum(axis=(1, 2)) - m0))
        err1 = np.max(np.abs(table.sum(axis=(0, 2)) - m1))
        err2 = np.max(np.abs(table.sum(axis=(0, 1)) - m2))

        if max(err0, err1, err2) < tol:
            break

    return table
