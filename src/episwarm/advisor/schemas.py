"""Pydantic schemas for Advisor outputs and policy recommendations."""

from typing import List, Optional
from pydantic import BaseModel, Field

from episwarm.packs.scenario import InterventionAction


class Recommendation(BaseModel):
    """Structured policy advisory output for human public health decision-makers."""
    priority_areas: List[str] = Field(
        ...,
        description="Administrative areas recommended for earliest intervention"
    )
    recommended_measures: List[InterventionAction] = Field(
        ...,
        description="Ordered sequence of recommended public health measures"
    )
    evidence_run_ids: List[str] = Field(
        default_factory=list,
        description="Simulation run IDs supporting the recommendation"
    )
    objective_achieved: bool = Field(
        default=False,
        description="Whether target objectives (e.g. ICU ceiling, fatality threshold) were satisfied"
    )
    predicted_deaths_reduction: Optional[float] = Field(
        default=None,
        description="Percentage reduction in fatalities compared to baseline"
    )
    caveats: List[str] = Field(
        default_factory=list,
        description="Assumptions, uncalibrated dependencies, and equity trade-offs"
    )
    human_in_the_loop_advisory: str = Field(
        default="This is a model recommendation under stated assumptions, not an empirical prediction. Decision-makers must evaluate local socioeconomic factors.",
        description="Mandatory disclaimer banner"
    )

