"""Pydantic v2 domain schemas and data transfer objects for EpiSwarm Service Facade.

Defines contracts for packs, simulation runs, job queue statuses, time series,
spatial layouts, capacity telemetry, trust artifacts, and RFC 7807 error representations.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict


# ==============================================================================
# Job & Execution Enums
# ==============================================================================

class JobStatus(str, Enum):
    """Execution state machine for asynchronous simulation runs."""
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# ==============================================================================
# Pack Schemas
# ==============================================================================

class RegionSummary(BaseModel):
    """Summary metadata of an installed regional configuration pack."""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(..., description="Region pack identifier")
    name: str = Field(..., description="Display name of the region")
    country_iso: Optional[str] = Field(default=None, description="ISO country code")
    data_year: Optional[int] = Field(default=None, description="Data vintage year")
    data_level: Optional[str] = Field(default=None, description="Readiness tier: L0, L1, L2")
    num_areas: Optional[int] = Field(default=None, description="Number of administrative units")
    total_population: Optional[int] = Field(default=None, description="Total regional population")
    areas_file_exists: bool = Field(default=False, description="Whether areas.csv is present")
    contacts_file_exists: bool = Field(default=False, description="Whether contacts.csv is present")
    commute_file_exists: bool = Field(default=False, description="Whether commute_od.csv is present")
    observed_cases_exists: bool = Field(default=False, description="Whether empirical observed_cases.csv is present")
    provenance_status: str = Field(default="SYNTHETIC", description="Classification: REAL or SYNTHETIC")
    notes: Optional[str] = Field(default=None, description="Descriptive notes or source attribution")


class DiseaseSummary(BaseModel):
    """Summary metadata of an installed pathogen configuration pack."""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(..., description="Disease identifier")
    name: str = Field(..., description="Clinical or common pathogen name")
    r0: Optional[float] = Field(default=None, description="Target reproductive number R0")
    incubation_days: Optional[float] = Field(default=None, description="Mean incubation duration in days")
    infectious_days: Optional[float] = Field(default=None, description="Mean infectious period in days")
    case_fatality_ratio: Optional[float] = Field(default=None, description="Estimated CFR")
    states_count: int = Field(default=0, description="Total number of discrete compartments in state graph")
    has_vulnerability_factors: bool = Field(default=False, description="Whether comorbidity factors are defined")
    description: Optional[str] = Field(default=None, description="Pathogen description")


class ScenarioSummary(BaseModel):
    """Summary metadata of an intervention scenario pack."""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(..., description="Scenario identifier")
    name: str = Field(..., description="Display name of the scenario")
    horizon_days: int = Field(default=90, description="Default simulation duration in days")
    behavior_mode: str = Field(default="rule", description="Behavior policy mode: none | rule | llm")
    n_interventions: int = Field(default=0, description="Count of declared policy intervention actions")
    description: Optional[str] = Field(default=None, description="Scenario description")


class BehaviorSummary(BaseModel):
    """Summary metadata of an agent behavior and compliance pack."""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(..., description="Behavior pack identifier")
    name: str = Field(..., description="Behavior configuration name")
    context: Optional[str] = Field(default=None, description="Narrative context prompt")
    rumor_spread_rate: Optional[float] = Field(default=None, description="Misinformation transmission rate")
    n_rumor_topics: int = Field(default=0, description="Number of rumor topics configured")
    n_questions: int = Field(default=0, description="Number of decision questions configured")


class PackValidationResult(BaseModel):
    """Audit verification report for any pack asset."""
    pack_type: str = Field(..., description="Type of pack: region | disease | scenario | behavior")
    pack_id: str = Field(..., description="Identifier of verified pack")
    is_valid: bool = Field(..., description="Whether pack complies with schema specifications")
    errors: List[str] = Field(default_factory=list, description="Validation error messages")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warning notices")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed component statuses")


# ==============================================================================
# Run Requests & Job Management Schemas
# ==============================================================================

class RunCreateRequest(BaseModel):
    """Specification for launching a new simulation run job."""
    model_config = ConfigDict(extra="ignore")
    region_id: str = Field(default="example_synthetic", description="Region identifier")
    disease_id: str = Field(default="respiratory_generic", description="Pathogen pack identifier")
    scenario_id: str = Field(default="targeted_containment", description="Scenario pack identifier")
    scale_agents: int = Field(default=3000, ge=100, le=50000, description="Synthetic agent population size")
    behavior_mode: str = Field(default="rule", description="Behavior policy mode: none | rule | llm")
    n_replicates: int = Field(default=5, ge=1, le=50, description="Number of stochastic replicates")
    random_seed: int = Field(default=42, description="Base pseudorandom generator seed")
    horizon_days: Optional[int] = Field(default=None, ge=1, le=365, description="Override simulation horizon")
    pause_at_day: Optional[int] = Field(default=None, ge=1, description="Day to pause and snapshot state")
    use_mock: bool = Field(default=False, description="Execute fast synthetic mock run for offline UI testing")


class JobRecord(BaseModel):
    """Persistent execution job status and progress descriptor."""
    model_config = ConfigDict(extra="ignore")
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(default=JobStatus.QUEUED, description="Current lifecycle status")
    created_at: str = Field(..., description="ISO 8601 UTC timestamp of creation")
    started_at: Optional[str] = Field(default=None, description="ISO 8601 UTC timestamp of execution start")
    completed_at: Optional[str] = Field(default=None, description="ISO 8601 UTC timestamp of completion/failure")
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="Execution progress ratio [0.0, 1.0]")
    current_day: int = Field(default=0, description="Last simulated day completed")
    total_days: int = Field(default=0, description="Total days targeted in simulation horizon")
    request: RunCreateRequest = Field(..., description="Original launch configuration")
    error: Optional[str] = Field(default=None, description="Error message if status is FAILED")
    results_summary: Optional[Dict[str, Any]] = Field(default=None, description="High-level metrics summary")
    is_mock: bool = Field(default=False, description="Whether generated via mock test fixture")


class JobListResponse(BaseModel):
    """Paginated list of historical simulation jobs."""
    jobs: List[JobRecord] = Field(default_factory=list)
    total: int = Field(..., description="Total number of jobs in database")


class JobCancelResponse(BaseModel):
    """Response returned upon cancelling an active simulation job."""
    job_id: str = Field(..., description="Job identifier")
    status: JobStatus = Field(..., description="Resulting status after cancellation request")
    message: str = Field(..., description="Human-readable cancellation status message")


# ==============================================================================
# Simulation Output Schemas
# ==============================================================================

class MetricBounds(BaseModel):
    """Mean and 95% confidence intervals for a scalar summary outcome."""
    mean: float
    ci_lower: float
    ci_upper: float
    std: Optional[float] = None


class MetricsSummary(BaseModel):
    """Comprehensive epidemic impact metrics across stochastic replicates."""
    attack_rate: MetricBounds
    peak_day: MetricBounds
    total_deaths: MetricBounds
    peak_hospital_demand: MetricBounds
    peak_icu_demand: MetricBounds
    overflow_deaths: Optional[MetricBounds] = None


class RunSummary(BaseModel):
    """Executive outcome summary for a completed simulation run."""
    job_id: str
    region_id: str
    disease_id: str
    scenario_id: str
    behavior_mode: str
    scale_agents: int
    n_replicates: int
    metrics: MetricsSummary
    validation_status: str = Field(default="UNCALIBRATED", description="Empirical validation classification")
    validation_card_url: str = Field(default="/api/v1/validation/card")
    is_mock: bool = Field(default=False, description="Flag indicating mock fixture data")
    banner: Optional[str] = Field(default=None, description="Banner message (e.g. MOCK DATA warning)")


class TimeSeriesData(BaseModel):
    """Temporal trajectory telemetry for states, demand, and compliance."""
    job_id: str
    horizon_days: int
    days: List[int]
    state_names: List[str]
    daily_states: Dict[str, List[float]] = Field(
        description="Daily population counts keyed by state name (e.g. 'S', 'E', 'I_symp', 'R', 'D')"
    )
    daily_hospital_demand: List[float]
    daily_icu_demand: List[float]
    daily_deaths: List[float]
    daily_mean_compliance: Optional[List[float]] = None
    daily_rumor_beliefs: Optional[Dict[str, List[float]]] = None
    is_mock: bool = False


class AreaSpatialPoint(BaseModel):
    """Spatial borough / area epidemic telemetry and isometric coordinates."""
    area_id: str
    name: str
    population: int
    density: float
    iso_x: float
    iso_y: float
    total_infections: int
    attack_rate: float
    daily_incident_infections: List[float]
    peak_day: int


class SpatialOutput(BaseModel):
    """Geographic distribution of transmission across regional sub-areas."""
    job_id: str
    region_id: str
    n_areas: int
    areas: List[AreaSpatialPoint]
    layers: List[Dict[str, Any]]
    is_mock: bool = False


class CapacityOutput(BaseModel):
    """Hospital and ICU resource strain, capacity thresholds, and unmet demand."""
    job_id: str
    hospital_capacity_beds: float
    icu_capacity_beds: float
    daily_hospital_demand: List[float]
    daily_icu_demand: List[float]
    overflow_days_hospital: int
    overflow_days_icu: int
    overflow_deaths: int
    daily_unmet_demand: Dict[str, List[int]] = Field(default_factory=dict)
    is_mock: bool = False


# ==============================================================================
# Scenario Comparison & What-If Schemas
# ==============================================================================

class CompareRequest(BaseModel):
    """Request for running or retrieving a paired counterfactual comparison."""
    region_id: str = Field(default="example_synthetic", description="Region identifier")
    disease_id: str = Field(default="respiratory_generic", description="Pathogen identifier")
    scenario_a: str = Field(default="baseline", description="Reference scenario identifier")
    scenario_b: str = Field(default="targeted_containment", description="Counterfactual scenario identifier")
    scale_agents: int = Field(default=3000, ge=100, le=50000)
    n_replicates: int = Field(default=5, ge=1, le=50)
    random_seed: int = Field(default=42)
    behavior_mode: str = Field(default="rule")


class CompareResponse(BaseModel):
    """Statistical counterfactual comparison between two policy scenarios."""
    scenario_a: str
    scenario_b: str
    n_replicates: int
    means_a: Dict[str, float]
    delta_means: Dict[str, float]
    delta_ci_95_lower: Dict[str, float]
    delta_ci_95_upper: Dict[str, float]
    comparison: Dict[str, float]
    validation_status: str = "UNCALIBRATED"


# ==============================================================================
# Trust, Validation & Evidence Schemas
# ==============================================================================

class AssumptionItem(BaseModel):
    """Provenance entry in assumptions register."""
    parameter: str
    value: Any
    source: str
    status: str
    notes: Optional[str] = None


class EvidenceItem(BaseModel):
    """Immutable ledger record for an empirical data download or derived asset."""
    id: str
    url: str
    retrieved_at: str
    sha256: str
    byte_count: int
    http_status: Optional[int] = None
    content_type: str
    license: str
    file_path: str
    record_status: str = "verified"
    notes: Optional[str] = None
    record_type: str = "download"
    parent_ids: Optional[str] = None
    transform_script: Optional[str] = None
    transform_script_sha256: Optional[str] = None


class ValidationCardResponse(BaseModel):
    """Full empirical validation card."""
    model_config = ConfigDict(extra="allow")
    status: str
    region: Optional[str] = None
    calibration_window: Optional[str] = None
    calibrated_parameters: Optional[Dict[str, Any]] = None
    targets_passed: Optional[str] = None
    targets: Optional[Dict[str, Any]] = None
    ledger_authenticated: Optional[bool] = None
    generated_at: Optional[str] = None


class ValidationReportResponse(BaseModel):
    """Validation report with markdown body and structured status summary."""
    status: str
    report_markdown: str
    assumptions_count: int


# ==============================================================================
# System & Health Schemas
# ==============================================================================

class HealthResponse(BaseModel):
    """System health and version check response."""
    status: str = "ok"
    service: str = "episwarm-api"
    version: str = "1.0.0"
    timestamp: str


class BackendItem(BaseModel):
    """Status information for an external or optional AI/database backend."""
    name: str = Field(..., description="Backend identifier (e.g. gemini, jev, local_llm, sqlite)")
    status: str = Field(..., description="'available' | 'unavailable' | 'configured'")
    configured: bool = Field(..., description="Whether required credentials or endpoints are provided")
    active_model: Optional[str] = Field(default=None, description="Active model name if applicable")
    details: Dict[str, Any] = Field(default_factory=dict, description="Non-sensitive backend configuration status")


class BackendsResponse(BaseModel):
    """Inventory of available simulation and reasoning backends."""
    backends: List[BackendItem]


# ==============================================================================
# RFC 7807 Problem Details
# ==============================================================================

class ProblemDetail(BaseModel):
    """RFC 7807 compliant problem details for HTTP APIs."""
    type: str = Field(default="about:blank", description="URI reference identifying problem type")
    title: str = Field(..., description="Short, human-readable summary of problem type")
    status: int = Field(..., description="HTTP status code")
    detail: str = Field(..., description="Human-readable explanation specific to this occurrence")
    instance: Optional[str] = Field(default=None, description="URI reference of specific resource occurrence")
    invalid_params: Optional[List[Dict[str, Any]]] = Field(default=None, description="Parameter validation errors")
