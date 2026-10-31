"""Pydantic schemas for ScenarioPack configuration and intervention plans."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, model_validator
from episwarm.packs.schema import ProvenanceRecord


class SeedingConfig(BaseModel):
    """Outbreak seeding conditions."""
    area_id: Optional[str] = Field(
        default=None,
        description="Target area ID to seed. If None and seed_all_areas is True, seeds all sequentially."
    )
    seed_all_areas: bool = Field(
        default=False,
        description="Flag indicating sequential evaluation across all areas (for spread matrix computation)"
    )
    initial_cases_per_area: int = Field(default=10, gt=0, description="Number of index cases seeded")
    seeded_state: str = Field(default="I_symp", description="State to place initial index cases in")


class InterventionAction(BaseModel):
    """A policy measure active during a designated time window."""
    name: str = Field(..., min_length=1)
    measure_type: str = Field(
        ...,
        description="Category: school_closure, workplace_reduction, market_closure, mask_mandate, surge_beds, oxygen_buffer, vaccination"
    )
    area_id: str = Field(
        default="ALL",
        description="Specific area ID, or 'ALL' for region-wide application"
    )
    start_day: int = Field(..., ge=0, description="Simulation day on which measure activates")
    end_day: int = Field(..., ge=0, description="Simulation day on which measure terminates")
    stringency: float = Field(
        default=1.0, ge=0.0, le=1.0,
        description="Intensity factor (e.g. 0.5 = 50% capacity reduction or 50% contact scaling)"
    )
    cost_per_day: float = Field(
        default=1.0, ge=0.0,
        description="Economic cost proxy per day active (e.g. lost agent-days or economic disruption unit)"
    )
    parameters: Dict[str, float] = Field(
        default_factory=dict,
        description="Optional auxiliary parameters (e.g. extra_beds, target_coverage)"
    )

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_day < self.start_day:
            raise ValueError(f"end_day ({self.end_day}) cannot precede start_day ({self.start_day})")
        return self


class TargetObjective(BaseModel):
    """Quantitative optimization targets."""
    max_deaths: Optional[int] = Field(default=None, ge=0)
    max_peak_icu_overflow_days: Optional[int] = Field(default=0, ge=0)
    max_cost_proxy: Optional[float] = Field(default=None, ge=0.0)
    max_equity_gap: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class ScenarioPack(BaseModel):
    """Complete simulation scenario configuration."""
    name: str = Field(..., min_length=1)
    horizon_days: int = Field(default=90, gt=0, le=730, description="Simulation duration in days")
    scale_agents: int = Field(default=50000, gt=0, description="Total synthetic agents to instantiate")
    random_seed: int = Field(default=42, description="Master random seed for full reproducibility")
    seeding: SeedingConfig
    interventions: List[InterventionAction] = Field(default_factory=list)
    objectives: Optional[TargetObjective] = None
    provenance: ProvenanceRecord

