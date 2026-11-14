# EpiSwarm Engine Capability Gaps & Roadmap (v2 Audit)

In accordance with EpiSwarm Non-Negotiable Rule 5:
> *"A parameter or UI control may exist only if the engine actually reads it. For capabilities the engine lacks, do not invent a control; list it in docs/CAPABILITY_GAPS.md and show it in the UI as 'planned' only inside the parameter explorer."*

This document catalogs every domain capability currently unmodeled or stubbed in the active engine (`src/episwarm/engine/`). In the UI, these features appear strictly under an **"Upcoming Capabilities (Planned)"** tab within the Parameter Explorer with disabled controls and links to this roadmap.

---

## 1. Pathogen & Immunology Gaps

| Capability | Current Engine Status | Target Engine Stage | Why No UI Control Exists |
|---|---|---|---|
| **Multi-Variant Competition** | Single pathogen state graph active per simulation. | S6 (Backlog) | Engine currently evaluates one `DiseasePack` at a time; cross-reactive fitness and co-circulation arrays do not exist. |
| **Waning Immunity Kinetics** | Binary recovery into `R` compartment without exponential decay. | S6 (Backlog) | Requires per-agent antibody decay timers ($\tau_{wane}$) and re-susceptibility hazard functions not yet in `infection.py`. |
| **Pre-symptomatic Sub-graph Dynamics** | Exposed ($E$) transitions directly to Symptomatic or Asymptomatic based on fixed draw. | S6 (Backlog) | Independent sub-infectious transmission windows are currently integrated into general infectiousness multipliers. |

---

## 2. Healthcare & Clinical Intervention Gaps

| Capability | Current Engine Status | Target Engine Stage | Why No UI Control Exists |
|---|---|---|---|
| **Dynamic Vaccine Rollout Schedules** | Pre-simulation binary immunization state (`vaccinated = 0 | 1`). | S6 (Backlog) | Engine does not currently support daily allocation queues (e.g. 5,000 doses/day prioritized by age tiers 65+). |
| **Testing & Contact Tracing (TTI)** | Generic isolation state; no forward or backward contact trace graph traversal. | S6 (Backlog) | Contact tracing requires storing dynamic contact histories and conditional PCR test turnaround delays. |
| **Specialized Clinical Staffing Constraints** | Hospital beds capped by generic physical count (`effective_beds`). | S6 (Backlog) | Physician-to-patient and ICU-nurse-to-ventilator ratios are not tracked dynamically; staffing is not a live state variable. |

---

## 3. Socioeconomic & Border Gaps

| Capability | Current Engine Status | Target Engine Stage | Why No UI Control Exists |
|---|---|---|---|
| **International Border & Port Seeding** | Initial infection seeds distributed exclusively at day 0 across local areas. | S6 (Backlog) | Dynamic daily airport/flight passenger import curves are not accepted by the engine's seeding step. |
| **Macroeconomic Loss & Lost-Work Valuation** | Crude NPI day counts; no GDP or wage-loss accounting model. | S6 (Backlog) | No audited microeconomic loss tables currently exist in the Evidence Ledger. |

---

## 4. UI Rendering Policy for Gaps
1. **Never render active sliders, toggles, or input fields** for items listed in this document.
2. In the **Case File Parameter Explorer**, these items are tagged with a purple badge: `PLANNED (ENGINE GAP)`.
3. Clicking a planned parameter opens an informative tooltip explaining: *"This capability is planned for Roadmap S6. The active vectorized simulation engine does not currently read this parameter."*

