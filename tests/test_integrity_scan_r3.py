"""Negative control tests for EpiSwarm Integrity Scanner (Stage R3.1).

Verifies that the scanner strictly fails when presented with:
1. Synthetic posterior ensembles / typed simulation metrics.
2. Hand-chosen "winner" policies in ablation studies.
3. Hard-coded scale_agents < 50,000 without CLI override.
4. Validation reports that soften failed threshold criteria.
5. Quarantined ablation scripts and reports.
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from scripts.integrity_scan import (
    scan_synthetic_posterior_ensembles,
    scan_hardcoded_winner_ablation,
    scan_hardcoded_scale_agents,
    scan_softened_threshold_claims,
)


def test_negative_control_synthetic_posterior_ensemble(tmp_path):
    """Negative Control 1: Scanner flags typed sim metrics and synthetic loops."""
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir(parents=True)
    bad_script = scripts_dir / "bad_particles.py"
    bad_script.write_text(
        "from episwarm.calibrate.smc_abc import Particle\n"
        "p = Particle(params={'r0': 2.5}, sim_peak_day=35, sim_peak_val=300.0, sim_total=2000.0)\n",
        encoding="utf-8"
    )

    violations = scan_synthetic_posterior_ensembles(tmp_path)
    assert len(violations) > 0
    assert any("Z1_SYNTHETIC_POSTERIOR_ENSEMBLE" in v.category for v in violations)


def test_negative_control_handchosen_ablation_winner(tmp_path):
    """Negative Control 2: Scanner flags hand-chosen 'agent_v3_robust_portfolio' APPROVED winners."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True)
    bad_doc = docs_dir / "fake_ablation.md"
    bad_doc.write_text(
        "# Ablation Study\n"
        "Policy agent_v3_robust_portfolio is declared APPROVED as optimal.\n",
        encoding="utf-8"
    )

    violations = scan_hardcoded_winner_ablation(tmp_path)
    assert len(violations) > 0
    assert any("Z2_HAND_CHOSEN_ABLATION_WINNER" in v.category for v in violations)


def test_negative_control_hardcoded_scale_agents(tmp_path):
    """Negative Control 3: Scanner flags hardcoded scale_agents < 50,000 without CLI override."""
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir(parents=True)
    bad_script = scripts_dir / "run_underresolved_val.py"
    bad_script.write_text(
        "pop = build_synthetic_population('regions/reference_london', scale_agents=5000, random_seed=42)\n",
        encoding="utf-8"
    )

    violations = scan_hardcoded_scale_agents(tmp_path)
    assert len(violations) > 0
    assert any("Z3_UNDER_RESOLVED_SIMULATION_SCALE" in v.category for v in violations)


def test_negative_control_softened_threshold_claims(tmp_path):
    """Negative Control 4: Scanner flags softened phrases like 'moderate agreement' or 'stabilizes as'."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(parents=True)
    bad_report = docs_dir / "softened_report.md"
    bad_report.write_text(
        "| Spatial | rho | >= 0.60 | 0.162 | Moderate monotonic agreement |\n",
        encoding="utf-8"
    )

    violations = scan_softened_threshold_claims(tmp_path)
    assert len(violations) > 0
    assert any("Z4_SOFTENED_THRESHOLD_CLAIM" in v.category for v in violations)


def test_quarantine_scan_detects_quarantined_ablation():
    """Verify scanner with include_quarantine=True detects quarantined ablation artifacts."""
    root = Path(__file__).resolve().parent.parent
    quarantine_violations = scan_synthetic_posterior_ensembles(root, include_quarantine=True)
    ablation_violations = [v for v in quarantine_violations if "run_agent_ablation.py" in v.file_path]
    assert len(ablation_violations) > 0, "Quarantined run_agent_ablation.py should trigger Z1 violation"
