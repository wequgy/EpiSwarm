"""API v2 router providing WebSocket live streaming, step controls, and parameter registry (Phase S1)."""

import asyncio
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from episwarm.packs.scenario import InterventionAction
from episwarm.service.estimator import ResourceEstimate, ResourceEstimator
from episwarm.service.live import LiveDayFrame, LiveRun
from episwarm.service.parameters import ParameterDescriptor, ParameterRegistryService
from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.packs.behavior import BehaviorPack
import yaml
from pathlib import Path

router = APIRouter(prefix="/v2", tags=["Live Simulation v2"])
registry_service = ParameterRegistryService()

# In-memory registry of active live runs
ACTIVE_LIVE_RUNS: Dict[str, LiveRun] = {}


def get_or_create_live_run(
    job_id: str,
    region_id: str = "reference_london",
    disease_id: str = "respiratory_generic",
    scenario_id: str = "targeted_containment",
    scale_agents: int = 50000,
    behavior_mode: str = "rule",
    random_seed: int = 42,
) -> LiveRun:
    """Retrieve active LiveRun or initialize a new instance."""
    if job_id in ACTIVE_LIVE_RUNS:
        return ACTIVE_LIVE_RUNS[job_id]

    r_dir = Path("regions") / region_id
    if not r_dir.exists():
        r_dir = Path("regions/example_synthetic")

    d_file = Path("diseases") / f"{disease_id}.yaml"
    with open(d_file, "r", encoding="utf-8") as f:
        d_pack = DiseasePack(**yaml.safe_load(f))

    s_file = Path("scenarios") / f"{scenario_id}.yaml"
    with open(s_file, "r", encoding="utf-8") as f:
        s_pack = ScenarioPack(**yaml.safe_load(f))
    s_pack.random_seed = random_seed

    b_file = Path("behavior/default.yaml")
    b_pack = None
    if b_file.exists():
        with open(b_file, "r", encoding="utf-8") as f:
            b_pack = BehaviorPack(**yaml.safe_load(f))

    pop = build_synthetic_population(
        region_dir=r_dir,
        scale_agents=scale_agents,
        random_seed=random_seed,
    )

    live_run = LiveRun(
        job_id=job_id,
        pop=pop,
        disease_pack=d_pack,
        scenario_pack=s_pack,
        behavior_pack=b_pack,
        behavior_mode=behavior_mode,
    )
    ACTIVE_LIVE_RUNS[job_id] = live_run
    return live_run


# ==============================================================================
# Parameter Registry Endpoints
# ==============================================================================

@router.get("/parameters/schema", response_model=List[ParameterDescriptor])
def list_parameters() -> List[ParameterDescriptor]:
    """Retrieve registry schema of all customizable simulation parameters."""
    return registry_service.list_parameters()


@router.get("/runs/estimate", response_model=ResourceEstimate)
def estimate_resources(
    scale_agents: int = Query(default=50000, ge=100, le=500000),
    n_replicates: int = Query(default=5, ge=1, le=50),
    horizon_days: int = Query(default=60, ge=1, le=365),
) -> ResourceEstimate:
    """Calculate hardware memory, wallclock time, and convergence recommendations."""
    return ResourceEstimator.estimate(
        scale_agents=scale_agents,
        n_replicates=n_replicates,
        horizon_days=horizon_days,
    )


# ==============================================================================
# Live Run Controls & Telemetry
# ==============================================================================

class StepRequest(BaseModel):
    n_days: int = 1


class InjectRequest(BaseModel):
    action: InterventionAction


class BranchRequest(BaseModel):
    branch_job_id: str
    checkpoint_day: Optional[int] = None
    overrides: Optional[Dict[str, Any]] = None


@router.post("/runs/{job_id}/step", response_model=List[LiveDayFrame])
def step_live_run(job_id: str, req: StepRequest) -> List[LiveDayFrame]:
    """Advance active simulation by N days."""
    live_run = get_or_create_live_run(job_id)
    return live_run.step(req.n_days)


@router.post("/runs/{job_id}/pause")
def pause_live_run(job_id: str) -> Dict[str, Any]:
    """Pause live run at current simulated day and snapshot state."""
    live_run = get_or_create_live_run(job_id)
    live_run.pause()
    return {"job_id": job_id, "status": "paused", "current_day": live_run.current_day}


@router.post("/runs/{job_id}/resume")
def resume_live_run(job_id: str) -> Dict[str, Any]:
    """Resume execution of paused simulation."""
    live_run = get_or_create_live_run(job_id)
    live_run.resume()
    return {"job_id": job_id, "status": "running", "current_day": live_run.current_day}


@router.post("/runs/{job_id}/inject")
def inject_intervention(job_id: str, req: InjectRequest) -> Dict[str, Any]:
    """Inject a dynamic policy intervention effective the next simulated day."""
    live_run = get_or_create_live_run(job_id)
    return live_run.inject_intervention(req.action)


@router.post("/runs/{job_id}/branch")
def branch_run(job_id: str, req: BranchRequest) -> Dict[str, Any]:
    """Fork an active run from a checkpoint into a new independent LiveRun."""
    live_run = get_or_create_live_run(job_id)
    branch = live_run.branch(
        branch_job_id=req.branch_job_id,
        checkpoint_day=req.checkpoint_day,
        overrides=req.overrides,
    )
    ACTIVE_LIVE_RUNS[req.branch_job_id] = branch
    return {
        "source_job_id": job_id,
        "branch_job_id": req.branch_job_id,
        "checkpoint_day": branch.current_day,
        "status": "branched_and_paused",
    }


@router.get("/runs/{job_id}/frames", response_model=List[LiveDayFrame])
def get_run_frames(job_id: str) -> List[LiveDayFrame]:
    """Retrieve full history of daily frames for playback and timeline scrub."""
    live_run = get_or_create_live_run(job_id)
    return live_run.frames


@router.get("/runs/{job_id}/frames/{day}", response_model=LiveDayFrame)
def get_single_frame(job_id: str, day: int) -> LiveDayFrame:
    """Retrieve telemetry frame for a specific historical day."""
    live_run = get_or_create_live_run(job_id)
    frame = live_run.get_frame(day)
    if not frame:
        raise HTTPException(status_code=404, detail=f"Frame for day {day} not found.")
    return frame


# ==============================================================================
# WebSocket Live Streaming Channel
# ==============================================================================

@router.websocket("/runs/{job_id}/live")
async def live_websocket_channel(websocket: WebSocket, job_id: str):
    """Bidirectional WebSocket streaming and control channel for live runs."""
    await websocket.accept()
    live_run = get_or_create_live_run(job_id)
    
    # Send initial status frame
    await websocket.send_json({
        "type": "connected",
        "job_id": job_id,
        "current_day": live_run.current_day,
        "horizon_days": live_run.horizon_days,
        "is_paused": live_run.is_paused,
        "is_completed": live_run.is_completed,
    })

    try:
        while True:
            # Receive client command
            data = await websocket.receive_json()
            cmd_type = data.get("type")

            if cmd_type == "play":
                live_run.resume()
                while not live_run.is_paused and not live_run.is_completed:
                    frames = live_run.step(1)
                    for frame in frames:
                        await websocket.send_json({"type": "frame", "frame": frame.model_dump()})
                    await asyncio.sleep(0.4)

            elif cmd_type == "pause":
                live_run.pause()
                await websocket.send_json({
                    "type": "paused",
                    "current_day": live_run.current_day,
                })

            elif cmd_type == "step":
                n_days = int(data.get("n_days", 1))
                frames = live_run.step(n_days)
                for frame in frames:
                    await websocket.send_json({"type": "frame", "frame": frame.model_dump()})

            elif cmd_type == "inject":
                action_data = data.get("action", {})
                action = InterventionAction(**action_data)
                record = live_run.inject_intervention(action)
                await websocket.send_json({"type": "injected", "record": record})

            elif cmd_type == "seek":
                target_day = int(data.get("target_day", 0))
                frame = live_run.get_frame(target_day)
                if frame:
                    await websocket.send_json({"type": "seek_result", "frame": frame.model_dump()})

            elif cmd_type == "stop":
                live_run.pause()
                await websocket.send_json({"type": "stopped", "current_day": live_run.current_day})
                break

    except WebSocketDisconnect:
        pass
