"""Column mapping wizard and schema transformation engine."""

from typing import Dict, List, Optional
import pandas as pd

from episwarm.importers.templates import CSV_CONTRACTS


# Canonical aliases for standard columns to assist auto-mapping
COLUMN_ALIASES: Dict[str, List[str]] = {
    "area_id": ["area", "ward_id", "zone_id", "district_id", "id", "code"],
    "name": ["area_name", "ward_name", "zone_name", "district_name", "label"],
    "level": ["admin_level", "hierarchy", "type"],
    "parent_id": ["parent", "zone", "district", "city_id"],
    "population": ["pop", "total_population", "persons", "residents"],
    "households": ["hh", "total_households", "num_households"],
    "area_km2": ["area", "size_km2", "sqkm", "area_sqkm"],
    "lat": ["latitude", "y", "centroid_lat"],
    "lon": ["longitude", "long", "x", "centroid_lon"],
    "sex": ["gender"],
    "age_band": ["age_group", "age_cohort", "age"],
    "share": ["proportion", "fraction", "percentage", "pct"],
    "jobs": ["total_jobs", "employment", "workers"],
    "venue_type": ["type", "facility_type", "category"],
    "count": ["num_venues", "total", "quantity"],
    "mean_size": ["avg_size", "capacity", "mean_capacity"],
    "from_area": ["origin", "source_area", "from"],
    "to_area": ["destination", "target_area", "to"],
    "contacts_per_day": ["contacts", "rate", "mean_contacts"],
    "nominal": ["beds", "capacity", "total_beds"],
    "effective_low": ["low_capacity", "min_beds"],
    "effective_high": ["high_capacity", "max_beds"],
    "source": ["data_source", "citation", "origin"],
    "status": ["provenance", "data_status"]
}


class ColumnMapper:
    """Detects and applies mappings between user upload columns and canonical contracts."""

    @staticmethod
    def suggest_mapping(filename: str, uploaded_columns: List[str]) -> Dict[str, str]:
        """Auto-suggest mapping from uploaded columns to target contract columns."""
        contract = CSV_CONTRACTS.get(filename, [])
        mapping: Dict[str, str] = {}
        normalized_upload = {c.lower().strip().replace(" ", "_"): c for c in uploaded_columns}

        for target_col in contract:
            # 1. Exact match
            if target_col in normalized_upload:
                mapping[target_col] = normalized_upload[target_col]
                continue

            # 2. Alias match
            aliases = COLUMN_ALIASES.get(target_col, [])
            matched = False
            for alias in aliases:
                if alias in normalized_upload:
                    mapping[target_col] = normalized_upload[alias]
                    matched = True
                    break
            if matched:
                continue

        return mapping

    @staticmethod
    def apply_mapping(
        df: pd.DataFrame,
        filename: str,
        mapping: Dict[str, str],
        default_status: str = "user_supplied"
    ) -> pd.DataFrame:
        """Rename DataFrame columns according to mapping and inject defaults for missing required provenance."""
        # Invert mapping: user_col -> target_col
        rename_dict = {user_col: target_col for target_col, user_col in mapping.items() if user_col in df.columns}
        remapped = df.rename(columns=rename_dict).copy()

        # Ensure provenance headers exist
        if "status" not in remapped.columns:
            remapped["status"] = default_status
        if "source" not in remapped.columns:
            remapped["source"] = "user_upload"

        return remapped

