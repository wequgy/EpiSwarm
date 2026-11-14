"""Unit tests for Stage A6 Fresh Held-Out Wave 3 Protocol & Validation."""

import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from episwarm.evidence.held_out import HeldOutGate
from scripts.run_held_out_evaluation_wave3 import run_fresh_held_out_evaluation


def test_wave3_held_out_gate_not_compromised():
    gate = HeldOutGate(
        log_path=Path("docs/validation/HELD_OUT_LOG.jsonl"),
        protocol_path=Path("docs/validation/PROTOCOL.md")
    )
    window_name = "London_Wave3_2020-12-01_to_2021-02-28"
    assert gate.is_window_compromised(window_name, "v3.0.0-phase6") is False


def test_protocol_hash_invariance():
    gate = HeldOutGate(
        log_path=Path("docs/validation/HELD_OUT_LOG.jsonl"),
        protocol_path=Path("docs/validation/PROTOCOL.md")
    )
    h = gate.compute_current_protocol_hash()
    assert len(h) == 64
    assert all(c in "0123456789abcdefABCDEF" for c in h)
