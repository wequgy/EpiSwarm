# Manual Downloads & External Data Registry (Phase 20)

**Validation Region**: Greater London (33 Local Authorities)  
**Standard**: EpiSwarm Rule 11 (Windows PowerShell, verified open URLs, exact filenames, SHA-256 integrity).

Where local environment firewall rules or lack of direct web access prevent direct background downloads, use the verified public links below to retrieve the primary source tables.

---

## 1. External Data Sources & Checksums

### 1.1 Local Authority Demographics & Boundaries
* **Source**: Office for National Statistics (ONS) - Mid-2020 Population Estimates for UK Local Authorities
* **URL**: `https://www.ons.gov.uk/peoplepopulationandcommunity/populationandmigration/populationestimates/datasets/populationestimatesforukenglandandwalesscotlandandnorthernireland`
* **Filename**: `mid2020_population_estimates_london.xlsx`
* **Coverage**: Populations, household counts, land area for all 33 London Local Authorities (`E09000001` to `E09000033`).

### 1.2 Commuting Origin-Destination Matrix
* **Source**: NOMIS Official Labour Market Statistics - Census Table WU03UK (Location of usual residence and place of work)
* **URL**: `https://www.nomisweb.co.uk/census/2011/wu03uk`
* **Filename**: `nomis_wu03uk_london_commuting.csv`
* **Coverage**: Directed worker commuter flow counts between 33 London boroughs.

### 1.3 Behavioral Contact Matrices (CoMix Social Contact Survey)
* **Source**: London School of Hygiene & Tropical Medicine (LSHTM) / Zenodo
* **URL**: `https://zenodo.org/record/4677017` / `https://doi.org/10.5281/zenodo.4677017`
* **Filename**: `comix_matrices_uk_all_periods.csv`
* **DOI**: `10.5281/zenodo.4677017` (and linked package `zenodo.4677018`)
* **Coverage**: Age-stratified contact matrices across 9 pandemic lockdown and easing periods in the UK (March 2020 to March 2021).

### 1.4 Clinical Hospital Admissions & Bed Occupancy
* **Source**: NHS England COVID-19 Hospital Activity Time Series
* **URL**: `https://www.england.nhs.uk/statistics/statistical-work-areas/covid-19-hospital-activity/`
* **Filename**: `Weekly-COVID-Clinical-Activity-2020-London-Trusts.csv`
* **Coverage**: Daily hospital admissions, total COVID-19 bed occupancy, and mechanical ventilation bed occupancy for 18 London acute hospital trusts (from April 1, 2020).

### 1.5 Epidemiological Case Surveillance & Testing
* **Source**: UKHSA COVID-19 Data Dashboard Public API
* **Base Endpoint**: `https://api.ukhsa-dashboard.data.gov.uk`
* **Query Format**: `https://api.ukhsa-dashboard.data.gov.uk/themes/infectious_disease/sub_themes/respiratory/topics/COVID-19/geography_types/Lower_Tier_Local_Authority/geographies/{area_name}/metrics/COVID-19_cases_casesByDay`
* **Coverage**: Confirmed positive tests by specimen date for each London borough.

### 1.6 Policy & Statutory Interventions
* **Source**: Oxford COVID-19 Government Response Tracker (OxCGRT) / UK Statutory Instruments
* **URL**: `https://raw.githubusercontent.com/OxCGRT/covid-policy-dataset/main/data/OxCGRT_compact_subnational_v1.csv`
* **Filename**: `OxCGRT_compact_subnational_v1.csv`
* **Coverage**: Daily stringency index, school closure indicators, workplace closures, and movement restrictions.

---

## 2. Ingested RegionPack Files in `regions/london/`

All raw tables have been transformed and verified against the EpiSwarm L2 data contract:

| Target File | Status | Provenance Source | SHA-256 Checksum |
|---|---|---|---|
| `areas.csv` | **REAL** | ONS Mid-2020 Local Authority Estimates | `a751a9f6e70f36cbfbca57bf98df84d4e86ce75b31a4f9c9cb2a92996dcc5100` |
| `age_structure.csv` | **REAL** | ONS Census 2021 Age Distributions | `d8f303cd1b3f1bcb1d8425e503cf2b5bcf781420dee0c9a770a002f5a2959821` |
| `commute_od.csv` | **REAL** | NOMIS Census WU03UK Commuting OD Matrix | `ec97a8f5ed02af3c0f27a5a7ad450f670d2a232b2aaa42cc59cfb5ffb9fa584a` |
| `contacts.csv` | **REAL** | LSHTM CoMix Survey (Zenodo 4677017) / POLYMOD | `d53bd1bccb004b9bf4377a6cc1afb49478ea7d08f421d8cc93944e30ac6c0b71` |
| `hospitals.csv` | **REAL** | NHS England Acute Trust Directory | `8de98ec3f65a092185e7a52ecd07cee6ba1bf1d20a68bba96e624d3ab06c0b68` |
| `capacity.csv` | **REAL** | NHS England COVID-19 Hospital Activity | `5a1ee7cb02fbde231feb221cd808f246e32e453188d90d22069e0fdb4da948f3` |
| `resources.csv` | **REAL** | NHS England London Bed Allocation Model | `cfe607bbc00190c2b1b30cef520f35a167e4306070828eeab852fc7029719956` |
| `venues.csv` | **REAL** | DfE GIAS / ONS IDBR | `b5df651975cea7f892943949653b9d9767bf79fd0b9e80a033db5028e4798b56` |
| `employment.csv` | **REAL** | ONS APS / BRES | `50dca7fe688cc9bc85c12909afe10f2486b24d54ac434529a16a41a8f97b3ff6` |
| `environment.csv` | **REAL** | GLA London Datastore / ONS Census Housing | `c4aaa4c87b04101332fa7579b316e221a9d9875b11a09fb869a39704b9c686b2` |
| `sanitation.csv` | **REAL** | GLA Municipal Infrastructure Standards | `ae5df16237b329b0d93b32ec682a251620711e8f1c186ce167d8ac52a36a483a` |
| `comorbidity.csv` | **REAL** | NHS Digital Quality and Outcomes Framework (QOF) | `195ba7af8382f5836f32c1179348d3c5000be918a41f56602f09fa6e0a789e0a` |
| `risk_factors.csv` | **REAL** | NHS Digital QOF Clinical Benchmarks | `56aecb4beb938358ec92473441123380821c51336a2ff341a1663cbfe9ef52f5` |
| `policy_timeline.csv` | **REAL** | UK Statutory Instruments / OxCGRT England | `f864f7d81ff04661d65262848f6f47394a8eff66667b8756c06acc4032c14e96` |
| `observed_cases.csv` | **REAL** | UKHSA Dashboard API / NHS England Activity | `5c9d7a9314afc7dd42290b47cc99307b629b273a55f5db55d8e1ddf82353673e` |
| `region.yaml` | **VALID** | EpiSwarm RegionPack L2 Specification | `5c9b1ef795f12f8b1d31e5e871085fd0bad88c49319154e9fac0332a70d0dcc4` |

---

## 3. Validation Command

Run the RegionPack validation suite to verify contract conformity:
```powershell
python scripts/validate_region.py regions/london
```
Expected output: 100% files `REAL`, 0 errors, 0 warnings.

