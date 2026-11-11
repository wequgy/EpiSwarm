# Validation Report: Greater London Reference Pack (regions/reference_london)

**Computed Status**: **UNCALIBRATED** (0/3 targets satisfied)

| Target Name | Peak Day Error | Peak Height Ratio | Cumulative Error | Computed Status |
|---|---|---|---|---|
| **Registered Deaths** | 0 days | 1.0 | 0.37% | **IN-SAMPLE (Calibration Fit)** |
| **Spatial Arrival Order** | - | - | - | **FAIL** |
| **Healthcare Overflow** | - | 8.517 | - | **FAIL** |
| **Held Out Wave2** | - | - | - | **FAIL** |

## Assumptions Register (Evidence Class C)

| Parameter | Nominal Value | Evidence Class | Uncertainty Bound / Notes |
|---|---|---|---|
| **London Baseline ICU Capacity** | 800 beds | Class C (Assumed) | [700, 950] beds; nominal pre-surge baseline without Nightingale capacity |
| **ICU Admission Fraction** | 0.18 | Class C (Assumed) | [0.12, 0.22] of acute respiratory hospital admissions |
| **ICU Length of Stay** | Gamma(mean=13.0d, shape=2.0, scale=6.5) | Class C (Assumed) | [10.0, 16.0] days duration parameterization |
| **Borough Centroid Coordinates** | OpenStreetMap Nominatim place coordinates | Class C (Assumed) | ODbL place-name geocoder proxy for administrative polygon centroids |
| **Hierarchical Behavior Compliance** | beta_compliance = 1.65, beta_fatigue = 0.45 | Class C (Assumed) | Assumed baseline archetype coefficients for social distancing adherence |

---
*Report rendered automatically from machine-readable ValidationCard.*