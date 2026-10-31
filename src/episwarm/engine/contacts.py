"""Contact matrix processing, spectral radius calculation, and R0-to-beta analytical calibration."""

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy.linalg import eigvals


def parse_contact_matrix(
    contacts_df: pd.DataFrame,
    age_bands: List[str]
) -> np.ndarray:
    """Construct an (n_ages x n_ages) conversational contact matrix M from contacts.csv.

    Rows: age_band_i (participant)
    Cols: age_band_j (contact)
    """
    n = len(age_bands)
    band_to_idx = {b: i for i, b in enumerate(age_bands)}
    M = np.zeros((n, n), dtype=np.float64)

    # Filter to overall or aggregate layer
    df = contacts_df.copy()
    if "layer" in df.columns:
        # If 'all' layer exists, prioritize it; otherwise sum layers
        if "all" in df["layer"].values:
            df = df[df["layer"] == "all"]

    for _, row in df.iterrows():
        b_i = str(row["age_band_i"])
        b_j = str(row["age_band_j"])
        rate = float(row["contacts_per_day"])

        if b_i in band_to_idx and b_j in band_to_idx:
            i = band_to_idx[b_i]
            j = band_to_idx[b_j]
            M[i, j] += rate

    # Reciprocity correction if off-diagonal asymmetry exists
    return M


def compute_spectral_radius(matrix: np.ndarray) -> float:
    """Compute the dominant eigenvalue (spectral radius Υ) of a non-negative contact matrix.

    Following Libin et al. (2020) and Diekmann et al. (2010):
    Υ(M) = max |λ_i(M)|
    """
    if matrix.size == 0 or np.all(matrix == 0):
        return 1.0

    evals = eigvals(matrix)
    spectral_radius = float(np.max(np.abs(evals)))
    return max(1e-6, spectral_radius)


def analytical_beta_from_r0(
    r0: float,
    mean_infectious_days: float,
    contact_matrix: np.ndarray
) -> Tuple[float, float]:
    """Calculate the starting transmission probability beta from target R0 and Next-Gen spectral radius.

    Formula (Libin et al. 2020):
    R0 = (beta / gamma) * Υ(M)
    => beta = (R0 * gamma) / Υ(M)
    where gamma = 1 / mean_infectious_days.

    Returns:
        beta: Initial estimated transmission probability
        spectral_radius: Dominant eigenvalue Υ(M)
    """
    gamma = 1.0 / max(0.1, mean_infectious_days)
    upsilon = compute_spectral_radius(contact_matrix)
    beta = (r0 * gamma) / upsilon
    return float(beta), float(upsilon)
