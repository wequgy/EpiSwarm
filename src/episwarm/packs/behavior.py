"""Pydantic schemas for BehaviorPack configuration and decision definitions."""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from episwarm.packs.schema import ProvenanceRecord


class QuestionType(str, Enum):
    """Supported decision query structures."""
    CHOICE = "choice"
    SCORE = "score"
    NOUL = "noul"  # Yes/No style binary choices


class DecisionQuestion(BaseModel):
    """Specification for a behavioral decision prompt."""
    id: str = Field(..., min_length=1, description="Unique identifier (e.g. 'work_attendance', 'wear_mask')")
    type: QuestionType = Field(default=QuestionType.CHOICE)
    options: List[str] = Field(..., min_length=2, description="Available discrete choices or score levels")
    plain_instructions: str = Field(
        ...,
        description="Plain-language decision instructions. Must be self-contained as IDs are omitted in prompts."
    )


class TraitDistribution(BaseModel):
    """Gaussian distribution parameters for agent psychographic traits bounded in [0, 1]."""
    mean: float = Field(..., ge=0.0, le=1.0)
    std: float = Field(..., ge=0.0, le=0.5)


class BehaviorPack(BaseModel):
    """Configuration bundle defining public behavior, traits, and compliance dynamics."""
    name: str = Field(..., min_length=1)
    context: str = Field(
        ...,
        description="Cultural, geographical, and situational context injected into every decision prompt"
    )
    questions: List[DecisionQuestion] = Field(default_factory=list)
    traits: Dict[str, TraitDistribution] = Field(
        default_factory=lambda: {
            "compliance": TraitDistribution(mean=0.70, std=0.15),
            "rumor_susceptibility": TraitDistribution(mean=0.30, std=0.20),
            "risk_tolerance": TraitDistribution(mean=0.40, std=0.20),
            "institutional_trust": TraitDistribution(mean=0.60, std=0.20)
        }
    )
    rumor_spread_rate: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description="Daily probability of misinformation transmission per contact"
    )
    provenance: ProvenanceRecord

