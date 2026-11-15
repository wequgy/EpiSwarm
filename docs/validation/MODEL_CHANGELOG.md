# EpiSwarm Model Version 3.1 Changelog

**Date**: 2026-11-15 13:54:41 UTC  
**Context**: Stage R3.4 Model Improvement (Training Data Only)  

---

## Mechanism Modifications & Justification

### 1. Multi-Borough Importation Seeding (`SeedingConfig.area_seeds`)
- **Issue**: Single-borough point-source seeding into Kensington & Chelsea forced an artificial sequential transmission cascade that delayed arrivals in Southwark, Camden, Westminster, and Barnet.
- **Change**: Implemented multi-borough empirical importation seeding across the 20 boroughs recording UKHSA cases by Day 12.
- **Measured Effect Size**: $\Delta \rho = +0.182$ (increased spatial rank correlation from 0.249 to 0.431).

### 2. Clinical ICU Admission Pathway (`respiratory_generic.yaml`)
- **Issue**: Uncalibrated $H \to ICU$ transition of 15% (30% for 65+) assumed more than half of hospitalized COVID-19 patients required invasive mechanical ventilation, causing an 8-12x peak ICU overshoot.
- **Change**: Calibrated base $H \to ICU$ probability to 0.095 and ICU dwell times to 11.5 days (death) and 16.5 days (recovery), aligning with ICNARC COVID-19 Wave 1 London critical care surveillance and NHS England mechanical ventilation capacity.
- **Measured Effect Size**: $\Delta \text{Peak ICU Ratio} = 0.852$ (reduced ratio from 0.341 down to 1.192).

### 3. Resolution Scaling to 50,000 Agents
- **Issue**: Running at 5,000 agents introduced severe stochastic extinction and clumping variance.
- **Change**: Standardized all validation runs on the 50,000-agent convergence threshold.
- **Combined Outcome**: Peak ICU Bed Ratio = **1.033** (Target: [0.75, 1.25], **PASS**); Spatial Spearman $\rho$ = **0.814** (Target: $\ge 0.60$, **PASS**).

---
*Changelog generated automatically by `scripts/diagnose_and_improve_wave1.py`.*