"""Dynamic age band parsing and vector mapping without hardcoded demographics (Spec 4.1 & Phase 17)."""

import re
from typing import List, Tuple, Optional
import numpy as np
import pandas as pd


def parse_age_band_bounds(band: str) -> Tuple[int, int]:
    """Parse age band string into (min_age, max_age) inclusive bounds.

    Supported formats:
    - '0-4' -> (0, 4)
    - '65+' -> (65, 150)
    - '19-64' -> (19, 64)
    - '80' -> (80, 80)
    """
    band = str(band).strip()
    if band.endswith("+"):
        try:
            return int(band[:-1]), 150
        except ValueError:
            return 65, 150
    m = re.match(r"^(\d+)\s*[-–]\s*(\d+)$", band)
    if m:
        return int(m.group(1)), int(m.group(2))
    try:
        val = int(band)
        return val, val
    except ValueError:
        return 0, 150


def resolve_age_bands_from_contacts(contacts_df: Optional[pd.DataFrame], fallback: Optional[List[str]] = None) -> List[str]:
    """Derive sorted age band labels dynamically from contacts dataframe or fallback."""
    if fallback is None:
        fallback = ["0-4", "5-18", "19-64", "65+"]
    if contacts_df is None or contacts_df.empty:
        return fallback

    candidates = set()
    for col in ("age_band_i", "age_band_j", "age_band"):
        if col in contacts_df.columns:
            candidates.update(contacts_df[col].dropna().astype(str).unique())

    if not candidates:
        return fallback

    # Sort age bands by lower bound
    return sorted(list(candidates), key=lambda b: parse_age_band_bounds(b)[0])


def assign_age_bands(ages: np.ndarray, age_bands: List[str]) -> np.ndarray:
    """Map an array of integer/float ages to integer age band indices 0..len(age_bands)-1."""
    out = np.zeros(len(ages), dtype=np.int8)
    for idx, band in enumerate(age_bands):
        min_a, max_a = parse_age_band_bounds(band)
        mask = (ages >= min_a) & (ages <= max_a)
        out[mask] = idx
    return out

