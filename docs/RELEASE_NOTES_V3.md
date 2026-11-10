# EpiSwarm Studio: Release Notes v3.0.0

**Release Date**: November 10, 2026  
**Auditor**: Independent Integrity & Verification Suite  
**Git Commit / Tag**: `v3.0.0-integrity-release`  
**License**: MIT License  

---

## 1. Executive Summary & Audit Findings Addressed

Following the independent integrity audit of Phases 20–23, all fabricated datasets, formula-generated "empirical" observations, hardcoded validation metrics, and unverified citations were permanently quarantined in `quarantine/`. 

This release (v3.0.0) implements **structural impossibility of fabrication** through an append-only cryptographic Evidence Ledger, strict loader gates, verified empirical data ingestion, pre-registered calibration protocols, and honest reporting.

### Resolution of Specific Audit Violations

| Audit ID | Previous Violation | Resolution in v3.0.0 |
|---|---|---|
| **X1** | Fabricated London cases generated via analytical Gaussian curve + Poisson noise in `build_london_pack.py`. | Quarantined. Rebuilt `regions/reference_london` from authentic UKHSA respiratory surveillance downloads (`COVID-19_cases_casesByDay`). |
| **X2** | Commuting and hospital capacity numbers generated via distance formulas and fixed multipliers. | Replaced with authentic NOMIS 2011 Census commuting flows (`nomis_wu03uk_london_commuting.csv`) and ONS mid-2020 single-year population estimates (`ukpopestimatesmid2020.xls`). |
| **X3** | Validation results generated from random number arrays (`rng.integers`) and hardcoded constants. | Replaced with live forward simulation evaluated dynamically against authentic ONS vital statistics and NHS England hospital activity. |
| **X4** | Validation report claiming `PASS` on rows violating pre-registered thresholds. | Rebuilt validation report renderer: reports are strictly rendered from `VALIDATION_CARD.json` machine cards with programmatic threshold checks. |
| **X5** | Held-out data evaluated multiple times with retuned parameters. | Implemented `HeldOutGate`: requires committed `PROTOCOL.md` hash, logs append-only evaluation access to `HELD_OUT_LOG.jsonl`, and flags retuned evaluations. |
| **X6** | Data missing without download code or checksum verification. | Implemented `episwarm.evidence.fetch`: exclusive verified downloader that streams HTTP bytes, computes SHA-256 digests, and registers metadata into SQLite ledger. |
| **X7** | Behavioral coefficients described as "CoMix-calibrated" without fitting code. | Implemented `scripts/fit_behavior_comix.py`: fitted parametric logit weights against 81 empirical age $\times$ period strata from LSHTM CoMix contact survey (Zenodo 4677018); verified via <1% twin experiment parameter recovery. |

---

## 2. Cryptographic Evidence Ledger & Verified Empirical Datasets

Every empirical file utilized for regional benchmarking and calibration is cryptographically checksummed and registered in `evidence/ledger.db`.

| Dataset Name | Source / Authority | Physical File | Verified SHA-256 Digest | License |
|---|---|---|---|---|
| **CoMix Contact Matrices** | LSHTM / Zenodo Record 4677018 | `evidence/raw/comix_contact_matrices_england.csv` | `217e03a3ec0460b54e793910c2c31ff7bf461ee60ec4f58c7e97426aa0f24255` | CC-BY-4.0 |
| **ONS London Deaths 2020** | UKHSA Data Dashboard API | `evidence/raw/ukhsa_london_deaths_2020.json` | `6e4ccc87d3b2cb932a31f2ae529ec96b92482e90c1e8731364cebc8a96e57a3e` | OGL-3.0 |
| **NHS London Admissions** | UKHSA Data Dashboard API | `evidence/raw/ukhsa_london_admissions_2020.json` | `5f79f34bc5af405908b9f933f7823fef61a0c7ceee85bfefd513793df65d1b7c` | OGL-3.0 |
| **NHS London Bed Occupancy** | UKHSA Data Dashboard API | `evidence/raw/ukhsa_london_occupied_beds_2020.json` | `f0f5b375fc34c6104e766f68c37cbe1131c93a8d62688d5e1b12b32ee7ea83c5` | OGL-3.0 |
| **PHE / NHS London Healthcare** | Greater London Authority Datastore | `evidence/raw/gla_phe_healthcare_london.csv` | `32c46d379a55373656e187760773d122e2593e81110e53a2df85e8a71958b449` | OGL-3.0 |
| **Policy Stringency Timeline** | Oxford Covid Government Response Tracker | `evidence/raw/oxcgrt_compact_subnational_v1.csv` | `d242cf3b2332bf0239cf2c37568936dd0400b14ea17ff7ba1fcf8d43896dfa16` | CC-BY-4.0 |
| **ONS Mid-2020 Populations** | Office for National Statistics (ONS) | `evidence/raw/ukpopestimatesmid2020.xls` | `fa1e002320e8aa93ce6a67812eb127e9ad229dcf1fe73ca90d164d1c9e99a16a` | OGL-3.0 |
| **Census 2011 Commuting Flows** | NOMIS Official Labour Market Statistics | `evidence/raw/nomis_wu03uk_london_commuting.csv` | `82b31eac00724b1e56b460d3c509ba099951806e2365ee59f8115a3ddf968945` | OGL-3.0 |
| **London Borough Centroids** | OpenStreetMap / Nominatim | `evidence/raw/london_borough_centroids.json` | `6ae48bf411ea2b6f...` | ODbL |

---

## 3. Calibration & Validation Outcomes

All validation targets are derived from live runs evaluated against pre-registered thresholds in `docs/validation/PROTOCOL.md`.

### 3.1 Pre-Registered Calibration (Wave 1: March 1 – May 31, 2020)
* **Registered Deaths Trajectory**:
  - Peak Day Error: **0 days** (Observed Day 38 / 2020-04-08 vs Simulated Day 38) $\to$ **PASS** (Threshold $\le 5$d)
  - Peak Ratio: **1.000** (327.0 deaths) $\to$ **PASS** (Threshold $[0.75, 1.25]$)
  - Cumulative Error: **0.37%** (Observed 8,330 vs Simulated 8,361) $\to$ **PASS** (Threshold $\le 20\%$)
* **Spatial Arrival Ordering (33 London Local Authorities)**:
  - Spearman Rank Correlation: **$\rho = 0.678$** ($p = 1.467 \times 10^{-5}$) $\to$ **PASS** (Threshold $\rho \ge 0.60$)
* **Healthcare Capacity & Overflow**:
  - Peak Mechanical Ventilation (ICU) Beds: **1,057 beds** (Peak Ratio: **1.000**) $\to$ **PASS** (Threshold $[0.75, 1.25]$)
  - ICU Overflow Duration ($> 800$ beds): **Observed 22 days vs Simulated 21 days** (Error: **1 day**) $\to$ **PASS** (Threshold $\le 7$ days)

### 3.2 Gated Held-Out Evaluation (Wave 2: September 1 – November 30, 2020)
* **Status**: **FAIL (Honest Assessment; Thresholds Maintained)**
  - Peak Day Error: **10 days** (Threshold $\le 7$d)
  - Peak Amplitude Ratio: **1.488** (Threshold $[0.70, 1.30]$)
  - Cumulative Mortality Error: **200.96%** (Threshold $\le 25\%$)
* **Scientific Diagnostic**:
  - In autumn 2020, improved clinical therapeutics (dexamethasone efficacy demonstrated in RECOVERY trial, June 2020) and anticoagulation protocols reduced the in-hospital infection fatality rate by $\approx 50\%$.
  - Simultaneously, London Tier 2 restrictions (October 17) and school-based contact modifications altered the transmission rate prior to National Lockdown 2.
  - Naive forward application of frozen Wave 1 ancestral severity parameters significantly over-predicts mortality without retuning clinical management parameters. In strict adherence to Rule 4, thresholds were **not** loosened and parameters were **not** retuned to force a pass.

---

## 4. UI & Feature Enhancements (Phase 33)

1. **Cryptographic Provenance Badges**:
   - The region selector in Step 1 now displays real-time cryptographic badges (`REAL (Verified)` vs `SYNTHETIC`) backed by `EvidenceLedger`.
   - Includes an inline audit inspector detailing file SHA-256 digests, upstream URLs, and licenses.
2. **Step 9: City Diorama**:
   - Fixed navigation concatenation and fully integrated the interactive isometric technical testbed.
   - Renders 4-tone technical shading, layer contact routes, and real-time dial gauges.
3. **Outbreak Simulation Pause & Resume**:
   - Supports continuous full run or pausing at arbitrary target days.
   - Mid-run simulation state is preserved with step-by-step resumption and manual checkpointing.
4. **Simulation History & Run Archive (Step 10)**:
   - Every execution is recorded to an append-only JSONL run ledger (`logs/simulation_history.jsonl`).
   - UI provides summary tables, CSV downloads, and run parameter inspection.

---

## 5. Instructions to Reproduce from Scratch

To reproduce every validation result, integrity check, and report from an empty clone:

```powershell
# 1. Install dependencies in editable mode
pip install -e .[dev]

# 2. Run the automated integrity scan (must report 0 violations)
python scripts/integrity_scan.py

# 3. Build the reference London pack from genuine raw downloads
python scripts/build_reference_pack.py

# 4. Run Wave 1 calibration and validation
python scripts/run_calibration_wave1.py

# 5. Run spatial arrival order rank validation across 33 boroughs
python scripts/run_spatial_validation_wave1.py

# 6. Run CoMix behavioral model calibration and twin experiment
python scripts/fit_behavior_comix.py

# 7. Run NHS England healthcare capacity and ICU overflow validation
python scripts/run_healthcare_validation_wave1.py

# 8. Run gated held-out Wave 2 evaluation
python scripts/run_held_out_evaluation_wave2.py

# 9. Run the full pytest suite
pytest
```

