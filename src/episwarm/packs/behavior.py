"""Pydantic schemas for BehaviorPack configuration, rumor topics, and compliance dynamics (Spec 7 & 8)."""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from episwarm.packs.schema import ProvenanceRecord


class QuestionType(str, Enum):
    """Supported decision query structures."""
    CHOICE = "choice"
    SCORE = "score"
    NOUL = "noul"


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


class RumorBehaviorEffects(BaseModel):
    """Spec 7.4: How rumor belief impacts protective and avoidance behaviors."""
    mask_reduction: float = Field(default=0.40, ge=0.0, le=1.0, description="Reduction in masking probability")
    vaccination_reduction: float = Field(default=0.50, ge=0.0, le=1.0, description="Reduction in vaccine acceptance")
    isolation_reduction: float = Field(default=0.35, ge=0.0, le=1.0, description="Reduction in home isolation adherence")
    attendance_boost: float = Field(default=0.20, ge=0.0, le=1.0, description="Increase in unnecessary public attendance")


class RumorTopic(BaseModel):
    """Spec 7.2: Misinformation / rumor topic definition."""
    id: str = Field(..., min_length=1, description="Unique topic key")
    label: str = Field(..., min_length=1, description="Display claim (e.g. 'Pathogen is harmless seasonal cold')")
    seed_area: str = Field(default="ALL", description="Area to inject initial believers or 'ALL'")
    seed_day: int = Field(default=0, ge=0, description="Day on which rumor seeding occurs")
    num_seeds: int = Field(default=10, ge=0, description="Number of initial believing agents")
    credibility: float = Field(default=0.75, ge=0.0, le=3.0, description="Credibility multiplier")
    behavior_effects: RumorBehaviorEffects = Field(default_factory=RumorBehaviorEffects)


class ComplianceWeights(BaseModel):
    """Spec 8: Linear compliance weights and fatigue rates."""
    w_risk: float = Field(default=0.25, ge=0.0, description="Weight on local risk perception")
    w_norm: float = Field(default=0.20, ge=0.0, description="Weight on peer network compliance norm")
    w_enf: float = Field(default=0.15, ge=0.0, description="Weight on area policy enforcement")
    w_fat: float = Field(default=0.20, ge=0.0, description="Weight on accumulated pandemic fatigue")
    kappa: float = Field(default=0.30, ge=0.0, description="Erosion per unit rumor belief")
    fatigue_rate: float = Field(default=0.015, ge=0.0, description="Fatigue accumulation rate when measures are active")
    fatigue_recovery: float = Field(default=0.02, ge=0.0, description="Fatigue recovery rate during open periods")


class BehaviorPack(BaseModel):
    """Configuration bundle defining public behavior, traits, rumor network, and compliance dynamics."""
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
    rumor_spread_rate: float = Field(default=0.05, ge=0.0, le=1.0)
    rumor_topics: List[RumorTopic] = Field(default_factory=list)
    compliance_weights: ComplianceWeights = Field(default_factory=ComplianceWeights)
    provenance: ProvenanceRecord
