"""Test for Phase 32: Gated Held-Out Wave 2 Evaluation."""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import pytest
from scripts.run_held_out_evaluation_wave2 import run_held_out_evaluation


def test_held_out_evaluation():
    res = run_held_out_evaluation()
    assert "status" in res

    # Verify log entry in docs/validation/HELD_OUT_LOG.jsonl
    log_path = Path("docs/validation/HELD_OUT_LOG.jsonl")
    assert log_path.exists()
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1
    last_entry = json.loads(lines[-1])
    assert last_entry["held_out_window"] == "London_Wave2_2020-09-01_to_2020-11-30"
    assert "protocol_hash" in last_entry

    # Verify report reflects honest evaluation
    report_path = Path("docs/validation/VALIDATION_REPORT.md")
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "Held Out Wave2" in content

