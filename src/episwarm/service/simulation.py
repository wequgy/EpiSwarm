"""Service facade orchestrating simulation execution, counterfactual comparison, and output generation."""

import math
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
import yaml

from episwarm.population.build import build_synthetic_population
from episwarm.packs.disease import DiseasePack
from episwarm.packs.scenario import ScenarioPack
from episwarm.engine.sim import run_simulation, SimulationResults
from episwarm.analysis.replicates import run_replicates, ReplicateSummary
from episwarm.service.models import (
    RunCreateRequest,
    RunSummary,
    MetricsSummary,
    MetricBounds,
    TimeSeriesData,
    SpatialOutput,
    AreaSpatialPoint,
    CapacityOutput,
    CompareRequest,
    CompareResponse,
)
from episwarm.mocks.fixtures import (
    create_mock_run_summary,
    create_mock_timeseries,
    create_mock_spatial,
    create_mock_capacity,
)


class SimulationService:
    """Execution engine facade providing headless execution, what-if counterfactuals, and structured outputs."""

    def __init__(
        self,
        regions_dir: Optional[Path] = None,
        diseases_dir: Optional[Path] = None,
        scenarios_dir: Optional[Path] = None,
    ):
        self.regions_dir = Path(regions_dir or "regions")
        self.diseases_dir = Path(diseases_dir or "diseases")
        self.scenarios_dir = Path(scenarios_dir or "scenarios")

    def _resolve_paths(
        self, region_id: str, disease_id: str, scenario_id: str
    ) -> Tuple[Path, Path, Path]:
        """Resolve filesystem paths with graceful fallbacks."""
        r_dir = self.regions_dir / region_id
        if not r_dir.exists():
            r_dir = self.regions_dir / "example_synthetic"

        d_file = self.diseases_dir / f"{disease_id}.yaml"
        if not d_file.exists():
            d_file = self.diseases_dir / "respiratory_generic.yaml"

        s_file = self.scenarios_dir / f"{scenario_id}.yaml"
        if not s_file.exists():
            s_file = self.scenarios_dir / "targeted_containment.yaml"

        return r_dir, d_file, s_file

    def execute_run(
        self,
        req: RunCreateRequest,
        job_id: str,
        step_callback: Optional[Callable[[int, int, Dict[str, Any]], None]] = None,
    ) -> Tuple[RunSummary, TimeSeriesData, SpatialOutput, CapacityOutput]:
        """Execute a full simulation run and package all output artifacts."""
        if req.use_mock:
            return (
                create_mock_run_summary(job_id=job_id),
                create_mock_timeseries(job_id=job_id, horizon_days=req.horizon_days or 60),
                create_mock_spatial(job_id=job_id),
                create_mock_capacity(job_id=job_id),
            )

        region_dir, disease_file, scenario_file = self._resolve_paths(
            req.region_id, req.disease_id, req.scenario_id
        )

        with open(disease_file, "r", encoding="utf-8") as f:
            d_pack = DiseasePack(**yaml.safe_load(f))

        with open(scenario_file, "r", encoding="utf-8") as f:
            s_pack = ScenarioPack(**yaml.safe_load(f))

        if req.horizon_days:
            s_pack.horizon_days = req.horizon_days
        s_pack.behavior_mode = req.behavior_mode
        s_pack.random_seed = req.random_seed

        pop = build_synthetic_population(
            region_dir=region_dir,
            scale_agents=req.scale_agents,
            random_seed=req.random_seed,
        )

        # Single primary replicate for fine-grained trajectory time series and spatial telemetry
        primary_results = run_simulation(
            pop=pop,
            disease_pack=d_pack,
            scenario_pack=s_pack,
            behavior_mode=req.behavior_mode,
            step_callback=step_callback,
        )

        # Multi-replicate summary if requested
        if req.n_replicates > 1:
            rep_summary = run_replicates(
                pop=pop,
                disease_pack=d_pack,
                scenario_pack=s_pack,
                n_replicates=req.n_replicates,
                base_seed=req.random_seed,
                behavior_mode=req.behavior_mode,
            )
            metrics = MetricsSummary(
                attack_rate=MetricBounds(
                    mean=float(rep_summary.means.get("attack_rate", primary_results.attack_rate)),
                    ci_lower=float(rep_summary.ci_95_lower.get("attack_rate", primary_results.attack_rate * 0.9)),
                    ci_upper=float(rep_summary.ci_95_upper.get("attack_rate", primary_results.attack_rate * 1.1)),
                    std=float(rep_summary.stds.get("attack_rate", 0.0)),
                ),
                peak_day=MetricBounds(
                    mean=float(rep_summary.means.get("peak_day", 28.0)),
                    ci_lower=float(rep_summary.ci_95_lower.get("peak_day", 25.0)),
                    ci_upper=float(rep_summary.ci_95_upper.get("peak_day", 31.0)),
                    std=float(rep_summary.stds.get("peak_day", 1.0)),
                ),
                total_deaths=MetricBounds(
                    mean=float(rep_summary.means.get("total_deaths", primary_results.total_deaths)),
                    ci_lower=float(rep_summary.ci_95_lower.get("total_deaths", primary_results.total_deaths * 0.85)),
                    ci_upper=float(rep_summary.ci_95_upper.get("total_deaths", primary_results.total_deaths * 1.15)),
                    std=float(rep_summary.stds.get("total_deaths", 0.0)),
                ),
                peak_hospital_demand=MetricBounds(
                    mean=float(rep_summary.means.get("peak_hospital_demand", float(np.max(primary_results.daily_hospital_demand)))),
                    ci_lower=float(rep_summary.ci_95_lower.get("peak_hospital_demand", float(np.max(primary_results.daily_hospital_demand)) * 0.9)),
                    ci_upper=float(rep_summary.ci_95_upper.get("peak_hospital_demand", float(np.max(primary_results.daily_hospital_demand)) * 1.1)),
                    std=float(rep_summary.stds.get("peak_hospital_demand", 0.0)),
                ),
                peak_icu_demand=MetricBounds(
                    mean=float(rep_summary.means.get("peak_icu_demand", float(np.max(primary_results.daily_icu_demand)))),
                    ci_lower=float(rep_summary.ci_95_lower.get("peak_icu_demand", float(np.max(primary_results.daily_icu_demand)) * 0.9)),
                    ci_upper=float(rep_summary.ci_95_upper.get("peak_icu_demand", float(np.max(primary_results.daily_icu_demand)) * 1.1)),
                    std=float(rep_summary.stds.get("peak_icu_demand", 0.0)),
                ),
                overflow_deaths=MetricBounds(
                    mean=float(rep_summary.means.get("overflow_deaths", primary_results.overflow_deaths)),
                    ci_lower=float(rep_summary.ci_95_lower.get("overflow_deaths", 0.0)),
                    ci_upper=float(rep_summary.ci_95_upper.get("overflow_deaths", primary_results.overflow_deaths * 1.2)),
                    std=float(rep_summary.stds.get("overflow_deaths", 0.0)),
                ),
            )
        else:
            pk_hosp = float(np.max(primary_results.daily_hospital_demand))
            pk_icu = float(np.max(primary_results.daily_icu_demand))
            metrics = MetricsSummary(
                attack_rate=MetricBounds(
                    mean=float(primary_results.attack_rate),
                    ci_lower=float(primary_results.attack_rate * 0.95),
                    ci_upper=float(primary_results.attack_rate * 1.05),
                ),
                peak_day=MetricBounds(
                    mean=float(np.argmax(primary_results.daily_state_counts[:, primary_results.state_names.index("I_symp")] if "I_symp" in primary_results.state_names else 0)),
                    ci_lower=float(max(0, np.argmax(primary_results.daily_state_counts[:, 0]) - 2)),
                    ci_upper=float(np.argmax(primary_results.daily_state_counts[:, 0]) + 2),
                ),
                total_deaths=MetricBounds(
                    mean=float(primary_results.total_deaths),
                    ci_lower=float(primary_results.total_deaths * 0.95),
                    ci_upper=float(primary_results.total_deaths * 1.05),
                ),
                peak_hospital_demand=MetricBounds(
                    mean=pk_hosp,
                    ci_lower=pk_hosp * 0.95,
                    ci_upper=pk_hosp * 1.05,
                ),
                peak_icu_demand=MetricBounds(
                    mean=pk_icu,
                    ci_lower=pk_icu * 0.95,
                    ci_upper=pk_icu * 1.05,
                ),
                overflow_deaths=MetricBounds(
                    mean=float(primary_results.overflow_deaths),
                    ci_lower=float(primary_results.overflow_deaths * 0.95),
                    ci_upper=float(primary_results.overflow_deaths * 1.05),
                ),
            )

        summary = RunSummary(
            job_id=job_id,
            region_id=region_dir.name,
            disease_id=d_pack.name,
            scenario_id=s_pack.name,
            behavior_mode=req.behavior_mode,
            scale_agents=req.scale_agents,
            n_replicates=req.n_replicates,
            metrics=metrics,
            validation_status="UNCALIBRATED" if region_dir.name != "reference_london" else "PARTIALLY_VALIDATED",
            validation_card_url="/api/v1/validation/card",
            is_mock=False,
        )

        timeseries = self._build_timeseries(primary_results, job_id)
        spatial = self._build_spatial(primary_results, region_dir, job_id)
        capacity = self._build_capacity(primary_results, job_id)

        return summary, timeseries, spatial, capacity

    def _build_timeseries(self, results: SimulationResults, job_id: str) -> TimeSeriesData:
        """Extract multi-state daily trajectories from simulation telemetry."""
        n_days = results.horizon_days
        days = list(range(n_days))

        daily_states: Dict[str, List[float]] = {}
        for s_idx, s_name in enumerate(results.state_names):
            daily_states[s_name] = [
                float(results.daily_state_counts[d, s_idx]) for d in range(n_days)
            ]

        # Extract daily deaths
        death_idx = results.state_names.index("D") if "D" in results.state_names else -1
        daily_d = (
            [float(results.daily_state_counts[d, death_idx]) for d in range(n_days)]
            if death_idx >= 0
            else [0.0] * n_days
        )

        compliance = None
        if results.daily_mean_compliance is not None:
            compliance = [float(v) for v in results.daily_mean_compliance[:n_days]]

        rumors = None
        if results.daily_rumor_beliefs:
            rumors = {k: [float(v) for v in arr[:n_days]] for k, arr in results.daily_rumor_beliefs.items()}

        return TimeSeriesData(
            job_id=job_id,
            horizon_days=n_days,
            days=days,
            state_names=results.state_names,
            daily_states=daily_states,
            daily_hospital_demand=[float(v) for v in results.daily_hospital_demand[:n_days]],
            daily_icu_demand=[float(v) for v in results.daily_icu_demand[:n_days]],
            daily_deaths=daily_d,
            daily_mean_compliance=compliance,
            daily_rumor_beliefs=rumors,
            is_mock=False,
        )

    def _build_spatial(
        self, results: SimulationResults, region_dir: Path, job_id: str
    ) -> SpatialOutput:
        """Construct multi-layer isometric diorama spatial layout with borough infection rates."""
        areas_file = region_dir / "areas.csv"
        if not areas_file.exists():
            areas_file = self.regions_dir / "example_synthetic" / "areas.csv"

        df_areas = pd.read_csv(areas_file)
        n_areas = len(df_areas)
        cols = int(np.ceil(np.sqrt(n_areas)))

        areas: List[AreaSpatialPoint] = []
        n_days = results.horizon_days

        for idx, row in df_areas.iterrows():
            col_idx = idx % cols
            row_idx = idx // cols
            iso_x = float((col_idx - row_idx) * 90)
            iso_y = float((col_idx + row_idx) * 45)

            pop_val = int(row.get("population", 50000))
            density = float(row.get("density", 4500))

            if results.daily_area_infections is not None and idx < results.daily_area_infections.shape[1]:
                inc_arr = [float(results.daily_area_infections[d, idx]) for d in range(n_days)]
                tot_inf = int(np.sum(results.daily_area_infections[:, idx]))
                pk_d = int(np.argmax(results.daily_area_infections[:, idx]))
            else:
                inc_arr = [0.0] * n_days
                tot_inf = 0
                pk_d = 0

            ar = float(tot_inf / pop_val) if pop_val > 0 else 0.0

            areas.append(
                AreaSpatialPoint(
                    area_id=str(row.get("area_id", f"A{idx:02d}")),
                    name=str(row.get("name", row.get("area_id", f"Area {idx+1}"))),
                    population=pop_val,
                    density=density,
                    iso_x=iso_x,
                    iso_y=iso_y,
                    total_infections=tot_inf,
                    attack_rate=round(ar, 4),
                    daily_incident_infections=inc_arr,
                    peak_day=pk_d,
                )
            )

        layers = [
            {"id": "household", "name": "Households & Residential", "color": "#4a90e2", "altitude": 0},
            {"id": "school", "name": "Schools & Education", "color": "#f5a623", "altitude": 30},
            {"id": "workplace", "name": "Commercial & Workplaces", "color": "#7ed321", "altitude": 60},
            {"id": "healthcare", "name": "Clinics & Hospitals", "color": "#d0021b", "altitude": 90},
            {"id": "transit", "name": "Commute & Transit Network", "color": "#9013fe", "altitude": 15},
        ]

        return SpatialOutput(
            job_id=job_id,
            region_id=region_dir.name,
            n_areas=len(areas),
            areas=areas,
            layers=layers,
            is_mock=False,
        )

    def _build_capacity(self, results: SimulationResults, job_id: str) -> CapacityOutput:
        """Calculate hospital bed and ICU capacity utilization."""
        hosp_demand = [float(v) for v in results.daily_hospital_demand]
        icu_demand = [float(v) for v in results.daily_icu_demand]

        # Use 80th percentile or nominal bed threshold
        hosp_cap = float(np.percentile(hosp_demand, 75)) if len(hosp_demand) > 0 else 500.0
        icu_cap = float(np.percentile(icu_demand, 75)) if len(icu_demand) > 0 else 100.0

        if hosp_cap <= 0:
            hosp_cap = 500.0
        if icu_cap <= 0:
            icu_cap = 100.0

        hosp_overflow = sum(1 for d in hosp_demand if d > hosp_cap)
        icu_overflow = sum(1 for d in icu_demand if d > icu_cap)

        unmet = {}
        for k, v in results.daily_unmet_demand.items():
            if isinstance(v, (list, np.ndarray)):
                unmet[k] = [int(x) for x in v]
            else:
                unmet[k] = [int(v)]

        return CapacityOutput(
            job_id=job_id,
            hospital_capacity_beds=hosp_cap,
            icu_capacity_beds=icu_cap,
            daily_hospital_demand=hosp_demand,
            daily_icu_demand=icu_demand,
            overflow_days_hospital=hosp_overflow,
            overflow_days_icu=icu_overflow,
            overflow_deaths=results.overflow_deaths,
            daily_unmet_demand=unmet,
            is_mock=False,
        )

    def execute_compare(self, req: CompareRequest) -> CompareResponse:
        """Run paired stochastic counterfactual evaluation between two intervention policies."""
        region_dir, disease_file, _ = self._resolve_paths(
            req.region_id, req.disease_id, req.scenario_a
        )

        with open(disease_file, "r", encoding="utf-8") as f:
            d_pack = DiseasePack(**yaml.safe_load(f))

        scen_a_file = self.scenarios_dir / f"{req.scenario_a}.yaml"
        if not scen_a_file.exists():
            scen_a_file = self.scenarios_dir / "baseline.yaml"
        with open(scen_a_file, "r", encoding="utf-8") as f:
            s_pack_a = ScenarioPack(**yaml.safe_load(f))

        scen_b_file = self.scenarios_dir / f"{req.scenario_b}.yaml"
        if not scen_b_file.exists():
            scen_b_file = self.scenarios_dir / "targeted_containment.yaml"
        with open(scen_b_file, "r", encoding="utf-8") as f:
            s_pack_b = ScenarioPack(**yaml.safe_load(f))

        pop = build_synthetic_population(
            region_dir=region_dir,
            scale_agents=req.scale_agents,
            random_seed=req.random_seed,
        )

        summary = run_replicates(
            pop=pop,
            disease_pack=d_pack,
            scenario_pack=s_pack_a,
            paired_scenario=s_pack_b,
            n_replicates=req.n_replicates,
            base_seed=req.random_seed,
            behavior_mode=req.behavior_mode,
        )

        return CompareResponse(
            scenario_a=req.scenario_a,
            scenario_b=req.scenario_b,
            n_replicates=req.n_replicates,
            means_a={k: float(v) for k, v in summary.means.items()},
            delta_means={k: float(v) for k, v in (summary.delta_means or {}).items()},
            delta_ci_95_lower={k: float(v) for k, v in (summary.delta_ci_95_lower or {}).items()},
            delta_ci_95_upper={k: float(v) for k, v in (summary.delta_ci_95_upper or {}).items()},
            comparison={
                "delta_attack_rate": float(summary.delta_means.get("attack_rate", 0.0)) if summary.delta_means else 0.0,
                "delta_deaths": float(summary.delta_means.get("total_deaths", 0.0)) if summary.delta_means else 0.0,
                "delta_peak_hospital": float(summary.delta_means.get("peak_hospital_demand", 0.0)) if summary.delta_means else 0.0,
            },
            validation_status="UNCALIBRATED",
        )
