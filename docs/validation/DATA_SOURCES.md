# RegionPack Data Sources and Methodology (Phase 20)

**Region**: Greater London (`regions/london`)  
**Data Tier**: L2 Full Multi-Layer Micro-Metapopulation  
**Reference Year**: 2020  

---

## 1. Demographic & Spatial Structure

### 1.1 Local Authority Demographics (`areas.csv`)
* **Source**: Office for National Statistics (ONS) - Mid-Year Population Estimates (mid-2020) and Census 2021.
* **License**: Open Government Licence v3.0 (OGL).
* **Content**: All 33 Local Authorities in Greater London (32 Boroughs and City of London). Total resident population: 9,012,200. Total households: 3,598,300.
* **Status**: **REAL**.

### 1.2 Age Distributions (`age_structure.csv`)
* **Source**: ONS Census 2021 table TS007 (Age by single year).
* **License**: Open Government Licence v3.0 (OGL).
* **Stratification**: 4 demographic age bands (`0-4`, `5-18`, `19-64`, `65+`) stratified by biological sex (M, F).
* **Validation**: Proportion shares sum to exactly 1.0000 across all 33 boroughs.
* **Status**: **REAL**.

### 1.3 Origin-Destination Commuting Matrix (`commute_od.csv`)
* **Source**: NOMIS Census Table WU03UK (Location of usual residence and place of work by Local Authority).
* **License**: Open Government Licence v3.0 (OGL).
* **Content**: 383 directed origin-destination worker flow links between London boroughs. Captures heavy daytime commuting inflows from outer boroughs into Central London employment centers (Westminster, City of London, Camden, Tower Hamlets).
* **Validation**: Outflow shares per origin borough sum to 1.0000.
* **Status**: **REAL**.

---

## 2. Transmission & Behavioral Dynamics

### 2.1 Contact Matrices (`contacts.csv`)
* **Source**: 
  - Base Matrices: POLYMOD UK (Mossong et al., 2008) and Prem et al. (2017) UK projection.
  - Longitudinal Wave Dynamics: London School of Hygiene & Tropical Medicine (LSHTM) CoMix Social Contact Survey (Jarvis et al., 2020; Gimma et al., 2022; Zenodo DOI: `10.5281/zenodo.4677017` / `4677018`).
* **License**: Creative Commons Attribution 4.0 International (CC-BY 4.0).
* **Content**: Age-stratified contact rates per person-day across transmission layers:
  - `home`: Family & household contacts.
  - `school`: Classroom & educational contacts.
  - `work`: Workplace & coworker contacts.
  - `community`: Public transport, markets, retail, and casual contacts.
* **Status**: **REAL**.

### 2.2 Policy Timeline (`policy_timeline.csv`)
* **Source**: UK Statutory Instruments (The Health Protection Coronavirus Regulations 2020) and Oxford COVID-19 Government Response Tracker (OxCGRT).
* **License**: Creative Commons Attribution 4.0 International (CC-BY 4.0).
* **Statutory Milestones**:
  - `2020-03-20`: School closures (SI 2020/350).
  - `2020-03-23`: National Lockdown 1 (Stay at Home order).
  - `2020-06-15`: Non-essential retail reopened; mandatory face coverings on public transport.
  - `2020-07-24`: Mandatory face coverings in retail shops.
  - `2020-09-01`: Reopening of schools for autumn term.
  - `2020-09-14`: "Rule of Six" gathering limits.
  - `2020-10-17`: London designated Tier 2 (High alert).
  - `2020-11-05`: National Lockdown 2 (SI 2020/1200).
* **Status**: **REAL**.

---

## 3. Clinical Healthcare Capacity & Observables

### 3.1 Hospital Directory & Capacity (`hospitals.csv`, `capacity.csv`, `resources.csv`)
* **Source**: NHS England COVID-19 Hospital Activity datasets & NHS Digital Acute Trust Directory.
* **License**: Open Government Licence v3.0 (OGL).
* **Content**: 18 major acute NHS hospital trusts operating in Greater London (e.g. Barts Health, Imperial College Healthcare, Guy's & St Thomas', King's College Hospital, Royal Free London, St George's).
* **Capacity Metrics**:
  - General acute bed capacity and surge ceilings.
  - Baseline non-outbreak bed occupancy (~80% baseline load).
  - Adult critical care / mechanical ventilation (IMV) bed capacity.
* **Status**: **REAL**.

### 3.2 Observed Surveillance Cases (`observed_cases.csv`)
* **Source**: UK Health Security Agency (UKHSA) Data Dashboard API & NHS England Daily Hospital Activity.
* **License**: Open Government Licence v3.0 (OGL).
* **Content**: Daily time series (March 1, 2020 to May 31, 2020) for positive tests by specimen date, daily hospital admissions, and vital statistics COVID-19 deaths across London.
* **Status**: **REAL**.

---

## 4. Environment & Demographics

### 4.1 Venues & Employment (`venues.csv`, `employment.csv`)
* **Source**: Department for Education (Get Information About Schools - GIAS) and ONS Business Register and Employment Survey (BRES).
* **Status**: **REAL**.

### 4.2 Environment & Housing (`environment.csv`, `sanitation.csv`)
* **Source**: Greater London Authority (GLA) London Datastore / ONS Census Housing Tables.
* **Status**: **REAL**.

### 4.3 Comorbidity & Clinical Risk (`comorbidity.csv`, `risk_factors.csv`)
* **Source**: NHS Digital Quality and Outcomes Framework (QOF) London Clinical Commissioning Group tables.
* **Status**: **REAL**.

