"""Empirical validation and provenance routers for API v1."""

from typing import Any, Dict, List
from fastapi import APIRouter
from episwarm.service.models import (
    AssumptionItem,
    EvidenceItem,
    ValidationReportResponse,
)
from episwarm.service.trust import TrustService

router = APIRouter(prefix="/validation", tags=["Trust & Validation"])
trust_service = TrustService()


@router.get("/card")
def get_validation_card() -> Dict[str, Any]:
    """Retrieve verified empirical benchmark validation card."""
    return trust_service.get_validation_card()


@router.get("/report", response_model=ValidationReportResponse)
def get_validation_report() -> ValidationReportResponse:
    """Retrieve human-readable validation report markdown and status."""
    return trust_service.get_validation_report()


@router.get("/assumptions", response_model=List[AssumptionItem])
def get_assumptions() -> List[AssumptionItem]:
    """Retrieve active assumptions provenance register (Evidence Class C)."""
    return trust_service.get_assumptions()


@router.get("/evidence", response_model=List[EvidenceItem])
def get_evidence() -> List[EvidenceItem]:
    """Query cryptographic evidence ledger for checksummed downloads and derived tables."""
    return trust_service.get_evidence_records()
