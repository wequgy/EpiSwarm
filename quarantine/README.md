# EpiSwarm Quarantine Directory

**Quarantine Date**: November 10, 2026  
**Auditor**: Independent Third Audit (Findings X1 - X7)  
**Standard**: Non-Negotiable Rule 1 (Never fabricate) & Rule 2 (Synthetic data isolation)

---

## 1. Reason for Quarantine

This directory contains artifacts, regional data, validation reports, evaluation logs, and scripts that violated fundamental scientific integrity rules:

1. **X1 - Fabricated "Observed" Data**:
   - `quarantine/regions/london/observed_cases.csv` was generated via analytical Gaussian wave curves and Poisson random variables in `scripts/build_london_pack.py` lines 485–496, but labeled with `status: real` and attributed to "UKHSA COVID-19 Dashboard API & NHS England Hospital Activity Time Series".
2. **X2 - Formula Output and Hardcoded Numbers Labeled `real`**:
   - `commute_od.csv`: distance gravity formula with manual multiplier for 4 central boroughs, labeled "NOMIS Census WU03UK".
   - `capacity.csv`: fixed heuristic multipliers (`effective_low = int(h['general'] * 0.75)`), labeled "NHS England COVID-19 Hospital Activity Trust Dataset".
   - `areas.csv`, `contacts.csv`, `environment.csv`, `sanitation.csv`: hand-typed values and synthetic defaults labeled `real`.
3. **X3 - Pseudo-Random & Hardcoded Validation Benchmarks**:
   - `scripts/run_validation_protocol.py` evaluated spatial arrival rank correlation by comparing random numbers `rng.integers(12, 38, size=33)` against itself with jitter, guaranteeing $\rho \approx 1.0$.
   - Healthcare overflow days and behavior contact reductions were hardcoded constants (`sim_overflow_days = 21`, `obs_overflow_days = 24`, `sim_reduction_pct = 70.5`).
4. **X4 - Self-Contradictory Validation Reporting**:
   - `docs/validation/VALIDATION_REPORT.md` printed **PASS** on rows violating pre-registered thresholds (e.g. peak ratio 0.42 against [0.75, 1.25], cumulative error 81.5% against $\le 20\%$).
   - Machine card `VALIDATION_CARD.json` showed 3/5 targets passed while report narrative claimed overall pass.
5. **X5 - Data Leakage & Retuning on Held-Out Data**:
   - `docs/validation/HELD_OUT_LOG.jsonl` logged repeated evaluations of the same Wave 2 held-out split with retuned transmission parameters ($R_0 = 2.8$ then $2.6$).
6. **X6 - Stand-in Generation After Download Failure**:
   - `docs/validation/MANUAL_DOWNLOADS.md` acknowledged missing data links, but rather than stopping, mock generators were executed without download records or SHA-256 validation.
7. **X7 - Unverified Calibration & Literature Claims**:
   - `src/episwarm/behavior/hierarchical.py` claimed logit coefficients were "CoMix-calibrated", though no empirical regression was fitted.
   - `docs/validation/ABLATION_REPORT.md` cited unverified compliance literature ranges.

---

## 2. Contents of this Quarantine

- `quarantine/regions/london/`: Entire unverified London data pack (15 CSVs and `region.yaml`).
- `quarantine/docs/validation/VALIDATION_REPORT.md`: Fabricated validation report.
- `quarantine/docs/validation/VALIDATION_CARD.json`: Fabricated validation card.
- `quarantine/docs/validation/HELD_OUT_LOG.jsonl`: Repeated held-out evaluation logs.
- `quarantine/docs/validation/BEHAVIOR_MODEL_REPORT.md`: Unverified CoMix-calibration report.
- `quarantine/docs/validation/ABLATION_REPORT.md`: Report with unverified literature citations.
- `quarantine/scripts/build_london_pack.py`: Script containing formulaic generation of "real" data.
- `quarantine/scripts/run_validation_protocol.py`: Script containing random array comparisons and hardcoded metrics.
- `quarantine/tests/test_london_pack_phase20.py`: Structural tests that validated fake `real` files.

---

## 3. Policy on Quarantined Files

- Quarantined files must NEVER be imported, referenced, executed, or used for model validation, calibration, or benchmarking.
- Active codebase must refer exclusively to genuine data verified through the Evidence Ledger (Phase 26) or explicitly isolated synthetic benchmarks in `regions/example_synthetic` and `regions/metro_dense`.

