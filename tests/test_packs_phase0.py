"""Unit and invariant tests for Phase 0 packs, schemas, validators, and generality."""

from pathlib import Path
import pytest
import yaml
from pydantic import ValidationError

from episwarm.packs.region import RegionPack
from episwarm.packs.disease import DiseasePack, DiseaseState, StateTransition, DurationDistribution, TransmissionConfig
from episwarm.packs.behavior import BehaviorPack
from episwarm.packs.scenario import ScenarioPack
from episwarm.importers.validate import validate_region_pack


def test_synthetic_region_pack():
    yaml_path = Path("regions/example_synthetic/region.yaml")
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    pack = RegionPack(**data)
    assert pack.meta.name == "example_synthetic"
    assert pack.meta.country_iso == "SYN"
    assert len(pack.meta.area_levels) == 2


def test_synthetic_region_validator():
    report = validate_region_pack(Path("regions/example_synthetic"))
    assert report.is_valid is True
    assert len(report.errors) == 0
    assert report.file_statuses["areas.csv"] == "SYNTHETIC"
    assert report.file_statuses["contacts.csv"] == "SYNTHETIC"


def test_disease_pack_valid():
    yaml_path = Path("diseases/respiratory_generic.yaml")
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    pack = DiseasePack(**data)
    assert pack.name == "respiratory_generic"
    assert pack.transmission.r0 == 2.5
    assert len(pack.states) == 8


def test_disease_pack_rejects_excess_probabilities():
    data = {
        "name": "invalid_disease",
        "provenance": {"source": "test", "status": "synthetic"},
        "transmission": {"mode": "person_to_person", "r0": 2.0},
        "states": [
            {"name": "S", "absorbing": False},
            {"name": "I", "infectious": True, "absorbing": False},
            {"name": "R", "absorbing": True}
        ],
        "transitions": [
            {
                "from_state": "I",
                "to_state": "R",
                "base_probability": 0.8,
                "duration": {"type": "constant", "mean_days": 5.0}
            },
            {
                "from_state": "I",
                "to_state": "S",
                "base_probability": 0.5,  # 0.8 + 0.5 = 1.3 > 1.0!
                "duration": {"type": "constant", "mean_days": 5.0}
            }
        ]
    }
    with pytest.raises(ValidationError) as excinfo:
        DiseasePack(**data)
    assert "Outgoing transition probabilities" in str(excinfo.value)


def test_disease_pack_rejects_outgoing_from_absorbing():
    data = {
        "name": "invalid_absorbing",
        "provenance": {"source": "test", "status": "synthetic"},
        "transmission": {"mode": "person_to_person", "r0": 2.0},
        "states": [
            {"name": "S", "absorbing": False},
            {"name": "R", "absorbing": True}
        ],
        "transitions": [
            {
                "from_state": "R",  # R is absorbing, cannot have outgoing transition
                "to_state": "S",
                "base_probability": 0.1,
                "duration": {"type": "constant", "mean_days": 5.0}
            }
        ]
    }
    with pytest.raises(ValidationError) as excinfo:
        DiseasePack(**data)
    assert "Absorbing state 'R' cannot have outgoing transitions" in str(excinfo.value)


def test_disease_pack_rejects_disconnected_graph():
    data = {
        "name": "disconnected",
        "provenance": {"source": "test", "status": "synthetic"},
        "transmission": {"mode": "person_to_person", "r0": 2.0},
        "states": [
            {"name": "S", "absorbing": False},
            {"name": "E", "absorbing": False},
            {"name": "R", "absorbing": True}  # R not reachable from S
        ],
        "transitions": [
            {
                "from_state": "S",
                "to_state": "E",
                "base_probability": 1.0,
                "duration": {"type": "constant", "mean_days": 3.0}
            }
        ]
    }
    with pytest.raises(ValidationError) as excinfo:
        DiseasePack(**data)
    assert "No absorbing state is reachable" in str(excinfo.value)


def test_behavior_pack_parsing():
    yaml_path = Path("behavior/default.yaml")
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    pack = BehaviorPack(**data)
    assert pack.name == "default"
    assert len(pack.questions) == 5
    assert "compliance" in pack.traits


def test_scenario_pack_parsing():
    yaml_path = Path("scenarios/baseline.yaml")
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    pack = ScenarioPack(**data)
    assert pack.name == "baseline"
    assert pack.horizon_days == 90
    assert len(pack.interventions) == 0
    with open("scenarios/targeted_containment.yaml", "r", encoding="utf-8") as f_tgt:
        tgt_pack = ScenarioPack(**yaml.safe_load(f_tgt))
    assert len(tgt_pack.interventions) >= 1


def test_generality_rule_no_hardcoded_places_or_diseases():
    """Generality test: Fails if src/ contains hardcoded specific place names or disease names."""
    src_dir = Path("src/episwarm")
    forbidden = [
        "bengaluru", "bangalore", "london", "wuhan", "mumbai", "delhi", "new york",
        "covid", "sars-cov-2", "influenza", "ebola", "smallpox"
    ]

    violations = []
    for py_file in src_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8").lower()
        for term in forbidden:
            if term in content:
                violations.append((str(py_file), term))

    assert not violations, f"Generality violation: hardcoded names found in src/: {violations}"

