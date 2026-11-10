"""Test for Phase 29: Spatial Arrival Rank Validation."""

import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from scripts.run_spatial_validation_wave1 import run_spatial_validation


def test_spatial_validation_execution():
    rho = run_spatial_validation()
    assert rho >= 0.60

    card_path = Path("docs/validation/VALIDATION_CARD.json")
    assert card_path.exists()
    card = json.loads(card_path.read_text(encoding="utf-8"))
    assert "spatial_arrival_order" in card["targets"]
    assert card["targets"]["spatial_arrival_order"]["status"] == "PASS"

    report_path = Path("docs/validation/VALIDATION_REPORT.md")
    assert report_path.exists()
    report_text = report_path.read_text(encoding="utf-8")
    assert "Spatial Arrival Order" in report_text
    assert "**PASS**" in report_text
