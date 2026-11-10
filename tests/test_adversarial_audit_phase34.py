"""Phase 34: Mutation Testing and Adversarial Integrity Audit.

Four adversarial invariant tests:
1. One-digit modification in observed data triggers IntegrityGateError.
2. Shuffled spatial data fails the rank-order threshold (negative control).
3. Loosening tolerances or fake PASS triggers IntegrityScan failure.
4. Strict AST import boundaries ban tuning/calibration from importing held_out.
"""

import ast
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pytest
from scipy.stats import spearmanr

from episwarm.evidence.gate import verify_real_dataset, IntegrityGateError
from episwarm.evidence.ledger import EvidenceLedger, compute_sha256
from scripts.integrity_scan import run_full_scan


def test_adversarial_tamper_observed_cases(tmp_path):
    """Adversarial Test 1: Tampering a single byte/digit raises IntegrityGateError."""
    ledger = EvidenceLedger()
    clean_csv = Path("regions/reference_london/observed_cases.csv")
    assert clean_csv.exists()

    # The clean file passes verification
    rec = verify_real_dataset(clean_csv, ledger=ledger)
    assert rec is not None

    # Create mutated copy with 1 byte altered
    mutated_csv = tmp_path / "observed_cases.csv"
    content = clean_csv.read_text(encoding="utf-8")
    # Mutate one number (e.g., change first '0' to '9')
    mutated_content = content.replace("0", "9", 1)
    mutated_csv.write_text(mutated_content, encoding="utf-8")

    # Gate MUST refuse the mutated file
    with pytest.raises(IntegrityGateError, match="Integrity Gate Violation"):
        verify_real_dataset(mutated_csv, ledger=ledger)


def test_negative_control_shuffled_boroughs():
    """Adversarial Test 2: Shuffled spatial target drops correlation and fails threshold."""
    # Simulated spatial arrivals
    sim_arrivals = np.array([8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 15, 16, 17, 18, 19, 20, 21])
    
    # Shuffled observed arrivals (break spatial structure)
    rng = np.random.default_rng(1337)
    shuffled_obs = rng.permutation(sim_arrivals)

    rho, p_val = spearmanr(shuffled_obs, sim_arrivals)
    # Shuffled data must be near 0 and strictly fail the >= 0.60 pre-registered threshold
    assert rho < 0.40, f"Negative control should not have high correlation: rho = {rho}"
    assert not (rho >= 0.60), "Negative control should have failed >= 0.60 threshold"


def test_loosening_gate_rejection(tmp_path):
    """Adversarial Test 3: Loosened thresholds or fake PASS in report trigger integrity scan failure."""
    fake_docs = tmp_path / "docs" / "validation"
    fake_docs.mkdir(parents=True, exist_ok=True)

    fake_card = {
        "status": "VALIDATED",
        "targets": {
            "registered_deaths": {"passed": False, "peak_ratio": 0.42}
        }
    }
    (fake_docs / "VALIDATION_CARD.json").write_text(json.dumps(fake_card), encoding="utf-8")

    # Contradictory report claiming PASS for passed=False target
    fake_report = (
        "# Validation Report\n\n"
        "| Registered Deaths | Ratio = **0.42** | [0.75, 1.25] | **PASS** |\n"
    )
    (fake_docs / "VALIDATION_REPORT.md").write_text(fake_report, encoding="utf-8")

    violations = run_full_scan(tmp_path)
    assert len(violations) > 0
    categories = [v.category for v in violations]
    assert "X4_REPORT_CONTRADICTS_CARD" in categories or "X4_REPORT_CONTRADICTS_THRESHOLD" in categories


def test_import_boundaries_held_out():
    """Adversarial Test 4: AST boundary check bans calibration/tuning from importing held_out."""
    banned_dirs = [
        Path("src/episwarm/calibration"),
        Path("src/episwarm/engine"),
        Path("src/episwarm/behavior")
    ]
    
    for b_dir in banned_dirs:
        if not b_dir.exists():
            continue
        for py_file in b_dir.rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "held_out" not in alias.name, f"Illegal held-out import in {py_file}: {alias.name}"
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    assert "held_out" not in mod, f"Illegal held-out import in {py_file}: {mod}"
