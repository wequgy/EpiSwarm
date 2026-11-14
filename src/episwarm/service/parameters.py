"""Parameter Registry service for schema discovery and JSON Pointer parameter overrides (Phase S1)."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ParameterDescriptor(BaseModel):
    """Schema descriptor for a customizable simulation parameter."""
    path: str = Field(..., description="RFC 6901 JSON pointer path")
    label: str = Field(..., description="Human-readable title")
    unit: Optional[str] = Field(default=None, description="Physical or scientific unit")
    description: str = Field(..., description="Scientific definition and guidance")
    type: str = Field(default="number", description="Type: number | integer | boolean | string")
    bounds: Optional[Dict[str, float]] = Field(default=None, description="Min, max, and step bounds")
    default_value: Any = Field(..., description="Baseline default value")
    pack_type: str = Field(..., description="Pack: region | disease | scenario | behavior | run")
    level: str = Field(default="Basic", description="Tier: Basic | Advanced | Expert")
    evidence_class: str = Field(default="C", description="Evidence class: A | B | C")
    source: Optional[str] = Field(default=None, description="Source citation or URL")
    affects: List[str] = Field(default_factory=list, description="Affected simulation dimensions")
    calibratable: bool = Field(default=False, description="Whether supported by SMC-ABC calibration")


# Canonical Core Registry Parameters
CORE_PARAMETERS: List[ParameterDescriptor] = [
    # Disease & Transmission
    ParameterDescriptor(
        path="/disease/transmission/r0",
        label="Basic Reproduction Number (R0)",
        unit="ratio",
        description="Expected secondary infections produced by a typical index case in a fully susceptible population.",
        type="number",
        bounds={"min": 0.5, "max": 8.0, "step": 0.05},
        default_value=2.8,
        pack_type="disease",
        level="Basic",
        evidence_class="B",
        source="Ferguson et al. / UKHSA",
        affects=["transmission"],
        calibratable=True,
    ),
    ParameterDescriptor(
        path="/disease/transmission/incubation_days",
        label="Mean Incubation Period",
        unit="days",
        description="Mean duration between exposure and onset of infectiousness/symptoms.",
        type="number",
        bounds={"min": 1.0, "max": 14.0, "step": 0.5},
        default_value=4.5,
        pack_type="disease",
        level="Basic",
        evidence_class="B",
        source="Lauer et al. / WHO",
        affects=["transmission"],
        calibratable=True,
    ),
    ParameterDescriptor(
        path="/disease/transmission/infectious_days",
        label="Mean Infectious Period",
        unit="days",
        description="Mean duration an infected individual can transmit the pathogen.",
        type="number",
        bounds={"min": 1.0, "max": 21.0, "step": 0.5},
        default_value=5.0,
        pack_type="disease",
        level="Basic",
        evidence_class="B",
        source="Byrne et al. / ECDC",
        affects=["transmission"],
        calibratable=True,
    ),
    ParameterDescriptor(
        path="/disease/transmission/layer_weights/home",
        label="Household Layer Relative Contact Weight",
        unit="multiplier",
        description="Relative transmission efficiency per contact in home vs. general community.",
        type="number",
        bounds={"min": 0.5, "max": 4.0, "step": 0.1},
        default_value=1.8,
        pack_type="disease",
        level="Advanced",
        evidence_class="B",
        source="CoMix Survey / Mossong et al.",
        affects=["transmission"],
        calibratable=True,
    ),
    ParameterDescriptor(
        path="/disease/transmission/layer_weights/school",
        label="School Layer Relative Contact Weight",
        unit="multiplier",
        description="Relative transmission efficiency per student contact in classroom cohorts.",
        type="number",
        bounds={"min": 0.2, "max": 3.0, "step": 0.1},
        default_value=1.2,
        pack_type="disease",
        level="Advanced",
        evidence_class="B",
        source="Prem et al.",
        affects=["transmission"],
        calibratable=True,
    ),
    ParameterDescriptor(
        path="/disease/transmission/layer_weights/work",
        label="Workplace Layer Relative Contact Weight",
        unit="multiplier",
        description="Relative transmission efficiency per coworker contact in workplace teams.",
        type="number",
        bounds={"min": 0.2, "max": 3.0, "step": 0.1},
        default_value=1.0,
        pack_type="disease",
        level="Advanced",
        evidence_class="B",
        source="Prem et al.",
        affects=["transmission"],
        calibratable=True,
    ),

    # Health System
    ParameterDescriptor(
        path="/region/resources/acute_beds/capacity",
        label="Total Regional Acute Hospital Beds",
        unit="beds",
        description="Nominal staffed acute inpatient beds available across healthcare providers.",
        type="integer",
        bounds={"min": 100, "max": 100000, "step": 50},
        default_value=18400,
        pack_type="region",
        level="Basic",
        evidence_class="A",
        source="NHS England Monthly SitRep",
        affects=["healthcare"],
        calibratable=False,
    ),
    ParameterDescriptor(
        path="/region/resources/icu_beds/capacity",
        label="Critical Care / ICU Ventilated Beds",
        unit="beds",
        description="Mechanical ventilator beds equipped for invasive respiratory care.",
        type="integer",
        bounds={"min": 10, "max": 10000, "step": 10},
        default_value=1120,
        pack_type="region",
        level="Basic",
        evidence_class="A",
        source="NHS England Critical Care Capacity",
        affects=["healthcare"],
        calibratable=False,
    ),

    # Behavior & Misinformation
    ParameterDescriptor(
        path="/behavior/rumor/spread_rate",
        label="Misinformation Spread Rate (beta_rumor)",
        unit="probability",
        description="Secondary transmission probability of a rumor topic per social network contact.",
        type="number",
        bounds={"min": 0.005, "max": 0.25, "step": 0.005},
        default_value=0.05,
        pack_type="behavior",
        level="Advanced",
        evidence_class="C",
        source="EpiSwarm Psychographic Default Prior",
        affects=["compliance"],
        calibratable=True,
    ),
    ParameterDescriptor(
        path="/behavior/compliance/fatigue_rate",
        label="Compliance Fatigue Decay Rate",
        unit="decay / day",
        description="Daily accumulation of adherence fatigue during active restrictions.",
        type="number",
        bounds={"min": 0.001, "max": 0.05, "step": 0.001},
        default_value=0.015,
        pack_type="behavior",
        level="Advanced",
        evidence_class="C",
        source="EpiSwarm Behavioral Dynamic Calibration",
        affects=["compliance"],
        calibratable=True,
    ),

    # Policy Interventions
    ParameterDescriptor(
        path="/scenario/interventions/mask_mandate/stringency",
        label="Mask Mandate Policy Stringency",
        unit="stringency ratio",
        description="Official mandate stringency and enforcement level for public indoor masking.",
        type="number",
        bounds={"min": 0.0, "max": 1.0, "step": 0.05},
        default_value=0.8,
        pack_type="scenario",
        level="Basic",
        evidence_class="B",
        source="UK Government Statutory Instruments",
        affects=["compliance", "transmission"],
        calibratable=False,
    ),
    ParameterDescriptor(
        path="/scenario/interventions/school_closure/stringency",
        label="School Closure Deactivation Rate",
        unit="ratio",
        description="Fraction of school-group and classroom edges deactivated during closure.",
        type="number",
        bounds={"min": 0.0, "max": 1.0, "step": 0.05},
        default_value=0.9,
        pack_type="scenario",
        level="Basic",
        evidence_class="B",
        source="Department for Education",
        affects=["transmission"],
        calibratable=False,
    ),
]


class ParameterRegistryService:
    """Manages parameter introspection and applies JSON pointer overrides."""

    def __init__(self):
        self._descriptors = {p.path: p for p in CORE_PARAMETERS}

    def list_parameters(self) -> List[ParameterDescriptor]:
        """Return all discoverable parameter descriptors."""
        return list(self._descriptors.values())

    def get_parameter(self, path: str) -> Optional[ParameterDescriptor]:
        """Retrieve descriptor by JSON pointer path."""
        return self._descriptors.get(path)

    @staticmethod
    def apply_overrides(target_dict: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
        """Apply RFC 6901 JSON Pointer key-value pairs to a nested dictionary in-place."""
        for pointer, value in overrides.items():
            if not pointer.startswith("/"):
                continue
            parts = pointer.strip("/").split("/")
            curr = target_dict
            for i, part in enumerate(parts[:-1]):
                if part not in curr or not isinstance(curr[part], dict):
                    curr[part] = {}
                curr = curr[part]
            curr[parts[-1]] = value
        return target_dict

