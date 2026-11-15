"""Test for Phase 29: Spatial Arrival Rank Validation (Repaired)."""

import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from scripts.run_spatial_validation_wave1 import run_spatial_validation


def test_spatial_validation_execution(tmp_path):
    """Verify that spatial validation runs the agent simulation and evaluates against UKHSA observations."""
    tmp_card = tmp_path / "VALIDATION_CARD.json"
    tmp_report = tmp_path / "VALIDATION_REPORT.md"
    res = run_spatial_validation(n_seeds=2, scale_agents=1000, card_path=tmp_card, report_path=tmp_report)
    assert "rank_correlation_rho" in res
    assert -1.0 <= res["rank_correlation_rho"] <= 1.0
    assert res["status"] in ("PASS", "FAIL")

    assert tmp_card.exists()
    card = json.loads(tmp_card.read_text(encoding="utf-8"))
    assert "spatial_arrival_ordering" in card["targets"]
    target = card["targets"]["spatial_arrival_ordering"]
    assert target["method"] == "agent_simulator_30_seeds"
    assert target["status"] in ("PASS", "FAIL")

    # Invariant: status must strictly match threshold comparison (Rule 5)
    val = target.get("rank_correlation_rho", target.get("spearman_rho", 0.0))
    expected_status = "PASS" if val >= 0.60 else "FAIL"
    assert target["status"] == expected_status
