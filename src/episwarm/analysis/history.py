"""Simulation run logging and historical trajectory archive (Spec 11 & Phase 24).

Persists every simulation execution to a structured JSONL archive and individual run manifests,
enabling historical comparison, audit log export, and post-run playback.
"""

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import json
import numpy as np
import pandas as pd

from episwarm.engine.sim import SimulationResults


class SimulationHistoryManager:
    """Manages persistent historical records of all simulation runs."""

    def __init__(self, logs_dir: Optional[Path] = None):
        self.logs_dir = Path(logs_dir or "logs")
        self.runs_dir = self.logs_dir / "runs"
        self.history_file = self.logs_dir / "simulation_history.jsonl"
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def save_run(
        self,
        results: SimulationResults,
        region_id: str,
        scenario_name: str,
        disease_name: str,
        behavior_mode: str,
        population_scale: int,
        interventions: Optional[List[str]] = None,
        extra_meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Save a complete structured run manifest to history."""
        timestamp_str = datetime.now().isoformat()
        run_id = results.run_id or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Daily trajectory table
        daily_records = []
        n_days = results.horizon_days
        symp_idx = results.state_names.index("I_symp") if "I_symp" in results.state_names else (
            results.state_names.index("I") if "I" in results.state_names else -1
        )
        death_idx = results.state_names.index("D") if "D" in results.state_names else -1

        for d in range(n_days):
            active_cases = int(results.daily_state_counts[d, symp_idx]) if symp_idx >= 0 else 0
            deaths = int(results.daily_state_counts[d, death_idx]) if death_idx >= 0 else 0
            hosp = int(results.daily_hospital_demand[d]) if d < len(results.daily_hospital_demand) else 0
            icu = int(results.daily_icu_demand[d]) if d < len(results.daily_icu_demand) else 0
            comp = float(results.daily_mean_compliance[d]) if results.daily_mean_compliance is not None and d < len(results.daily_mean_compliance) else 0.0

            daily_records.append({
                "day": d,
                "active_cases": active_cases,
                "hospitalized": hosp,
                "icu": icu,
                "cumulative_deaths": deaths,
                "mean_compliance": round(comp, 3)
            })

        # Compile full run record
        record: Dict[str, Any] = {
            "run_id": run_id,
            "timestamp": timestamp_str,
            "region_id": region_id,
            "scenario_name": scenario_name,
            "disease_name": disease_name,
            "behavior_mode": behavior_mode,
            "population_scale": population_scale,
            "horizon_days": n_days,
            "is_paused": getattr(results, "is_paused", False),
            "interventions": interventions or [],
            "metrics": {
                "attack_rate_pct": round(float(results.attack_rate * 100), 2),
                "total_infections": int(results.total_infections),
                "total_deaths": int(results.total_deaths),
                "overflow_deaths": int(results.overflow_deaths),
                "peak_day": int(np.argmax(results.daily_hospital_demand)) if len(results.daily_hospital_demand) > 0 else 0,
                "peak_hospital_demand": int(np.max(results.daily_hospital_demand)) if len(results.daily_hospital_demand) > 0 else 0,
                "peak_icu_demand": int(np.max(results.daily_icu_demand)) if len(results.daily_icu_demand) > 0 else 0,
                "calibrated_beta": round(float(results.calibrated_beta), 4),
                "target_r0": round(float(results.target_r0), 2),
                "empirical_r0": round(float(results.empirical_r0), 2)
            },
            "events_log": getattr(results, "event_logs", []),
            "daily_timeline": daily_records,
            "metadata": extra_meta or {}
        }

        # 1. Append line to history.jsonl
        with open(self.history_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        # 2. Write individual detailed run file
        run_file = self.runs_dir / f"{run_id}.json"
        with open(run_file, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)

        return record

    def load_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Load recent runs from history.jsonl in reverse chronological order."""
        if not self.history_file.exists():
            return []

        records = []
        with open(self.history_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except Exception:
                        pass
        return list(reversed(records))[:limit]

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve full details of a specific past run."""
        run_file = self.runs_dir / f"{run_id}.json"
        if run_file.exists():
            with open(run_file, "r", encoding="utf-8") as f:
                return json.load(f)

        # Fallback search in history.jsonl
        for r in self.load_history(limit=500):
            if r.get("run_id") == run_id:
                return r
        return None

    def export_summary_df(self) -> pd.DataFrame:
        """Export tabular summary of all past runs for comparison."""
        runs = self.load_history(limit=100)
        rows = []
        for r in runs:
            m = r.get("metrics", {})
            rows.append({
                "Run ID": r.get("run_id"),
                "Timestamp": r.get("timestamp", "")[:19].replace("T", " "),
                "Region": r.get("region_id"),
                "Scenario": r.get("scenario_name"),
                "Disease": r.get("disease_name"),
                "Behavior Mode": r.get("behavior_mode"),
                "Days": r.get("horizon_days"),
                "Attack Rate (%)": m.get("attack_rate_pct"),
                "Total Deaths": m.get("total_deaths"),
                "Peak Hospital Beds": m.get("peak_hospital_demand"),
                "Peak ICU Beds": m.get("peak_icu_demand"),
                "Status": "PAUSED" if r.get("is_paused") else "COMPLETED"
            })
        return pd.DataFrame(rows)

    def clear_history(self) -> bool:
        """Clear the historical log archive."""
        if self.history_file.exists():
            self.history_file.unlink()
        return True

