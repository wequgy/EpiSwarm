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

    # Symmetrize if upper/lower triangle only was provided
    for i in range(n):
        for j in range(n):
            if M[i, j] > 0 and M[j, i] == 0:
                M[j, i] = M[i, j]
            elif M[j, i] > 0 and M[i, j] == 0:
                M[i, j] = M[j, i]

    return M


def parse_layer_contact_matrices(
    contacts_df: Optional[pd.DataFrame],
    age_bands: List[str],
    layer_weights: Optional[Dict[str, float]] = None
) -> Dict[str, np.ndarray]:
    """Parse or synthesize layer-specific contact matrices M^l for Prem-style transmission (Spec 4.1).

    Layers: home, school, work, community
    Guarantees sum_l M^l = M_total.
    """
    if layer_weights is None:
        layer_weights = {"home": 0.35, "school": 0.25, "work": 0.25, "community": 0.15}

    n = len(age_bands)
    band_to_idx = {b: i for i, b in enumerate(age_bands)}

    if contacts_df is None or contacts_df.empty:
        # Default fallback symmetric matrix
        M_total = np.eye(n, dtype=np.float64) * 4.0 + 1.0
        return {l: w * M_total for l, w in layer_weights.items()}

    layers_present = set(contacts_df["layer"].unique()) if "layer" in contacts_df.columns else set()
    needed_layers = {"home", "school", "work", "community"}

    if needed_layers.issubset(layers_present):
        result = {}
        for l in ["home", "school", "work", "community"]:
            M_l = np.zeros((n, n), dtype=np.float64)
            sub = contacts_df[contacts_df["layer"] == l]
            for _, row in sub.iterrows():
                b_i = str(row["age_band_i"])
                b_j = str(row["age_band_j"])
                rate = float(row["contacts_per_day"])
                if b_i in band_to_idx and b_j in band_to_idx:
                    M_l[band_to_idx[b_i], band_to_idx[b_j]] += rate
            for i in range(n):
                for j in range(n):
                    if M_l[i, j] > 0 and M_l[j, i] == 0:
                        M_l[j, i] = M_l[i, j]
                    elif M_l[j, i] > 0 and M_l[i, j] == 0:
                        M_l[i, j] = M_l[j, i]
            result[l] = M_l
        return result

    # Otherwise decompose M_total by layer weights
    M_total = parse_contact_matrix(contacts_df, age_bands)
    return {l: float(w) * M_total for l, w in layer_weights.items()}


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
