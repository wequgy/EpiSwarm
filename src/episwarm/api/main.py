"""FastAPI application service for EpiSwarm Studio (Phase 24).

Exposes simulation execution, replicate analysis, pre-registered validation cards,
assumptions provenance, and isometric diorama topology.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import yaml
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.engine.sim import run_simulation
from episwarm.analysis.replicates import run_replicates, ReplicateSummary


app = FastAPI(
    title="EpiSwarm Studio API",
    description="Agent-based epidemic simulation, policy optimization, and validation platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SimulationRequest(BaseModel):
    region_id: str = Field(default="example_synthetic", description="Region identifier")
    disease_id: str = Field(default="respiratory_generic", description="Pathogen pack identifier")
    scenario_id: str = Field(default="targeted_containment", description="Scenario pack identifier")
    scale_agents: int = Field(default=3000, ge=500, le=50000, description="Synthetic agent population size")
    behavior_mode: str = Field(default="rule", description="Behavior policy mode: none | rule | llm")
    n_replicates: int = Field(default=5, ge=1, le=50, description="Number of stochastic replicates for intervals")
    random_seed: int = Field(default=42, description="Random seed")
    horizon_days: Optional[int] = Field(default=None, description="Optional override for simulation horizon")


class WhatIfRequest(BaseModel):
    region_id: str = "example_synthetic"
    disease_id: str = "respiratory_generic"
    scenario_a: str = "baseline"
    scenario_b: str = "targeted_containment"
    scale_agents: int = 3000
    n_replicates: int = 5
    random_seed: int = 42


@app.get("/health")
def get_health() -> Dict[str, str]:
    return {"status": "ok", "service": "episwarm-api", "version": "1.0.0"}


@app.get("/api/regions")
def list_regions() -> List[Dict[str, Any]]:
    regions_root = Path("regions")
    results = []
    if not regions_root.exists():
        return results

    for r_dir in sorted(regions_root.iterdir()):
        if r_dir.is_dir():
            yaml_path = r_dir / "region.yaml"
            meta = {}
            if yaml_path.exists():
                try:
                    with open(yaml_path, "r", encoding="utf-8") as f:
                        meta = yaml.safe_load(f)
                except Exception:
                    pass
            results.append({
                "id": r_dir.name,
                "name": meta.get("name", r_dir.name),
                "areas_file_exists": (r_dir / "areas.csv").exists(),
                "contacts_file_exists": (r_dir / "contacts.csv").exists(),
                "provenance_status": "REAL" if (r_dir / "observed_cases.csv").exists() else "SYNTHETIC"
            })
    return results


@app.get("/api/scenarios")
def list_scenarios() -> List[Dict[str, Any]]:
    scen_root = Path("scenarios")
    results = []
    if not scen_root.exists():
        return results

    for s_file in sorted(scen_root.glob("*.yaml")):
        try:
            with open(s_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            results.append({
                "id": s_file.stem,
                "name": data.get("name", s_file.stem),
                "horizon_days": data.get("horizon_days", 90),
                "behavior_mode": data.get("behavior_mode", "rule"),
                "n_interventions": len(data.get("interventions", []))
            })
        except Exception:
            pass
    return results


@app.get("/api/validation-card")
def get_validation_card() -> Dict[str, Any]:
    card_path = Path("docs/validation/VALIDATION_CARD.json")
    if not card_path.exists():
        raise HTTPException(status_code=404, detail="Validation card not found")
    with open(card_path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/assumptions")
def get_assumptions() -> List[Dict[str, Any]]:
    """Return live list of all execution parameters, thresholds, and their provenance records."""
    from episwarm.packs.behavior import BehaviorExecutionConfig
    cfg = BehaviorExecutionConfig()

    return [
        {
            "parameter": "compliance_baseline",
            "value": cfg.compliance_baseline,
            "source": "assumed (F1 audit / Phase 17)",
            "status": "ASSUMED",
            "notes": "Baseline execution probability at zero compliance"
        },
        {
            "parameter": "compliance_slope",
            "value": cfg.compliance_slope,
            "source": "assumed (F1 audit / Phase 17)",
            "status": "ASSUMED",
            "notes": "Compliance multiplier slope"
        },
        {
            "parameter": "compliance_acquisition_reduction",
            "value": cfg.compliance_acquisition_reduction,
            "source": "assumed (Phase 17 audit F5)",
            "status": "ASSUMED",
            "notes": "Direct transmission acquisition reduction from compliance"
        },
        {
            "parameter": "area_risk_medium_threshold",
            "value": cfg.area_risk_medium_threshold,
            "source": "assumed (Phase 17 audit F5)",
            "status": "ASSUMED",
            "notes": "Incidence rate threshold for medium area risk band"
        },
        {
            "parameter": "area_risk_critical_threshold",
            "value": cfg.area_risk_critical_threshold,
            "source": "assumed (Phase 17 audit F5)",
            "status": "ASSUMED",
            "notes": "Incidence rate threshold for critical area risk band"
        },
        {
            "parameter": "external_inflow_fraction",
            "value": cfg.external_inflow_fraction,
            "source": "assumed (Phase 17 audit F5)",
            "status": "ASSUMED",
            "notes": "External patient inflow fraction into regional hospitals"
        }
    ]


@app.get("/api/diorama")
def get_diorama_topology(region_id: str = "example_synthetic") -> Dict[str, Any]:
    """Provide isometric coordinates, areas, and multi-layer layout for city diorama visualization."""
    region_dir = Path(f"regions/{region_id}")
    if not region_dir.exists():
        region_dir = Path("regions/example_synthetic")

    areas_file = region_dir / "areas.csv"
    if not areas_file.exists():
        raise HTTPException(status_code=404, detail=f"No areas file found for region {region_id}")

    df_areas = pd.read_csv(areas_file)
    n_areas = len(df_areas)

    cols = int(np.ceil(np.sqrt(n_areas)))
    boroughs = []
    for idx, row in df_areas.iterrows():
        col_idx = idx % cols
        row_idx = idx // cols
        iso_x = (col_idx - row_idx) * 90
        iso_y = (col_idx + row_idx) * 45

        boroughs.append({
            "id": str(row.get("area_id", f"A{idx:02d}")),
            "name": str(row.get("name", row.get("area_id", f"Area {idx+1}"))),
            "population": int(row.get("population", 50000)),
            "density": float(row.get("density", 4500)),
            "iso_x": iso_x,
            "iso_y": iso_y,
            "layers": ["household", "school", "workplace", "healthcare", "community"]
        })

    return {
        "region_id": region_dir.name,
        "n_boroughs": len(boroughs),
        "boroughs": boroughs,
        "layers": [
            {"id": "household", "name": "Households & Residential", "color": "#4a90e2", "altitude": 0},
            {"id": "school", "name": "Schools & Education", "color": "#f5a623", "altitude": 30},
            {"id": "workplace", "name": "Commercial & Workplaces", "color": "#7ed321", "altitude": 60},
            {"id": "healthcare", "name": "Clinics & Hospitals", "color": "#d0021b", "altitude": 90},
            {"id": "transit", "name": "Commute & Transit Network", "color": "#9013fe", "altitude": 15}
        ]
    }


@app.post("/api/simulate")
def run_simulation_endpoint(req: SimulationRequest) -> Dict[str, Any]:
    """Execute replicate simulation with confidence intervals and full assumptions."""
    region_dir = Path(f"regions/{req.region_id}")
    if not region_dir.exists():
        region_dir = Path("regions/example_synthetic")

    disease_file = Path(f"diseases/{req.disease_id}.yaml")
    if not disease_file.exists():
        disease_file = Path("diseases/respiratory_generic.yaml")
    with open(disease_file, "r", encoding="utf-8") as f:
        d_pack = DiseasePack(**yaml.safe_load(f))

    scenario_file = Path(f"scenarios/{req.scenario_id}.yaml")
    if not scenario_file.exists():
        scenario_file = Path("scenarios/targeted_containment.yaml")
    with open(scenario_file, "r", encoding="utf-8") as f:
        s_pack = ScenarioPack(**yaml.safe_load(f))

    if req.horizon_days:
        s_pack.horizon_days = req.horizon_days

    s_pack.behavior_mode = req.behavior_mode

    pop = build_synthetic_population(
        region_dir=region_dir,
        scale_agents=req.scale_agents,
        random_seed=req.random_seed
    )

    summary = run_replicates(
        pop=pop,
        disease_pack=d_pack,
        scenario_pack=s_pack,
        n_replicates=req.n_replicates,
        base_seed=req.random_seed,
        behavior_mode=req.behavior_mode
    )

    return {
        "region_id": region_dir.name,
        "disease_id": d_pack.name,
        "scenario_id": s_pack.name,
        "behavior_mode": req.behavior_mode,
        "n_replicates": req.n_replicates,
        "scale_agents": req.scale_agents,
        "metrics": {
            "attack_rate": {
                "mean": summary.means["attack_rate"],
                "ci_lower": summary.ci_95_lower["attack_rate"],
                "ci_upper": summary.ci_95_upper["attack_rate"],
            },
            "peak_day": {
                "mean": summary.means["peak_day"],
                "ci_lower": summary.ci_95_lower["peak_day"],
                "ci_upper": summary.ci_95_upper["peak_day"],
            },
            "total_deaths": {
                "mean": summary.means["total_deaths"],
                "ci_lower": summary.ci_95_lower["total_deaths"],
                "ci_upper": summary.ci_95_upper["total_deaths"],
            },
            "peak_hospital_demand": {
                "mean": summary.means["peak_hospital_demand"],
                "ci_lower": summary.ci_95_lower["peak_hospital_demand"],
                "ci_upper": summary.ci_95_upper["peak_hospital_demand"],
            },
            "peak_icu_demand": {
                "mean": summary.means["peak_icu_demand"],
                "ci_lower": summary.ci_95_lower["peak_icu_demand"],
                "ci_upper": summary.ci_95_upper["peak_icu_demand"],
            }
        },
        "timeseries": {
            "replicate_seeds": [s.seed for s in summary.per_seed],
            "attack_rates": [s.attack_rate for s in summary.per_seed],
            "peak_days": [s.peak_day for s in summary.per_seed],
            "peak_hospital": [s.peak_hospital_demand for s in summary.per_seed]
        },
        "per_seed": [
            {
                "seed": s.seed,
                "attack_rate": s.attack_rate,
                "peak_day": s.peak_day,
                "total_deaths": s.total_deaths
            }
            for s in summary.per_seed
        ],
        "validation_status": "PARTIALLY_VALIDATED",
        "validation_card_url": "/api/validation-card"
    }


@app.post("/api/what-if")
def compare_scenarios_endpoint(req: WhatIfRequest) -> Dict[str, Any]:
    """Compare two scenarios under paired replicate random seeds."""
    region_dir = Path(f"regions/{req.region_id}")
    if not region_dir.exists():
        region_dir = Path("regions/example_synthetic")

    disease_file = Path(f"diseases/{req.disease_id}.yaml")
    if not disease_file.exists():
        disease_file = Path("diseases/respiratory_generic.yaml")
    with open(disease_file, "r", encoding="utf-8") as f:
        d_pack = DiseasePack(**yaml.safe_load(f))

    with open(f"scenarios/{req.scenario_a}.yaml", "r", encoding="utf-8") as f:
        s_pack_a = ScenarioPack(**yaml.safe_load(f))

    with open(f"scenarios/{req.scenario_b}.yaml", "r", encoding="utf-8") as f:
        s_pack_b = ScenarioPack(**yaml.safe_load(f))

    pop = build_synthetic_population(
        region_dir=region_dir,
        scale_agents=req.scale_agents,
        random_seed=req.random_seed
    )

    summary = run_replicates(
        pop=pop,
        disease_pack=d_pack,
        scenario_pack=s_pack_a,
        paired_scenario=s_pack_b,
        n_replicates=req.n_replicates,
        base_seed=req.random_seed
    )

    return {
        "scenario_a": req.scenario_a,
        "scenario_b": req.scenario_b,
        "n_replicates": req.n_replicates,
        "means_a": summary.means,
        "delta_means": summary.delta_means,
        "delta_ci_95_lower": summary.delta_ci_95_lower,
        "delta_ci_95_upper": summary.delta_ci_95_upper,
        "comparison": {
            "delta_attack_rate": summary.delta_means.get("attack_rate", 0.0) if summary.delta_means else 0.0,
            "delta_deaths": summary.delta_means.get("total_deaths", 0.0) if summary.delta_means else 0.0,
            "delta_peak_hospital": summary.delta_means.get("peak_hospital_demand", 0.0) if summary.delta_means else 0.0
        }
    }
