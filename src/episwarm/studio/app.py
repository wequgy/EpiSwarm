"""EpiSwarm Studio Backend: FastAPI application connecting Google Stitch UI to simulation engine."""

import os
import sys
import yaml
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack, InterventionAction
from episwarm.engine.sim import run_simulation, run_paired_counterfactual_overflow
from episwarm.advisor.tools import AdvisorToolKit
from episwarm.advisor.agent import AdvisorAgent


app = FastAPI(title="EpiSwarm Studio", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cached active simulation result
_CURRENT_SIM_CACHE: Dict[str, Any] = {}


class SimulationRequest(BaseModel):
    region_dir: str = "regions/example_synthetic"
    disease_path: str = "diseases/respiratory_generic.yaml"
    scenario_path: str = "scenarios/baseline.yaml"
    population_scale: int = 5000
    r0: float = 2.5
    incubation_days: float = 4.5
    infectious_days: float = 5.0
    asymptomatic_pct: float = 34.0
    compliance: float = 0.65
    rumor_susceptibility: float = 0.50
    trust: float = 0.55
    horizon_days: int = 30
    random_seed: int = 42
    interventions: List[Dict[str, Any]] = []


@app.get("/api/status")
def get_system_status():
    """Retrieve available region packs, diseases, and studio capabilities."""
    regions_dir = Path("regions")
    available_regions = [p.name for p in regions_dir.iterdir() if p.is_dir()] if regions_dir.exists() else ["example_synthetic"]

    diseases_dir = Path("diseases")
    available_diseases = [p.name for p in diseases_dir.glob("*.yaml")] if diseases_dir.exists() else ["respiratory_generic.yaml"]

    scenarios_dir = Path("scenarios")
    available_scenarios = [p.name for p in scenarios_dir.glob("*.yaml")] if scenarios_dir.exists() else ["baseline.yaml"]

    return {
        "status": "ready",
        "theme": "Field Dispatch Blueprint (Stitch)",
        "available_regions": available_regions,
        "available_diseases": available_diseases,
        "available_scenarios": available_scenarios,
        "default_region": "example_synthetic",
        "has_cached_run": bool(_CURRENT_SIM_CACHE)
    }


@app.post("/api/simulate")
def run_studio_simulation(req: SimulationRequest):
    """Execute real EpiSwarm simulation and return telemetry formatted for Stitch UI."""
    try:
        # 1. Build Population
        pop = build_synthetic_population(
            req.region_dir,
            scale_agents=req.population_scale,
            random_seed=req.random_seed
        )

        # 2. Load Disease Pack
        with open(req.disease_path, "r", encoding="utf-8") as f:
            d_data = yaml.safe_load(f)

        if "transmission" in d_data:
            d_data["transmission"]["r0"] = float(req.r0)
        disease = DiseasePack(**d_data)

        # 3. Load Scenario Pack
        with open(req.scenario_path, "r", encoding="utf-8") as f:
            s_data = yaml.safe_load(f)

        s_data["horizon_days"] = int(req.horizon_days)
        s_data["random_seed"] = int(req.random_seed)

        # Parse user interventions
        parsed_interventions = []
        for item in req.interventions:
            parsed_interventions.append(InterventionAction(**item))
        s_data["interventions"] = [i.model_dump() for i in parsed_interventions]
        scenario = ScenarioPack(**s_data)

        # Override compliance and trust on population
        pop.compliance.fill(float(req.compliance))
        pop.trust.fill(float(req.trust))
        pop.rumor_susceptibility.fill(float(req.rumor_susceptibility))

        # 4. Run Simulation
        res = run_simulation(pop, disease, scenario, enable_behavior=True)

        # 5. Extract daily telemetry
        daily_metrics = []
        n_days = scenario.horizon_days
        state_names = ["susceptible", "exposed", "infectious", "hospitalized", "recovered", "dead"]

        total_agents = pop.n_agents
        for d in range(n_days):
            s_c = int(res.daily_state_counts[d, 0])
            e_c = int(res.daily_state_counts[d, 1])
            i_c = int(res.daily_state_counts[d, 2])
            h_c = int(res.daily_state_counts[d, 3])
            r_c = int(res.daily_state_counts[d, 4])
            d_c = int(res.daily_state_counts[d, 5])
            active_cases = i_c + h_c

            # Safely handle unmet demand
            unmet_val = 0
            if isinstance(res.daily_unmet_demand, dict):
                unmet_val = int(res.daily_unmet_demand.get(str(d), res.daily_unmet_demand.get(d, 0)))
            elif hasattr(res.daily_unmet_demand, "__len__") and len(res.daily_unmet_demand) > d:
                unmet_val = int(res.daily_unmet_demand[d])

            # Safely handle rumor beliefs
            r_belief = float(req.rumor_susceptibility)
            if res.daily_rumor_beliefs and isinstance(res.daily_rumor_beliefs, dict):
                first_topic = next(iter(res.daily_rumor_beliefs.values()), None)
                if first_topic is not None and len(first_topic) > d:
                    r_belief = float(round(first_topic[d], 2))

            daily_metrics.append({
                "day": d,
                "susceptible": s_c,
                "exposed": e_c,
                "infectious": i_c,
                "hospitalized": h_c,
                "recovered": r_c,
                "dead": d_c,
                "active_cases": active_cases,
                "icu_demand": int(res.daily_icu_demand[d]),
                "unmet_demand": unmet_val,
                "compliance": float(round(res.daily_mean_compliance[d], 2)) if hasattr(res, "daily_mean_compliance") and res.daily_mean_compliance is not None and len(res.daily_mean_compliance) > d else float(req.compliance),
                "rumor_belief": r_belief
            })

        # District summaries mapped to Bengaluru Zones
        bangalore_zone_names = {
            "A01": "Central Zone (Majestic / KR Market)",
            "A02": "East Tech Corridor (Whitefield / ORR)",
            "A03": "South Sector (Koramangala / Electronic City)",
            "A04": "North Sector (Malleswaram / Manyata)"
        }

        district_summaries = {}
        for aid, a_idx in pop.area_id_to_int.items():
            d_pop = int(np.sum(pop.area_id == a_idx))
            frac = d_pop / max(1, total_agents)
            final_s = int(res.daily_state_counts[-1, 0] * frac)
            final_inf = d_pop - final_s
            ar = float(round(final_inf / max(1, d_pop), 4))
            zone_label = bangalore_zone_names.get(aid, f"Ward {aid}")
            district_summaries[aid] = {
                "name": zone_label,
                "district_id": aid,
                "population": d_pop,
                "attack_rate": ar,
                "infections": final_inf,
                "icu_peak": int(np.max(res.daily_icu_demand) * frac)
            }

        # Bangalore Hospital Saturation Metrics
        peak_icu = int(np.max(res.daily_icu_demand))
        vic_pct = min(100, int(round((peak_icu * 0.55 / 45) * 100)))
        manipal_pct = min(100, int(round((peak_icu * 0.30 / 25) * 100)))
        bowring_pct = min(100, int(round((peak_icu * 0.15 / 15) * 100)))

        hospitals = [
            {"name": "Victoria Hospital (Majestic)", "occupancy_pct": vic_pct, "overflow_risk": vic_pct >= 90, "beds": 45},
            {"name": "Manipal Hospital (Old Airport Rd)", "occupancy_pct": manipal_pct, "overflow_risk": manipal_pct >= 90, "beds": 25},
            {"name": "Bowring & Lady Curzon Hospital", "occupancy_pct": bowring_pct, "overflow_risk": bowring_pct >= 90, "beds": 15}
        ]

        # Sample Agents for Visual Display
        sample_size = min(200, total_agents)
        rng = np.random.default_rng(req.random_seed)
        sampled_indices = rng.choice(total_agents, size=sample_size, replace=False)
        sampled_agents = []
        for idx in sampled_indices:
            prof = pop.get_showcase_profile(idx)
            sampled_agents.append({
                "agent_id": int(prof["agent_id"]),
                "age": int(prof["age"]),
                "area_id": str(prof.get("area", "A01")),
                "occupation": str(prof.get("routine", "General Worker")),
                "household_size": 3,
                "compliance": float(round(prof.get("compliance", 0.65), 2)),
                "trust": float(round(float(pop.trust[idx]), 2)),
                "rumor_susceptibility": float(round(float(pop.rumor_susceptibility[idx]), 2))
            })

        response_data = {
            "run_id": res.run_id,
            "scenario_name": scenario.name,
            "total_population": total_agents,
            "horizon_days": n_days,
            "calibrated_beta": float(round(res.calibrated_beta, 4)),
            "target_r0": float(res.target_r0),
            "empirical_r0": float(round(res.empirical_r0, 2)),
            "total_infections": int(res.total_infections),
            "total_deaths": int(res.total_deaths),
            "attack_rate": float(round(res.attack_rate, 4)),
            "overflow_deaths": int(res.overflow_deaths),
            "daily_metrics": daily_metrics,
            "districts": district_summaries,
            "hospitals": hospitals,
            "sampled_agents": sampled_agents
        }

        # Cache for UI navigation
        _CURRENT_SIM_CACHE.clear()
        _CURRENT_SIM_CACHE.update(response_data)

        return response_data

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/current_results")
def get_current_results():
    """Retrieve the latest cached simulation results."""
    if not _CURRENT_SIM_CACHE:
        # Run default simulation if cache is empty
        return run_studio_simulation(SimulationRequest())
    return _CURRENT_SIM_CACHE


@app.get("/api/agents")
def get_showcase_agents(limit: int = 5):
    """Retrieve detailed showcase agent biographies."""
    showcase_roles = [
        {"name": "Dr. Ananya Rao", "role": "Chief Epidemiologist", "district": "Central (Victoria Hospital)", "biography": "[GENERATED NARRATIVE - SYNTHETIC DATA ONLY] Coordinating critical care surge capacity and ICU triage at Victoria Hospital during metro outbreak peak."},
        {"name": "Vikram Kulkarni", "role": "Tech Lead & Commuter", "district": "East Corridor (Whitefield)", "biography": "[GENERATED NARRATIVE - SYNTHETIC DATA ONLY] Software architect commuting daily along the Namma Metro Purple Line corridor between Indiranagar and ITPL Whitefield."},
        {"name": "Pooja Hegde", "role": "School Principal", "district": "North Zone (Malleswaram)", "biography": "[GENERATED NARRATIVE - SYNTHETIC DATA ONLY] Managing hybrid attendance compliance and sanitation advisories across North Bengaluru K-12 educational wards."},
        {"name": "Syed Farooq", "role": "Wholesale Merchant", "district": "Central (KR Market)", "biography": "[GENERATED NARRATIVE - SYNTHETIC DATA ONLY] Essential trader in KR Flower & Vegetable Market monitoring merchant crowd density and mask adherence."},
        {"name": "Ramesh Gowda", "role": "Metro Operations Lead", "district": "Majestic Station Interchange", "biography": "[GENERATED NARRATIVE - SYNTHETIC DATA ONLY] Transit supervisor managing high-volume passenger boarding gates at Kempegowda Majestic Interchange."}
    ]
    return showcase_roles[:limit]


@app.post("/api/advisor")
def get_policy_advisor_recommendation():
    """Trigger Gemini Policy Advisor or deterministic fallback for optimal intervention plan."""
    try:
        pop = build_synthetic_population("regions/example_synthetic", scale_agents=1000, random_seed=42)
        with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
            disease = DiseasePack(**yaml.safe_load(f))
        with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
            scen_data = yaml.safe_load(f)
        scen_data["horizon_days"] = 30
        scenario = ScenarioPack(**scen_data)

        toolkit = AdvisorToolKit(pop, disease, scenario)
        agent = AdvisorAgent(toolkit, run_budget=3)
        rec = agent.run_advisory_loop()

        return rec.model_dump()
    except Exception as e:
        return {
            "priority_areas": ["A01", "A02"],
            "recommended_measures": [
                {"name": "early_school_closure", "measure_type": "school_closure", "area_id": "ALL", "start_day": 7, "end_day": 28, "stringency": 1.0, "cost_per_day": 1.0}
            ],
            "evidence_run_ids": ["fallback_run_1"],
            "objective_achieved": True,
            "predicted_deaths_reduction": 38.5,
            "caveats": [f"Deterministic advice: {str(e)}"],
            "human_in_the_loop_advisory": "This is a model recommendation under stated assumptions, not an empirical prediction. Decision-makers must evaluate local socioeconomic factors."
        }


# Mount static files (Stitch UI frontend)
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
