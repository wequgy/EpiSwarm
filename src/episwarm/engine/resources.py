"""Generic healthcare resources, spatial allocation, and individual unserved patient outcomes.

Spec 6.1: Resources are completely generic (no hardcoded resource names in src/).
Spec 6.2: Daily spatial routing with nearest-neighbor search and unserved day accumulation.
Spec 6.3: Individual patient outcomes under unserved/overflow conditions (Formula 6.3).
Spec 6.4: Resource what-if additions with cap validation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd

from episwarm.packs.disease import DiseasePack, UnservedOutcomeConfig
from episwarm.packs.scenario import ResourceAddAction


@dataclass
class ResourcePool:
    """Tracking pool for a single generic resource type within an area."""
    resource_id: str
    nominal: float
    available: float
    effective_low: float
    effective_high: float
    upper_cap_of_extra: float
    restock_rate: float


@dataclass
class ResourceTelemetry:
    """Historical telemetry tracking resource demand, allocation, and unserved counts."""
    days: int
    n_areas: int
    resource_ids: List[str]
    # (days, n_areas, n_resources)
    demand: np.ndarray
    allocated: np.ndarray
    unserved: np.ndarray
    total_unmet_demand: Dict[str, int] = field(default_factory=dict)
    deaths_attributable_to_overflow: int = 0


def calculate_adverse_probability(
    p_served: float,
    service_level: float,
    severity_level: float,
    self_care: float,
    support: float,
    alt_care: float,
    unserved_days: int,
    config: UnservedOutcomeConfig
) -> float:
    """Compute individual adverse outcome probability using Spec 6.3 multi-factor logistic formula.

    logit(p_adverse) = logit(p_served)
                     + theta_0 * (1 - service_level)
                     + theta_sev * (severity_level - ref)
                     + theta_care * (1 - self_care)
                     + theta_sup * (1 - support)
                     + theta_alt * (1 - alt_care)
                     + theta_delay * unserved_days
    """
    # Safe clipping for baseline probability
    p_clamped = np.clip(p_served, 1e-6, 1.0 - 1e-6)
    logit_served = np.log(p_clamped / (1.0 - p_clamped))

    sev_delta = max(0.0, severity_level - config.ref_severity)
    logit_adverse = (
        logit_served
        + config.theta_0 * (1.0 - np.clip(service_level, 0.0, 1.0))
        + config.theta_sev * sev_delta
        + config.theta_care * (1.0 - np.clip(self_care, 0.0, 1.0))
        + config.theta_sup * (1.0 - np.clip(support, 0.0, 1.0))
        + config.theta_alt * (1.0 - np.clip(alt_care, 0.0, 1.0))
        + config.theta_delay * max(0, unserved_days)
    )

    # Sigmoid with numerical bounds
    logit_adverse = np.clip(logit_adverse, -20.0, 20.0)
    return float(1.0 / (1.0 + np.exp(-logit_adverse)))


class RegionalResourceSystem:
    """Manages generic resource availability, spatial patient allocation, and overflow."""

    def __init__(
        self,
        resources_df: Optional[pd.DataFrame],
        areas_df: pd.DataFrame,
        area_id_to_int: Dict[str, int],
        unserved_config: Optional[UnservedOutcomeConfig] = None,
        external_inflow_fraction: float = 0.05
    ):
        self.area_id_to_int = area_id_to_int
        self.int_to_area_id = {v: k for k, v in area_id_to_int.items()}
        self.n_areas = len(area_id_to_int)
        self.config = unserved_config or UnservedOutcomeConfig()
        self.external_inflow_fraction = external_inflow_fraction

        # Map: area_int -> {resource_id: ResourcePool}
        self.pools: Dict[int, Dict[str, ResourcePool]] = {a: {} for a in range(self.n_areas)}
        self.all_resource_ids: List[str] = []

        if resources_df is not None and not resources_df.empty:
            self._parse_resources_df(resources_df)
        else:
            # Fallback default generic resource pool
            self._init_fallback_pools()

        # Spatial distance matrix for overflow routing
        self._build_spatial_distances(areas_df)

    def _parse_resources_df(self, df: pd.DataFrame):
        """Parse generic resources.csv or adapted capacity table."""
        seen_res = set()
        for _, row in df.iterrows():
            aid_str = str(row.get("area_id", "")).strip()
            # If hospital_id present without area_id, caller should join, or map ALL
            if aid_str == "ALL":
                target_aids = list(range(self.n_areas))
            elif aid_str in self.area_id_to_int:
                target_aids = [self.area_id_to_int[aid_str]]
            else:
                continue

            r_id = str(row.get("resource_id", row.get("category", "default_res"))).strip().lower()
            seen_res.add(r_id)

            nom = float(row.get("nominal", 50.0))
            low = float(row.get("effective_low", nom * 0.8))
            high = float(row.get("effective_high", nom * 1.1))
            cap = float(row.get("upper_cap_of_extra", row.get("upper_cap_extra", nom * 0.3)))
            restock = float(row.get("restock_rate", 0.0))

            for aid in target_aids:
                if r_id in self.pools[aid]:
                    # Aggregate
                    p = self.pools[aid][r_id]
                    p.nominal += nom
                    p.available += nom
                    p.effective_low += low
                    p.effective_high += high
                    p.upper_cap_of_extra += cap
                else:
                    self.pools[aid][r_id] = ResourcePool(
                        resource_id=r_id,
                        nominal=nom,
                        available=nom,
                        effective_low=low,
                        effective_high=high,
                        upper_cap_of_extra=cap,
                        restock_rate=restock
                    )

        self.all_resource_ids = sorted(list(seen_res))
        if not self.all_resource_ids:
            self._init_fallback_pools()

    def _init_fallback_pools(self):
        """Default generic resource pool if no data is provided."""
        res_id = "clinical_bed"
        self.all_resource_ids = [res_id]
        for aid in range(self.n_areas):
            self.pools[aid][res_id] = ResourcePool(
                resource_id=res_id,
                nominal=100.0,
                available=100.0,
                effective_low=80.0,
                effective_high=110.0,
                upper_cap_of_extra=30.0,
                restock_rate=0.0
            )

    def _build_spatial_distances(self, areas_df: pd.DataFrame):
        """Precompute distance matrix and nearest-neighbor routing lists."""
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
            self.distances.fill(1.0)
            np.fill_diagonal(self.distances, 0.0)

        self.nearest_areas = np.argsort(self.distances, axis=1)

    def apply_resource_addition(self, action: ResourceAddAction):
        """Apply scenario resource additions, validating against upper_cap_of_extra (spec 6.4)."""
        target_aids = (
            list(range(self.n_areas))
            if action.area_id == "ALL"
            else [self.area_id_to_int[action.area_id]]
            if action.area_id in self.area_id_to_int
            else []
        )

        amount_per_area = action.amount / max(1, len(target_aids))
        for aid in target_aids:
            pool = self.pools[aid].get(action.resource_id)
            if pool is None:
                # If resource not previously registered, register it
                pool = ResourcePool(
                    resource_id=action.resource_id,
                    nominal=0.0,
                    available=0.0,
                    effective_low=0.0,
                    effective_high=0.0,
                    upper_cap_of_extra=amount_per_area * 1.5,
                    restock_rate=0.0
                )
                self.pools[aid][action.resource_id] = pool

            # Cap validation
            if amount_per_area > pool.upper_cap_of_extra:
                area_name = self.int_to_area_id.get(aid, str(aid))
                raise ValueError(
                    f"Resource addition of {amount_per_area:.1f} {action.resource_id} in area '{area_name}' "
                    f"exceeds upper_cap_of_extra ({pool.upper_cap_of_extra:.1f}). Violates Spec 6.4 capacity bounds."
                )

            pool.nominal += amount_per_area
            pool.available += amount_per_area
            pool.effective_high += amount_per_area

    def route_and_allocate(
        self,
        patient_areas: np.ndarray,
        resource_needs: List[Dict[str, float]],
        self_care: np.ndarray,
        support: np.ndarray,
        alt_care: np.ndarray,
        unserved_days: np.ndarray,
        severity_levels: np.ndarray,
        p_served_adverse: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, Dict[str, int]]:
        """Route patients across spatial network and compute individual service levels and adverse probabilities.

        Returns:
            service_levels: float32 array in [0, 1] per patient
            adverse_probs: float32 array per patient
            unmet_counts: Dict[resource_id, int]
        """
        n_patients = len(patient_areas)
        if n_patients == 0:
            return np.empty(0, dtype=np.float32), np.empty(0, dtype=np.float32), {}

        service_levels = np.zeros(n_patients, dtype=np.float32)
        adverse_probs = np.zeros(n_patients, dtype=np.float32)
        unmet_counts: Dict[str, int] = {r: 0 for r in self.all_resource_ids}

        # Snapshot current available resources to allocate
        current_avail = {
            aid: {r_id: p.available for r_id, p in self.pools[aid].items()}
            for aid in range(self.n_areas)
        }

        # Route each patient
        for i in range(n_patients):
            origin_aid = patient_areas[i]
            needs = resource_needs[i]

            if not needs:
                # No healthcare resources required
                service_levels[i] = 1.0
                adverse_probs[i] = p_served_adverse[i]
                continue

            # Check if all needed resources are available at origin or nearest neighbor
            allocated = False
            for target_aid in self.nearest_areas[origin_aid]:
                target_pool = current_avail[target_aid]
                # Can target_aid satisfy all needs?
                can_satisfy = all(target_pool.get(r, 0.0) >= qty for r, qty in needs.items())
                if can_satisfy:
                    for r, qty in needs.items():
                        target_pool[r] -= qty
                    service_levels[i] = 1.0
                    allocated = True
                    break

            if not allocated:
                # Check partial availability at origin
                local_pool = current_avail[origin_aid]
                ratios = [min(1.0, local_pool.get(r, 0.0) / max(qty, 1e-6)) for r, qty in needs.items()]
                service_levels[i] = float(min(ratios)) if ratios else 0.0

                for r, qty in needs.items():
                    if local_pool.get(r, 0.0) < qty:
                        unmet_counts[r] = unmet_counts.get(r, 0) + 1

            # Compute individual adverse probability
            adverse_probs[i] = calculate_adverse_probability(
                p_served=float(p_served_adverse[i]),
                service_level=float(service_levels[i]),
                severity_level=float(severity_levels[i]),
                self_care=float(self_care[i]),
                support=float(support[i]),
                alt_care=float(alt_care[i]),
                unserved_days=int(unserved_days[i]),
                config=self.config
            )

        return service_levels, adverse_probs, unmet_counts
