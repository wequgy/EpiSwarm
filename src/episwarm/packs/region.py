"""Pydantic schemas for RegionPack configuration and metadata."""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, model_validator
from episwarm.packs.schema import ProvenanceRecord, ProvenanceStatus


class DataLevel(str, Enum):
    """Hierarchy of available data richness for a region."""
    L0_QUICK = "L0"
    L1_AREA = "L1"
    L2_FULL = "L2"


class L0QuickInputs(BaseModel):
    """High-level aggregate parameters used to synthesize detailed tables."""
    total_population: int = Field(..., gt=0, description="Total regional population")
    num_areas: int = Field(..., gt=0, description="Number of primary administrative units")
    avg_household_size: float = Field(default=3.5, gt=0.0, description="Mean household size")
    urban_fraction: float = Field(default=0.8, ge=0.0, le=1.0, description="Urban population share")
    employment_rate: float = Field(default=0.6, ge=0.0, le=1.0, description="Labor participation rate")
    beds_per_1000: float = Field(default=1.5, ge=0.0, description="General hospital beds per 1k people")
    icu_beds_per_1000: float = Field(default=0.1, ge=0.0, description="ICU beds per 1k people")
    num_schools: Optional[int] = Field(default=None, ge=0, description="Total schools (auto-estimated if null)")
    num_markets: Optional[int] = Field(default=None, ge=0, description="Total markets/gathering hubs")


class RegionMeta(BaseModel):
    """Metadata describing a RegionPack."""
    name: str = Field(..., min_length=1, description="Region identifier name (agnostic)")
    country_iso: str = Field(..., min_length=2, max_length=3, description="ISO country code (e.g. GBR, IND, USA)")
    data_year: int = Field(..., ge=1900, le=2100, description="Reference data vintage year")
    data_level: DataLevel = Field(default=DataLevel.L0_QUICK, description="Data readiness tier")
    area_levels: List[str] = Field(
        ...,
        min_length=1,
        max_length=3,
        description="Names of administrative hierarchy levels, from finest to coarsest (e.g. ['ward', 'zone'])"
    )
    contact_country: Optional[str] = Field(
        default=None,
        description="ISO code for Prem et al. contact matrix lookup if contacts.csv is omitted"
    )
    units: Dict[str, str] = Field(
        default_factory=lambda: {
            "distance": "km",
            "area": "km2",
            "currency": "local"
        },
        description="Units used for spatial and economic metrics"
    )
    notes: Optional[str] = None
    file_levels: Dict[str, DataLevel] = Field(
        default_factory=dict,
        description="Data level mapping per CSV file"
    )
    provenance: Dict[str, ProvenanceRecord] = Field(
        default_factory=dict,
        description="Provenance record per component/file"
    )

    @model_validator(mode="after")
    def validate_contact_fallback(self):
        if not self.contact_country:
            self.contact_country = self.country_iso
        return self


class RegionPack(BaseModel):
    """Complete Region configuration bundle."""
    meta: RegionMeta
    quick_inputs: Optional[L0QuickInputs] = None
