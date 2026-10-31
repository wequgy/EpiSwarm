"""CSV data contracts, templates, and header definitions for EpiSwarm Studio."""

from typing import Dict, List

# Standard schemas with mandatory primary headers and provenance headers (source, status)
CSV_CONTRACTS: Dict[str, List[str]] = {
    "areas.csv": [
        "area_id", "name", "level", "parent_id", "population",
        "households", "area_km2", "lat", "lon", "source", "status"
    ],
    "age_structure.csv": [
        "area_id", "sex", "age_band", "share", "source", "status"
    ],
    "employment.csv": [
        "area_id", "jobs", "employment_rate", "sector_shares", "source", "status"
    ],
    "venues.csv": [
        "area_id", "venue_type", "count", "mean_size", "size_sd", "source", "status"
    ],
    "commute_od.csv": [
        "from_area", "to_area", "share", "source", "status"
    ],
    "contacts.csv": [
        "layer", "age_band_i", "age_band_j", "contacts_per_day", "source", "status"
    ],
    "hospitals.csv": [
        "hospital_id", "name", "area_id", "lat", "lon", "sector", "source", "status"
    ],
    "capacity.csv": [
        "date", "hospital_id", "category", "nominal", "effective_low",
        "effective_high", "medicine_stock", "upper_cap_extra", "source", "status"
    ],
    "resources.csv": [
        "resource_id", "name", "unit", "area_id", "date_or_static", "nominal",
        "effective_low", "effective_high", "upper_cap_of_extra", "restock_rate", "source", "status"
    ],
    "risk_factors.csv": [
        "area_id", "sex", "age_band", "factor_id", "prevalence", "source", "status"
    ],
    "environment.csv": [
        "area_id", "safe_water_share", "improved_sanitation_share", "handwashing_facility_share",
        "persons_per_room", "informal_settlement_share", "clean_cooking_share", "green_space_share",
        "climate_zone", "extra", "source", "status"
    ],
    "comorbidity.csv": [
        "age_band", "sex", "condition", "prevalence", "source", "status"
    ],
    "observed_cases.csv": [
        "date", "positives", "hospitalized", "deaths", "source", "status"
    ],
    "policy_timeline.csv": [
        "date_start", "date_end", "measure", "stringency", "area_id", "source", "status"
    ],
    "sanitation.csv": [
        "area_id", "water_access_score", "drainage_coverage",
        "waste_collection_frequency", "source", "status"
    ]
}

# Example template rows for generating starter CSVs
TEMPLATE_EXAMPLES: Dict[str, List[Dict[str, str]]] = {
    "areas.csv": [
        {
            "area_id": "A01", "name": "North District", "level": "ward", "parent_id": "Z1",
            "population": "50000", "households": "12500", "area_km2": "5.2",
            "lat": "12.9716", "lon": "77.5946", "source": "synthetic_generator", "status": "synthetic"
        },
        {
            "area_id": "A02", "name": "South District", "level": "ward", "parent_id": "Z1",
            "population": "60000", "households": "15000", "area_km2": "6.8",
            "lat": "12.9352", "lon": "77.6245", "source": "synthetic_generator", "status": "synthetic"
        }
    ],
    "age_structure.csv": [
        {"area_id": "ALL", "sex": "M", "age_band": "0-4", "share": "0.04", "source": "synthetic_generator", "status": "synthetic"},
        {"area_id": "ALL", "sex": "F", "age_band": "0-4", "share": "0.04", "source": "synthetic_generator", "status": "synthetic"},
        {"area_id": "ALL", "sex": "M", "age_band": "5-18", "share": "0.12", "source": "synthetic_generator", "status": "synthetic"},
        {"area_id": "ALL", "sex": "F", "age_band": "5-18", "share": "0.12", "source": "synthetic_generator", "status": "synthetic"},
        {"area_id": "ALL", "sex": "M", "age_band": "19-64", "share": "0.30", "source": "synthetic_generator", "status": "synthetic"},
        {"area_id": "ALL", "sex": "F", "age_band": "19-64", "share": "0.30", "source": "synthetic_generator", "status": "synthetic"},
        {"area_id": "ALL", "sex": "M", "age_band": "65+", "share": "0.04", "source": "synthetic_generator", "status": "synthetic"},
        {"area_id": "ALL", "sex": "F", "age_band": "65+", "share": "0.04", "source": "synthetic_generator", "status": "synthetic"}
    ],
    "employment.csv": [
        {"area_id": "A01", "jobs": "25000", "employment_rate": "0.60", "sector_shares": "services:0.7,mfg:0.3", "source": "synthetic_generator", "status": "synthetic"},
        {"area_id": "A02", "jobs": "30000", "employment_rate": "0.62", "sector_shares": "services:0.8,mfg:0.2", "source": "synthetic_generator", "status": "synthetic"}
    ],
    "venues.csv": [
        {"area_id": "A01", "venue_type": "school", "count": "20", "mean_size": "300", "size_sd": "50", "source": "synthetic_generator", "status": "synthetic"},
        {"area_id": "A01", "venue_type": "workplace", "count": "150", "mean_size": "40", "size_sd": "20", "source": "synthetic_generator", "status": "synthetic"},
        {"area_id": "A02", "venue_type": "school", "count": "25", "mean_size": "320", "size_sd": "60", "source": "synthetic_generator", "status": "synthetic"},
        {"area_id": "A02", "venue_type": "workplace", "count": "180", "mean_size": "45", "size_sd": "25", "source": "synthetic_generator", "status": "synthetic"}
    ],
    "commute_od.csv": [
        {"from_area": "A01", "to_area": "A01", "share": "0.65", "source": "synthetic_generator", "status": "synthetic"},
        {"from_area": "A01", "to_area": "A02", "share": "0.35", "source": "synthetic_generator", "status": "synthetic"},
        {"from_area": "A02", "to_area": "A01", "share": "0.30", "source": "synthetic_generator", "status": "synthetic"},
        {"from_area": "A02", "to_area": "A02", "share": "0.70", "source": "synthetic_generator", "status": "synthetic"}
    ],
    "contacts.csv": [
        {"layer": "all", "age_band_i": "0-4", "age_band_j": "0-4", "contacts_per_day": "3.5", "source": "synthetic_generator", "status": "synthetic"},
        {"layer": "all", "age_band_i": "0-4", "age_band_j": "5-18", "contacts_per_day": "1.2", "source": "synthetic_generator", "status": "synthetic"},
        {"layer": "all", "age_band_i": "0-4", "age_band_j": "19-64", "contacts_per_day": "4.8", "source": "synthetic_generator", "status": "synthetic"},
        {"layer": "all", "age_band_i": "0-4", "age_band_j": "65+", "contacts_per_day": "0.8", "source": "synthetic_generator", "status": "synthetic"},
        {"layer": "all", "age_band_i": "5-18", "age_band_j": "5-18", "contacts_per_day": "8.5", "source": "synthetic_generator", "status": "synthetic"},
        {"layer": "all", "age_band_i": "5-18", "age_band_j": "19-64", "contacts_per_day": "5.0", "source": "synthetic_generator", "status": "synthetic"},
        {"layer": "all", "age_band_i": "5-18", "age_band_j": "65+", "contacts_per_day": "0.9", "source": "synthetic_generator", "status": "synthetic"},
        {"layer": "all", "age_band_i": "19-64", "age_band_j": "19-64", "contacts_per_day": "9.2", "source": "synthetic_generator", "status": "synthetic"},
        {"layer": "all", "age_band_i": "19-64", "age_band_j": "65+", "contacts_per_day": "1.5", "source": "synthetic_generator", "status": "synthetic"},
        {"layer": "all", "age_band_i": "65+", "age_band_j": "65+", "contacts_per_day": "2.8", "source": "synthetic_generator", "status": "synthetic"}
    ],
    "hospitals.csv": [
        {"hospital_id": "H01", "name": "General Hospital A", "area_id": "A01", "lat": "12.9720", "lon": "77.5950", "sector": "government", "source": "synthetic_generator", "status": "synthetic"},
        {"hospital_id": "H02", "name": "Community Hospital B", "area_id": "A02", "lat": "12.9360", "lon": "77.6250", "sector": "private", "source": "synthetic_generator", "status": "synthetic"}
    ],
    "capacity.csv": [
        {"date": "static", "hospital_id": "H01", "category": "general", "nominal": "100", "effective_low": "80", "effective_high": "110", "medicine_stock": "adequate", "upper_cap_extra": "25", "source": "synthetic_generator", "status": "synthetic"},
        {"date": "static", "hospital_id": "H01", "category": "icu", "nominal": "15", "effective_low": "12", "effective_high": "18", "medicine_stock": "adequate", "upper_cap_extra": "5", "source": "synthetic_generator", "status": "synthetic"},
        {"date": "static", "hospital_id": "H02", "category": "general", "nominal": "120", "effective_low": "100", "effective_high": "130", "medicine_stock": "adequate", "upper_cap_extra": "30", "source": "synthetic_generator", "status": "synthetic"},
        {"date": "static", "hospital_id": "H02", "category": "icu", "nominal": "20", "effective_low": "15", "effective_high": "22", "medicine_stock": "adequate", "upper_cap_extra": "8", "source": "synthetic_generator", "status": "synthetic"}
    ],
    "resources.csv": [
        {"resource_id": "res_bed", "name": "Clinical Care Bed", "unit": "beds", "area_id": "A01", "date_or_static": "static", "nominal": "100", "effective_low": "80", "effective_high": "110", "upper_cap_of_extra": "25", "restock_rate": "0", "source": "synthetic_generator", "status": "synthetic"},
        {"resource_id": "res_bed", "name": "Clinical Care Bed", "unit": "beds", "area_id": "A02", "date_or_static": "static", "nominal": "120", "effective_low": "100", "effective_high": "130", "upper_cap_of_extra": "30", "restock_rate": "0", "source": "synthetic_generator", "status": "synthetic"},
        {"resource_id": "res_support", "name": "Respiratory Support Unit", "unit": "units", "area_id": "A01", "date_or_static": "static", "nominal": "20", "effective_low": "15", "effective_high": "25", "upper_cap_of_extra": "10", "restock_rate": "2", "source": "synthetic_generator", "status": "synthetic"},
        {"resource_id": "res_support", "name": "Respiratory Support Unit", "unit": "units", "area_id": "A02", "date_or_static": "static", "nominal": "25", "effective_low": "20", "effective_high": "30", "upper_cap_of_extra": "10", "restock_rate": "2", "source": "synthetic_generator", "status": "synthetic"}
    ],
    "risk_factors.csv": [
        {"area_id": "ALL", "sex": "M", "age_band": "19-64", "factor_id": "hypertension", "prevalence": "0.22", "source": "synthetic_generator", "status": "synthetic"},
        {"area_id": "ALL", "sex": "F", "age_band": "19-64", "factor_id": "hypertension", "prevalence": "0.19", "source": "synthetic_generator", "status": "synthetic"},
        {"area_id": "ALL", "sex": "M", "age_band": "65+", "factor_id": "hypertension", "prevalence": "0.45", "source": "synthetic_generator", "status": "synthetic"},
        {"area_id": "ALL", "sex": "F", "age_band": "65+", "factor_id": "hypertension", "prevalence": "0.42", "source": "synthetic_generator", "status": "synthetic"},
        {"area_id": "ALL", "sex": "M", "age_band": "65+", "factor_id": "respiratory_chronic", "prevalence": "0.20", "source": "synthetic_generator", "status": "synthetic"},
        {"area_id": "ALL", "sex": "F", "age_band": "65+", "factor_id": "respiratory_chronic", "prevalence": "0.18", "source": "synthetic_generator", "status": "synthetic"}
    ],
    "environment.csv": [
        {"area_id": "A01", "safe_water_share": "0.92", "improved_sanitation_share": "0.88", "handwashing_facility_share": "0.85", "persons_per_room": "1.4", "informal_settlement_share": "0.08", "clean_cooking_share": "0.89", "green_space_share": "0.22", "climate_zone": "temperate", "extra": "{}", "source": "synthetic_generator", "status": "synthetic"},
        {"area_id": "A02", "safe_water_share": "0.78", "improved_sanitation_share": "0.72", "handwashing_facility_share": "0.68", "persons_per_room": "2.2", "informal_settlement_share": "0.25", "clean_cooking_share": "0.70", "green_space_share": "0.12", "climate_zone": "temperate", "extra": "{}", "source": "synthetic_generator", "status": "synthetic"}
    ],
    "comorbidity.csv": [
        {"age_band": "19-64", "sex": "M", "condition": "hypertension", "prevalence": "0.22", "source": "synthetic_generator", "status": "synthetic"},
        {"age_band": "19-64", "sex": "F", "condition": "hypertension", "prevalence": "0.19", "source": "synthetic_generator", "status": "synthetic"},
        {"age_band": "65+", "sex": "M", "condition": "diabetes", "prevalence": "0.35", "source": "synthetic_generator", "status": "synthetic"},
        {"age_band": "65+", "sex": "F", "condition": "diabetes", "prevalence": "0.32", "source": "synthetic_generator", "status": "synthetic"}
    ],
    "observed_cases.csv": [
        {"date": "2024-01-01", "positives": "10", "hospitalized": "2", "deaths": "0", "source": "synthetic_generator", "status": "synthetic"},
        {"date": "2024-01-02", "positives": "15", "hospitalized": "3", "deaths": "0", "source": "synthetic_generator", "status": "synthetic"}
    ],
    "policy_timeline.csv": [
        {"date_start": "2024-01-10", "date_end": "2024-01-25", "measure": "school_closure", "stringency": "1.0", "area_id": "ALL", "source": "synthetic_generator", "status": "synthetic"}
    ],
    "sanitation.csv": [
        {"area_id": "A01", "water_access_score": "0.90", "drainage_coverage": "0.85", "waste_collection_frequency": "0.95", "source": "synthetic_generator", "status": "synthetic"},
        {"area_id": "A02", "water_access_score": "0.75", "drainage_coverage": "0.70", "waste_collection_frequency": "0.80", "source": "synthetic_generator", "status": "synthetic"}
    ]
}


def get_template_csv(filename: str) -> str:
    """Generate CSV content for a specific template."""
    if filename not in CSV_CONTRACTS:
        raise ValueError(f"Unknown template file: {filename}")

    headers = CSV_CONTRACTS[filename]
    lines = [",".join(headers)]
    rows = TEMPLATE_EXAMPLES.get(filename, [])
    for row in rows:
        row_values = [str(row.get(h, "")) for h in headers]
        lines.append(",".join(row_values))

    return "\n".join(lines) + "\n"

