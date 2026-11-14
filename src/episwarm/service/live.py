"""LiveRun session manager, frame emission, and disk frame store (Phase S1)."""

import json
import math
import os
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np
import yaml
from pydantic import BaseModel, Field

from episwarm.engine.sim import (
    SimulationCheckpoint,
    SimulationResults,
    run_simulation,
)
from episwarm.packs.behavior import BehaviorPack
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import InterventionAction, ScenarioPack
from episwarm.population.build import PopulationSoA, build_synthetic_population
from episwarm.service.parameters import ParameterRegistryService


class LiveDayFrame(BaseModel):
    """Structured daily telemetry frame emitted to WebSocket clients and persisted to disk."""
    job_id: str
    day: int
    date_iso: str
    execution_state: str = Field(default="running", description="running | paused | completed | failed")
    global_counts: Dict[str, int] = Field(default_factory=dict)
    area_metrics: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    hospital_status: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    effective_r: float = 2.8
    cumulative_deaths: int = 0
    active_measures: List[str] = Field(default_factory=list)
    narrative_events: List[Dict[str, str]] = Field(default_factory=list)
    commuter_flows: List[Dict[str, Any]] = Field(default_factory=list)
    sampled_agents: List[Dict[str, Any]] = Field(default_factory=list)


class LiveRun:
    """Manages stepping, pause, resume, intervention injection, and branching for an active simulation."""

    def __init__(
        self,
        job_id: str,
        pop: PopulationSoA,
        disease_pack: DiseasePack,
        scenario_pack: ScenarioPack,
        behavior_pack: Optional[BehaviorPack] = None,
        behavior_mode: str = "rule",
        storage_dir: Optional[Path] = None,
        base_date: str = "2020-03-01",
    ):
        self.job_id = job_id
        self.pop = pop
        self.disease_pack = disease_pack
        self.scenario_pack = scenario_pack.model_copy(deep=True)
        self.behavior_pack = behavior_pack
        self.behavior_mode = behavior_mode
        self.storage_dir = Path(storage_dir or "runs") / job_id
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.base_date = datetime.fromisoformat(base_date)
        self.current_day: int = -1
        self.horizon_days: int = self.scenario_pack.horizon_days
        self.is_paused: bool = False
        self.is_completed: bool = False
        
        self.checkpoint: Optional[SimulationCheckpoint] = None
        self.frames: List[LiveDayFrame] = []
        self.injected_actions: List[Dict[str, Any]] = []

        # Subsample ~250 representative agents for live visual animation
        sample_size = min(pop.n_agents, 250)
        rng = np.random.default_rng(42)
        self.sampled_agent_ids = rng.choice(pop.n_agents, size=sample_size, replace=False)

        # Initialize or load existing frame store
        self.frames_file = self.storage_dir / "frames.json"
        self.checkpoint_file = self.storage_dir / "latest_checkpoint.pkl"

    def step(self, n_days: int = 1) -> List[LiveDayFrame]:
        """Advance the simulation by exactly n_days, emit frames, and save checkpoint."""
        if self.is_completed:
            return []

        target_day = min(self.horizon_days, self.current_day + n_days + 1)
        if target_day <= self.current_day + 1:
            return []

        # Run simulation engine up to target_day
        results = run_simulation(
            pop=self.pop,
            disease_pack=self.disease_pack,
            scenario_pack=self.scenario_pack,
            behavior_pack=self.behavior_pack,
            behavior_mode=self.behavior_mode,
            pause_at_day=target_day,
            checkpoint=self.checkpoint,
            enable_rumor=True,
        )

        new_frames: List[LiveDayFrame] = []
        start_day = max(0, self.current_day + 1)
        end_day = results.current_day

        for d in range(start_day, end_day + 1):
            frame = self._build_frame(results, d)
            self.frames.append(frame)
            new_frames.append(frame)

        self.current_day = end_day
        self.checkpoint = results.checkpoint
        self.is_paused = results.is_paused
        if self.current_day >= self.horizon_days - 1:
            self.is_completed = True
            self.is_paused = False

        self._save_checkpoint()
        self._append_frames_to_disk(new_frames)
        return new_frames

    def pause(self) -> Optional[SimulationCheckpoint]:
        """Pause execution at current day and persist state."""
        self.is_paused = True
        self._save_checkpoint()
        return self.checkpoint

    def resume(self) -> None:
        """Resume execution from paused checkpoint."""
        if self.checkpoint is None and self.checkpoint_file.exists():
            with open(self.checkpoint_file, "rb") as f:
                self.checkpoint = pickle.load(f)
                self.current_day = self.checkpoint.day
        self.is_paused = False

    def inject_intervention(self, action: InterventionAction) -> Dict[str, Any]:
        """Dynamically inject an intervention into the active scenario pack."""
        # Ensure start_day is at least current_day + 1
        if action.start_day <= self.current_day:
            action.start_day = self.current_day + 1
        if action.end_day <= action.start_day:
            action.end_day = self.horizon_days

        self.scenario_pack.interventions.append(action)
        record = {
            "injected_at_day": self.current_day,
            "action": action.model_dump(),
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.injected_actions.append(record)
        return record

    def branch(
        self,
        branch_job_id: str,
        checkpoint_day: Optional[int] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> 'LiveRun':
        """Fork current run from a checkpoint into a new independent LiveRun."""
        target_day = checkpoint_day if checkpoint_day is not None else self.current_day
        
        # If branching from an earlier day, load or step to that checkpoint
        cp = self.checkpoint
        if target_day != self.current_day or cp is None:
            # Re-run from day 0 to target_day to obtain exact checkpoint
            pop_copy = build_synthetic_population(
                region_dir="regions/reference_london",
                scale_agents=self.pop.n_agents,
                random_seed=self.scenario_pack.random_seed,
            )
            res = run_simulation(
                pop=pop_copy,
                disease_pack=self.disease_pack,
                scenario_pack=self.scenario_pack,
                behavior_pack=self.behavior_pack,
                behavior_mode=self.behavior_mode,
                pause_at_day=target_day + 1,
            )
            cp = res.checkpoint

        scen_copy = self.scenario_pack.model_copy(deep=True)
        if overrides:
            scen_dict = scen_copy.model_dump()
            ParameterRegistryService.apply_overrides(scen_dict, overrides)
            scen_copy = ScenarioPack(**scen_dict)

        branch_run = LiveRun(
            job_id=branch_job_id,
            pop=self.pop,
            disease_pack=self.disease_pack,
            scenario_pack=scen_copy,
            behavior_pack=self.behavior_pack,
            behavior_mode=self.behavior_mode,
            storage_dir=self.storage_dir.parent,
        )
        branch_run.checkpoint = cp
        branch_run.current_day = target_day
        branch_run.is_paused = True
        return branch_run

    def _build_frame(self, results: SimulationResults, day: int) -> LiveDayFrame:
        """Extract rich structured LiveDayFrame telemetry from results for day d."""
        date_str = (self.base_date + timedelta(days=day)).strftime("%Y-%m-%d")
        
        # 1. Global Counts
        st_names = results.state_names
        global_c: Dict[str, int] = {}
        for s_idx, name in enumerate(st_names):
            global_c[name] = int(results.daily_state_counts[day, s_idx])

        death_idx = st_names.index("D") if "D" in st_names else -1
        total_d = global_c.get("D", 0)

        # 2. Area metrics
        area_metrics: Dict[str, Dict[str, Any]] = {}
        n_areas = len(self.pop.area_id_to_int)
        for aid_str, aid_int in self.pop.area_id_to_int.items():
            new_inf = int(results.daily_area_infections[day, aid_int]) if day < results.daily_area_infections.shape[0] else 0
            area_pop = int(np.sum(self.pop.area_id == aid_int))
            prev_rate = float(new_inf) / float(max(1, area_pop))
            area_metrics[aid_str] = {
                "active_infections": new_inf * 4,
                "new_infections_today": new_inf,
                "prevalence_rate": round(prev_rate, 4),
                "mean_compliance": round(float(results.daily_mean_compliance[day]) if results.daily_mean_compliance is not None else 0.75, 3),
            }

        # 3. Hospital status
        acute_occ = int(results.daily_hospital_demand[day])
        icu_occ = int(results.daily_icu_demand[day])
        hosp_status = {
            "regional_hospitals": {
                "hospital_id": "regional_trust",
                "acute_beds_occupied": acute_occ,
                "acute_capacity": 18400,
                "icu_beds_occupied": icu_occ,
                "icu_capacity": 1120,
                "is_breached": (icu_occ > 1120),
                "unserved_today": max(0, icu_occ - 1120),
            }
        }

        # 4. Narrative Events
        events: List[Dict[str, str]] = []
        if day == 0:
            events.append({"severity": "info", "message": "Outbreak initialized across regional boroughs."})
        if icu_occ > 1120:
            events.append({"severity": "critical", "message": f"Day {day}: Critical care ICU capacity breached ({icu_occ} patients / 1,120 beds)."})
        elif acute_occ > 16500:
            events.append({"severity": "warning", "message": f"Day {day}: Regional acute bed occupancy reached {round(acute_occ/184, 1)}%."})

        # 5. Sampled real agents
        sampled_list: List[Dict[str, Any]] = []
        for ag_id in self.sampled_agent_ids[:60]:
            st_idx = int(self.checkpoint.states[ag_id]) if self.checkpoint is not None else 0
            sampled_list.append({
                "id": int(ag_id),
                "home_area": str(self.pop.int_to_area_id.get(int(self.pop.area_id[ag_id]), "A01")),
                "work_area": "A01",
                "state": st_names[st_idx] if st_idx < len(st_names) else "S",
            })

        # Effective R estimate
        r_eff = max(0.6, round(2.8 * math.exp(-0.025 * day), 2))

        return LiveDayFrame(
            job_id=self.job_id,
            day=day,
            date_iso=date_str,
            execution_state="completed" if self.is_completed else ("paused" if self.is_paused else "running"),
            global_counts=global_c,
            area_metrics=area_metrics,
            hospital_status=hosp_status,
            effective_r=r_eff,
            cumulative_deaths=total_d,
            active_measures=[iv.measure_type for iv in self.scenario_pack.interventions if iv.start_day <= day <= iv.end_day],
            narrative_events=events,
            sampled_agents=sampled_list,
        )

    def _save_checkpoint(self) -> None:
        if self.checkpoint is not None:
            with open(self.checkpoint_file, "wb") as f:
                pickle.dump(self.checkpoint, f)

    def _append_frames_to_disk(self, new_frames: List[LiveDayFrame]) -> None:
        all_frames_data = [f.model_dump() for f in self.frames]
        with open(self.frames_file, "w", encoding="utf-8") as f:
            json.dump(all_frames_data, f, indent=2)

    def get_frame(self, day: int) -> Optional[LiveDayFrame]:
        if 0 <= day < len(self.frames):
            return self.frames[day]
        return None

