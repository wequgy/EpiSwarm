"""Validation Harness with Positive and Negative Controls (Phase 26).

Enforces:
1. No hand-typed report text or verdicts: markdown is rendered strictly from machine cards.
2. Positive control: A model validated against its own simulated data must PASS.
3. Negative control: A model validated against shuffled, reversed, or mismatched data must FAIL.
"""

from dataclasses import dataclass, asdict
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np


@dataclass
class TargetResult:
    target_name: str
    observed_peak_day: int
    simulated_peak_day: int
    peak_day_error: int
    peak_ratio: float
    cumulative_error_pct: float
    passed: bool
    details: Dict[str, Any]


@dataclass
class ValidationCard:
    status: str  # 'VALIDATED', 'PARTIALLY_VALIDATED', 'FAILED'
    region_id: str
    targets_passed: str  # e.g. '2/2'
    targets: Dict[str, Dict[str, Any]]
    all_passed: bool


def evaluate_curve_target(
    name: str,
    obs_curve: np.ndarray,
    sim_curve: np.ndarray,
    max_peak_day_error: int = 5,
    min_peak_ratio: float = 0.75,
    max_peak_ratio: float = 1.25,
    max_cumulative_error_pct: float = 20.0
) -> TargetResult:
    """Evaluate simulated trajectory against observed curve under pre-registered thresholds."""
    obs_peak_day = int(np.argmax(obs_curve))
    sim_peak_day = int(np.argmax(sim_curve))
    peak_day_error = abs(sim_peak_day - obs_peak_day)

    obs_peak_val = float(np.max(obs_curve))
    sim_peak_val = float(np.max(sim_curve))
    peak_ratio = sim_peak_val / max(1e-6, obs_peak_val)

    obs_total = float(np.sum(obs_curve))
    sim_total = float(np.sum(sim_curve))
    cum_error_pct = abs(sim_total - obs_total) / max(1e-6, obs_total) * 100.0

    passed = (
        peak_day_error <= max_peak_day_error and
        min_peak_ratio <= peak_ratio <= max_peak_ratio and
        cum_error_pct <= max_cumulative_error_pct
    )

    return TargetResult(
        target_name=name,
        observed_peak_day=obs_peak_day,
        simulated_peak_day=sim_peak_day,
        peak_day_error=peak_day_error,
        peak_ratio=round(peak_ratio, 3),
        cumulative_error_pct=round(cum_error_pct, 2),
        passed=passed,
        details={
            "obs_peak": obs_peak_val,
            "sim_peak": sim_peak_val,
            "obs_total": obs_total,
            "sim_total": sim_total
        }
    )


def build_validation_card(
    region_id: str,
    target_results: List[TargetResult]
) -> ValidationCard:
    """Construct an immutable ValidationCard where status and verdicts are strictly computed."""
    targets_dict = {}
    passed_count = 0

    for r in target_results:
        if r.passed:
            passed_count += 1
        targets_dict[r.target_name.lower().replace(" ", "_")] = {
            "passed": r.passed,
            "peak_day_error": f"{r.peak_day_error} days",
            "peak_ratio": r.peak_ratio,
            "cumulative_error": f"{r.cumulative_error_pct}%",
            "status": "PASS" if r.passed else "FAIL"
        }

    total_count = len(target_results)
    all_passed = (passed_count == total_count and total_count > 0)
    
    if all_passed:
        overall_status = "VALIDATED"
    elif passed_count > 0:
        overall_status = "PARTIALLY_VALIDATED"
    else:
        overall_status = "FAILED"

    return ValidationCard(
        status=overall_status,
        region_id=region_id,
        targets_passed=f"{passed_count}/{total_count}",
        targets=targets_dict,
        all_passed=all_passed
    )


def render_markdown_report_from_card(card: ValidationCard) -> str:
    """Render validation report markdown strictly from machine card with zero hand-typed verdicts."""
    lines = [
        f"# Validation Report: {card.region_id}",
        "",
        f"**Computed Status**: **{card.status}** ({card.targets_passed} targets satisfied)",
        "",
        "| Target Name | Peak Day Error | Peak Height Ratio | Cumulative Error | Computed Status |",
        "|---|---|---|---|---|"
    ]

    for t_id, data in card.targets.items():
        name_str = t_id.replace("_", " ").title()
        if data.get("in_sample") or data.get("status") == "IN-SAMPLE":
            status_str = "**IN-SAMPLE (Calibration Fit)**"
        elif data.get("passed", False):
            status_str = "**PASS**"
        else:
            status_str = "**FAIL**"
        peak_err = data.get("peak_day_error", "-")
        peak_ratio = data.get("peak_ratio", "-")
        cum_err = data.get("cumulative_error", "-")
        lines.append(
            f"| **{name_str}** | {peak_err} | {peak_ratio} | {cum_err} | {status_str} |"
        )

    assumptions = getattr(card, "assumptions", None)
    if assumptions:
        lines.append("")
        lines.append("## Assumptions Register (Evidence Class C)")
        lines.append("")
        lines.append("| Parameter | Nominal Value | Evidence Class | Uncertainty Bound / Notes |")
        lines.append("|---|---|---|---|")
        for a_name, a_info in assumptions.items():
            lines.append(f"| **{a_name}** | {a_info.get('value', '-')} | {a_info.get('class', 'Class C')} | {a_info.get('bounds', '-')} |")

    lines.append("")
    lines.append("---")
    lines.append("*Report rendered automatically from machine-readable ValidationCard.*")
    return "\n".join(lines)


def run_positive_control(synthetic_signal: np.ndarray) -> ValidationCard:
    """Positive control: Validate simulated signal against itself. MUST PASS 100%."""
    # Self-validation must have 0 error and 1.0 ratio
    t1 = evaluate_curve_target("Admissions Control", synthetic_signal, synthetic_signal)
    card = build_validation_card("positive_control", [t1])
    return card


def run_negative_control(synthetic_signal: np.ndarray) -> ValidationCard:
    """Negative control: Validate against inverted/reversed signal. MUST FAIL."""
    shuffled_wrong = np.roll(synthetic_signal[::-1], len(synthetic_signal) // 2) * 5.0
    t1 = evaluate_curve_target("Admissions Negative", synthetic_signal, shuffled_wrong)
    card = build_validation_card("negative_control", [t1])
    return card

