"""System hardware information and resource estimation endpoints (API v1)."""

from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from episwarm.system.hardware import probe_hardware, estimate_resources

router = APIRouter(prefix="/system", tags=["System"])


class ResourceEstimateRequest(BaseModel):
    agents: int = Field(default=50000, ge=100, le=2000000, description="Number of agents")
    days: int = Field(default=60, ge=1, le=365, description="Simulation horizon in days")
    replicates: int = Field(default=5, ge=1, le=100, description="Replicate count")
    workers: Optional[int] = Field(default=None, description="Number of concurrent workers")


@router.get("", summary="Get system hardware probe and recommendations")
def get_system_hardware():
    """Returns hardware probe details including CPU cores, memory, GPU, runtime, and worker recommendations."""
    return probe_hardware()


@router.get("/estimate", summary="Estimate required resources for a simulation run")
def get_resource_estimate(
    agents: int = Query(default=50000, ge=100, le=2000000),
    days: int = Query(default=60, ge=1, le=365),
    replicates: int = Query(default=5, ge=1, le=100),
    workers: Optional[int] = Query(default=None, ge=1, le=64),
):
    """Estimate memory and wall time given simulation parameters."""
    return estimate_resources(agents=agents, days=days, replicates=replicates, workers=workers)


@router.post("/estimate", summary="Estimate required resources for a simulation run via POST")
def post_resource_estimate(req: ResourceEstimateRequest):
    """Estimate memory and wall time given simulation parameters."""
    return estimate_resources(
        agents=req.agents,
        days=req.days,
        replicates=req.replicates,
        workers=req.workers,
    )
