# EpiSwarm Platform Architecture & Web Studio (v1.0.0)

EpiSwarm Studio is a decoupled full-stack platform for agent-based epidemic modeling, behavioral compliance dynamics, healthcare overflow analysis, and empirical benchmark validation.

---

## 1. Architecture Overview

```
+---------------------------------------------------------------------------------+
|                                 Browser Client                                  |
|   React 18 + TypeScript + Vite + Tailwind CSS + TanStack Query + ECharts + SVG   |
+---------------------------------------------------------------------------------+
                                        |
                         HTTP / REST & SSE Event Streams
                                        |
+---------------------------------------------------------------------------------+
|                            FastAPI Application (app)                            |
|  - Root SPA Static Serving (web/dist/) with HTML5 History Routing Fallback      |
|  - RFC 7807 problem+json Error Representation Handlers                          |
|  - API v1 Routers (/api/v1/*)                                                   |
|  - Legacy Compatibility Endpoints (/health, /api/regions, /api/simulate, etc.)  |
+---------------------------------------------------------------------------------+
                                        |
+---------------------------------------------------------------------------------+
|                                 Service Facade                                  |
|  - SimulationService: headless engine execution, what-if, scenario compare       |
|  - JobManager: SQLite-backed persistent queue (QUEUED/RUNNING/COMPLETED) & SSE  |
|  - PacksService: discovery, manifest parsing, and pack contract validation     |
|  - TrustService: benchmark cards, audit reports, assumptions register            |
|  - SystemService: backend health & model readiness without secret leakage       |
+---------------------------------------------------------------------------------+
                                        |
+---------------------------------------------------------------------------------+
|                             Core Scientific Kernels                             |
|  - Engine (PopulationSoA, compiled state graph, infection dynamics)             |
|  - Behavior (psychographic traits, social network, rumor belief dynamics)       |
|  - Evidence Ledger (evidence/ledger.db, SHA-256 downloads & derived tables)     |
+---------------------------------------------------------------------------------+
```

---

## 2. API v1 Endpoints

### System & Health
- `GET /api/v1/health`: Basic operational status and UTC timestamp.
- `GET /api/v1/backends`: Readiness of simulation engines (ABM, Gemini, TypeSafe Jev, Ollama, OpenAI, SQLite).

### Packs & Governance
- `GET /api/v1/packs/regions`: Installed regional geographies and readiness tiers (`L0`, `L1`, `L2`).
- `GET /api/v1/packs/regions/{id}`: Full regional manifest and table inventory.
- `POST /api/v1/packs/regions/{id}/validate`: Contract schema validation of tables.
- `GET /api/v1/packs/diseases`: Installed pathogen packs with R0 and incubation times.
- `POST /api/v1/packs/diseases/{id}/validate`: State graph reachability and probability validation.
- `GET /api/v1/packs/scenarios`: Policy intervention scenario definitions.
- `POST /api/v1/packs/scenarios/{id}/validate`: Action date bounds and stringency validation.
- `GET /api/v1/packs/behaviors`: Psychographic compliance distributions and rumor topics.

### Execution & Jobs
- `POST /api/v1/runs`: Submit asynchronous simulation job or synchronous mock run.
- `GET /api/v1/runs`: Paginated history of simulation jobs.
- `GET /api/v1/runs/{id}`: Status, completion percentage, and execution metadata.
- `POST /api/v1/runs/{id}/cancel`: Request immediate cancellation of a running job.
- `GET /api/v1/runs/{id}/events`: Server-Sent Events (SSE) streaming real-time simulation day progress.
- `GET /api/v1/runs/{id}/summary`: Executive outcome metrics with 95% confidence intervals.
- `GET /api/v1/runs/{id}/timeseries`: Multi-state compartmental trajectories (S, E, I, R, D) and compliance.
- `GET /api/v1/runs/{id}/spatial`: Borough-level incidence and isometric diorama coordinates.
- `GET /api/v1/runs/{id}/capacity`: Hospital & ICU bed demand curves and overflow durations.

### Advisory & Optimization
- `POST /api/v1/compare`: Paired counterfactual comparison between policies under identical seeds.
- `POST /api/v1/what-if`: Alias for counterfactual policy exploration.

### Trust & Evidence
- `GET /api/v1/validation/card`: Machine-readable validation card (`VALIDATION_CARD.json`).
- `GET /api/v1/validation/report`: Human-readable validation report markdown.
- `GET /api/v1/validation/assumptions`: Register of assumed parameters (Evidence Class C).
- `GET /api/v1/validation/evidence`: Cryptographic evidence ledger records.

---

## 3. Web Studio Features

- **Home Dashboard**: System readiness, benchmark validation status, and quick simulation launcher.
- **Simulation Runs**: Background job execution queue, progress bars, cancellation, and mock toggle.
- **Results Overview**: 95% confidence intervals on attack rates, peak days, hospital/ICU demand, and interactive compartmental curves.
- **3D Isometric City Diorama**: 3D extruded borough blocks, timeline wavefront scrubber, commute network lines, and layer toggles (household, school, workplace, healthcare, transit).
- **Healthcare Capacity**: Bed demand vs physical threshold curves, overflow duration, and attributable mortality.
- **Equity Analysis**: Comorbidity odds ratios, age-band mortality breakdown, and Gini spatial inequality metrics.
- **Behavior & Misinformation**: Rumor propagation curves and compliance fatigue decay.
- **Counterfactual Compare**: Side-by-side policy delta tables under paired stochastic seeds.
- **Marginal Value & Pareto Frontier**: Multi-objective Pareto frontier balancing cost disruption against infections averted.
- **Policy Advisor Agent**: Interactive chat assistant providing structured intervention recommendations.
- **Evidence & Governance**: Immutable ledger inspection of SHA-256 checksummed downloads.

---

## 4. Local Development & Deployment

### Development Mode
```powershell
# Run backend and frontend concurrently
.\scripts\dev.ps1

# Or run backend only
.\scripts\dev.ps1 -BackendOnly

# Or run frontend only
.\scripts\dev.ps1 -FrontendOnly
```

### Production Build
```powershell
Set-Location web
npm run build
```

### Docker Deployment
```bash
docker compose up --build -d
```
The application will be accessible at `http://localhost:8000`.
