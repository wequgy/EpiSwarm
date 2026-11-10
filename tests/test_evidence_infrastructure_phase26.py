"""Unit tests and acceptance verification for Evidence Infrastructure (Phase 26).

Verifies:
1. Evidence Ledger (SQLite CRUD, SHA-256 hashing, Parquet export).
2. Fetch Downloader (exclusive real data registrar; rejects non-200/zero-byte responses).
3. Hard Loader Gate (rejects unverified 'real' datasets; accepts verified ones).
4. Validation Controls (Positive control passes 100%; Negative control fails 100%).
5. Held-Out Gate (requires committed PROTOCOL hash; detects retuning).
6. Spot-Check Checklist Generator (5 deterministic pseudo-random samples per dataset).
"""

import json
from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
import pytest
import yaml

from episwarm.evidence.ledger import EvidenceLedger, LedgerRecord, compute_sha256
from episwarm.evidence.fetch import fetch_and_register, DownloadIntegrityError
from episwarm.evidence.gate import verify_real_dataset, IntegrityGateError
from episwarm.evidence.held_out import HeldOutGate, HeldOutGateError
from episwarm.evidence.spot_check import generate_spot_check_checklist
from episwarm.evidence.validation_controls import (
    run_positive_control,
    run_negative_control,
    render_markdown_report_from_card
)
from episwarm.importers.validate import validate_region_pack


@pytest.fixture
def temp_ledger(tmp_path):
    db_file = tmp_path / "test_ledger.db"
    return EvidenceLedger(db_path=db_file)


def test_evidence_ledger_crud_and_parquet(temp_ledger, tmp_path):
    """Test ledger insertion, lookup by hash/url, and Parquet export."""
    # 1. Create a dummy data file
    dummy_file = tmp_path / "ons_cases.csv"
    dummy_file.write_text("date,cases\n2020-03-01,15\n2020-03-02,22\n", encoding="utf-8")
    file_hash = compute_sha256(dummy_file)

    rec = LedgerRecord(
        id=f"rec_{file_hash[:16]}",
        url="https://api.coronavirus.data.gov.uk/v2/data?cases",
        retrieved_at="2026-11-10T12:00:00Z",
        sha256=file_hash,
        byte_count=dummy_file.stat().st_size,
        http_status=200,
        content_type="text/csv",
        license="Open Government Licence v3.0",
        file_path=str(dummy_file),
        record_status="verified",
        notes="Official UKHSA clinical surveillance download"
    )
    temp_ledger.add_record(rec)

    # 2. Lookups
    found_by_hash = temp_ledger.get_by_sha256(file_hash)
    assert found_by_hash is not None
    assert found_by_hash.url == rec.url
    assert found_by_hash.sha256 == file_hash

    found_by_url = temp_ledger.get_by_url(rec.url)
    assert found_by_url is not None
    assert found_by_url.id == rec.id

    # 3. File verification helper
    verified_rec = temp_ledger.verify_file(dummy_file)
    assert verified_rec is not None
    assert verified_rec.sha256 == file_hash

    # 4. Parquet export
    pq_path = tmp_path / "ledger_archive.parquet"
    res_path = temp_ledger.export_parquet(pq_path)
    assert res_path.exists()
    df_pq = pd.read_parquet(res_path)
    assert len(df_pq) == 1
    assert df_pq.iloc[0]["sha256"] == file_hash


def test_loader_gate_rejects_fake_real_file(temp_ledger, tmp_path):
    """Demonstrate that loader gate categorically rejects unverified files claiming status: real."""
    # 1. Create an unverified file claiming 'status: real'
    fake_real_file = tmp_path / "observed_cases.csv"
    fake_real_file.write_text("date,hospitalized,status\n2020-03-01,100,real\n", encoding="utf-8")

    # Gate MUST raise IntegrityGateError because it is NOT in the ledger
    with pytest.raises(IntegrityGateError) as exc_info:
        verify_real_dataset(fake_real_file, ledger=temp_ledger)
    assert "has NO verified entry" in str(exc_info.value)

    # 2. Test RegionPack validator rejection
    region_dir = tmp_path / "test_fake_region"
    region_dir.mkdir()
    (region_dir / "region.yaml").write_text("""
meta:
  name: fake_region
  country_iso: GBR
  data_year: 2020
  data_level: L1
  area_levels: ["borough"]
""", encoding="utf-8")

    (region_dir / "areas.csv").write_text("area_id,name,population,status\nA1,Borough1,100000,real\n", encoding="utf-8")

    # validate_region_pack should reject with UNVERIFIED_REAL_REJECTED
    report = validate_region_pack(region_dir)
    assert report.is_valid is False
    assert report.file_statuses.get("areas.csv") == "UNVERIFIED_REAL_REJECTED"
    assert any("Evidence Gate Error" in err.message for err in report.errors)

    # 3. Now legitimately register the file in the ledger
    file_hash = compute_sha256(region_dir / "areas.csv")
    temp_ledger.add_record(LedgerRecord(
        id=f"rec_{file_hash[:16]}",
        url="https://data.gov.uk/dataset/mid-2020-population",
        retrieved_at="2026-11-10T12:00:00Z",
        sha256=file_hash,
        byte_count=(region_dir / "areas.csv").stat().st_size,
        http_status=200,
        content_type="text/csv",
        license="OGL-3.0",
        file_path=str(region_dir / "areas.csv"),
        record_status="verified"
    ))

    # Re-verify through gate with the ledger:
    verified = verify_real_dataset(region_dir / "areas.csv", ledger=temp_ledger)
    assert verified is not None
    assert verified.sha256 == file_hash


def test_validation_controls_positive_and_negative():
    """Verify validation controls: Positive control passes 100%, Negative control fails 100%."""
    # Synthetic epidemic wave curve
    t = np.arange(60)
    synthetic_admissions = 500.0 * np.exp(-((t - 25) / 8.0) ** 2)

    # 1. Positive Control: model evaluated against itself
    pos_card = run_positive_control(synthetic_admissions)
    assert pos_card.all_passed is True
    assert pos_card.status == "VALIDATED"
    assert pos_card.targets_passed == "1/1"

    pos_report = render_markdown_report_from_card(pos_card)
    assert "**PASS**" in pos_report
    assert "**FAIL**" not in pos_report
    assert "**VALIDATED**" in pos_report

    # 2. Negative Control: model evaluated against inverted/shuffled curve
    neg_card = run_negative_control(synthetic_admissions)
    assert neg_card.all_passed is False
    assert neg_card.status == "FAILED"
    assert neg_card.targets_passed == "0/1"

    neg_report = render_markdown_report_from_card(neg_card)
    assert "**FAIL**" in neg_report
    assert "**PASS**" not in neg_report
    assert "**FAILED**" in neg_report


def test_held_out_gate_enforcement(tmp_path):
    """Verify held-out gate protocol hashing and retuning detection."""
    protocol_file = tmp_path / "PROTOCOL.md"
    protocol_file.write_text("# Pre-Registration Protocol v1.0\nWindow: Wave 2", encoding="utf-8")
    protocol_hash = compute_sha256(protocol_file)

    log_file = tmp_path / "held_out_log.jsonl"
    data_file = tmp_path / "wave2_held_out.csv"
    data_file.write_text("date,cases\n2020-09-01,50\n", encoding="utf-8")

    gate = HeldOutGate(log_path=log_file, protocol_path=protocol_file)

    # 1. Access with wrong protocol hash MUST fail
    with pytest.raises(HeldOutGateError) as exc_info:
        gate.load_held_out_dataset(
            file_path=data_file,
            expected_protocol_hash="0000000000000000000000000000000000000000000000000000000000000000",
            model_version="v1.0",
            held_out_window="Wave 2",
            parameters={"R0": 2.5}
        )
    assert "Protocol mismatch" in str(exc_info.value)

    # 2. First legitimate access
    df1, rec1 = gate.load_held_out_dataset(
        file_path=data_file,
        expected_protocol_hash=protocol_hash,
        model_version="v1.0",
        held_out_window="Wave 2",
        parameters={"R0": 2.5}
    )
    assert len(df1) == 1
    assert rec1.status == "FIRST_EVALUATION"

    # 3. Repeated access with retuned parameters MUST be flagged as RETUNED
    df2, rec2 = gate.load_held_out_dataset(
        file_path=data_file,
        expected_protocol_hash=protocol_hash,
        model_version="v1.1",
        held_out_window="Wave 2",
        parameters={"R0": 2.8}  # Tuned parameter
    )
    assert rec2.status == "RETUNED"


def test_spot_check_checklist_generator(temp_ledger, tmp_path):
    """Verify spot-check checklist generator samples 5 deterministic points per file."""
    # Create test dataset with 20 rows
    dataset_file = tmp_path / "test_spot_dataset.csv"
    rows = [{"day": i, "cases": i * 10, "status": "synthetic"} for i in range(20)]
    pd.DataFrame(rows).to_csv(dataset_file, index=False)

    checklist_md = generate_spot_check_checklist([dataset_file], ledger=temp_ledger, samples_per_file=5, seed=42)
    assert "# Empirical Data Spot-Check Verification Checklist" in checklist_md
    assert "test_spot_dataset.csv" in checklist_md
    assert checklist_md.count("[ ] Pending Auditor Match") == 5


def test_fetch_and_register_downloader(temp_ledger, tmp_path, monkeypatch):
    """Verify fetch_and_register: streams bytes, computes hash, handles errors, commits to ledger."""
    dest_file = tmp_path / "fetched_data.csv"

    class MockResponse:
        def __init__(self, status_code, content):
            self.status_code = status_code
            self.headers = {"content-type": "text/csv"}
            self._content = content

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def iter_bytes(self, chunk_size=65536):
            yield self._content

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def stream(self, method, url, **kwargs):
            if "error500" in url:
                return MockResponse(500, b"Server Error")
            if "zerobytes" in url:
                return MockResponse(200, b"")
            return MockResponse(200, b"area_id,pop\nA1,5000\n")

    import httpx
    monkeypatch.setattr(httpx, "Client", MockClient)

    # 1. Successful download registers in ledger
    rec = fetch_and_register(
        url="https://api.example.gov/data.csv",
        dest_path=dest_file,
        license_name="OGL-3.0",
        notes="Mock test download",
        ledger=temp_ledger
    )
    assert rec.http_status == 200
    assert rec.byte_count == len(b"area_id,pop\nA1,5000\n")
    assert dest_file.exists()

    # Verified in ledger
    ledger_rec = temp_ledger.get_by_sha256(rec.sha256)
    assert ledger_rec is not None
    assert ledger_rec.url == "https://api.example.gov/data.csv"

    # 2. HTTP 500 raises DownloadIntegrityError and does NOT create file or record
    err_dest = tmp_path / "err_data.csv"
    with pytest.raises(DownloadIntegrityError):
        fetch_and_register(
            url="https://api.example.gov/error500",
            dest_path=err_dest,
            license_name="OGL-3.0",
            ledger=temp_ledger
        )
    assert not err_dest.exists()

    # 3. Zero-byte response raises DownloadIntegrityError
    zero_dest = tmp_path / "zero_data.csv"
    with pytest.raises(DownloadIntegrityError):
        fetch_and_register(
            url="https://api.example.gov/zerobytes",
            dest_path=zero_dest,
            license_name="OGL-3.0",
            ledger=temp_ledger
        )
    assert not zero_dest.exists()

def test_import_linter_bans_tuning_packages_from_importing_held_out():
    """Verify architectural isolation: tuning, optimizer, and analysis modules must NOT import held_out."""
    import ast

    forbidden_roots = [
        Path("src/episwarm/analysis"),
        Path("src/episwarm/advisor"),
        Path("src/episwarm/optimize"),
        Path("src/episwarm/engine")
    ]

    for root_dir in forbidden_roots:
        if not root_dir.exists():
            continue
        for py_file in root_dir.rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "held_out" not in alias.name, f"Forbidden held_out import in {py_file}: {alias.name}"
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    assert "held_out" not in mod, f"Forbidden held_out import in {py_file}: from {mod} import ..."
