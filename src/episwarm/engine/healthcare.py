"""Healthcare capacity, patient routing, oxygen tracking, and overflow mortality engine."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from episwarm.packs.disease import DiseasePack, OverflowMortalityConfig


@dataclass
class AreaCapacity:
    """Bed and resource availability within a single administrative area."""
    area_id: str
    area_int: int
    general_nominal: int
    general_available: int
    icu_nominal: int
    icu_available: int
    oxygen_buffer_days: float = 30.0


@dataclass
class HealthcareTelemetry:
    """Historical daily tracking of hospital resource utilization and overflow."""
    days: int
    n_areas: int

    # (days, n_areas)
    general_occupancy: np.ndarray
    icu_occupancy: np.ndarray
    unserved_general: np.ndarray
    unserved_icu: np.ndarray

    # Overall counters
    total_unmet_demand_general: int = 0
    total_unmet_demand_icu: int = 0
    deaths_attributable_to_overflow: int = 0


class RegionalHealthcareSystem:
    """Models spatial routing of severe patients to hospital beds and overflow penalties."""

    def __init__(
        self,
        capacity_df: pd.DataFrame,
        hospitals_df: Optional[pd.DataFrame],
        areas_df: pd.DataFrame,
        area_id_to_int: Dict[str, int],
        overflow_config: OverflowMortalityConfig,
        external_inflow_fraction: float = 0.05
    ):
        self.area_id_to_int = area_id_to_int
        self.int_to_area_id = {v: k for k, v in area_id_to_int.items()}
        self.n_areas = len(area_id_to_int)
        self.overflow_config = overflow_config
        self.external_inflow_fraction = external_inflow_fraction

        # 1. Initialize nominal capacities per area
        self.general_cap = np.zeros(self.n_areas, dtype=np.int32)
        self.icu_cap = np.zeros(self.n_areas, dtype=np.int32)

        # Parse capacity_df
        # If capacity table has hospital_id, join with hospitals_df to resolve area_id
        cap_merged = capacity_df.copy()
        if "hospital_id" in cap_merged.columns and hospitals_df is not None:
            if "area_id" not in cap_merged.columns:
                h_map = hospitals_df.set_index("hospital_id")["area_id"].to_dict()
                cap_merged["area_id"] = cap_merged["hospital_id"].map(h_map)

        for _, row in cap_merged.iterrows():
            aid_str = str(row.get("area_id", ""))
            if aid_str not in self.area_id_to_int:
                continue
            aid = self.area_id_to_int[aid_str]
            cat = str(row.get("category", "")).strip().lower()
            nom = int(row.get("nominal", 0))

            if "icu" in cat:
                self.icu_cap[aid] += nom
            else:
                self.general_cap[aid] += nom

        # Fallback only if capacity_df is empty or missing
        if capacity_df.empty:
            self.general_cap.fill(100)
            self.icu_cap.fill(15)

        # 2. Build spatial distance matrix between areas for overflow routing
        self.distances = np.zeros((self.n_areas, self.n_areas), dtype=np.float32)
        if "lat" in areas_df.columns and "lon" in areas_df.columns:
            coords = np.zeros((self.n_areas, 2), dtype=np.float32)
            for _, r in areas_df.iterrows():
                aid_s = str(r["area_id"])
                if aid_s in self.area_id_to_int:
                    idx = self.area_id_to_int[aid_s]
                    coords[idx] = [float(r["lat"]), float(r["lon"])]

            for i in range(self.n_areas):
                for j in range(self.n_areas):
                    self.distances[i, j] = np.linalg.norm(coords[i] - coords[j])
        else:
            # Fallback uniform distance
            self.distances.fill(1.0)
            np.fill_diagonal(self.distances, 0.0)

        # Ordered nearest neighbors per area
        self.nearest_areas = np.argsort(self.distances, axis=1)

    def route_patients(
        self,
        needed_category: int,        # 1: general, 3: icu
        patient_areas: np.ndarray,   # int16 array of origin areas
        patient_compliances: np.ndarray # float32 array in [0, 1]
    ) -> Tuple[np.ndarray, np.ndarray, int]:
        """Route severe patients to available beds, returning routing success and mortality multipliers.

        Returns:
            is_served: bool array (True if admitted to a bed)
            mortality_multipliers: float32 array (amplification due to overflow / lack of care)
            unmet_count: int total count of unserved patients
        """
        n_patients = len(patient_areas)
        if n_patients == 0:
            return np.empty(0, dtype=bool), np.empty(0, dtype=np.float32), 0

        # Choose capacity pool
        pool = np.copy(self.icu_cap if needed_category == 3 else self.general_cap)

        # Add external inflow demand
        ext_demand = int(round(n_patients * self.external_inflow_fraction))
        if ext_demand > 0:
            # Consume external fraction uniformly across areas
            dec = ext_demand // self.n_areas
            pool = np.maximum(0, pool - dec)

        is_served = np.zeros(n_patients, dtype=bool)
        mortality_mults = np.ones(n_patients, dtype=np.float32)

        base_multiplier = (
            self.overflow_config.icu_unavailable_mortality_multiplier
            if needed_category == 3 else
            self.overflow_config.bed_unavailable_mortality_multiplier
        )

        # Route each patient
        for i in range(n_patients):
            origin_aid = patient_areas[i]
            comp = patient_compliances[i]

            # Try local area first, then nearest neighbors
            admitted = False
            for target_aid in self.nearest_areas[origin_aid]:
                if pool[target_aid] > 0:
                    pool[target_aid] -= 1
                    admitted = True
                    is_served[i] = True
                    break

            if not admitted:
                # Patient is unserved: apply overflow mortality penalty modulated by compliance
                # Compliant: comp -> 1.0 (benefit ~ 0.85); Non-compliant: comp -> 0.0 (penalty ~ 1.25)
                comp_factor = (
                    self.overflow_config.compliance_mortality_benefit * comp +
                    self.overflow_config.non_compliance_mortality_penalty * (1.0 - comp)
                )
                mortality_mults[i] = base_multiplier * comp_factor

        unmet = int(np.sum(~is_served))
        return is_served, mortality_mults, unmet
