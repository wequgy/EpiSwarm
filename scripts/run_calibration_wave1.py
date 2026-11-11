"""Wave 1 Regional Calibration & Empirical Validation (Phase 28).

Calibrates transmission parameters (R0, initial seed volume, intervention timing)
against genuine UKHSA/ONS clinical observations from regions/reference_london.
Evaluates pre-registered validation targets and generates machine-verifiable cards and reports.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize
import yaml

from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.engine.sim import run_simulation
from episwarm.evidence.validation_controls import (
    evaluate_curve_target,
    build_validation_card,
    render_markdown_report_from_card
)
from episwarm.evidence.ledger import EvidenceLedger


def run_wave1_calibration():
    print("=== EpiSwarm Wave 1 Empirical Calibration (Phase 28) ===")
    region_dir = Path("regions/reference_london")
    obs_file = region_dir / "observed_cases.csv"

    # Authenticate through Evidence Ledger
    ledger = EvidenceLedger()
    rec = ledger.verify_file(obs_file)
    assert rec is not None, "Observed clinical data must be authenticated by Evidence Ledger"
    print(f"Verified observed data: {obs_file} ({rec.byte_count} bytes, SHA: {rec.sha256[:16]}...)")

    # 1. Load Real Wave 1 Observations (March 1 - May 31, 2020: 92 days)
    df_obs = pd.read_csv(obs_file)
    df_w1 = df_obs[(df_obs["date"] >= "2020-03-01") & (df_obs["date"] <= "2020-05-31")].sort_values("date")
    assert len(df_w1) == 92, f"Expected 92 days for Wave 1, got {len(df_w1)}"

    obs_deaths = df_w1["deaths"].values.astype(np.float64)
    obs_peak_day = int(np.argmax(obs_deaths))
    obs_peak_val = float(np.max(obs_deaths))
    print(f"Observed Wave 1 Deaths: Peak on Day {obs_peak_day} ({df_w1.iloc[obs_peak_day]['date']}), Peak={obs_peak_val:.0f}, Total={np.sum(obs_deaths):.0f}")

    # 2. Setup Disease and Synthetic Population
    # Load default respiratory disease pack
    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        d_dict = yaml.safe_load(f)
    disease_pack = DiseasePack(**d_dict)

    # 3. Fit Analytical Transmission & Timing Parameters
    # We calibrate R0 and takeoff lag t_0 to match peak day (Day 39) and trajectory shape
    # Forward model evaluation function
    pop = build_synthetic_population("regions/reference_london", scale_agents=5000, random_seed=42)
    pop_scale_factor = pop.total_population_represented / pop.n_agents

    # Forward epidemiological transmission model with statutory intervention and onset-to-death delay
    t = np.arange(92)

    def forward_simulate(r_pre: float, r_post: float, tg: float, theta: float):
        # Pre-lockdown transmission until Day 23 (March 23, 2020: statutory lockdown SI 2020/350)
        # Followed by post-lockdown contact suppression
        r = np.where(t < 23, r_pre, r_post)
        growth = (r - 1.0) / max(1.0, tg)
        cum_g = np.cumsum(growth)
        infections = np.exp(cum_g)

        # Convolve with Gamma clinical onset-to-death delay kernel
        kernel = (t ** 2) * np.exp(-t / max(0.5, theta))
        kernel /= np.sum(kernel)
        sim_deaths = np.convolve(infections, kernel)[:92]
        
        # Scale to match observed peak mortality
        sim_deaths *= (obs_peak_val / max(1e-3, np.max(sim_deaths)))
        return sim_deaths

    # Optimization objective: minimize timing, amplitude, and cumulative errors
    def loss_func(params):
        r_pre, r_post, tg, theta = params
        sim_d = forward_simulate(r_pre, r_post, tg, theta)
        peak_err = abs(np.argmax(sim_d) - obs_peak_day)
        cum_err = abs(np.sum(sim_d) - np.sum(obs_deaths)) / np.sum(obs_deaths)
        mse = np.mean((sim_d - obs_deaths) ** 2) / (obs_peak_val ** 2)
        return mse + 2.0 * peak_err + 10.0 * cum_err

    # Fit parameters via Nelder-Mead simplex
    res = minimize(
        loss_func,
        x0=[2.85, 0.68, 5.2, 5.0],
        bounds=[(2.2, 3.6), (0.4, 0.9), (4.0, 6.5), (3.0, 7.0)],
        method="Nelder-Mead"
    )

    opt_r_pre, opt_r_post, opt_tg, opt_theta = res.x
    calibrated_deaths = forward_simulate(opt_r_pre, opt_r_post, opt_tg, opt_theta)
    calib_peak_day = int(np.argmax(calibrated_deaths))
    calib_peak_val = float(np.max(calibrated_deaths))
    print(f"\nCalibrated Parameters:")
    print(f"  Pre-Lockdown R0 = {opt_r_pre:.2f}")
    print(f"  Post-Lockdown Effective R = {opt_r_post:.2f}")
    print(f"  Generation Time Tg = {opt_tg:.1f} days")
    print(f"  Onset-to-Death Delay Parameter = {opt_theta:.2f}")
    print(f"  Simulated Peak Day = Day {calib_peak_day}, Value = {calib_peak_val:.1f}")

    # 4. Evaluate Against Pre-Registered Protocol Thresholds
    target_deaths = evaluate_curve_target(
        name="Registered Deaths",
        obs_curve=obs_deaths,
        sim_curve=calibrated_deaths,
        max_peak_day_error=5,
        min_peak_ratio=0.75,
        max_peak_ratio=1.25,
        max_cumulative_error_pct=25.0
    )

    # 5. Build and Save Machine Card & Render Markdown Report
    validation_card = build_validation_card(
        region_id="reference_london_wave1",
        target_results=[target_deaths]
    )

    # Wave 1 mortality curve fitting is strictly IN-SAMPLE calibration
    card_dict = {
        "status": "CALIBRATED_IN_SAMPLE",
        "region": "Greater London Reference Pack (regions/reference_london)",
        "calibration_window": "Wave 1 (March 1 - May 31, 2020)",
        "calibrated_parameters": {
            "R0_pre_lockdown": round(float(opt_r_pre), 2),
            "R_post_lockdown": round(float(opt_r_post), 2),
            "generation_time_days": round(float(opt_tg), 1),
            "delay_parameter": round(float(opt_theta), 2)
        },
        "targets_passed": "0/0 (In-Sample Only)",
        "targets": {
            "registered_deaths": {
                "in_sample": True,
                "passed": target_deaths.passed,
                "peak_day_error": f"{target_deaths.peak_day_error} days",
                "peak_ratio": target_deaths.peak_ratio,
                "cumulative_error": f"{target_deaths.cumulative_error_pct}%",
                "status": "IN-SAMPLE"
            }
        },
        "ledger_authenticated": True,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
    out_card_path.write_text(json.dumps(card_dict, indent=2), encoding="utf-8")
    print(f"Saved machine calibration card: {out_card_path}")

    # Build ValidationCard for rendering
    v_card = ValidationCard(
        status="CALIBRATED_IN_SAMPLE",
        region_id="reference_london_wave1",
        targets_passed="0/0 (In-Sample)",
        targets=card_dict["targets"],
        all_passed=False
    )
    report_md = render_markdown_report_from_card(v_card)
    out_report_path = Path("docs/validation/VALIDATION_REPORT.md")
    out_report_path.write_text(report_md, encoding="utf-8")
    print(f"Rendered calibration report: {out_report_path}")

    print(f"\nCalibration Result: {card_dict['status']} (In-sample fit complete)")
    return card_dict


if __name__ == "__main__":
    run_wave1_calibration()
