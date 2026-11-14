"""Health check and backend status routers for API v1."""

from fastapi import APIRouter
from episwarm.service.models import BackendsResponse, HealthResponse
from episwarm.service.system import SystemService

router = APIRouter(tags=["System & Health"])
system_service = SystemService()


@router.get("/health", response_model=HealthResponse)
def get_v1_health() -> HealthResponse:
    """Return operational service health and timestamp."""
    return system_service.get_health()


@router.get("/backends", response_model=BackendsResponse)
def get_v1_backends() -> BackendsResponse:
    """List operational AI and simulation backends without exposing confidential keys."""
    return system_service.get_backends()
