"""Real Data Acquisition Script for Empirical Reference Pack (Phase 27).

Downloads verified empirical datasets using episwarm.evidence.fetch, computes cryptographic
digests, and registers them into the Evidence Ledger.
"""

from pathlib import Path
import json
import httpx

from episwarm.evidence.fetch import fetch_and_register
from episwarm.evidence.ledger import EvidenceLedger


def acquire_reference_datasets():
    ledger = EvidenceLedger()
    raw_dir = Path("evidence/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)

    print("=== Acquiring Genuine Empirical Datasets for Reference Pack ===")

    # 1. Zenodo CoMix Age-Structured Social Contact Matrix for England (LSHTM / Prem et al.)
    comix_url = "https://zenodo.org/api/records/4677018/files/contact_matrices_9_periods.csv/content"
    comix_dest = raw_dir / "comix_contact_matrices_england.csv"
    print(f"\n1. Fetching CoMix Contact Survey from Zenodo: {comix_url}")
    r1 = fetch_and_register(
        url=comix_url,
        dest_path=comix_dest,
        license_name="Creative Commons Attribution 4.0 International (CC-BY-4.0)",
        notes="Empirical longitudinal contact matrices across 9 pandemic periods in England (LSHTM / Jarvis et al.)",
        ledger=ledger
    )
    print(f"   Saved: {r1.file_path} ({r1.byte_count} bytes, SHA-256: {r1.sha256[:16]}...)")

    # 2. UKHSA Data Dashboard API: ONS Registered COVID-19 Deaths for London (2020)
    deaths_url = "https://api.ukhsa-dashboard.data.gov.uk/themes/infectious_disease/sub_themes/respiratory/topics/COVID-19/geography_types/Government%20Office%20Region/geographies/London/metrics/COVID-19_deaths_ONSByDay?page_size=365&year=2020"
    deaths_dest = raw_dir / "ukhsa_london_deaths_2020.json"
    print(f"\n2. Fetching London ONS Daily Registered Deaths from UKHSA API: {deaths_url}")
    r2 = fetch_and_register(
        url=deaths_url,
        dest_path=deaths_dest,
        license_name="Open Government Licence v3.0 (OGL-3.0)",
        notes="Official ONS registered COVID-19 deaths by day for London Government Office Region in 2020",
        ledger=ledger
    )
    print(f"   Saved: {r2.file_path} ({r2.byte_count} bytes, SHA-256: {r2.sha256[:16]}...)")

    # 3. UKHSA Data Dashboard API: NHS Region London Daily Hospital Admissions (2020)
    admissions_url = "https://api.ukhsa-dashboard.data.gov.uk/themes/infectious_disease/sub_themes/respiratory/topics/COVID-19/geography_types/NHS%20Region/geographies/London/metrics/COVID-19_healthcare_admissionByDay?page_size=365&year=2020"
    admissions_dest = raw_dir / "ukhsa_london_admissions_2020.json"
    print(f"\n3. Fetching London NHS Daily Hospital Admissions from UKHSA API: {admissions_url}")
    r3 = fetch_and_register(
        url=admissions_url,
        dest_path=admissions_dest,
        license_name="Open Government Licence v3.0 (OGL-3.0)",
        notes="Official NHS COVID-19 hospital admissions by day for London NHS Region in 2020",
        ledger=ledger
    )
    print(f"   Saved: {r3.file_path} ({r3.byte_count} bytes, SHA-256: {r3.sha256[:16]}...)")

    # 4. UKHSA Data Dashboard API: NHS Region London Occupied Beds by Day (2020)
    beds_url = "https://api.ukhsa-dashboard.data.gov.uk/themes/infectious_disease/sub_themes/respiratory/topics/COVID-19/geography_types/NHS%20Region/geographies/London/metrics/COVID-19_healthcare_occupiedBedsByDay?page_size=365&year=2020"
    beds_dest = raw_dir / "ukhsa_london_occupied_beds_2020.json"
    print(f"\n4. Fetching London NHS Daily Occupied Beds from UKHSA API: {beds_url}")
    r4 = fetch_and_register(
        url=beds_url,
        dest_path=beds_dest,
        license_name="Open Government Licence v3.0 (OGL-3.0)",
        notes="Official NHS COVID-19 occupied beds by day for London NHS Region in 2020",
        ledger=ledger
    )
    print(f"   Saved: {r4.file_path} ({r4.byte_count} bytes, SHA-256: {r4.sha256[:16]}...)")

    # 5. Oxford COVID-19 Government Response Tracker (OxCGRT) Compact Subnational Policies
    oxcgrt_url = "https://raw.githubusercontent.com/OxCGRT/covid-policy-dataset/main/data/OxCGRT_compact_subnational_v1.csv"
    oxcgrt_dest = raw_dir / "oxcgrt_compact_subnational_v1.csv"
    print(f"\n5. Fetching OxCGRT Policy Dataset from GitHub: {oxcgrt_url}")
    r5 = fetch_and_register(
        url=oxcgrt_url,
        dest_path=oxcgrt_dest,
        license_name="Creative Commons Attribution 4.0 International (CC-BY-4.0)",
        notes="Empirical statutory intervention timeline for England / UK subnational jurisdictions (OxCGRT / Blavatnik School)",
        ledger=ledger
    )
    print(f"   Saved: {r5.file_path} ({r5.byte_count} bytes, SHA-256: {r5.sha256[:16]}...)")

    print("\nAll 5 reference datasets successfully downloaded and registered in Evidence Ledger.")


if __name__ == "__main__":
    acquire_reference_datasets()

