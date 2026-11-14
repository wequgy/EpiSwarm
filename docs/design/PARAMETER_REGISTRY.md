# EpiSwarm Studio v2: Parameter Registry & Dynamic Override System

## 1. Overview
The **Parameter Registry** provides a unified schema-driven mechanism allowing the UI to discover, validate, edit, calibrate, and override any simulation parameter across all packs (`RegionPack`, `DiseasePack`, `ScenarioPack`, `BehaviorPack`, `RunConfig`) without manually mutating pack YAML files on disk.

Every parameter is identified by an RFC 6901 **JSON Pointer** path. When launching or branching a run, the UI sends a map of `{ [json_pointer]: value }` overrides that the service facade dynamically patches into the in-memory pack models.

---

## 2. Parameter Schema Specification
Every registered parameter exposes the following schema:
```typescript
interface ParameterDescriptor<T = any> {
  path: string;                    // e.g. "/disease/transmission/r0"
  label: string;                   // Display title
  unit: string | null;             // e.g. "ratio", "days", "beds", "probability"
  description: string;             // Plain-language scientific definition
  type: 'number' | 'integer' | 'boolean' | 'string' | 'distribution' | 'matrix';
  bounds?: { min?: number; max?: number; step?: number };
  default_value: T;
  pack_type: 'region' | 'disease' | 'scenario' | 'behavior' | 'run';
  level: 'Basic' | 'Advanced' | 'Expert';
  dependencies?: string[];         // Other pointer paths this parameter requires
  evidence_class: 'A' | 'B' | 'C'; // Provenance tier
  provenance?: { source: string; locator?: string; doi?: string };
  affects: Array<'transmission' | 'severity' | 'healthcare' | 'compliance' | 'spatial'>;
  calibratable: boolean;           // Whether SMC-ABC or Bayesian optimization can tune it
}
```

---

## 3. Five Concrete Example Parameter Definitions

### Example 1: Basic Disease Transmission ($R_0$)
```json
{
  "path": "/disease/transmission/r0",
  "label": "Basic Reproductive Number (R0)",
  "unit": "ratio",
  "description": "Expected secondary infections produced by a single infectious individual in a fully susceptible population with nominal mixing.",
  "type": "number",
  "bounds": { "min": 0.5, "max": 8.0, "step": 0.05 },
  "default_value": 2.8,
  "pack_type": "disease",
  "level": "Basic",
  "evidence_class": "B",
  "provenance": { "source": "Ferguson et al. 2020", "locator": "Report 9, Table 1" },
  "affects": ["transmission"],
  "calibratable": true
}
```

### Example 2: Household Layer Contact Multiplier
```json
{
  "path": "/disease/transmission/layer_weights/home",
  "label": "Household Layer Relative Weight",
  "unit": "multiplier",
  "description": "Relative transmission efficiency per contact in the household layer compared to community settings.",
  "type": "number",
  "bounds": { "min": 0.5, "max": 4.0, "step": 0.1 },
  "default_value": 1.8,
  "pack_type": "disease",
  "level": "Advanced",
  "evidence_class": "B",
  "provenance": { "source": "CoMix UK Survey / Mossong et al." },
  "affects": ["transmission"],
  "calibratable": true
}
```

### Example 3: Effective ICU Bed Surge Threshold
```json
{
  "path": "/region/resources/icu_beds/effective_capacity",
  "label": "Effective ICU Ventilated Capacity",
  "unit": "beds",
  "description": "Maximum number of simultaneous critical care patients supported before overflow protocols are triggered.",
  "type": "integer",
  "bounds": { "min": 10, "max": 5000, "step": 1 },
  "default_value": 480,
  "pack_type": "region",
  "level": "Basic",
  "evidence_class": "A",
  "provenance": { "source": "NHS England Acute & Critical Care Bed SitRep" },
  "affects": ["healthcare"],
  "calibratable": false
}
```

### Example 4: Secondary Misinformation Spread Rate ($\beta_{rumor}$)
```json
{
  "path": "/behavior/rumor/spread_rate",
  "label": "Misinformation Transmission Probability",
  "unit": "probability / social contact",
  "description": "Probability that an uninfected peer adopts a rumor topic upon interaction with a believing social contact.",
  "type": "number",
  "bounds": { "min": 0.005, "max": 0.25, "step": 0.005 },
  "default_value": 0.05,
  "pack_type": "behavior",
  "level": "Advanced",
  "evidence_class": "C",
  "provenance": { "source": "EpiSwarm Psychographic Default Prior" },
  "affects": ["compliance"],
  "calibratable": true
}
```

### Example 5: Mask Mandate Transmission Reduction Factor
```json
{
  "path": "/scenario/interventions/mask_mandate/efficiency",
  "label": "Universal Masking Inward/Outward Reduction",
  "unit": "fractional reduction",
  "description": "Reduction in aerosol and droplet transmission load when a compliant individual wears a standard face covering.",
  "type": "number",
  "bounds": { "min": 0.1, "max": 0.85, "step": 0.05 },
  "default_value": 0.45,
  "pack_type": "scenario",
  "level": "Basic",
  "evidence_class": "B",
  "provenance": { "source": "Chu et al. Lancet Systematic Review 2020" },
  "affects": ["transmission", "compliance"],
  "calibratable": false
}
```

---

## 4. REST API Endpoint Contract
- **Schema Discovery**: `GET /api/v2/parameters/schema` returns the complete array of all registered `ParameterDescriptor` objects.
- **Run Overrides Payload**:
```json
{
  "region_id": "reference_london",
  "disease_id": "respiratory_generic",
  "scenario_id": "targeted_containment",
  "scale_agents": 50000,
  "overrides": {
    "/disease/transmission/r0": 3.1,
    "/behavior/rumor/spread_rate": 0.08,
    "/region/resources/icu_beds/effective_capacity": 550
  }
}
```

