"""Test for Phase 31: Healthcare Capacity & Overflow Validation."""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import pytest
from scripts.run_healthcare_validation_wave1 import run_healthcare_validation


def test_healthcare_validation():
    res = run_healthcare_validation()
    assert res["passed"] is True
    assert 0.75 <= res["peak_ratio"] <= 1.25
    assert res["overflow_days_error"] <= 7

    card_path = Path("docs/validation/VALIDATION_CARD.json")
    assert card_path.exists()
    card = json.loads(card_path.read_text(encoding="utf-8"))
    assert "healthcare_overflow" in card["targets"]
    assert card["targets"]["healthcare_overflow"]["status"] == "PASS"

    report_path = Path("docs/validation/VALIDATION_REPORT.md")
    assert report_path.exists()
    report = report_path.read_text(encoding="utf-8")
    assert "Healthcare Overflow" in report
    assert "**PASS**" in report

