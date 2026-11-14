"""Counterfactual comparison and what-if policy exploration routers for API v1."""

from fastapi import APIRouter
from episwarm.service.models import CompareRequest, CompareResponse
from episwarm.service.simulation import SimulationService

router = APIRouter(tags=["Scenario Comparison & What-If"])
sim_service = SimulationService()


@router.post("/compare", response_model=CompareResponse)
def compare_scenarios(req: CompareRequest) -> CompareResponse:
    """Run paired stochastic counterfactual evaluation between two intervention scenarios."""
    return sim_service.execute_compare(req)


@router.post("/what-if", response_model=CompareResponse)
def what_if_analysis(req: CompareRequest) -> CompareResponse:
    """Alias for /compare supporting what-if policy queries under identical random seeds."""
    return sim_service.execute_compare(req)
