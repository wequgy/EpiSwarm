# EpiSwarm Studio v2: Live Run WebSocket Protocol Specification

## 1. Connection Lifecycle
The live simulation streaming and interactive control channel is mediated via WebSocket at:
```
ws://127.0.0.1:8000/api/v2/runs/{job_id}/live
```
Fallback: Where WebSockets are restricted by reverse proxies, the client falls back to the existing SSE stream (`/api/v1/runs/{job_id}/stream`) for read-only telemetry.

---

## 2. Client-to-Server Command Messages (`LiveCommand`)

Commands are dispatched as JSON objects with a mandatory `type` discriminant:

### 2.1 Playback Controls
```typescript
// Resume or start simulation execution
{ "type": "play" }

// Pause simulation at the end of the current simulated day (emits checkpoint)
{ "type": "pause" }

// Step forward exactly N simulated days, then pause
{ "type": "step", "n_days": 1 }

// Adjust frame emission pacing (multiplier: 0.5x, 1x, 2x, 5x, 10x)
{ "type": "speed", "speed_multiplier": 2.0 }

// Scrub / seek to historical day (replay from local frame store)
{ "type": "seek", "target_day": 14 }

// Terminate run and release compute workers
{ "type": "stop" }
```

### 2.2 Live Intervention Injection
Injects a non-pharmaceutical measure or clinical resource surge taking effect on the next simulated day:
```typescript
{
  "type": "inject",
  "action": {
    "measure_type": "school_closure" | "mask_mandate" | "curfew" | "resource_add",
    "area_ids": ["E09000007", "E09000001"] | "ALL",
    "stringency": 0.85,
    "effective_day": 24,
    "duration_days": 14,
    "description": "Emergency primary and secondary school suspension in high-prevalence boroughs."
  }
}
```

### 2.3 Counterfactual Branching
Forks an active or historical checkpoint into a new independent simulation run:
```typescript
{
  "type": "branch",
  "checkpoint_day": 22,
  "branch_label": "Branch A: Strict Curfew from Day 22",
  "parameter_overrides": {
    "/scenario/interventions/curfew/stringency": 0.90
  }
}
```

---

## 3. Server-to-Client Daily Frame Schema (`LiveDayFrame`)

For each simulated day, the engine packages a compact telemetry frame:
```typescript
interface LiveDayFrame {
  job_id: string;
  day: number;
  date_iso: string;                     // e.g. "2020-03-24"
  execution_state: 'running' | 'paused' | 'completed' | 'failed';
  
  // 1. Global Compartment Totals
  global_counts: {
    S: number;
    E: number;
    I_asymp: number;
    I_symp: number;
    Hosp: number;
    ICU: number;
    R: number;
    D: number;
  };
  
  // 2. Area-level Telemetry (keyed by area_id)
  area_metrics: Record<string, {
    active_infections: number;
    new_infections_today: number;
    prevalence_rate: number;            // [0.0, 1.0]
    mean_compliance: number;            // [0.0, 1.0]
    rumor_belief_rate?: number;         // [0.0, 1.0]
  }>;
  
  // 3. Clinical Strain & Occupancy
  hospital_status: Record<string, {
    hospital_id: string;
    acute_beds_occupied: number;
    acute_capacity: number;
    icu_beds_occupied: number;
    icu_capacity: number;
    is_breached: boolean;
    unserved_today: number;
  }>;
  
  // 4. Epidemiological Metrics
  effective_r: number;                  // R_t estimate
  cumulative_deaths: number;
  
  // 5. Active Policies
  active_measures: string[];            // e.g. ["mask_mandate", "school_closure"]
  
  // 6. Plain-Language Narrative Events
  narrative_events: Array<{
    severity: 'info' | 'warning' | 'critical';
    message: string;                    // e.g. "ICU in Camden has reached 100% capacity; 4 patients unserved."
    area_id?: string;
  }>;
  
  // 7. Aggregate Commuter Fluxes (inter-borough active transmission load)
  commuter_flows: Array<{
    origin_area: string;
    destination_area: string;
    infectious_commuters: number;
  }>;
  
  // 8. Sampled Real Agents (Sub-sampled cohort for illustrative animation)
  sampled_agents: Array<{
    id: number;
    home_area: string;
    work_area: string;
    state: string;                      // "S" | "E" | "I" | "R"
    state_changed_today: boolean;
  }>;
}
```

---

## 4. Backpressure & Client Acknowledgement
- In **Watch Mode**, the server maintains a frame buffer of at most 3 frames. It waits for the client to send `{ "type": "ack", "day": N }` before emitting the next frame, ensuring animation smoothness even on modest hardware.
- In **Fast Mode**, frames stream at full computational speed and are persisted directly to the local chunked Frame Store on disk (`runs/{job_id}/frames.bin`) for subsequent scrubbing and replay.
