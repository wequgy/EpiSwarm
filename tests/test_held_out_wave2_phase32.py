"""Test for Phase 32: Gated Held-Out Wave 2 Evaluation (Repaired)."""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import pytest
from scripts.run_held_out_evaluation_wave2 import run_held_out_evaluation
from episwarm.evidence.held_out import HeldOutGate


def test_held_out_evaluation():
    """Verify held-out gate correctly detects COMPROMISED window and enforces refusal."""
    res = run_held_out_evaluation()
    assert res["status"] == "COMPROMISED"
    assert res["passed"] is False

    # Verify log entry in docs/validation/HELD_OUT_LOG.jsonl
    log_path = Path("docs/validation/HELD_OUT_LOG.jsonl")
    assert log_path.exists()
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1
    
    # Check that a COMPROMISED record exists in log
    records = [json.loads(line) for line in lines]
    compromised_records = [r for r in records if r.get("status") == "COMPROMISED"]
    assert len(compromised_records) >= 1
    assert compromised_records[-1]["held_out_window"] == "London_Wave2_2020-09-01_to_2020-11-30"

    # Check hash-chain property
    gate = HeldOutGate(log_path=log_path)
    assert gate.is_window_compromised("London_Wave2_2020-09-01_to_2020-11-30", "v3.0.0") is True
