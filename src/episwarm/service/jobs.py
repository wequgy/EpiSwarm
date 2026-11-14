"""Persistent SQLite-backed job queue, async execution manager, and SSE event streaming."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import threading
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Set
import uuid

from episwarm.service.models import (
    JobCancelResponse,
    JobListResponse,
    JobRecord,
    JobStatus,
    RunCreateRequest,
    RunSummary,
    TimeSeriesData,
    SpatialOutput,
    CapacityOutput,
)
from episwarm.service.simulation import SimulationService


class JobCancelledException(Exception):
    """Raised when an active simulation job is cancelled by user request."""
    pass


class JobManager:
    """SQLite-backed persistent job queue managing simulation lifecycles and real-time SSE streaming."""

    DEFAULT_DB_PATH = Path("logs/jobs.db")

    def __init__(
        self,
        db_path: Optional[Path] = None,
        max_workers: int = 4,
        simulation_service: Optional[SimulationService] = None,
    ):
        self.db_path = Path(db_path or self.DEFAULT_DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.sim_service = simulation_service or SimulationService()
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="episwarm-worker")
        
        # Real-time event pub/sub structures
        self._lock = threading.Lock()
        self._cancelled_jobs: Set[str] = set()
        self._listeners: Dict[str, List[asyncio.Queue]] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    progress REAL NOT NULL DEFAULT 0.0,
                    current_day INTEGER NOT NULL DEFAULT 0,
                    total_days INTEGER NOT NULL DEFAULT 0,
                    request_json TEXT NOT NULL,
                    error TEXT,
                    results_summary_json TEXT,
                    timeseries_json TEXT,
                    spatial_json TEXT,
                    capacity_json TEXT,
                    is_mock INTEGER NOT NULL DEFAULT 0
                );
            """)
            conn.commit()

    def submit_job(self, req: RunCreateRequest) -> JobRecord:
        """Create, enqueue, and trigger execution of a new simulation job."""
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        total_days = req.horizon_days or 60

        record = JobRecord(
            job_id=job_id,
            status=JobStatus.QUEUED,
            created_at=now,
            progress=0.0,
            current_day=0,
            total_days=total_days,
            request=req,
            is_mock=req.use_mock,
        )

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO jobs (
                    job_id, status, created_at, progress, current_day, total_days,
                    request_json, is_mock
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.job_id,
                record.status.value,
                record.created_at,
                record.progress,
                record.current_day,
                record.total_days,
                req.model_dump_json(),
                1 if req.use_mock else 0,
            ))
            conn.commit()

        # Submit to thread pool worker
        self.executor.submit(self._run_job_worker, job_id, req)
        return record

    def _run_job_worker(self, job_id: str, req: RunCreateRequest):
        """Worker thread entry point executing simulation with progress callbacks."""
        started_at = datetime.now(timezone.utc).isoformat()
        
        # Check if cancelled before starting
        with self._lock:
            if job_id in self._cancelled_jobs:
                self._update_job_status(job_id, JobStatus.CANCELLED, completed_at=started_at)
                self._publish_event(job_id, "cancelled", {"job_id": job_id, "message": "Job cancelled prior to execution"})
                return

        self._update_job_status(job_id, JobStatus.RUNNING, started_at=started_at)
        self._publish_event(job_id, "started", {"job_id": job_id, "status": "RUNNING"})

        def step_callback(day: int, total_days: int, metrics: Dict[str, Any]):
            with self._lock:
                if job_id in self._cancelled_jobs:
                    raise JobCancelledException(f"Job {job_id} cancelled during day {day}")

            progress = float(min(1.0, max(0.0, (day + 1) / max(1, total_days))))
            self._update_job_progress(job_id, progress, day, total_days)
            self._publish_event(job_id, "progress", {
                "job_id": job_id,
                "day": day,
                "total_days": total_days,
                "progress": progress,
                "metrics": metrics,
            })

        try:
            summary, timeseries, spatial, capacity = self.sim_service.execute_run(
                req=req,
                job_id=job_id,
                step_callback=step_callback if not req.use_mock else None,
            )

            # If mock, simulate quick progressive SSE events for testing
            if req.use_mock:
                horizon = req.horizon_days or 60
                self._publish_event(job_id, "progress", {
                    "job_id": job_id,
                    "day": horizon,
                    "total_days": horizon,
                    "progress": 1.0,
                    "metrics": {"active_infected": 150},
                })

            completed_at = datetime.now(timezone.utc).isoformat()
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE jobs SET
                        status = ?,
                        completed_at = ?,
                        progress = 1.0,
                        current_day = total_days,
                        results_summary_json = ?,
                        timeseries_json = ?,
                        spatial_json = ?,
                        capacity_json = ?
                    WHERE job_id = ?
                """, (
                    JobStatus.COMPLETED.value,
                    completed_at,
                    summary.model_dump_json(),
                    timeseries.model_dump_json(),
                    spatial.model_dump_json(),
                    capacity.model_dump_json(),
                    job_id,
                ))
                conn.commit()

            self._publish_event(job_id, "complete", {
                "job_id": job_id,
                "status": "COMPLETED",
                "summary": summary.model_dump(),
            })

        except JobCancelledException:
            completed_at = datetime.now(timezone.utc).isoformat()
            self._update_job_status(job_id, JobStatus.CANCELLED, completed_at=completed_at)
            self._publish_event(job_id, "cancelled", {"job_id": job_id, "message": "Execution cancelled"})

        except Exception as e:
            completed_at = datetime.now(timezone.utc).isoformat()
            err_msg = str(e)
            with self._get_connection() as conn:
                conn.execute("""
                    UPDATE jobs SET
                        status = ?,
                        completed_at = ?,
                        error = ?
                    WHERE job_id = ?
                """, (
                    JobStatus.FAILED.value,
                    completed_at,
                    err_msg,
                    job_id,
                ))
                conn.commit()

            self._publish_event(job_id, "error", {"job_id": job_id, "error": err_msg})

    def _update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        started_at: Optional[str] = None,
        completed_at: Optional[str] = None,
    ):
        with self._get_connection() as conn:
            if started_at:
                conn.execute("UPDATE jobs SET status = ?, started_at = ? WHERE job_id = ?", (status.value, started_at, job_id))
            elif completed_at:
                conn.execute("UPDATE jobs SET status = ?, completed_at = ? WHERE job_id = ?", (status.value, completed_at, job_id))
            else:
                conn.execute("UPDATE jobs SET status = ? WHERE job_id = ?", (status.value, job_id))
            conn.commit()

    def _update_job_progress(self, job_id: str, progress: float, day: int, total_days: int):
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE jobs SET
                    progress = ?,
                    current_day = ?,
                    total_days = ?
                WHERE job_id = ?
            """, (progress, day, total_days, job_id))
            conn.commit()

    def cancel_job(self, job_id: str) -> JobCancelResponse:
        """Request immediate cancellation of a running or queued job."""
        job = self.get_job(job_id)
        if not job:
            return JobCancelResponse(
                job_id=job_id,
                status=JobStatus.FAILED,
                message=f"Job '{job_id}' not found.",
            )

        if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            return JobCancelResponse(
                job_id=job_id,
                status=job.status,
                message=f"Job '{job_id}' is already in terminal state {job.status.value}.",
            )

        with self._lock:
            self._cancelled_jobs.add(job_id)

        now = datetime.now(timezone.utc).isoformat()
        self._update_job_status(job_id, JobStatus.CANCELLED, completed_at=now)
        self._publish_event(job_id, "cancelled", {"job_id": job_id, "message": "Job cancellation requested"})

        return JobCancelResponse(
            job_id=job_id,
            status=JobStatus.CANCELLED,
            message=f"Job '{job_id}' successfully cancelled.",
        )

    def get_job(self, job_id: str) -> Optional[JobRecord]:
        """Fetch job metadata and status from persistent database."""
        with self._get_connection() as conn:
            cur = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_record(row)

    def list_jobs(self, limit: int = 50, offset: int = 0) -> JobListResponse:
        """List historical jobs ordered by creation date descending."""
        with self._get_connection() as conn:
            cur = conn.execute("SELECT COUNT(*) as cnt FROM jobs")
            total = cur.fetchone()["cnt"]

            cur = conn.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            jobs = [self._row_to_record(row) for row in cur.fetchall()]
            return JobListResponse(jobs=jobs, total=total)

    def _row_to_record(self, row: sqlite3.Row) -> JobRecord:
        req_data = json.loads(row["request_json"])
        summary_data = json.loads(row["results_summary_json"]) if row["results_summary_json"] else None
        return JobRecord(
            job_id=row["job_id"],
            status=JobStatus(row["status"]),
            created_at=row["created_at"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            progress=row["progress"],
            current_day=row["current_day"],
            total_days=row["total_days"],
            request=RunCreateRequest(**req_data),
            error=row["error"],
            results_summary=summary_data,
            is_mock=bool(row["is_mock"]),
        )

    def get_summary(self, job_id: str) -> Optional[RunSummary]:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT results_summary_json FROM jobs WHERE job_id = ?", (job_id,))
            row = cur.fetchone()
            if not row or not row["results_summary_json"]:
                return None
            return RunSummary.model_validate_json(row["results_summary_json"])

    def get_timeseries(self, job_id: str) -> Optional[TimeSeriesData]:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT timeseries_json FROM jobs WHERE job_id = ?", (job_id,))
            row = cur.fetchone()
            if not row or not row["timeseries_json"]:
                return None
            return TimeSeriesData.model_validate_json(row["timeseries_json"])

    def get_spatial(self, job_id: str) -> Optional[SpatialOutput]:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT spatial_json FROM jobs WHERE job_id = ?", (job_id,))
            row = cur.fetchone()
            if not row or not row["spatial_json"]:
                return None
            return SpatialOutput.model_validate_json(row["spatial_json"])

    def get_capacity(self, job_id: str) -> Optional[CapacityOutput]:
        with self._get_connection() as conn:
            cur = conn.execute("SELECT capacity_json FROM jobs WHERE job_id = ?", (job_id,))
            row = cur.fetchone()
            if not row or not row["capacity_json"]:
                return None
            return CapacityOutput.model_validate_json(row["capacity_json"])

    # --------------------------------------------------------------------------
    # Real-Time SSE Event Pub/Sub
    # --------------------------------------------------------------------------

    def _publish_event(self, job_id: str, event_type: str, payload: Dict[str, Any]):
        """Publish an event to all connected async listeners."""
        with self._lock:
            queues = list(self._listeners.get(job_id, []))

        event_text = f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"
        for q in queues:
            try:
                # Put without blocking if queue loop is running
                q.put_nowait(event_text)
            except Exception:
                pass

    async def stream_events(self, job_id: str) -> AsyncGenerator[str, None]:
        """Subscribe to real-time execution progress events for SSE response."""
        job = self.get_job(job_id)
        if not job:
            yield f"event: error\ndata: {json.dumps({'error': f'Job {job_id} not found'})}\n\n"
            return

        # If job is already in terminal state, yield final event and finish
        if job.status == JobStatus.COMPLETED:
            summary = self.get_summary(job_id)
            yield f"event: complete\ndata: {json.dumps({'job_id': job_id, 'status': 'COMPLETED', 'summary': summary.model_dump() if summary else {}})}\n\n"
            return
        elif job.status == JobStatus.FAILED:
            yield f"event: error\ndata: {json.dumps({'job_id': job_id, 'status': 'FAILED', 'error': job.error})}\n\n"
            return
        elif job.status == JobStatus.CANCELLED:
            yield f"event: cancelled\ndata: {json.dumps({'job_id': job_id, 'status': 'CANCELLED'})}\n\n"
            return

        queue: asyncio.Queue = asyncio.Queue()
        with self._lock:
            if job_id not in self._listeners:
                self._listeners[job_id] = []
            self._listeners[job_id].append(queue)

        try:
            # Yield initial status
            yield f"event: status\ndata: {json.dumps({'job_id': job_id, 'status': job.status.value, 'progress': job.progress})}\n\n"

            while True:
                msg = await queue.get()
                yield msg
                if "event: complete" in msg or "event: error" in msg or "event: cancelled" in msg:
                    break
        finally:
            with self._lock:
                if job_id in self._listeners and queue in self._listeners[job_id]:
                    self._listeners[job_id].remove(queue)
                    if not self._listeners[job_id]:
                        del self._listeners[job_id]
