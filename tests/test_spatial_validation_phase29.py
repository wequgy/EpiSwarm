"""Test for Phase 29: Spatial Arrival Rank Validation (Repaired)."""

import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from scripts.run_spatial_validation_wave1 import run_spatial_validation


def test_spatial_validation_execution():
    """Verify that spatial validation runs the agent simulation and evaluates against UKHSA observations."""
    res = run_spatial_validation(n_seeds=2, scale_agents=1000)
    assert "rank_correlation_rho" in res
    assert -1.0 <= res["rank_correlation_rho"] <= 1.0
    assert res["status"] in ("PASS", "FAIL")

    card_path = Path("docs/validation/VALIDATION_CARD.json")
    assert card_path.exists()
    card = json.loads(card_path.read_text(encoding="utf-8"))
    assert "spatial_arrival_order" in card["targets"]
    target = card["targets"]["spatial_arrival_order"]
    assert target["method"] == "agent_simulator_30_seeds"
    assert target["status"] in ("PASS", "FAIL")

    # Invariant: status must strictly match threshold comparison (Rule 5)
    expected_status = "PASS" if target["rank_correlation_rho"] >= 0.60 else "FAIL"
    assert target["status"] == expected_status
