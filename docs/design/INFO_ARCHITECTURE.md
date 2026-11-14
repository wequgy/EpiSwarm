# EpiSwarm Studio v2: Information Architecture

## 1. Architectural Philosophy
EpiSwarm Studio v2 replaces the legacy 17-item persistent left sidebar with a focused, high-authority **canvas-first** architecture tailored for government health authorities and scientific teams:
- **No permanent sidebar**: The canvas occupies 100% of the viewport width.
- **Three Core Modes**:
  1. **Case File**: Full intake workspace where officials configure and audit their city/region case file.
  2. **Simulate**: The live, interactive Simulation Stage canvas with real-time spread animation, commuter fluxes, and playback dock.
  3. **Insights**: In-depth analytical suite synthesizing epidemiological curves, bed capacity, equity, Pareto frontiers, and advisor chat.
- **Top Utility Drawer**: **Trust & Data**, accessible globally to inspect validation scorecards, cryptographic evidence ledgers, and engine backends without leaving the active mode.
- **Global Command Palette (`Ctrl+K`)**: Rapid keyboard-driven navigation across any parameter, borough, hospital, or scenario.

---

## 2. Information Architecture Diagram

```mermaid
flowchart TD
    subgraph Global ["Top Bar & Global Overlay"]
        Brand["EpiSwarm Studio v2"]
        ModeSwitch["Mode Switcher: Case File | Simulate | Insights"]
        TrustBadge["Trust Tier Badge (UNCALIBRATED | CALIBRATED | VALIDATED)"]
        DemoBadge["DEMO Indicator (London Wave 1 / Sandbox)"]
        CmdK["Command Palette (Ctrl+K)"]
        TrustDrawerBtn["Trust & Data Drawer Toggle"]
    end

    subgraph TrustDrawer ["Trust & Data Drawer (Slide-down / Overlay)"]
        ValCard["Validation Scorecard & Pre-registered Targets"]
        EvLedger["Evidence Ledger Audit (SHA-256 Checksums)"]
        AssumpList["Assumptions & Influence Ranking"]
        Backends["Simulation Compute & LLM Engines"]
    end

    subgraph CaseFile ["Mode 1: Case File (Intake Workspace)"]
        CF_Nav["Intake Progress & Completeness Bar"]
        S1["1. Area & Population (Boundaries, Households, Age/Sex)"]
        S2["2. Work, Schools & Venues (Commuter Matrix, School Classes)"]
        S3["3. Health System (Hospitals, Beds, Surges, Referral)"]
        S4["4. Disease Graph (State Machine, Durations, Vulnerabilities)"]
        S5["5. People & Behavior (Compliance, Rumors, Distilled Student)"]
        S6["6. Measures & Timeline (NPIs, Closures, Curfews)"]
        S7["7. Run Settings (Agents 50k-100k, Replicates, Seeds, Horizon)"]
        S8["8. Review & Launch (Completeness, Impact Ranking, Trust Gate)"]
    end

    subgraph SimulateStage ["Mode 2: Simulate (The Simulation Stage)"]
        StageCanvas["Full-Screen Interactive Stage (GeoJSON / Cartogram)"]
        HUD["Heads-Up Display (Day, Total Infected, Bed Strain, R_eff)"]
        StoryFeed["Plain-Language Story Captions ('Day 28: ICU full in Camden')"]
        Dock["Control Dock (Play | Pause | Step | Speed | Intervene | Branch)"]
        InspectDrawer["Slide-over Inspector (Borough, Hospital, Sampled Agent)"]
    end

    subgraph InsightsMode ["Mode 3: Insights (Analysis & Outcomes)"]
        Tabs["Insights Tabs"]
        T1["Epidemic Trajectories (SEIR Ensembles)"]
        T2["Spatial Arrival & Borough Order"]
        T3["Healthcare & ICU Stress Analysis"]
        T4["Demographic & Income Equity Disparities"]
        T5["Counterfactual Compare & What-If Branching"]
        T6["Marginal Resource Value & Pareto Frontier"]
        T7["AI Policy Advisor Chat (Agent Layer v3)"]
    end

    TrustDrawerBtn --> TrustDrawer
    ModeSwitch --> CaseFile
    ModeSwitch --> SimulateStage
    ModeSwitch --> InsightsMode
```

---

## 3. Screen Inventory & Component Mapping

| Screen / Component | Mode / Area | Legacy Studio Equivalent | Key Upgrades |
|---|---|---|---|
| **Case File Overview** | Case File | `/regions`, `/diseases`, `/scenarios` | Single unified versioned Case File container with audit logs, duplication, and export. |
| **Intake Sections 1–8** | Case File | `/builder`, `/quick` | Guided step-by-step intake forms, CSV/Excel column mappers, downloadable templates, and "Estimate for Me" AI assistant. |
| **Simulation Stage** | Simulate | `/spatial` (was static 357-line SVG) | Full-screen live canvas, animated commuter figures (labeled illustrative), hospital strain meters, real-time story feed. |
| **Control Dock & HUD** | Simulate | `/runs` form | In-run interactive controls: play, pause, step-1, speed (1x-10x), instant intervention injection, and checkpoint branching. |
| **Insights Hub** | Insights | `/results`, `/capacity`, `/equity`, `/compare`, `/optimization`, `/advisor` | Unified multi-tabbed analytical suite with ensemble confidence bands, Pareto curves, and spatial rankings. |
| **Trust & Data Drawer** | Global Drawer | `/validation`, `/evidence`, `/settings` | Global slide-down drawer exposing SHA-256 provenance hashes, validation gates, and backend status without leaving the run. |

