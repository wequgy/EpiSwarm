"""Common provenance schemas and base types for EpiSwarm Studio."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ProvenanceStatus(str, Enum):
    """Data provenance classification."""
    USER_SUPPLIED = "user_supplied"
    SOURCED = "sourced"
    ASSUMED = "assumed"
    SYNTHETIC = "synthetic"


class ProvenanceRecord(BaseModel):
    """Audit record capturing the origin and classification of parameters."""
    source: Optional[str] = Field(
        default=None,
        description="URL, DOI, or organizational origin of the data/parameter."
    )
    status: ProvenanceStatus = Field(
        default=ProvenanceStatus.ASSUMED,
        description="Confidence status: user_supplied, sourced, assumed, or synthetic."
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional explanatory notes or assumptions regarding this value."
    )
