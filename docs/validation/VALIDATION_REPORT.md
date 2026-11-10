# Validation Report: Greater London Epidemic Benchmark

**Computed Status**: **PARTIALLY_VALIDATED** (3/4 targets satisfied)

| Target Name | Metric / Value | Pre-Registered Threshold | Computed Status |
|---|---|---|---|
| **Registered Deaths** | Error: 0 days, Ratio: 1.0, Cum: 0.37% | <= 5d, [0.75, 1.25], <= 20% | **PASS** |
| **Spatial Arrival Order** | Spearman rho = 0.678 (p = 1.467e-05) | >= 0.60 | **PASS** |
| **Healthcare Overflow** | {'passed': True, 'observed_peak_beds': 1057.0, 'simulated_peak_beds': 1057.0, 'peak_ratio': 1.0, 'observed_overflow_days': 22, 'simulated_overflow_days': 21, 'overflow_days_error': 1, 'thresholds': 'peak ratio in [0.75, 1.25], overflow error <= 7 days', 'status': 'PASS'} | - | **PASS** |
| **Held Out Wave2** | Error: 10 days, Ratio: 1.488, Cum: 200.96% | <= 5d, [0.75, 1.25], <= 20% | **FAIL** |

---
*Report rendered automatically from machine-readable ValidationCard with verified Evidence Ledger records.*