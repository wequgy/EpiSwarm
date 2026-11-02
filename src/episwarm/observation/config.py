"""Observation model configuration, delay distributions, day-of-week effects, and provenance (Phase 18)."""

from typing import List, Optional, Literal, Dict, Any
import numpy as np
from pydantic import BaseModel, Field, field_validator
from scipy import stats

from episwarm.packs.schema import ProvenanceRecord, ProvenanceStatus


class DelayDistribution(BaseModel):
    """Parametric or discrete delay distribution for epidemiological observation delays."""
    dist_type: Literal["gamma", "lognormal", "weibull", "fixed", "discrete"] = Field(
        default="gamma",
        description="Type of distribution: gamma, lognormal, weibull, fixed, or discrete PMF"
    )
    mean: float = Field(default=5.0, description="Mean delay in days")
    std: float = Field(default=2.5, description="Standard deviation of delay in days")
    max_days: int = Field(default=30, description="Truncation horizon in days")
    discrete_pmf: Optional[List[float]] = Field(
        default=None,
        description="Explicit discrete PMF if dist_type='discrete'"
    )
    provenance: ProvenanceRecord = Field(
        default_factory=lambda: ProvenanceRecord(
            source="EpiSwarm Clinical Observation Standard",
            status=ProvenanceStatus.ASSUMED,
            notes="Standard parametric epidemiological delay distribution"
        )
    )

    def to_pmf(self, max_days: Optional[int] = None) -> np.ndarray:
        """Convert continuous delay distribution into discrete probability mass function."""
        horizon = max_days if max_days is not None else self.max_days
        if self.dist_type == "discrete" and self.discrete_pmf is not None:
            raw = np.array(self.discrete_pmf, dtype=np.float64)
            if len(raw) < horizon + 1:
                padded = np.zeros(horizon + 1, dtype=np.float64)
                padded[:len(raw)] = raw
                raw = padded
            else:
                raw = raw[:horizon + 1]
            s = np.sum(raw)
            return raw / s if s > 0 else np.ones(horizon + 1) / (horizon + 1)

        if self.dist_type == "fixed" or self.std <= 1e-4:
            pmf = np.zeros(horizon + 1, dtype=np.float64)
            idx = int(np.clip(np.round(self.mean), 0, horizon))
            pmf[idx] = 1.0
            return pmf

        days = np.arange(horizon + 1, dtype=np.float64)
        if self.dist_type == "gamma":
            # shape k, scale theta: mean = k * theta, var = k * theta^2
            variance = max(1e-4, self.std ** 2)
            k = (self.mean ** 2) / variance
            theta = variance / max(1e-4, self.mean)
            cdf = stats.gamma.cdf(days + 0.5, a=k, scale=theta)
        elif self.dist_type == "lognormal":
            variance = max(1e-4, self.std ** 2)
            sigma2 = np.log(1.0 + variance / (self.mean ** 2))
            sigma = np.sqrt(sigma2)
            mu = np.log(max(1e-4, self.mean)) - 0.5 * sigma2
            cdf = stats.lognorm.cdf(days + 0.5, s=sigma, scale=np.exp(mu))
        elif self.dist_type == "weibull":
            # Approximation via mean and variance
            c = max(0.5, (self.std / max(1e-4, self.mean)) ** -1.086)
            scale = self.mean / stats.gamma.gamma(1.0 + 1.0 / c)
            cdf = stats.weibull_min.cdf(days + 0.5, c=c, scale=scale)
        else:
            cdf = days / horizon

        pmf = np.diff(np.concatenate(([0.0], cdf)))
        s = np.sum(pmf)
        if s > 0:
            pmf /= s
        return pmf


class DayOfWeekEffect(BaseModel):
    """Weekly cyclical modulation for case and death reporting (7 days: Mon..Sun)."""
    weights: List[float] = Field(
        default=[1.20, 1.15, 1.05, 1.00, 0.95, 0.85, 0.80],
        description="Multipliers for Monday through Sunday, mean normalized to 1.0"
    )
    start_day_of_week: int = Field(
        default=0,
        description="Day of week for simulation day 0 (0=Monday, 6=Sunday)"
    )
    provenance: ProvenanceRecord = Field(
        default_factory=lambda: ProvenanceRecord(
            source="EpiSwarm Reporting Dynamics Baseline",
            status=ProvenanceStatus.ASSUMED,
            notes="7-day reporting cycle with Monday catch-up and weekend dip"
        )
    )

    @field_validator("weights")
    @classmethod
    def validate_weights(cls, v: List[float]) -> List[float]:
        if len(v) != 7:
            raise ValueError("weights must have exactly 7 elements (Mon..Sun)")
        arr = np.array(v, dtype=np.float64)
        if np.any(arr < 0):
            raise ValueError("weights must be non-negative")
        mean_w = np.mean(arr)
        if mean_w > 0:
            norm_arr = arr / mean_w
            return [float(x) for x in norm_arr]
        return v

    def get_factor(self, day: int) -> float:
        """Return the day-of-week multiplier for simulation day t."""
        dow = (day + self.start_day_of_week) % 7
        return float(self.weights[dow])


class AscertainmentModel(BaseModel):
    """Time-varying case ascertainment fraction rho(t) reflecting testing capacity."""
    model_type: Literal["constant", "sigmoid", "piecewise_linear"] = Field(
        default="constant",
        description="Functional form of time-varying ascertainment"
    )
    base_fraction: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Baseline case ascertainment fraction"
    )
    max_fraction: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
        description="Maximum ascertainment fraction during testing surge"
    )
    transition_day: float = Field(
        default=30.0,
        description="Midpoint day of testing capacity transition"
    )
    transition_speed: float = Field(
        default=5.0,
        description="Scale parameter (days) for sigmoid testing expansion"
    )
    provenance: ProvenanceRecord = Field(
        default_factory=lambda: ProvenanceRecord(
            source="EpiSwarm Testing Capacity Baseline",
            status=ProvenanceStatus.ASSUMED,
            notes="Under-ascertainment model: true symptomatic cases to reported positive tests"
        )
    )

    def get_fraction(self, day: int, horizon: int) -> float:
        """Compute ascertainment probability on day t."""
        if self.model_type == "constant":
            return float(self.base_fraction)
        elif self.model_type == "sigmoid":
            arg = (day - self.transition_day) / max(0.1, self.transition_speed)
            sig = 1.0 / (1.0 + np.exp(-np.clip(arg, -20.0, 20.0)))
            return float(self.base_fraction + (self.max_fraction - self.base_fraction) * sig)
        elif self.model_type == "piecewise_linear":
            if day <= self.transition_day:
                return float(self.base_fraction)
            end_day = min(float(horizon), self.transition_day + 2.0 * self.transition_speed)
            if day >= end_day:
                return float(self.max_fraction)
            prog = (day - self.transition_day) / max(0.1, end_day - self.transition_day)
            return float(self.base_fraction + (self.max_fraction - self.base_fraction) * prog)
        return float(self.base_fraction)


class HospitalObservationConfig(BaseModel):
    """Observation parameters for hospital admissions and bed occupancy."""
    admission_delay: DelayDistribution = Field(
        default_factory=lambda: DelayDistribution(
            dist_type="gamma",
            mean=6.5,
            std=3.0,
            max_days=25,
            provenance=ProvenanceRecord(
                source="Clinical progression literature (onset to admission)",
                status=ProvenanceStatus.SOURCED,
                notes="Mean onset-to-admission delay ~6.5 days"
            )
        )
    )
    acute_los: DelayDistribution = Field(
        default_factory=lambda: DelayDistribution(
            dist_type="gamma",
            mean=8.0,
            std=4.0,
            max_days=40,
            provenance=ProvenanceRecord(
                source="Hospital length of stay distribution (general ward)",
                status=ProvenanceStatus.SOURCED,
                notes="Mean acute bed length of stay ~8.0 days"
            )
        )
    )
    icu_los: DelayDistribution = Field(
        default_factory=lambda: DelayDistribution(
            dist_type="gamma",
            mean=10.0,
            std=5.0,
            max_days=50,
            provenance=ProvenanceRecord(
                source="ICU length of stay distribution",
                status=ProvenanceStatus.SOURCED,
                notes="Mean critical care length of stay ~10.0 days"
            )
        )
    )
    ventilated_fraction: float = Field(
        default=0.60,
        ge=0.0,
        le=1.0,
        description="Fraction of ICU patients requiring mechanical ventilation"
    )
    admission_reporting_fraction: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Completeness of hospital admission reporting"
    )
    provenance: ProvenanceRecord = Field(
        default_factory=lambda: ProvenanceRecord(
            source="Hospital observation reporting standards",
            status=ProvenanceStatus.ASSUMED,
            notes="Clinical bed occupancy and admission reporting configuration"
        )
    )


class MortalityObservationConfig(BaseModel):
    """Observation parameters for death reporting and registration delays."""
    registration_delay: DelayDistribution = Field(
        default_factory=lambda: DelayDistribution(
            dist_type="gamma",
            mean=4.0,
            std=2.5,
            max_days=30,
            provenance=ProvenanceRecord(
                source="Vital statistics death registration latency",
                status=ProvenanceStatus.SOURCED,
                notes="Mean death occurrence to registry notification delay ~4.0 days"
            )
        )
    )
    reporting_completeness: float = Field(
        default=0.98,
        ge=0.0,
        le=1.0,
        description="Completeness of death certification/registration"
    )
    day_of_week: Optional[DayOfWeekEffect] = Field(
        default_factory=lambda: DayOfWeekEffect(
            weights=[1.10, 1.10, 1.05, 1.00, 0.95, 0.90, 0.90],
            start_day_of_week=0
        )
    )
    provenance: ProvenanceRecord = Field(
        default_factory=lambda: ProvenanceRecord(
            source="Vital statistics registry reporting standards",
            status=ProvenanceStatus.ASSUMED,
            notes="Death reporting configuration"
        )
    )


class SerologyObservationConfig(BaseModel):
    """Parameters for cross-sectional seroprevalence surveillance."""
    test_sensitivity: float = Field(default=0.98, ge=0.5, le=1.0)
    test_specificity: float = Field(default=0.99, ge=0.5, le=1.0)
    seroconversion_delay_days: int = Field(default=14, ge=0, le=60)
    waning_half_life_days: Optional[float] = Field(
        default=180.0,
        description="Half-life of IgG antibody detectability in days (None if no waning)"
    )
    provenance: ProvenanceRecord = Field(
        default_factory=lambda: ProvenanceRecord(
            source="Immunoassay performance characteristics",
            status=ProvenanceStatus.SOURCED,
            notes="ELISA / CLIA antibody test performance"
        )
    )


class ObservationConfig(BaseModel):
    """Complete specification of the epidemiological observation process (Phase 18)."""
    name: str = Field(default="default_surveillance", description="Name of observation specification")
    case_delay: DelayDistribution = Field(
        default_factory=lambda: DelayDistribution(
            dist_type="gamma",
            mean=5.5,
            std=2.5,
            max_days=25,
            provenance=ProvenanceRecord(
                source="Surveillance case reporting delay (onset to public report)",
                status=ProvenanceStatus.SOURCED,
                notes="Mean onset-to-report delay ~5.5 days"
            )
        )
    )
    day_of_week: DayOfWeekEffect = Field(default_factory=DayOfWeekEffect)
    ascertainment: AscertainmentModel = Field(default_factory=AscertainmentModel)
    hospital: HospitalObservationConfig = Field(default_factory=HospitalObservationConfig)
    mortality: MortalityObservationConfig = Field(default_factory=MortalityObservationConfig)
    serology: SerologyObservationConfig = Field(default_factory=SerologyObservationConfig)

    reporting_noise: Literal["none", "poisson", "negbin"] = Field(
        default="negbin",
        description="Observation error noise distribution"
    )
    negbin_dispersion: float = Field(
        default=15.0,
        description="Overdispersion parameter phi for NegBin (higher = closer to Poisson)"
    )
    mode: Literal["as_eventually_reported", "vintage_delayed"] = Field(
        default="as_eventually_reported",
        description="Reporting vintage mode: revision-free as eventually reported or vintage cuts"
    )
    provenance: ProvenanceRecord = Field(
        default_factory=lambda: ProvenanceRecord(
            source="EpiSwarm Public Health Surveillance Standard",
            status=ProvenanceStatus.ASSUMED,
            notes="Comprehensive observation and reporting model configuration"
        )
    )

