"""Behavior System v3: Teacher-Student Behavioral Architecture (Stage A4).

Implements:
1. CoMixEmpiricalTeacher: Macro/archetype prior provider calibrated to CoMix survey by period & age.
2. VectorizedStudentEvaluator: Fast vectorized logit evaluator operating over individual agent state arrays.
3. OutOfRangeDetector: Detects when simulation conditions depart from empirical CoMix support.
4. DataConstrainedTier: Fallback specification with wider uncertainty bounds for regions lacking local survey data.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd

from episwarm.population.build import PopulationSoA
from episwarm.packs.schema import ProvenanceRecord, ProvenanceStatus
from episwarm.behavior.hierarchical import HierarchicalCoefficients


# Empirical baseline contact rates (Jarvis et al. 2020 / Mossong et al. 2008 Polymod)
POLYMOD_BASELINE_CONTACTS: Dict[str, float] = {
    "0-4": 10.2,
    "5-11": 14.8,
    "12-17": 18.2,
    "18-29": 11.5,
    "30-39": 10.5,
    "40-49": 10.8,
    "50-59": 9.8,
    "60-69": 7.8,
    "70+": 5.6
}

# Empirical period policy stringency from OxCGRT England index
COMIX_PERIOD_STRINGENCY: Dict[str, float] = {
    "1. Lockdown 1": 0.85,
    "2. Lockdown 1 easing": 0.65,
    "3. Relaxed restrictions": 0.45,
    "4. School reopening": 0.50,
    "5. Lockdown 2": 0.75,
    "6. Lockdown 2 easing": 0.65,
    "7. Christmas": 0.70,
    "8. Lockdown 3": 0.88,
    "9. Lockdown 3 + schools": 0.82
}

# Age clinical vulnerability / risk weight
AGE_VULNERABILITY: Dict[str, float] = {
    "0-4": 0.05,
    "5-11": 0.05,
    "12-17": 0.10,
    "18-29": 0.20,
    "30-39": 0.35,
    "40-49": 0.50,
    "50-59": 0.65,
    "60-69": 0.80,
    "70+": 0.95
}


@dataclass
class TeacherArchetypePrior:
    """Archetype macro-level compliance and behavioral reduction prior."""
    period: str
    age_band: str
    stringency: float
    base_reduction: float
    std_error: float
    decision_priors: Dict[str, float]


class CoMixEmpiricalTeacher:
    """Teacher model: Generates macro/archetype priors calibrated to CoMix contact survey."""

    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = data_path or Path("evidence/raw/comix_contact_matrices_england.csv")
        self.calibrated = False
        self.strata_priors: Dict[Tuple[str, str], TeacherArchetypePrior] = {}
        self.beta_weights: Dict[str, float] = {
            "intercept": -1.75,
            "stringency": 3.05,
            "vulnerability": 0.44,
            "fatigue": -0.55
        }
        self._load_or_fit()

    def _load_or_fit(self) -> None:
        if self.data_path.exists():
            try:
                df = pd.read_csv(self.data_path)
                tot = df.groupby(["Period", "Participant age"])["mean contacts"].sum().reset_index()
                tot["baseline"] = tot["Participant age"].map(POLYMOD_BASELINE_CONTACTS).fillna(10.0)
                tot["reduction"] = np.clip(1.0 - (tot["mean contacts"] / tot["baseline"]), 0.05, 0.95)

                for _, row in tot.iterrows():
                    period = str(row["Period"])
                    age_b = str(row["Participant age"])
                    red = float(row["reduction"])
                    stringency = COMIX_PERIOD_STRINGENCY.get(period, 0.50)
                    
                    # Compute specific question priors from reduction
                    priors = {
                        "limit_social_contacts": red,
                        "isolate_symptomatic": float(np.clip(red * 1.15, 0.20, 0.98)),
                        "workplace_attendance": float(np.clip(1.0 - red * 0.90, 0.05, 0.95)),
                        "wear_mask": float(np.clip(red * 1.05, 0.10, 0.95)),
                        "school_attendance": float(np.clip(1.0 - red * 1.10, 0.05, 0.95))
                    }
                    self.strata_priors[(period, age_b)] = TeacherArchetypePrior(
                        period=period,
                        age_band=age_b,
                        stringency=stringency,
                        base_reduction=red,
                        std_error=0.04,
                        decision_priors=priors
                    )
                self.calibrated = True
            except Exception:
                self._fallback_synthetic()
        else:
            self._fallback_synthetic()

    def _fallback_synthetic(self) -> None:
        for p, s in COMIX_PERIOD_STRINGENCY.items():
            for a, v in AGE_VULNERABILITY.items():
                logit = -1.75 + 3.05 * s + 0.44 * v
                red = float(1.0 / (1.0 + np.exp(-logit)))
                self.strata_priors[(p, a)] = TeacherArchetypePrior(
                    period=p,
                    age_band=a,
                    stringency=s,
                    base_reduction=red,
                    std_error=0.08,
                    decision_priors={
                        "limit_social_contacts": red,
                        "isolate_symptomatic": float(np.clip(red * 1.15, 0.20, 0.98)),
                        "workplace_attendance": float(np.clip(1.0 - red * 0.90, 0.05, 0.95)),
                        "wear_mask": float(np.clip(red * 1.05, 0.10, 0.95)),
                        "school_attendance": float(np.clip(1.0 - red * 1.10, 0.05, 0.95))
                    }
                )

    def get_macro_prior(
        self,
        question_id: str,
        age: int,
        policy_stringency: float,
        fatigue: float = 0.0,
        period: Optional[str] = None
    ) -> Tuple[float, float]:
        """Return base prior probability and standard error for given question and demographic."""
        # Map integer age to age band
        if age <= 4:
            ab = "0-4"
        elif age <= 11:
            ab = "5-11"
        elif age <= 17:
            ab = "12-17"
        elif age <= 29:
            ab = "18-29"
        elif age <= 39:
            ab = "30-39"
        elif age <= 49:
            ab = "40-49"
        elif age <= 59:
            ab = "50-59"
        elif age <= 69:
            ab = "60-69"
        else:
            ab = "70+"

        vuln = AGE_VULNERABILITY.get(ab, 0.50)
        logit_pred = (
            self.beta_weights["intercept"] +
            self.beta_weights["stringency"] * policy_stringency +
            self.beta_weights["vulnerability"] * vuln +
            self.beta_weights["fatigue"] * fatigue
        )
        base_p = float(1.0 / (1.0 + np.exp(-logit_pred)))
        base_p = float(np.clip(base_p, 0.05, 0.95))

        if question_id == "isolate_symptomatic":
            p = float(np.clip(base_p * 1.15, 0.10, 0.98))
        elif question_id == "workplace_attendance":
            p = float(np.clip(1.0 - base_p * 0.85, 0.05, 0.95))
        elif question_id == "wear_mask":
            p = float(np.clip(base_p * 1.05, 0.05, 0.95))
        elif question_id == "school_attendance":
            p = float(np.clip(1.0 - base_p * 1.10, 0.05, 0.95))
        else:
            p = base_p

        return p, 0.05


class VectorizedStudentEvaluator:
    """Student model: Ultra-fast vectorized evaluator operating over individual agent state arrays."""

    def __init__(self, coefs: Optional[HierarchicalCoefficients] = None):
        self.coefs = coefs or HierarchicalCoefficients()

    def evaluate_vectorized(
        self,
        pop: PopulationSoA,
        base_priors: np.ndarray,      # Base prior per agent (shape: N)
        question_id: str,
        peer_social_norm: np.ndarray, # Peer norm per agent (shape: N)
        fatigue_array: np.ndarray,    # Dynamic fatigue per agent (shape: N)
        rumor_beliefs: Optional[np.ndarray] = None # Misinformation belief (shape: N)
    ) -> np.ndarray:
        """Compute individual decision probabilities for all N agents simultaneously in O(N) vectorized time."""
        N = pop.n_agents
        p0 = np.clip(base_priors, 0.005, 0.995)
        alpha_0 = np.log(p0 / (1.0 - p0))

        # Vectorized trait arrays
        c_arr = pop.compliance
        trust_arr = pop.trust
        risk_arr = pop.risk_tolerance
        buff_arr = pop.financial_buffer
        bereave_arr = pop.past_bereavement.astype(np.float32)

        rumor_arr = rumor_beliefs if rumor_beliefs is not None else np.zeros(N, dtype=np.float32)

        # Vectorized logit shift
        delta_logit = (
            self.coefs.beta_compliance * (c_arr - 0.5) +
            self.coefs.beta_trust * (trust_arr - 0.5) -
            self.coefs.beta_risk_tolerance * (risk_arr - 0.5) +
            self.coefs.beta_social_norm * (peer_social_norm - 0.5) -
            self.coefs.beta_fatigue * fatigue_array -
            self.coefs.beta_rumor * rumor_arr
        )

        if question_id in ("isolate_symptomatic", "workplace_attendance"):
            delta_logit += self.coefs.beta_financial_buffer * (buff_arr - 0.5)

        if question_id == "wear_mask":
            delta_logit += self.coefs.beta_past_bereavement * bereave_arr

        # Numerically stable sigmoid evaluation
        total_logit = np.clip(alpha_0 + delta_logit, -8.0, 8.0)
        p_individual = 1.0 / (1.0 + np.exp(-total_logit))
        return np.clip(p_individual, 0.01, 0.99).astype(np.float32)


@dataclass
class OutOfRangeWarning:
    severity: str  # "WARNING" or "CRITICAL"
    condition: str
    message: str
    empirical_bound: Tuple[float, float]
    observed_value: float


class OutOfRangeDetector:
    """Detects when simulation conditions operate outside the empirical support of the CoMix survey."""

    def __init__(self):
        # Empirical support ranges observed in CoMix England 2020-2021
        self.support_bounds = {
            "policy_stringency": (0.30, 0.92),
            "fatigue_level": (0.00, 0.85),
            "mean_compliance_prior": (0.15, 0.90),
            "age_mean": (30.0, 48.0)
        }

    def check_conditions(
        self,
        policy_stringency: float,
        fatigue_level: float,
        mean_compliance_prior: float,
        agent_ages: Optional[np.ndarray] = None
    ) -> List[OutOfRangeWarning]:
        warnings = []

        # 1. Stringency bounds
        b_min, b_max = self.support_bounds["policy_stringency"]
        if policy_stringency < b_min or policy_stringency > b_max:
            warnings.append(OutOfRangeWarning(
                severity="WARNING" if policy_stringency > b_max else "CRITICAL",
                condition="POLICY_STRINGENCY_OUT_OF_BOUNDS",
                message=f"Stringency {policy_stringency:.2f} lies outside empirical CoMix support [{b_min}, {b_max}].",
                empirical_bound=(b_min, b_max),
                observed_value=policy_stringency
            ))

        # 2. Fatigue bounds
        f_min, f_max = self.support_bounds["fatigue_level"]
        if fatigue_level > f_max:
            warnings.append(OutOfRangeWarning(
                severity="WARNING",
                condition="EXCESSIVE_FATIGUE",
                message=f"Fatigue level {fatigue_level:.2f} exceeds peak survey fatigue {f_max}.",
                empirical_bound=(f_min, f_max),
                observed_value=fatigue_level
            ))

        # 3. Unrealistic zero fatigue at ultra-high stringency
        if policy_stringency > 0.80 and fatigue_level < 0.02:
            warnings.append(OutOfRangeWarning(
                severity="WARNING",
                condition="UNREALISTIC_FATIGUE_ASSUMPTION",
                message="Near-zero fatigue under strict lockdown (>0.80) departs from longitudinal survey dynamics.",
                empirical_bound=(0.10, 0.85),
                observed_value=fatigue_level
            ))

        # 4. Demographic support
        if agent_ages is not None and len(agent_ages) > 0:
            mean_age = float(np.mean(agent_ages))
            a_min, a_max = self.support_bounds["age_mean"]
            if mean_age < a_min or mean_age > a_max:
                warnings.append(OutOfRangeWarning(
                    severity="WARNING",
                    condition="EXTREME_AGE_DEMOGRAPHY",
                    message=f"Mean agent age {mean_age:.1f} deviates from representative population support [{a_min}, {a_max}].",
                    empirical_bound=(a_min, a_max),
                    observed_value=mean_age
                ))

        return warnings


class DataConstrainedTier:
    """Fallback specification with explicit uncertainty inflation for regions lacking localized survey data."""

    def __init__(self, uncertainty_multiplier: float = 2.5):
        self.uncertainty_multiplier = uncertainty_multiplier
        self.provenance = ProvenanceRecord(
            source="Data-Constrained Behavioral Envelope (Generic International Priors)",
            status=ProvenanceStatus.SYNTHETIC,
            notes="No local contact survey detected. Defaulting to widened empirical envelope with 2.5x variance inflation."
        )

    def apply_uncertainty_inflation(
        self,
        base_probabilities: np.ndarray,
        std_error: float = 0.05
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return central probabilities along with widened [lower, upper] confidence envelopes."""
        inflated_se = std_error * self.uncertainty_multiplier
        # Widened 95% intervals
        lower = np.clip(base_probabilities - 1.96 * inflated_se, 0.01, 0.99)
        upper = np.clip(base_probabilities + 1.96 * inflated_se, 0.01, 0.99)
        return base_probabilities, lower, upper
