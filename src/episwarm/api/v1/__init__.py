"""API v1 router composition."""

from fastapi import APIRouter

from episwarm.api.v1.health import router as health_router
from episwarm.api.v1.validation import router as validation_router
from episwarm.api.v1.packs import router as packs_router
from episwarm.api.v1.runs import router as runs_router
from episwarm.api.v1.compare import router as compare_router
from episwarm.api.v1.system import router as system_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(health_router)
api_v1_router.include_router(validation_router)
api_v1_router.include_router(packs_router)
api_v1_router.include_router(runs_router)
api_v1_router.include_router(compare_router)
api_v1_router.include_router(system_router)

__all__ = ["api_v1_router"]
