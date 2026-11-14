# EpiSwarm Studio v2: User Journeys

This document defines the two primary user paths through the authority-grade simulation workbench:
1. **The Government Health Authority Official**: A Ministry of Health director or municipal epidemiologist modeling an outbreak in their specific jurisdiction.
2. **The First-Time Visitor / External Auditor**: A public health analyst evaluating EpiSwarm's methodology, validation honesty, and real-time visualization capabilities.

---

## Journey 1: Government Health Authority Official (End-to-End Intake to Action)

### Goal:
Model an emerging respiratory virus in a real municipality (e.g. Manchester or Birmingham), identify hospital ICU overflow dates, evaluate school closures vs. mask mandates, and export an audited provenance report for ministers.

```mermaid
sequenceDiagram
    autonumber
    actor Official as Health Authority Official
    participant UI as EpiSwarm Studio (Web)
    participant Intake as Case File Intake Engine
    participant Engine as Vectorized Engine & WebSocket
    participant Ledger as Cryptographic Evidence Ledger

    Official->>UI: Create New Case File ("Manchester Winter Surge")
    UI->>Official: Present 8-step intake wizard with completeness meter (0%)
    
    rect rgb(240, 248, 255)
    note right of Official: Section 1 & 2: Geography & Population
    Official->>UI: Uploads `boroughs_boundary.geojson` & `commute_flows.csv`
    UI->>Intake: Column mapper validates units, checks missing fields
    Intake-->>Official: Displays 2 warnings (rural density estimated, marked Class C)
    Official->>UI: Downloads Excel template for hospital ICU beds, fills & uploads
    end

    rect rgb(255, 250, 240)
    note right of Official: Section 4 & 5: Pathogen & Behavior
    Official->>UI: Selects "Respiratory Generic (R0 2.8)", clicks "Customize"
    Official->>UI: Enters local survey compliance rate (68%), tags source
    UI->>Ledger: Records checksums, tags inputs as `user_supplied` (Class A/B)
    end

    rect rgb(245, 255, 245)
    note right of Official: Review & Launch
    Official->>UI: Reaches "Review & Launch" (Completeness: 94%, Resolution: 50,000 agents)
    UI->>Official: Shows Resource Estimate: ~1.2 GB RAM, ~22s execution, Trust Tier: CALIBRATED
    Official->>UI: Clicks "Launch Live Simulation"
    end

    rect rgb(240, 245, 255)
    note right of Official: Live Simulation Stage
    UI->>Engine: Connects via WebSocket (`/api/v2/runs/{id}/live`)
    Engine-->>UI: Streams daily frames (day, area states, commuter fluxes, hospital strain)
    UI->>Official: Animates infection spread; story caption: "Day 19: Central ICU reaches 92% capacity"
    Official->>UI: Clicks "PAUSE" at Day 22
    Engine-->>UI: Checkpoints state to disk (run survives browser restart)
    Official->>UI: Clicks "Intervene Now" -> Inject School Closure (Day 23)
    Official->>UI: Clicks "Branch Run" ("Branch A: Rapid Closure") and hits PLAY
    Engine-->>UI: Simulates branch to completion (Day 60)
    end

    rect rgb(255, 245, 250)
    note right of Official: Insights & Export
    Official->>UI: Switches to "Insights" Mode
    UI->>Official: Shows counterfactual comparison: Baseline vs Branch A (340 fewer ICU deaths)
    Official->>UI: Clicks "Export Official Briefing (PDF & JSON Ledger)"
    UI->>Official: Generates cryptographically signed dossier with explicit Class C assumption appendix
    end
```

---

## Journey 2: First-Time Visitor / Auditor (Instant Demo & Verification)

### Goal:
Experience the system's live capabilities within 45 seconds without configuring raw data, while seeing absolute transparency regarding validation status.

1. **Arrival & Landing**:
   - The user opens `http://localhost:8000`.
   - The top bar immediately shows a distinct **`DEMO: London Wave 1 (2020)`** banner alongside the **`UNCALIBRATED / CLASS C`** evidence badge.
   - The user is greeted by a streamlined hero modal: *"Explore preloaded London demonstration or create your own authority Case File."*
2. **Instant Live Replay**:
   - The user clicks **"Watch London Outbreak (Live Stage)"**.
   - The app transitions to the **Simulate Stage** in under 1 second.
   - The simulation plays immediately from cached daily frames at 60 fps:
     - 33 London local authorities pulse with color-coded infection prevalence.
     - Sampled commuter figures traverse the transit network along commuter arcs.
     - NHS acute & ICU capacity strain bars rise.
     - Live story captions report historical timeline events (e.g. *"Day 14: Stay-at-home order announced"*).
3. **Interactive Control & Scrutiny**:
   - The user drags the timeline scrubber back to Day 10, pauses, steps frame-by-frame (+1 day).
   - The user clicks the **Trust & Data Drawer** at the top right:
     - The sliding drawer reveals the exact validation scorecard: 0 integrity violations, London spatial arrival rank correlation ($\rho = 0.678$), and all SHA-256 ledger records.
   - The user is satisfied that the system is scientifically rigorous, completely honest about its data origins, and ready for production deployment.
