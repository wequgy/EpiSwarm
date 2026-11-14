"""Simulation run execution, job queue management, and SSE streaming routers for API v1."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse

from episwarm.service.jobs import JobManager
from episwarm.service.models import (
    CapacityOutput,
    JobCancelResponse,
    JobListResponse,
    JobRecord,
    JobStatus,
    RunCreateRequest,
    RunSummary,
    SpatialOutput,
    TimeSeriesData,
)

router = APIRouter(prefix="/runs", tags=["Simulation Runs & Jobs"])
job_manager = JobManager()


@router.post("", response_model=JobRecord, status_code=status.HTTP_201_CREATED)
def launch_run(req: RunCreateRequest, response: Response) -> JobRecord:
    """Launch an asynchronous simulation job or synchronous mock execution."""
    job = job_manager.submit_job(req)
    if req.use_mock:
        response.headers["X-EpiSwarm-Mock"] = "true"
    return job


@router.get("", response_model=JobListResponse)
def list_runs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> JobListResponse:
    """List historical simulation runs in descending order of creation."""
    return job_manager.list_jobs(limit=limit, offset=offset)


@router.get("/{run_id}", response_model=JobRecord)
def get_run(run_id: str, response: Response) -> JobRecord:
    """Get metadata, execution status, and progress for a specific simulation job."""
    job = job_manager.get_job(run_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Simulation run '{run_id}' not found.")
    if job.is_mock:
        response.headers["X-EpiSwarm-Mock"] = "true"
    return job


@router.post("/{run_id}/cancel", response_model=JobCancelResponse)
def cancel_run(run_id: str) -> JobCancelResponse:
    """Request immediate cancellation of a running or queued simulation."""
    res = job_manager.cancel_job(run_id)
    if res.status == JobStatus.FAILED and "not found" in res.message:
        raise HTTPException(status_code=404, detail=res.message)
    return res


@router.get("/{run_id}/events")
async def stream_run_events(run_id: str):
    """Server-Sent Events (SSE) streaming real-time simulation progress and telemetry."""
    job = job_manager.get_job(run_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Simulation run '{run_id}' not found.")

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "text/event-stream",
    }
    if job.is_mock:
        headers["X-EpiSwarm-Mock"] = "true"

    return StreamingResponse(
        job_manager.stream_events(run_id),
        media_type="text/event-stream",
        headers=headers,
    )


@router.get("/{run_id}/summary", response_model=RunSummary)
def get_run_summary(run_id: str, response: Response) -> RunSummary:
    """Retrieve epidemiological outcome summary and metrics with confidence bounds."""
    job = job_manager.get_job(run_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Simulation run '{run_id}' not found.")

    if job.status == JobStatus.FAILED:
        raise HTTPException(status_code=500, detail=f"Simulation run failed: {job.error}")
    elif job.status in (JobStatus.QUEUED, JobStatus.RUNNING):
        raise HTTPException(
            status_code=409,
            detail=f"Run '{run_id}' is currently {job.status.value}. Results are generated upon completion.",
        )

    summary = job_manager.get_summary(run_id)
    if not summary:
        raise HTTPException(status_code=404, detail=f"Summary for run '{run_id}' not available.")

    if job.is_mock:
        response.headers["X-EpiSwarm-Mock"] = "true"
    return summary


@router.get("/{run_id}/timeseries", response_model=TimeSeriesData)
def get_run_timeseries(run_id: str, response: Response) -> TimeSeriesData:
    """Retrieve daily compartmental states, demand, and compliance trajectory curves."""
    job = job_manager.get_job(run_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Simulation run '{run_id}' not found.")

    if job.status == JobStatus.FAILED:
        raise HTTPException(status_code=500, detail=f"Simulation run failed: {job.error}")
    elif job.status in (JobStatus.QUEUED, JobStatus.RUNNING):
        raise HTTPException(
            status_code=409,
            detail=f"Run '{run_id}' is currently {job.status.value}. Trajectories available upon completion.",
        )

    ts = job_manager.get_timeseries(run_id)
    if not ts:
        raise HTTPException(status_code=404, detail=f"Time series for run '{run_id}' not available.")

    if job.is_mock:
        response.headers["X-EpiSwarm-Mock"] = "true"
    return ts


@router.get("/{run_id}/spatial", response_model=SpatialOutput)
def get_run_spatial(run_id: str, response: Response) -> SpatialOutput:
    """Retrieve spatial borough attack rates and multi-layer isometric diorama coordinates."""
    job = job_manager.get_job(run_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Simulation run '{run_id}' not found.")

    if job.status == JobStatus.FAILED:
        raise HTTPException(status_code=500, detail=f"Simulation run failed: {job.error}")
    elif job.status in (JobStatus.QUEUED, JobStatus.RUNNING):
        raise HTTPException(
            status_code=409,
            detail=f"Run '{run_id}' is currently {job.status.value}. Spatial layout available upon completion.",
        )

    spatial = job_manager.get_spatial(run_id)
    if not spatial:
        raise HTTPException(status_code=404, detail=f"Spatial telemetry for run '{run_id}' not available.")

    if job.is_mock:
        response.headers["X-EpiSwarm-Mock"] = "true"
    return spatial


@router.get("/{run_id}/capacity", response_model=CapacityOutput)
def get_run_capacity(run_id: str, response: Response) -> CapacityOutput:
    """Retrieve healthcare bed thresholds, overflow durations, and unmet demand."""
    job = job_manager.get_job(run_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Simulation run '{run_id}' not found.")

    if job.status == JobStatus.FAILED:
        raise HTTPException(status_code=500, detail=f"Simulation run failed: {job.error}")
    elif job.status in (JobStatus.QUEUED, JobStatus.RUNNING):
        raise HTTPException(
            status_code=409,
            detail=f"Run '{run_id}' is currently {job.status.value}. Capacity stress available upon completion.",
        )

    cap = job_manager.get_capacity(run_id)
    if not cap:
        raise HTTPException(status_code=404, detail=f"Capacity stress telemetry for run '{run_id}' not available.")

    if job.is_mock:
        response.headers["X-EpiSwarm-Mock"] = "true"
    return cap
