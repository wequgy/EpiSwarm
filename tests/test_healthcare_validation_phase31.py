"""Test for Phase 31: Healthcare Capacity & Overflow Validation (Repaired)."""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import pytest
from scripts.run_healthcare_validation_wave1 import run_healthcare_validation


def test_healthcare_validation():
    """Verify healthcare validation runs agent simulation without analytic stand-ins."""
    res = run_healthcare_validation(n_seeds=2, scale_agents=1000)
    assert "peak_ratio" in res
    assert "overflow_days_error" in res
    assert res["status"] in ("PASS", "FAIL")

    card_path = Path("docs/validation/VALIDATION_CARD.json")
    assert card_path.exists()
    card = json.loads(card_path.read_text(encoding="utf-8"))
    assert "healthcare_overflow" in card["targets"]
    target = card["targets"]["healthcare_overflow"]
    assert target["method"] == "agent_simulator_30_seeds"

    # Invariant: status must strictly match threshold comparison (Rule 5)
    ratio_pass = (0.75 <= target["peak_ratio"] <= 1.25)
    overflow_pass = (target["overflow_days_error"] <= 7)
    expected_status = "PASS" if (ratio_pass and overflow_pass) else "FAIL"
    assert target["status"] == expected_status
