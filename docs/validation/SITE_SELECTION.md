# Validation Site Selection & Data Feasibility Report (Phase 19)

**Date**: November 3, 2026  
**Status**: Completed Research & Evaluation (No Modeling)  
**Deliverable**: Comparative Evaluation of Real-World Outbreak Validation Sites  

---

## 1. Overview & Selection Criteria

To transition EpiSwarm from a synthetic model to a validated epidemiological simulator (addressing audit finding **F6**), we evaluated candidates against six non-negotiable operational requirements:

1. **Granular Spatial Topology**: Multi-area structure (10 to 35 sub-regions) with empirically measured commuting and mobility flux (not synthetic gravity models).
2. **Granular Clinical Observables**: Daily hospital admissions, acute general bed occupancy, and mechanical ventilation / ICU bed occupancy at the healthcare trust/facility level.
3. **Behavioral Ground Truth**: Empirical contact matrices over time (e.g., longitudinal contact surveys) and measured face-covering compliance to validate the behavioral decision layer independently from case curves.
4. **Unbiased Prevalence Anchors**: Randomized household infection surveys (serology or PCR) to break structural unidentifiability between ascertainment fraction $\rho$ and transmission rate $\beta$.
5. **Open License & Machine Accessibility**: Publicly available APIs or version-controlled open data repositories with stable URLs and checksums.
6. **Clean Epidemiological Windows**: Availability of epidemic periods free from unmodeled confounders (e.g., multi-strain variant competition or differential vaccine rollouts).

---

## 2. Candidate Evaluation Matrix

| Criterion | 1. England: Greater London (Recommended) | 2. Germany: Berlin / Bavaria Districts | 3. New York City: 5 Boroughs | 4. Bengaluru: BBMP Wards |
|---|---|---|---|---|
| **Spatial Resolution** | 33 Local Authorities (32 Boroughs + City of London) | 401 Landkreise (or 12 Berlin districts) | 5 Boroughs or 177 ZCTAs | 198 BBMP Administrative Wards |
| **Mobility & Commuting** | **REAL**: ONS Census 2011/2021 WU03UK (Borough-to-Borough OD matrix) | **REAL**: Destatis Pendlerverflechtung (commuter flows) | **PARTIAL**: US Census LEHD/LODES (noisy at ZIP level) | **SYNTHETIC**: Gravity model approximations |
| **Case Surveillance** | **REAL**: UKHSA Dashboard API (`api.ukhsa-dashboard.data.gov.uk`) by LTLA | **REAL**: RKI GitHub repository by Landkreis | **REAL**: NYC Health GitHub (`nychealth/coronavirus-data`) | **PARTIAL**: State bulletin scrapes (inconsistent format) |
| **Hospital & ICU Data** | **REAL**: NHS England Hospital Activity (Daily admissions, COVID beds, MV/ICU beds by NHS Trust) | **PARTIAL**: DIVI Intensivregister (ICU only; acute general ward data missing at district level) | **PARTIAL**: NYC DOHMH daily borough hospitalizations (bed type breakdown limited) | **MISSING**: Aggregate city-wide only, bed occupancy not published by ward |
| **Behavioral Ground Truth** | **REAL**: CoMix Social Contact Survey (Zenodo 4677017/4677018: 9 pandemic period matrices & mask use) | **PARTIAL**: COSMO behavioral survey (attitudinal, limited contact matrices) | **MISSING**: General US survey averages; no localized NYC contact matrices | **MISSING**: No empirical ward-level contact surveys |
| **Prevalence Surveys** | **REAL**: ONS Infection Survey (CIS) & Imperial College REACT-1 | **PARTIAL**: RKI Corona-Monitoring lokal (few select hotspots) | **PARTIAL**: NYC DOHMH blood donor antibody surveys (infrequent) | **PARTIAL**: Serosurveys conducted at 3 discrete rounds |
| **Policy Timeline** | **REAL**: OxCGRT subnational England + UK statutory instruments | **REAL**: OxCGRT Germany + Bundesländer decrees | **REAL**: OxCGRT US/NY state + NYC mayoral executive orders | **PARTIAL**: National lockdown dates, municipal enforcement unquantified |
| **Data Licensing** | Open Government Licence (OGL v3.0) & CC-BY 4.0 | CC-BY 4.0 / Data licence Germany - zero | CC0 / Public Domain | Government of Karnataka Open Data (varies) |
| **Download Access Today** | **VERIFIED**: UKHSA REST API, NHS England CSV archives, Zenodo DOI | **VERIFIED**: RKI GitHub raw CSVs, Zenodo DIVI snapshots | **VERIFIED**: NYC Health GitHub raw CSVs | **UNVERIFIED**: Multiple broken portal links |

---

## 3. Recommended Validation Site: Greater London (33 Local Authorities)

### 3.1 Justification
Greater London provides the single most complete, publicly verified data ecosystem in modern epidemiology:
1. **Self-Contained Urban Metapopulation**: 33 lower-tier local authorities (LTLAs) encompassing 8.9 million residents with dense daily commuting captured in the Census WU03UK origin-destination matrix.
2. **Empirical Behavior Anchors (CoMix)**: Unlike models that infer behavior purely from mobility reduction (Google/Apple mobility), London can be cross-validated against the London School of Hygiene & Tropical Medicine (LSHTM) CoMix survey (Zenodo record `10.5281/zenodo.4677017` / `4677018`), which measured actual face-to-face contacts by age band across 9 statutory intervention phases.
3. **Dual Hospital Metrics**: NHS England publishes trust-level time series separating acute general ward admissions and occupancy from invasive mechanical ventilation (IMV) ICU occupancy across London acute hospital trusts (e.g., Guy's and St Thomas', Barts Health, Imperial College Healthcare, King's College Hospital, Royal Free).
4. **Community Prevalence Anchors**: Imperial College REACT-1 and ONS CIS provide gold-standard, swab-based random surveillance percentages to ground ascertainment.

### 3.2 Pre-Registered Epidemiology Windows
To ensure strict pre-registration and avoid data leakage (Rules 4 and 5):
- **Training & Calibration Window (Wave 1)**: March 1, 2020 – May 31, 2020 (92 days).
  - *Characteristics*: Wild-type Wuhan/D614G lineage, single-strain dynamics, no vaccination, first national lockdown statutory timeline (March 23).
- **Held-Out Evaluation Window (Wave 2 Pre-Alpha)**: September 1, 2020 – November 30, 2020 (91 days).
  - *Characteristics*: Pre-Alpha variant period, tiered regional restrictions (Tier 1/2/3 system and second national lockdown in November 2020), before vaccination commenced (December 8, 2020).
- **Strict Quarantine Rule**: The held-out window is never touched during calibration, debugging, or hyperparameter tuning.

---

## 4. Critical Data Biases, Breaks, and Caveats

Any empirical comparison against real-world data must account for the following documented artifacts:

1. **Wave 1 Case Ascertainment Collapse**:
   - In March–April 2020, community PCR testing (Pillar 2) did not exist in the UK; tests were restricted to hospitalized patients (Pillar 1). True community ascertainment dropped below 10%.
   - **Protocol Response**: Never calibrate transmission parameters or R0 to early case counts. Calibrate against hospital admissions, mechanical ventilation bed occupancy, and vital statistics deaths.
2. **Local Authority vs. NHS Trust Catchment Mismatch**:
   - Local authorities report residence; NHS trusts report admissions. While borough boundaries are administrative, NHS trusts have catchment overlap (e.g., Barts Health admits from Tower Hamlets, Newham, and Waltham Forest).
   - **Protocol Response**: Build an explicit borough-to-trust catchment mapping matrix based on published NHS catchment population estimates.
3. **Data Revisions and Backdating**:
   - UKHSA historical cases are backdated by specimen date (date of swab), whereas media dashboards reported by publication date.
   - **Protocol Response**: Always use the historical series by `specimen_date`, not `notification_date`, and apply the observation delay model developed in Phase 18.
4. **Non-COVID Baseline Hospital Pressure**:
   - Total acute/ICU bed capacity is not entirely available to the epidemic; routine emergencies, elective care, and baseline occupancy consume 75–85% of standard bed availability.
   - **Protocol Response**: RegionPack hospital data must declare baseline non-outbreak occupancy alongside surge capacity ceilings.

---

## 5. Decision & Proposed Next Steps

We recommend validating EpiSwarm against **Greater London (33 Local Authorities)** during the 2020 wild-type epidemic waves.

Upon confirmation:
- Proceed to **Phase 20**: Build the automated download and ingestion scripts transforming ONS Census, UKHSA Dashboard, NHS Hospital Activity, NOMIS commuting, and CoMix contact matrices into the standardized `regions/london` RegionPack with complete checksums and validation.
