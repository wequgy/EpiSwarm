"""Validation tests for Empirical Reference Pack (Phase 27)."""

from pathlib import Path
import pandas as pd
import pytest

from episwarm.importers.validate import validate_region_pack
from episwarm.population.build import build_synthetic_population
from episwarm.evidence.ledger import EvidenceLedger


def test_reference_pack_contract_and_ledger_gate():
    """Verify that regions/reference_london passes all data contracts and is verified by the ledger gate."""
    pack_dir = Path("regions/reference_london")
    assert pack_dir.exists() and pack_dir.is_dir()

    report = validate_region_pack(pack_dir)
    print("\n" + report.summary_table())

    assert report.is_valid is True
    assert len(report.errors) == 0

    # Ensure all empirical files carry REAL status and are authenticated
    expected_real = ["areas.csv", "age_structure.csv", "commute_od.csv", "contacts.csv", "observed_cases.csv", "policy_timeline.csv"]
    for fname in expected_real:
        assert report.file_statuses.get(fname) == "REAL", f"Expected verified REAL for {fname}"


def test_reference_population_synthesis():
    """Verify synthetic population generation from genuine ONS demographics."""
    pack_dir = "regions/reference_london"
    scale_agents = 2000
    pop = build_synthetic_population(pack_dir, scale_agents=scale_agents, random_seed=42)

    assert pop.n_agents == scale_agents
    assert len(pop.int_to_area_id) == 33  # All 33 London Local Authorities
    assert pop.total_population_represented > 8_000_000
    assert len(pop.area_id) == scale_agents
    assert len(pop.age) == scale_agents


def test_empirical_observed_cases_fidelity():
    """Verify that observed_cases.csv contains genuine UKHSA/ONS clinical surveillance numbers."""
    obs_path = Path("regions/reference_london/observed_cases.csv")
    df = pd.read_csv(obs_path)

    # Check official ONS Wave 1 Peak Mortality: 2020-04-08 with 327 registered deaths
    peak_row = df.loc[df["deaths"].idxmax()]
    assert peak_row["date"] == "2020-04-08"
    assert int(peak_row["deaths"]) == 327

    # Check that status is verified real
    assert (df["status"] == "real").all()

