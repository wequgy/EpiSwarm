"""Healthcare Capacity & Overflow Validation (Phase 31 - Repaired).

Validates simulated hospital and ICU bed occupancy dynamics against genuine
NHS England London Wave 1 clinical surveillance data across >= 30 paired seeds.
Evaluates pre-registered targets:
- Peak ICU bed ratio within [0.75, 1.25]
- ICU overflow duration (> baseline capacity) error <= 7 days
Strictly forbids analytic curve generators, gamma convolutions, and post-hoc
rescaling to observed peaks.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import yaml

from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.engine.sim import run_simulation
from episwarm.evidence.fetch import fetch_and_register
from episwarm.evidence.ledger import EvidenceLedger


def download_healthcare_data(ledger: EvidenceLedger) -> Path:
    """Download or retrieve authentic NHS England / GLA daily hospital activity data for London."""
    dest_path = Path("evidence/raw/gla_phe_healthcare_london.csv")
    if dest_path.exists():
        rec = ledger.verify_file(dest_path)
        if rec is not None:
            return dest_path

    url = "https://data.london.gov.uk/download/e6yg0/87ee8ecb-00e3-4ed1-beb8-56cc043ef0df/phe_healthcare.csv"
    rec = fetch_and_register(
        url=url,
        dest_path=dest_path,
        license_name="Open Government Licence v3.0 (OGL-3.0)",
        notes="GLA / NHS England London daily hospital admissions, total occupied beds, and mechanical ventilation (ICU) beds.",
        ledger=ledger,
        timeout=30.0
    )
    return dest_path


def run_healthcare_validation(n_seeds: int = 30, scale_agents: int = 5000) -> Dict[str, Any]:
    print(f"=== EpiSwarm Healthcare Capacity Validation (Phase 31 - {n_seeds} seeds) ===")
    region_dir = Path("regions/reference_london")
    ledger = EvidenceLedger()

    # 1. Authentic empirical metrics from NHS England
    csv_path = download_healthcare_data(ledger)
    df = pd.read_csv(csv_path)

    w1_icu = df[(df["area_name"] == "London") & 
                (df["healthcare_type"] == "Patients in mechanical ventilation beds") & 
                (df["date"] <= "2020-05-31")].dropna().sort_values("date")
    w1_hosp = df[(df["area_name"] == "London") & 
                 (df["healthcare_type"] == "Patients in Hospital") & 
                 (df["date"] <= "2020-05-31")].dropna().sort_values("date")

    obs_peak_hosp = float(w1_hosp["patients"].max())
    obs_peak_icu = float(w1_icu["patients"].max())
    obs_icu_date = w1_icu.loc[w1_icu["patients"].idxmax(), "date"]

    # London nominal ICU baseline capacity: 800 beds (Class C Assumed)
    icu_capacity_threshold = 800
    obs_overflow_days = int((w1_icu["patients"] > icu_capacity_threshold).sum())

    print(f"Empirical NHS London Wave 1 Data:")
    print(f"  Peak Total Hospital Occupancy: {obs_peak_hosp:.0f} beds")
    print(f"  Peak Mechanical Ventilation (ICU): {obs_peak_icu:.0f} beds on {obs_icu_date}")
    print(f"  Empirical ICU Overflow Days (> {icu_capacity_threshold} beds): {obs_overflow_days} days")

    # 2. Genuine Multi-Seed Agent Simulation (NO analytic curves, NO peak rescaling)
    print(f"\nSynthesizing population ({scale_agents} agents) and setting up Wave 1 statutory interventions...")
    pop = build_synthetic_population(str(region_dir), scale_agents=scale_agents, random_seed=42)
    contacts_df = pd.read_csv(region_dir / "contacts.csv")

    with open("diseases/respiratory_generic.yaml", "r", encoding="utf-8") as f:
        d_dict = yaml.safe_load(f)
    disease_pack = DiseasePack(**d_dict)

    with open("scenarios/baseline.yaml", "r", encoding="utf-8") as f:
        s_dict = yaml.safe_load(f)

    # Configure Wave 1 seeding and statutory intervention package (SI 2020/350)
    s_dict["seeding"]["area_id"] = "E09000020"
    s_dict["seeding"]["initial_cases_per_area"] = 30
    s_dict["interventions"] = [
        {"name": "workplace_reduction", "measure_type": "workplace_reduction", "area_id": "ALL", "start_day": 16, "end_day": 90, "stringency": 0.60},
        {"name": "statutory_lockdown", "measure_type": "curfew", "area_id": "ALL", "start_day": 23, "end_day": 90, "stringency": 0.75},
        {"name": "school_closure", "measure_type": "school_closure", "area_id": "ALL", "start_day": 23, "end_day": 90, "stringency": 1.0}
    ]

    sim_peaks: List[float] = []
    sim_overflows: List[int] = []

    print(f"Running {n_seeds} simulation runs with genuine StateGraph healthcare accounting...")
    for s_idx in range(n_seeds):
        s_dict["random_seed"] = 5200 + s_idx
        scenario_pack = ScenarioPack(**s_dict)
        res = run_simulation(pop, disease_pack, scenario_pack, contacts_df=contacts_df)

        scaled_icu = res.daily_icu_demand * res.sampling_ratio
        sim_peaks.append(float(np.max(scaled_icu)))
        sim_overflows.append(int(np.sum(scaled_icu > icu_capacity_threshold)))

    mean_sim_peak = float(np.mean(sim_peaks))
    mean_sim_overflow = float(np.mean(sim_overflows))
    peak_ratio = mean_sim_peak / max(1e-6, obs_peak_icu)
    overflow_diff = abs(int(round(mean_sim_overflow)) - obs_overflow_days)

    print(f"\nSimulated Healthcare Dynamics (Agent Engine across {n_seeds} seeds):")
    print(f"  Simulated Mean Peak ICU: {mean_sim_peak:.1f} beds (Observed: {obs_peak_icu:.0f}, Ratio: {peak_ratio:.3f})")
    print(f"  Simulated Mean Overflow Days: {mean_sim_overflow:.1f} days (Observed: {obs_overflow_days}, Error: {overflow_diff} days)")

    # 3. Check Pre-Registered Thresholds
    ratio_pass = bool(0.75 <= peak_ratio <= 1.25)
    overflow_pass = bool(overflow_diff <= 7)
    target_pass = bool(ratio_pass and overflow_pass)

    print(f"\nValidation Targets:")
    print(f"  Peak Bed Ratio within [0.75, 1.25]: {peak_ratio:.3f} -> {'PASS' if ratio_pass else 'FAIL'}")
    print(f"  Overflow Days Error <= 7: {overflow_diff} days -> {'PASS' if overflow_pass else 'FAIL'}")

    # 4. Update VALIDATION_CARD.json
    card_path = Path("docs/validation/VALIDATION_CARD.json")
    if card_path.exists():
        card_data = json.loads(card_path.read_text(encoding="utf-8"))
    else:
        card_data = {"status": "UNCALIBRATED", "targets": {}}

    card_data["targets"]["healthcare_overflow"] = {
        "passed": target_pass,
        "observed_peak_beds": obs_peak_icu,
        "simulated_peak_beds": round(mean_sim_peak, 1),
        "peak_ratio": round(peak_ratio, 3),
        "observed_overflow_days": obs_overflow_days,
        "simulated_overflow_days": round(mean_sim_overflow, 1),
        "overflow_days_error": overflow_diff,
        "thresholds": "peak ratio in [0.75, 1.25], overflow error <= 7 days",
        "method": "agent_simulator_30_seeds",
        "status": "PASS" if target_pass else "FAIL"
    }

    all_targets = [t.get("passed", False) for t in card_data["targets"].values() if not t.get("in_sample", False)]
    passed_cnt = sum(all_targets)
    tot_cnt = len(all_targets)
    card_data["status"] = "VALIDATED" if (passed_cnt == tot_cnt and tot_cnt > 0) else "PARTIALLY_VALIDATED"
    card_data["targets_passed"] = f"{passed_cnt}/{tot_cnt}"
    card_data["generated_at"] = datetime.now(timezone.utc).isoformat()

    card_path.write_text(json.dumps(card_data, indent=2), encoding="utf-8")
    print(f"Updated machine validation card: {card_path} ({card_data['status']}, {card_data['targets_passed']})")

    return {
        "passed": target_pass,
        "peak_ratio": peak_ratio,
        "overflow_days_error": overflow_diff,
        "status": "PASS" if target_pass else "FAIL"
    }


if __name__ == "__main__":
    run_healthcare_validation(n_seeds=30)
