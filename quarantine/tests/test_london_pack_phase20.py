"""Unit tests and validation checks for Greater London RegionPack (Phase 20)."""

from pathlib import Path
import numpy as np
import pytest
import yaml

from episwarm.importers.validate import validate_region_pack
from episwarm.packs.region import RegionPack
from episwarm.population.build import build_synthetic_population


def test_london_region_contract_validation():
    """Verify that regions/london passes all contract validations with 100% REAL files."""
    region_dir = Path("regions/london")
    assert region_dir.exists() and region_dir.is_dir()

    report = validate_region_pack(region_dir)
    print("\n" + report.summary_table())

    assert report.is_valid is True
    assert len(report.errors) == 0

    # Ensure every single required CSV is present and classified as REAL
    expected_real = [
        "areas.csv", "age_structure.csv", "commute_od.csv", "contacts.csv",
        "hospitals.csv", "capacity.csv", "resources.csv", "venues.csv",
        "employment.csv", "environment.csv", "comorbidity.csv", "risk_factors.csv",
        "policy_timeline.csv", "observed_cases.csv", "sanitation.csv"
    ]
    for fname in expected_real:
        assert report.file_statuses.get(fname) == "REAL", f"Expected REAL status for {fname}, got {report.file_statuses.get(fname)}"

    assert report.file_statuses.get("region.yaml") == "VALID"


def test_london_population_synthesis():
    """Verify that build_synthetic_population can successfully synthesize agents from regions/london."""
    region_dir = "regions/london"
    scale_agents = 2000
    pop = build_synthetic_population(region_dir, scale_agents=scale_agents, random_seed=42)

    assert pop.n_agents == scale_agents
    assert len(pop.int_to_area_id) == 33  # All 33 London Boroughs
    assert pop.total_population_represented > 8_000_000
    assert len(pop.area_id) == scale_agents
    assert np.all(pop.area_id >= 0) and np.all(pop.area_id < 33)

    # Check age structure bounds
    assert np.all(pop.age >= 0) and np.all(pop.age <= 105)


def test_london_metadata_parsing():
    """Verify RegionPack metadata schema compliance."""
    yaml_path = Path("regions/london/region.yaml")
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    pack = RegionPack(**data)

    assert pack.meta.name == "london"
    assert pack.meta.country_iso == "GBR"
    assert pack.meta.data_year == 2020
    assert pack.meta.data_level.value == "L2"
    assert pack.meta.area_levels == ["borough", "region"]
