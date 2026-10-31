"""Healthcare capacity and patient routing adapter.

Spec 6.1: Generic resources underlying model.
This module maintains backwards compatibility for RegionalHealthcareSystem.
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from episwarm.packs.disease import DiseasePack, OverflowMortalityConfig
from episwarm.engine.resources import RegionalResourceSystem, UnservedOutcomeConfig


class RegionalHealthcareSystem:
    """Backwards-compatible adapter routing severe patients to available capacity."""

    def __init__(
        self,
        capacity_df: pd.DataFrame,
        hospitals_df: Optional[pd.DataFrame],
        areas_df: pd.DataFrame,
        area_id_to_int: Dict[str, int],
        overflow_config: Optional[OverflowMortalityConfig] = None,
        external_inflow_fraction: float = 0.05
    ):
        self.area_id_to_int = area_id_to_int
        self.int_to_area_id = {v: k for k, v in area_id_to_int.items()}
        self.n_areas = len(area_id_to_int)
        self.overflow_config = overflow_config or OverflowMortalityConfig()
        self.external_inflow_fraction = external_inflow_fraction

        # Map capacity_df into generic resources df
        cap_merged = capacity_df.copy()
        if "hospital_id" in cap_merged.columns and hospitals_df is not None:
            if "area_id" not in cap_merged.columns:
                h_map = hospitals_df.set_index("hospital_id")["area_id"].to_dict()
                cap_merged["area_id"] = cap_merged["hospital_id"].map(h_map)

        if "resource_id" not in cap_merged.columns and "category" in cap_merged.columns:
            cap_merged["resource_id"] = cap_merged["category"]

        unserved_cfg = UnservedOutcomeConfig(
            theta_0=float(getattr(self.overflow_config, "bed_unavailable_mortality_multiplier", 2.0)) - 1.0,
            compliance_benefit=float(getattr(self.overflow_config, "compliance_mortality_benefit", 0.85)),
            non_compliance_penalty=float(getattr(self.overflow_config, "non_compliance_mortality_penalty", 1.25))
        )

        self.resource_system = RegionalResourceSystem(
            resources_df=cap_merged,
            areas_df=areas_df,
            area_id_to_int=area_id_to_int,
            unserved_config=unserved_cfg,
            external_inflow_fraction=external_inflow_fraction
        )

    def route_patients(
        self,
        needed_category: int,
        patient_areas: np.ndarray,
        patient_compliances: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, int]:
        """Route severe patients to available beds, returning routing success and mortality multipliers."""
        n_patients = len(patient_areas)
        if n_patients == 0:
            return np.empty(0, dtype=bool), np.empty(0, dtype=np.float32), 0

        res_key = "icu" if needed_category == 3 else "general"
        needs = [{res_key: 1.0} for _ in range(n_patients)]

        # Run allocation through generic resource system
        service_levels, adverse_probs, unmet_counts = self.resource_system.route_and_allocate(
            patient_areas=patient_areas,
            resource_needs=needs,
            self_care=patient_compliances,
            support=np.full(n_patients, 0.5, dtype=np.float32),
            alt_care=np.full(n_patients, 0.5, dtype=np.float32),
            unserved_days=np.zeros(n_patients, dtype=np.int16),
            severity_levels=np.full(n_patients, 1.0, dtype=np.float32),
            p_served_adverse=np.full(n_patients, 0.05, dtype=np.float32)
        )

        is_served = (service_levels >= 1.0)
        base_mult = (
            self.overflow_config.icu_unavailable_mortality_multiplier
            if needed_category == 3
            else self.overflow_config.bed_unavailable_mortality_multiplier
        )

        mortality_mults = np.ones(n_patients, dtype=np.float32)
        for i in range(n_patients):
            if not is_served[i]:
                comp = patient_compliances[i]
                comp_factor = (
                    self.overflow_config.compliance_mortality_benefit * comp +
                    self.overflow_config.non_compliance_mortality_penalty * (1.0 - comp)
                )
                mortality_mults[i] = base_mult * comp_factor

        unmet = int(np.sum(~is_served))
        return is_served, mortality_mults, unmet
