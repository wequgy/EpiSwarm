"""Test Validation Status Logic and Report-Card Coherence (Stage A1).

Verifies:
1. Card builder computes status strictly from targets:
   - 0 passed -> UNCALIBRATED
   - >=1 passed (but < total) -> PARTIALLY_VALIDATED
   - all passed (total > 0) -> VALIDATED
   - 0 total targets -> UNCALIBRATED
2. Rendered markdown report matches machine validation card strictly:
   - Overall status header matches card.status
   - Targets satisfied ratio matches card.targets_passed
   - Each row verdict matches target passed boolean
3. Active repository card and report files are coherent without contradictions.
"""

import json
from pathlib import Path
import pytest
import numpy as np

from episwarm.evidence.validation_controls import (
    TargetResult,
    ValidationCard,
    build_validation_card,
    render_markdown_report_from_card
)


def _make_dummy_target(name: str, passed: bool) -> TargetResult:
    return TargetResult(
        target_name=name,
        observed_peak_day=20,
        simulated_peak_day=20 if passed else 35,
        peak_day_error=0 if passed else 15,
        peak_ratio=1.0 if passed else 2.5,
        cumulative_error_pct=5.0 if passed else 50.0,
        passed=passed,
        details={"obs_peak": 100.0, "sim_peak": 100.0 if passed else 250.0}
    )


def test_card_status_zero_passed():
    """0 passed out of 3 -> UNCALIBRATED."""
    targets = [
        _make_dummy_target("t1", False),
        _make_dummy_target("t2", False),
        _make_dummy_target("t3", False)
    ]
    card = build_validation_card("test_region", targets)
    assert card.status == "UNCALIBRATED"
    assert card.targets_passed == "0/3"
    assert card.all_passed is False

    report = render_markdown_report_from_card(card)
    assert "**Computed Status**: **UNCALIBRATED** (0/3 targets satisfied)" in report
    assert report.count("**FAIL**") == 3
    assert "**PASS**" not in report


def test_card_status_partially_validated_one_of_three():
    """1 passed out of 3 -> PARTIALLY_VALIDATED."""
    targets = [
        _make_dummy_target("t1", True),
        _make_dummy_target("t2", False),
        _make_dummy_target("t3", False)
    ]
    card = build_validation_card("test_region", targets)
    assert card.status == "PARTIALLY_VALIDATED"
    assert card.targets_passed == "1/3"
    assert card.all_passed is False

    report = render_markdown_report_from_card(card)
    assert "**Computed Status**: **PARTIALLY_VALIDATED** (1/3 targets satisfied)" in report
    assert report.count("**PASS**") == 1
    assert report.count("**FAIL**") == 2


def test_card_status_partially_validated_two_of_three():
    """2 passed out of 3 -> PARTIALLY_VALIDATED."""
    targets = [
        _make_dummy_target("t1", True),
        _make_dummy_target("t2", True),
        _make_dummy_target("t3", False)
    ]
    card = build_validation_card("test_region", targets)
    assert card.status == "PARTIALLY_VALIDATED"
    assert card.targets_passed == "2/3"
    assert card.all_passed is False

    report = render_markdown_report_from_card(card)
    assert "**Computed Status**: **PARTIALLY_VALIDATED** (2/3 targets satisfied)" in report
    assert report.count("**PASS**") == 2
    assert report.count("**FAIL**") == 1


def test_card_status_all_passed():
    """All passed (3/3) -> VALIDATED."""
    targets = [
        _make_dummy_target("t1", True),
        _make_dummy_target("t2", True),
        _make_dummy_target("t3", True)
    ]
    card = build_validation_card("test_region", targets)
    assert card.status == "VALIDATED"
    assert card.targets_passed == "3/3"
    assert card.all_passed is True

    report = render_markdown_report_from_card(card)
    assert "**Computed Status**: **VALIDATED** (3/3 targets satisfied)" in report
    assert report.count("**PASS**") == 3
    assert "**FAIL**" not in report


def test_card_status_single_target():
    """Single target: 1/1 -> VALIDATED, 0/1 -> UNCALIBRATED."""
    card_pass = build_validation_card("test_region", [_make_dummy_target("t1", True)])
    assert card_pass.status == "VALIDATED"
    assert card_pass.targets_passed == "1/1"

    card_fail = build_validation_card("test_region", [_make_dummy_target("t1", False)])
    assert card_fail.status == "UNCALIBRATED"
    assert card_fail.targets_passed == "0/1"


def test_card_status_empty_targets():
    """0 targets -> UNCALIBRATED."""
    card = build_validation_card("test_region", [])
    assert card.status == "UNCALIBRATED"
    assert card.targets_passed == "0/0"
    assert card.all_passed is False


def test_active_card_and_report_coherence():
    """Verify active VALIDATION_CARD.json and VALIDATION_REPORT.md match exactly."""
    card_path = Path("docs/validation/VALIDATION_CARD.json")
    report_path = Path("docs/validation/VALIDATION_REPORT.md")

    if card_path.exists() and report_path.exists():
        card_data = json.loads(card_path.read_text(encoding="utf-8"))
        report_text = report_path.read_text(encoding="utf-8")

        expected_status = card_data.get("status")
        expected_ratio = card_data.get("targets_passed")

        assert f"**Computed Status**: **{expected_status}**" in report_text, (
            f"Report computed status must match card status '{expected_status}'"
        )
        if expected_ratio:
            assert f"({expected_ratio} targets satisfied)" in report_text, (
                f"Report ratio must match card targets_passed '{expected_ratio}'"
            )
