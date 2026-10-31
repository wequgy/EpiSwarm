"""Unit and invariant tests for Phase 1: population synthesis, IPF, venues, and L0 builder."""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from episwarm.packs.region import RegionMeta, L0QuickInputs
from episwarm.importers.quick_region import QuickRegionBuilder
from episwarm.importers.mapper import ColumnMapper
from episwarm.population.ipf import run_ipf_2d, run_ipf_3d
from episwarm.population.build import build_synthetic_population, PopulationSoA


def test_ipf_convergence_2d():
    # Target marginals
    row_targets = np.array([100.0, 200.0, 300.0])
    col_targets = np.array([150.0, 450.0])
    table = run_ipf_2d(row_targets, col_targets)

    # Check rows match within numerical tolerance
    np.testing.assert_allclose(table.sum(axis=1), row_targets, rtol=1e-5)
    np.testing.assert_allclose(table.sum(axis=0), col_targets, rtol=1e-5)


def test_column_mapper_suggestions_and_apply():
    user_cols = ["Ward_ID", "Residents", "Latitude", "Longitude", "Random_Extra"]
    suggested = ColumnMapper.suggest_mapping("areas.csv", user_cols)

    assert suggested.get("area_id") == "Ward_ID"
    assert suggested.get("population") == "Residents"
    assert suggested.get("lat") == "Latitude"
    assert suggested.get("lon") == "Longitude"

    df_raw = pd.DataFrame({
        "Ward_ID": ["W1", "W2"],
        "Residents": [1000, 2000],
        "Latitude": [12.1, 12.2],
        "Longitude": [77.1, 77.2]
    })
    mapped_df = ColumnMapper.apply_mapping(df_raw, "areas.csv", suggested)
    assert "area_id" in mapped_df.columns
    assert "population" in mapped_df.columns
    assert "status" in mapped_df.columns
    assert mapped_df["status"].iloc[0] == "user_supplied"


def test_quick_region_l0_generation(tmp_path):
    meta = RegionMeta(
        name="test_quick_region",
        country_iso="SYN",
        data_year=2024,
        area_levels=["ward", "zone"]
    )
    inputs = L0QuickInputs(
        total_population=50000,
        num_areas=4,
        avg_household_size=4.0,
        employment_rate=0.60,
        beds_per_1000=2.0
    )
    builder = QuickRegionBuilder(meta, inputs)
    builder.generate_all(tmp_path)

    assert (tmp_path / "region.yaml").exists()
    assert (tmp_path / "areas.csv").exists()
    assert (tmp_path / "venues.csv").exists()
    assert (tmp_path / "commute_od.csv").exists()

    df_areas = pd.read_csv(tmp_path / "areas.csv")
    assert len(df_areas) == 4
    assert df_areas["population"].sum() == 50000


@pytest.mark.parametrize("scale", [5000, 50000, 100000])
def test_population_scale_and_area_conservation(scale):
    """Area totals must match within 1% at 5k, 50k, and 100k agents."""
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=scale, random_seed=42)

    assert pop.n_agents == scale
    assert len(pop.agent_id) == scale
    assert len(pop.area_id) == scale

    # Check conservation across areas: relative error <= 1%
    areas_df = pd.read_csv("regions/example_synthetic/areas.csv")
    total_real = areas_df["population"].sum()

    for _, row in areas_df.iterrows():
        aid_str = str(row["area_id"])
        aid_int = pop.area_id_to_int[aid_str]
        actual_agents = np.sum(pop.area_id == aid_int)
        expected_pop = row["population"]
        represented_pop = actual_agents * pop.sampling_ratio

        rel_error = abs(represented_pop - expected_pop) / expected_pop
        assert rel_error <= 0.01, f"Area {aid_str} rel error {rel_error:.4f} exceeds 1% at scale {scale}"


def test_household_adult_invariant():
    """Every household must have at least one adult (age >= 18)."""
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=10000, random_seed=123)

    h_ids = pop.household_id
    ages = pop.age

    unique_h = np.unique(h_ids)
    for hid in unique_h:
        members_age = ages[h_ids == hid]
        has_adult = np.any(members_age >= 18)
        assert has_adult, f"Household {hid} contains no adults! Ages: {members_age}"


def test_reproducibility():
    """Identical seed produces bit-exact arrays."""
    pop1 = build_synthetic_population("regions/example_synthetic", scale_agents=5000, random_seed=999)
    pop2 = build_synthetic_population("regions/example_synthetic", scale_agents=5000, random_seed=999)

    np.testing.assert_array_equal(pop1.age, pop2.age)
    np.testing.assert_array_equal(pop1.area_id, pop2.area_id)
    np.testing.assert_array_equal(pop1.household_id, pop2.household_id)
    np.testing.assert_array_equal(pop1.workplace_id, pop2.workplace_id)
    np.testing.assert_array_equal(pop1.compliance, pop2.compliance)

