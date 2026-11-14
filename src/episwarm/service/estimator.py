"""Simulation hardware and computational resource estimator (Phase S1)."""

from typing import Dict, Any
from pydantic import BaseModel, Field


class ResourceEstimate(BaseModel):
    """Estimated memory, wallclock time, and stability recommendations."""
    scale_agents: int = Field(..., description="Targeted agent population size")
    n_replicates: int = Field(..., description="Stochastic replicate count")
    horizon_days: int = Field(..., description="Simulation duration in days")
    estimated_memory_mb: float = Field(..., description="Estimated peak memory in MB")
    estimated_memory_gb: float = Field(..., description="Estimated peak memory in GB")
    estimated_wallclock_seconds: float = Field(..., description="Estimated total runtime in seconds")
    throughput_agent_days_per_sec: float = Field(..., description="Throughput rate in agent-days/sec")
    recommended_min_agents: int = Field(default=50000, description="Minimum recommended resolution for numerical stability")
    stability_status: str = Field(..., description="STABLE | SUB_CONVERGENT | HIGH_RESOLUTION")
    within_memory_budget: bool = Field(default=True, description="Whether execution fits within 11GB budget")


class ResourceEstimator:
    """Estimates computational footprint from agent scale and time horizon."""

    # Baseline memory consumption per agent:
    # 24 SoA fields (~120 bytes) + ~15 network edges (15 * 8 bytes = 120 bytes) + telemetry buffers (~60 bytes)
    BYTES_PER_AGENT = 320
    BASE_SYSTEM_OVERHEAD_MB = 180.0
    
    # Benchmarked throughput on Core i5 / Windows: ~120,000 to 180,000 agent-days/sec
    DEFAULT_THROUGHPUT = 140000.0

    @classmethod
    def estimate(cls, scale_agents: int, n_replicates: int = 1, horizon_days: int = 60) -> ResourceEstimate:
        """Compute memory and runtime estimates for simulation execution."""
        total_agent_days = float(scale_agents) * float(horizon_days) * float(n_replicates)
        
        # Memory calculation (primary replicate population + network + telemetry buffers)
        mem_mb = cls.BASE_SYSTEM_OVERHEAD_MB + (scale_agents * cls.BYTES_PER_AGENT) / (1024 * 1024)
        mem_gb = mem_mb / 1024.0

        # Runtime calculation
        wallclock_sec = max(0.5, round(total_agent_days / cls.DEFAULT_THROUGHPUT, 2))

        # Stability recommendation from convergence study (A1 benchmark)
        if scale_agents < 20000:
            status = "SUB_CONVERGENT"
        elif scale_agents <= 50000:
            status = "STABLE"
        else:
            status = "HIGH_RESOLUTION"

        return ResourceEstimate(
            scale_agents=scale_agents,
            n_replicates=n_replicates,
            horizon_days=horizon_days,
            estimated_memory_mb=round(mem_mb, 2),
            estimated_memory_gb=round(mem_gb, 3),
            estimated_wallclock_seconds=wallclock_sec,
            throughput_agent_days_per_sec=cls.DEFAULT_THROUGHPUT,
            recommended_min_agents=50000,
            stability_status=status,
            within_memory_budget=(mem_gb < 11.0),
        )
