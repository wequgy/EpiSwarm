"""Tests for EpiSwarm Studio v2 Stage S2: Case Files, Provenance, and Demo Modes."""

import json
import os
import tempfile
import zipfile
import pytest
from fastapi.testclient import TestClient
from episwarm.api.main import app
from episwarm.service.case_file import CaseFileService, CaseFileManifest
from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.engine.sim import run_simulation
import yaml

client = TestClient(app)


def test_preloaded_demos_exist():
    """Verify London Wave 1 and Sandbox preloaded demos exist with DEMO flags."""
    svc = CaseFileService()
    files = svc.list_case_files()
    file_ids = [f["id"] for f in files]

    assert "case_london_wave1" in file_ids
    assert "case_sandbox" in file_ids

    london = svc.get_case_file("case_london_wave1")
    assert london.is_demo is True
    assert london.completeness == 1.0
    assert "area_population.total_population" in london.evidence_ledger
    assert london.evidence_ledger["area_population.total_population"].evidence_class == "sourced"

    sandbox = svc.get_case_file("case_sandbox")
    assert sandbox.is_demo is True
    assert sandbox.sections["area_population"]["total_population"] == 10000


def test_official_intake_workflow():
    """Verify an authority officer can create a case file, update sections, and track completeness."""
    res = client.post("/api/v2/case-files", json={
        "title": "Metropolitan District Health Case",
        "description": "Autumn 2026 surveillance readiness",
        "author": "Chief Medical Officer"
    })
    assert res.status_code == 200
    case_data = res.json()
    case_id = case_data["id"]
    assert case_data["is_demo"] is False

    # Update Area and Population section
    up_res = client.put(f"/api/v2/case-files/{case_id}/sections/area_population", json={
        "data": {
            "region_name": "Metro North",
            "total_population": 450000,
            "areas": [
                {"id": "north_core", "name": "North Core", "population": 250000},
                {"id": "north_suburbs", "name": "North Suburbs", "population": 200000}
            ]
        },
        "user": "Dr. Aris (Epidemiologist)"
    })
    assert up_res.status_code == 200
    updated_manifest = up_res.json()
    assert updated_manifest["sections"]["area_population"]["total_population"] == 450000
    assert updated_manifest["sections"]["area_population"]["is_complete"] is True
    assert updated_manifest["completeness"] > 0.125

    # Check audit log recorded officer action
    audit = updated_manifest["audit_log"]
    assert any(a["user"] == "Dr. Aris (Epidemiologist)" and "AREA_POPULATION" in a["action"] for a in audit)


def test_csv_upload_and_evidence_ledger():
    """Verify uploaded CSV is checksummed with SHA-256 and recorded as user_supplied."""
    svc = CaseFileService()
    case = svc.create_case_file(title="Upload Test Case")
    case_id = case.id

    csv_content = b"hospital_name,acute_beds,icu_beds\nCentral General,350,30\nEast Clinic,120,10\n"
    res = client.post(
        f"/api/v2/case-files/{case_id}/upload",
        data={
            "section_key": "health_system",
            "column_mapping": json.dumps({"acute_beds": "beds", "icu_beds": "icu"})
        },
        files={"file": ("hospitals_input.csv", csv_content, "text/csv")}
    )
    assert res.status_code == 200
    upload_res = res.json()
    assert upload_res["evidence_class"] == "user_supplied"
    assert "sha256" in upload_res

    # Check manifest updated with user_supplied entry
    case_updated = svc.get_case_file(case_id)
    ledger_entry = case_updated.evidence_ledger.get("health_system.import_hospitals_input.csv")
    assert ledger_entry is not None
    assert ledger_entry.evidence_class == "user_supplied"
    assert ledger_entry.checksum == upload_res["sha256"]


def test_duplicate_and_lock_case_file():
    """Verify duplication and version locking before simulation execution."""
    res_dup = client.post("/api/v2/case-files/case_sandbox/duplicate", json={
        "new_title": "Custom Sandbox Branch"
    })
    assert res_dup.status_code == 200
    new_case = res_dup.json()
    new_id = new_case["id"]
    assert new_case["is_demo"] is False
    assert new_case["title"] == "Custom Sandbox Branch"

    # Lock version for a run
    res_lock = client.post(f"/api/v2/case-files/{new_id}/lock", json={
        "run_id": "run_test_lock_001"
    })
    assert res_lock.status_code == 200
    locked_case = res_lock.json()
    assert locked_case["locked"] is True
    assert locked_case["locked_run_id"] == "run_test_lock_001"

    # Export bundle and verify checksums.sha256 inside zip
    res_export = client.get(f"/api/v2/case-files/{new_id}/export")
    assert res_export.status_code == 200
    zip_bytes = res_export.content
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(zip_bytes)
        tmp_name = tmp.name

    try:
        with zipfile.ZipFile(tmp_name, "r") as z:
            names = z.namelist()
            assert "case_file.json" in names
            assert "checksums.sha256" in names
            checksum_data = z.read("checksums.sha256").decode("utf-8")
            assert "case_file.json" in checksum_data
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def test_launch_simulation_from_case_file():
    """Verify simulation engine launches correctly using parameters derived from a Case File."""
    svc = CaseFileService()
    case = svc.get_case_file("case_sandbox")
    run_settings = case.sections["run_settings"]

    # Build population using case file scale
    pop = build_synthetic_population("regions/example_synthetic", scale_agents=run_settings["scale_agents"], random_seed=run_settings["seed"])
    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        d_pack = DiseasePack(**yaml.safe_load(f))
    with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
        s_pack = ScenarioPack(**yaml.safe_load(f))

    # Override target R0 from case file disease section
    d_pack.transmission.r0 = case.sections["disease"]["target_r0"]

    results = run_simulation(pop, d_pack, s_pack)
    assert results.n_agents == run_settings["scale_agents"]
    assert results.target_r0 == case.sections["disease"]["target_r0"]
    assert results.daily_state_counts.shape[0] == s_pack.horizon_days
