"""Pack inspection and schema contract validation routers for API v1."""

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException
from episwarm.service.models import (
    BehaviorSummary,
    DiseaseSummary,
    PackValidationResult,
    RegionSummary,
    ScenarioSummary,
)
from episwarm.service.packs import PacksService

router = APIRouter(prefix="/packs", tags=["Domain Packs"])
packs_service = PacksService()


# ------------------------------------------------------------------------------
# Regions
# ------------------------------------------------------------------------------

@router.get("/regions", response_model=List[RegionSummary])
def list_regions() -> List[RegionSummary]:
    """List all installed geographic regions with readiness tiers."""
    return packs_service.list_regions()


@router.get("/regions/{region_id}")
def get_region(region_id: str) -> Dict[str, Any]:
    """Retrieve raw manifest and table inventory for a specific region."""
    data = packs_service.get_region(region_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Region pack '{region_id}' not found.")
    return data


@router.get("/regions/{region_id}/validate", response_model=PackValidationResult)
@router.post("/regions/{region_id}/validate", response_model=PackValidationResult)
def validate_region(region_id: str) -> PackValidationResult:
    """Validate all tables and metadata within a region pack directory."""
    result = packs_service.validate_region(region_id)
    if not result.is_valid and "not found" in (result.errors[0] if result.errors else "").lower():
        raise HTTPException(status_code=404, detail=f"Region pack '{region_id}' not found.")
    return result


# ------------------------------------------------------------------------------
# Diseases
# ------------------------------------------------------------------------------

@router.get("/diseases", response_model=List[DiseaseSummary])
def list_diseases() -> List[DiseaseSummary]:
    """List all installed pathogen packs."""
    return packs_service.list_diseases()


@router.get("/diseases/{disease_id}")
def get_disease(disease_id: str) -> Dict[str, Any]:
    """Retrieve full disease pack specification and state transitions."""
    data = packs_service.get_disease(disease_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Disease pack '{disease_id}' not found.")
    return data


@router.get("/diseases/{disease_id}/validate", response_model=PackValidationResult)
@router.post("/diseases/{disease_id}/validate", response_model=PackValidationResult)
def validate_disease(disease_id: str) -> PackValidationResult:
    """Validate pathogen state graph, reachability, and probability constraints."""
    result = packs_service.validate_disease(disease_id)
    if not result.is_valid and "not found" in (result.errors[0] if result.errors else "").lower():
        raise HTTPException(status_code=404, detail=f"Disease pack '{disease_id}' not found.")
    return result


# ------------------------------------------------------------------------------
# Scenarios
# ------------------------------------------------------------------------------

@router.get("/scenarios", response_model=List[ScenarioSummary])
def list_scenarios() -> List[ScenarioSummary]:
    """List all installed intervention scenario packs."""
    return packs_service.list_scenarios()


@router.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: str) -> Dict[str, Any]:
    """Retrieve full scenario pack policy parameters and intervention timeline."""
    data = packs_service.get_scenario(scenario_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Scenario pack '{scenario_id}' not found.")
    return data


@router.get("/scenarios/{scenario_id}/validate", response_model=PackValidationResult)
@router.post("/scenarios/{scenario_id}/validate", response_model=PackValidationResult)
def validate_scenario(scenario_id: str) -> PackValidationResult:
    """Validate scenario action dates, stringency bounds, and parameters."""
    result = packs_service.validate_scenario(scenario_id)
    if not result.is_valid and "not found" in (result.errors[0] if result.errors else "").lower():
        raise HTTPException(status_code=404, detail=f"Scenario pack '{scenario_id}' not found.")
    return result


# ------------------------------------------------------------------------------
# Behaviors
# ------------------------------------------------------------------------------

@router.get("/behaviors", response_model=List[BehaviorSummary])
def list_behaviors() -> List[BehaviorSummary]:
    """List all agent compliance and rumor behavior packs."""
    return packs_service.list_behaviors()


@router.get("/behaviors/{behavior_id}")
def get_behavior(behavior_id: str) -> Dict[str, Any]:
    """Retrieve behavior questions, rumor topics, and compliance weights."""
    data = packs_service.get_behavior(behavior_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Behavior pack '{behavior_id}' not found.")
    return data


@router.get("/behaviors/{behavior_id}/validate", response_model=PackValidationResult)
@router.post("/behaviors/{behavior_id}/validate", response_model=PackValidationResult)
def validate_behavior(behavior_id: str) -> PackValidationResult:
    """Validate psychographic trait distributions and decision schemas."""
    result = packs_service.validate_behavior(behavior_id)
    if not result.is_valid and "not found" in (result.errors[0] if result.errors else "").lower():
        raise HTTPException(status_code=404, detail=f"Behavior pack '{behavior_id}' not found.")
    return result
