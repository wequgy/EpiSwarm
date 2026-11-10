"""Test for Phase 30: CoMix Behavioral Calibration & Twin Experiment."""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pytest
from scripts.fit_behavior_comix import fit_comix_model
from episwarm.behavior.hierarchical import HierarchicalCoefficients
from episwarm.packs.schema import ProvenanceStatus


def test_fit_comix_model():
    res = fit_comix_model()
    assert res["beta_compliance"] > 2.0
    assert res["beta_fatigue"] > 0.0
    assert res["r2"] > 0.20

    report_path = Path("docs/validation/BEHAVIOR_MODEL_REPORT.md")
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "LSHTM CoMix Contact Survey" in content
    assert "Parametric Identifiability" in content

    coefs = HierarchicalCoefficients()
    assert coefs.provenance.status == ProvenanceStatus.SOURCED
    assert "CoMix" in coefs.provenance.source


def test_behavior_twin_experiment():
    """Verify that OLS on synthetic cohorts recovers true parameters within 10%."""
    beta_true = np.array([-1.75, 3.05, 0.44, -0.55])
    rng = np.random.default_rng(42)
    N = 10000
    x_policy = rng.uniform(0.3, 0.9, size=N)
    x_vuln = rng.uniform(0.0, 1.0, size=N)
    x_fatigue = rng.uniform(0.0, 1.0, size=N)

    X = np.column_stack([np.ones(N), x_policy, x_vuln, x_fatigue])
    noise = rng.normal(0, 0.15, size=N)
    y_logit = X @ beta_true + noise

    beta_hat = np.linalg.inv(X.T @ X) @ X.T @ y_logit
    rel_errors = np.abs(beta_hat - beta_true) / np.abs(beta_true)
    assert np.all(rel_errors <= 0.10), f"Twin experiment exceeded 10% error: {rel_errors}"
