"""Synthetic test run fixture for frontend development with MOCK DATA banner and headers."""

import math
from typing import Any, Dict, List
from episwarm.service.models import (
    RunSummary,
    MetricsSummary,
    MetricBounds,
    TimeSeriesData,
    SpatialOutput,
    AreaSpatialPoint,
    CapacityOutput,
    JobRecord,
    JobStatus,
    RunCreateRequest,
)

MOCK_HEADER = {"X-EpiSwarm-Mock": "true"}
MOCK_BANNER = "[MOCK DATA] Synthetic Run Fixture for Offline UI Development - Not Clinically Validated"


def create_mock_job_record(job_id: str = "mock-run-fixture-001") -> JobRecord:
    """Return a pre-computed completed mock job record."""
    return JobRecord(
        job_id=job_id,
        status=JobStatus.COMPLETED,
        created_at="2026-11-14T10:00:00Z",
        started_at="2026-11-14T10:00:01Z",
        completed_at="2026-11-14T10:00:05Z",
        progress=1.0,
        current_day=60,
        total_days=60,
        request=RunCreateRequest(
            region_id="example_synthetic",
            disease_id="respiratory_generic",
            scenario_id="targeted_containment",
            scale_agents=3000,
            behavior_mode="rule",
            n_replicates=5,
            random_seed=42,
            horizon_days=60,
            use_mock=True,
        ),
        results_summary={
            "attack_rate": 0.425,
            "peak_day": 28,
            "total_deaths": 142,
            "peak_hospital_demand": 380,
            "peak_icu_demand": 64,
        },
        is_mock=True,
    )


def create_mock_run_summary(job_id: str = "mock-run-fixture-001") -> RunSummary:
    """Return an executive summary for a synthetic mock run."""
    return RunSummary(
        job_id=job_id,
        region_id="example_synthetic",
        disease_id="respiratory_generic",
        scenario_id="targeted_containment",
        behavior_mode="rule",
        scale_agents=3000,
        n_replicates=5,
        metrics=MetricsSummary(
            attack_rate=MetricBounds(mean=0.425, ci_lower=0.392, ci_upper=0.458, std=0.016),
            peak_day=MetricBounds(mean=28.0, ci_lower=26.0, ci_upper=30.0, std=1.0),
            total_deaths=MetricBounds(mean=142.0, ci_lower=124.0, ci_upper=160.0, std=9.0),
            peak_hospital_demand=MetricBounds(mean=380.0, ci_lower=340.0, ci_upper=420.0, std=20.0),
            peak_icu_demand=MetricBounds(mean=64.0, ci_lower=52.0, ci_upper=76.0, std=6.0),
            overflow_deaths=MetricBounds(mean=12.0, ci_lower=4.0, ci_upper=20.0, std=4.0),
        ),
        validation_status="SYNTHETIC_MOCK",
        validation_card_url="/api/v1/validation/card",
        is_mock=True,
        banner=MOCK_BANNER,
    )


def create_mock_timeseries(job_id: str = "mock-run-fixture-001", horizon_days: int = 60) -> TimeSeriesData:
    """Generate smooth epidemiological curve telemetry for mock frontend charts."""
    days = list(range(horizon_days + 1))
    s_curve = []
    e_curve = []
    i_curve = []
    r_curve = []
    d_curve = []
    hosp_curve = []
    icu_curve = []
    deaths_daily = []
    compliance = []

    total_pop = 3000.0
    for d in days:
        # Gaussian infection wave peak around day 28
        wave = math.exp(-0.5 * ((d - 28.0) / 7.0) ** 2)
        inf = total_pop * 0.18 * wave
        cum_inf = total_pop * 0.425 / (1.0 + math.exp(-0.2 * (d - 24.0)))
        exp = inf * 0.6
        dead = cum_inf * 0.025
        rec = max(0.0, cum_inf - inf - exp - dead)
        sus = max(0.0, total_pop - cum_inf)

        hosp = inf * 0.14
        icu = hosp * 0.22
        daily_d = dead * 0.08 if d > 10 else 0.0

        comp = 0.5 + 0.35 * (inf / (total_pop * 0.18 + 1e-5))

        s_curve.append(round(sus, 1))
        e_curve.append(round(exp, 1))
        i_curve.append(round(inf, 1))
        r_curve.append(round(rec, 1))
        d_curve.append(round(dead, 1))
        hosp_curve.append(round(hosp, 1))
        icu_curve.append(round(icu, 1))
        deaths_daily.append(round(daily_d, 2))
        compliance.append(round(min(1.0, comp), 3))

    return TimeSeriesData(
        job_id=job_id,
        horizon_days=horizon_days,
        days=days,
        state_names=["S", "E", "I_symp", "R", "D"],
        daily_states={
            "S": s_curve,
            "E": e_curve,
            "I_symp": i_curve,
            "R": r_curve,
            "D": d_curve,
        },
        daily_hospital_demand=hosp_curve,
        daily_icu_demand=icu_curve,
        daily_deaths=deaths_daily,
        daily_mean_compliance=compliance,
        is_mock=True,
    )


def create_mock_spatial(job_id: str = "mock-run-fixture-001") -> SpatialOutput:
    """Generate 6-borough mock isometric city layout with infection heatmaps."""
    borough_defs = [
        ("A01", "Central Business Core", 60000, 12000, 0, 0, 0.48),
        ("A02", "North Riverside", 45000, 7500, 90, 45, 0.44),
        ("A03", "South Commerce District", 50000, 8900, -90, 45, 0.46),
        ("A04", "East Residential Park", 38000, 4200, 90, -45, 0.38),
        ("A05", "West Innovation Hub", 52000, 9500, -90, -45, 0.41),
        ("A06", "Harbor Port & Industrial", 32000, 3100, 180, 0, 0.35),
    ]

    areas: List[AreaSpatialPoint] = []
    for b_id, name, pop, density, iso_x, iso_y, ar in borough_defs:
        tot_inf = int(pop * ar)
        daily_inc = [
            round(tot_inf * 0.05 * math.exp(-0.5 * ((d - 27.0) / 6.0) ** 2), 1)
            for d in range(61)
        ]
        areas.append(
            AreaSpatialPoint(
                area_id=b_id,
                name=name,
                population=pop,
                density=float(density),
                iso_x=float(iso_x),
                iso_y=float(iso_y),
                total_infections=tot_inf,
                attack_rate=ar,
                daily_incident_infections=daily_inc,
                peak_day=27,
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
        region_id="example_synthetic",
        n_areas=len(areas),
        areas=areas,
        layers=layers,
        is_mock=True,
    )


def create_mock_capacity(job_id: str = "mock-run-fixture-001") -> CapacityOutput:
    """Generate hospital & ICU capacity stress output for mock runs."""
    ts = create_mock_timeseries(job_id=job_id)
    hosp_cap = 280.0
    icu_cap = 45.0

    hosp_overflow_days = sum(1 for d in ts.daily_hospital_demand if d > hosp_cap)
    icu_overflow_days = sum(1 for d in ts.daily_icu_demand if d > icu_cap)

    unmet_hosp = [int(max(0, d - hosp_cap)) for d in ts.daily_hospital_demand]
    unmet_icu = [int(max(0, d - icu_cap)) for d in ts.daily_icu_demand]

    return CapacityOutput(
        job_id=job_id,
        hospital_capacity_beds=hosp_cap,
        icu_capacity_beds=icu_cap,
        daily_hospital_demand=ts.daily_hospital_demand,
        daily_icu_demand=ts.daily_icu_demand,
        overflow_days_hospital=hosp_overflow_days,
        overflow_days_icu=icu_overflow_days,
        overflow_deaths=14,
        daily_unmet_demand={"hospital_beds": unmet_hosp, "icu_beds": unmet_icu},
        is_mock=True,
    )
