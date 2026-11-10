"""Test automated integrity scanner (Phase 25 Audit X1-X7)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.integrity_scan import (
    run_full_scan,
    scan_unverified_real_status,
    scan_suspicious_builders_and_validation,
    scan_report_card_discrepancies
)


def test_active_codebase_zero_integrity_violations():
    """Ensure the active working tree has zero integrity violations."""
    root = Path(__file__).resolve().parent.parent
    violations = run_full_scan(root, include_quarantine=False)
    assert len(violations) == 0, f"Expected 0 violations in active tree, found {len(violations)}: {[str(v) for v in violations]}"


def test_quarantined_artifacts_properly_flagged():
    """Ensure scanner accurately flags known fabricated items in quarantine."""
    root = Path(__file__).resolve().parent.parent
    violations = run_full_scan(root, include_quarantine=True)
    assert len(violations) >= 25, f"Expected at least 25 violations in quarantine, found {len(violations)}"

    categories = {v.category for v in violations}
    assert "X1/X2_UNVERIFIED_REAL_DATA" in categories
    assert "X1/X3_FABRICATED_LOGIC" in categories
    assert "X4_REPORT_CONTRADICTS_CARD" in categories or "X4_REPORT_CONTRADICTS_THRESHOLD" in categories
