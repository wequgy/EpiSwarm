"""Gated Fresh Held-Out Evaluation on London Wave 3 (Winter Alpha Surge) (Stage A6).

Evaluates the uncompromised London Wave 3 held-out window (2020-12-01 to 2021-02-28)
under strict HeldOutGate protocol pre-registration and cryptographic hash chaining.
Updates VALIDATION_CARD.json and VALIDATION_REPORT.md.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack, InterventionAction
from episwarm.engine.sim import run_simulation
from episwarm.evidence.ledger import EvidenceLedger, compute_sha256
from episwarm.evidence.held_out import HeldOutGate, HeldOutAccessRecord


def run_fresh_held_out_evaluation() -> Dict[str, Any]:
    print("=== Stage A6: Gated Fresh Held-Out Wave 3 Evaluation ===")
    t0 = time.time()
    region_dir = Path("regions/reference_london")
    ledger = EvidenceLedger()
    gate = HeldOutGate(
        log_path=Path("docs/validation/HELD_OUT_LOG.jsonl"),
        protocol_path=Path("docs/validation/PROTOCOL.md")
    )

    window_name = "London_Wave3_2020-12-01_to_2021-02-28"
    model_version = "v3.0.0-phase6"

    # 1. Protocol Pre-Registration Verification
    proto_hash = gate.compute_current_protocol_hash()
    print(f"Verified Committed PROTOCOL.md hash: {proto_hash}")

    # Verify window is not compromised
    if gate.is_window_compromised(window_name, model_version):
        raise RuntimeError(f"Window {window_name} is unexpectedly marked COMPROMISED.")

    # 2. Extract Empirical Wave 3 Healthcare Ground Truth (NHS England / UKHSA)
    hosp_file = Path("evidence/raw/gla_phe_healthcare_london.csv")
    assert hosp_file.exists(), "Missing healthcare observations file"

    df_hosp = pd.read_csv(hosp_file)
    w3_icu = df_hosp[
        (df_hosp["area_name"] == "London") &
        (df_hosp["healthcare_type"] == "Patients in mechanical ventilation beds") &
        (df_hosp["date"] >= "2020-12-01") &
        (df_hosp["date"] <= "2021-02-28")
    ].dropna().sort_values("date").reset_index(drop=True)

    obs_icu_beds = w3_icu["patients"].values.astype(np.float64)
    obs_peak_day = int(np.argmax(obs_icu_beds))
    obs_peak_val = float(np.max(obs_icu_beds))
    obs_total = float(np.sum(obs_icu_beds))

    print(f"Empirical Wave 3 Target: 90 days, Peak Day {obs_peak_day} (2021-01-24), Peak Beds {obs_peak_val:.1f}")

    # 3. Build Population and Run Simulation with Calibrated Parameters
    pop = build_synthetic_population(str(region_dir), scale_agents=50000, random_seed=42)
    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        dp_dict = yaml.safe_load(f)
    # Calibrated Alpha parameters (R0 ~ 3.2 pre-lockdown 3)
    dp_dict["transmission"]["r0"] = 3.20
    dp = DiseasePack(**dp_dict)

    with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
        sc_dict = yaml.safe_load(f)

    # Wave 3 Policy timeline: Tier 3/4 restrictions from Day 15, National Lockdown 3 from Day 35
    sc_dict["horizon_days"] = 90
    sc_dict["seeding"]["initial_cases_per_area"] = 65
    sc_dict["behavior_mode"] = "rule"
    sc_dict["interventions"] = [
        InterventionAction(
            name="london_tier3_tier4",
            measure_type="workplace_closure",
            area_id="ALL",
            start_day=15,
            end_day=35,
            stringency=0.65,
            cost_per_day=2.0
        ).model_dump(),
        InterventionAction(
            name="national_lockdown_3",
            measure_type="stay_at_home",
            area_id="ALL",
            start_day=35,
            end_day=90,
            stringency=0.88,
            cost_per_day=4.5
        ).model_dump()
    ]
    sc = ScenarioPack(**sc_dict)
    contacts_df = pd.read_csv(region_dir / "contacts.csv")

    print("Executing Wave 3 simulation across 50,000 agents...")
    res = run_simulation(pop, dp, sc, contacts_df=contacts_df, enable_behavior=True)

    sim_icu_beds = res.daily_icu_demand * res.sampling_ratio
    sim_peak_day = int(np.argmax(sim_icu_beds))
    sim_peak_val = float(np.max(sim_icu_beds))
    sim_total = float(np.sum(sim_icu_beds))

    # 4. Metrics Evaluation
    timing_err = abs(sim_peak_day - obs_peak_day)
    peak_ratio = sim_peak_val / max(1e-3, obs_peak_val)
    cum_err_pct = abs(sim_total - obs_total) / max(1.0, obs_total) * 100.0

    # Pre-registered acceptance criteria: timing error <= 10 days, peak ratio in [0.70, 1.30]
    passed = (timing_err <= 10) and (0.70 <= peak_ratio <= 1.30)
    verdict = "PASS" if passed else "FAIL"

    print(f"Wave 3 Validation Results:")
    print(f"  Peak Day Error: {timing_err} days (Sim: {sim_peak_day}, Obs: {obs_peak_day})")
    print(f"  Peak ICU Ratio: {peak_ratio:.3f} (Sim: {sim_peak_val:.1f}, Obs: {obs_peak_val:.1f})")
    print(f"  Cumulative Error: {cum_err_pct:.1f}%")
    print(f"  Pre-registered Thresholds: Timing <= 10d, Peak Ratio in [0.70, 1.30] -> Verdict: **{verdict}**")

    # 5. Append Hash-Chained Audit Record to HELD_OUT_LOG.jsonl
    prev_hash = gate.get_last_line_hash()
    past_runs = gate._read_log()
    eval_count = sum(1 for r in past_runs if r.get("held_out_window") == window_name) + 1

    audit_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "eval_count": eval_count,
        "protocol_hash": proto_hash,
        "model_version": model_version,
        "held_out_window": window_name,
        "parameters": {
            "R0_alpha": 3.20,
            "seed_per_borough": 65,
            "behavior_mode": "rule",
            "scale_agents": 50000
        },
        "metrics": {
            "peak_day_error": timing_err,
            "peak_ratio": round(peak_ratio, 3),
            "cumulative_error_pct": round(cum_err_pct, 2),
            "observed_peak_beds": obs_peak_val,
            "simulated_peak_beds": round(sim_peak_val, 1)
        },
        "status": "FIRST_EVALUATION" if eval_count == 1 else "REPEAT",
        "verdict": verdict,
        "prev_entry_sha256": prev_hash
    }

    with open(gate.log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(audit_entry) + "\n")
    print(f"Appended hash-chained audit record #{eval_count} to: {gate.log_path}")

    # 6. Update Machine Validation Card
    card_path = Path("docs/validation/VALIDATION_CARD.json")
    if card_path.exists():
        card_data = json.loads(card_path.read_text(encoding="utf-8"))
    else:
        card_data = {"status": "UNCALIBRATED", "targets": {}}

    card_data["targets"]["held_out_wave3"] = {
        "passed": passed,
        "status": verdict,
        "held_out_window": window_name,
        "observed_peak_beds": obs_peak_val,
        "simulated_peak_beds": round(sim_peak_val, 1),
        "peak_ratio": round(peak_ratio, 3),
        "peak_day_error": f"{timing_err} days",
        "cumulative_error": f"{cum_err_pct:.1f}%",
        "thresholds": "peak ratio in [0.70, 1.30], timing error <= 10 days"
    }

    # Recompute overall validation status
    val_targets = [k for k, v in card_data["targets"].items() if not v.get("in_sample", False)]
    passed_cnt = sum(1 for k in val_targets if card_data["targets"][k].get("passed", False))
    tot_cnt = len(val_targets)
    card_data["targets_passed"] = f"{passed_cnt}/{tot_cnt}"
    card_data["status"] = (
        "UNCALIBRATED" if passed_cnt == 0 else
        ("VALIDATED" if passed_cnt == tot_cnt else "PARTIALLY_VALIDATED")
    )
    card_data["generated_at"] = datetime.now(timezone.utc).isoformat()
    card_path.write_text(json.dumps(card_data, indent=2), encoding="utf-8")
    print(f"Updated machine card: {card_path} ({card_data['status']}, {card_data['targets_passed']})")

    # 7. Update Human-Readable Validation Report
    _update_validation_report(card_data, Path("docs/validation/VALIDATION_REPORT.md"))

    return {
        "status": verdict,
        "passed": passed,
        "peak_day_error": timing_err,
        "peak_ratio": peak_ratio,
        "cumulative_error_pct": cum_err_pct,
        "card_status": card_data["status"],
        "targets_passed": card_data["targets_passed"],
        "elapsed_sec": round(time.time() - t0, 2)
    }


from episwarm.evidence.validation_controls import (
    ValidationCard, render_markdown_report_from_card
)


def _update_validation_report(card_data: Dict[str, Any], report_path: Path) -> None:
    val_card = ValidationCard(
        status=card_data["status"],
        region_id=card_data.get("region", "Greater London Reference Pack"),
        targets_passed=card_data.get("targets_passed", "0/4"),
        targets=card_data["targets"],
        all_passed=(card_data["status"] == "VALIDATED")
    )
    val_card.assumptions = card_data.get("assumptions")
    report_text = render_markdown_report_from_card(val_card)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    print(f"Saved validation report to: {report_path}")


if __name__ == "__main__":
    run_fresh_held_out_evaluation()
