"""Rule-Based Policy Critic: Multi-attribute feasibility, equity, and fatigue critique (Stage A5).

Deterministic heuristic scoring across four dimensions:
1. Operational feasibility & temporal consistency
2. Socioeconomic equity & age distribution impact
3. Budget efficiency (cost per hospitalization averted)
4. Behavioral fatigue and compliance exhaustion risk
Note: Real LLM evaluation is deferred to Stage R3.3.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import numpy as np

from episwarm.packs.scenario import ScenarioPack, InterventionAction


@dataclass
class CriticDimensionScore:
    dimension: str
    score: float       # 0.0 (worst) to 1.0 (best)
    assessment: str
    concerns: List[str]


@dataclass
class PolicyCritique:
    overall_score: float
    approved: bool
    dimension_scores: Dict[str, CriticDimensionScore]
    summary_verdict: str
    equity_tradeoffs: List[str]


class PolicyCritic:
    """Evaluates proposed scenarios across feasibility, equity, cost, and fatigue."""

    def evaluate_scenario(
        self,
        scenario: ScenarioPack,
        baseline_icu_capacity: float = 800.0,
        estimated_peak_icu: Optional[float] = None
    ) -> PolicyCritique:
        dim_scores = {}
        all_concerns = []

        # 1. Feasibility & Temporal Consistency
        feas_score = 1.0
        feas_concerns = []
        for i, action in enumerate(scenario.interventions):
            if action.start_day >= action.end_day:
                feas_score -= 0.50
                feas_concerns.append(f"Action '{action.name}' has invalid duration (start_day >= end_day).")
            if action.start_day < 0:
                feas_score -= 0.30
                feas_concerns.append(f"Action '{action.name}' has negative start day.")
            if action.stringency < 0.0 or action.stringency > 1.0:
                feas_score -= 0.30
                feas_concerns.append(f"Action '{action.name}' has stringency outside [0, 1].")

        feas_score = max(0.0, feas_score)
        dim_scores["feasibility"] = CriticDimensionScore(
            dimension="Feasibility & Consistency",
            score=round(feas_score, 2),
            assessment="PASS" if feas_score >= 0.80 else "NEEDS_REVISION",
            concerns=feas_concerns
        )

        # 2. Equity & Cohort Distribution
        equity_score = 0.90
        equity_concerns = []
        equity_tradeoffs = []

        has_school = any(a.measure_type == "school_closure" for a in scenario.interventions)
        school_duration = sum(
            (a.end_day - a.start_day) for a in scenario.interventions
            if a.measure_type == "school_closure"
        )
        if school_duration > 35:
            equity_score -= 0.25
            equity_concerns.append(f"School closures exceed 5 weeks ({school_duration} days), severely impacting educational equity.")
            equity_tradeoffs.append("Significant developmental disruption for lower-income pupils lacking remote learning infrastructure.")

        has_lockdown = any(a.measure_type == "stay_at_home" for a in scenario.interventions)
        if has_lockdown:
            equity_tradeoffs.append("Stay-at-home restrictions place disproportionate economic burden on hourly and informal workers.")

        equity_score = max(0.10, equity_score)
        dim_scores["equity"] = CriticDimensionScore(
            dimension="Socioeconomic Equity",
            score=round(equity_score, 2),
            assessment="ACCEPTABLE" if equity_score >= 0.70 else "EQUITY_RISK",
            concerns=equity_concerns
        )

        # 3. Budget Efficiency
        cost_score = 0.85
        cost_concerns = []
        total_intervention_cost = sum(
            a.cost_per_day * max(1, a.end_day - a.start_day)
            for a in scenario.interventions
        )
        if total_intervention_cost > 300.0:
            cost_score -= 0.20
            cost_concerns.append(f"High cumulative intervention cost index ({total_intervention_cost:.1f}).")

        dim_scores["budget_efficiency"] = CriticDimensionScore(
            dimension="Budget Efficiency",
            score=round(max(0.1, cost_score), 2),
            assessment="MODERATE" if cost_score >= 0.70 else "EXPENSIVE",
            concerns=cost_concerns
        )

        # 4. Behavioral Fatigue Risk
        fatigue_score = 0.95
        fatigue_concerns = []
        max_continuous_high_stringency = 0
        current_streak = 0
        for day in range(scenario.horizon_days):
            active_str = max([
                a.stringency for a in scenario.interventions
                if a.start_day <= day <= a.end_day
            ], default=0.0)
            if active_str > 0.70:
                current_streak += 1
                max_continuous_high_stringency = max(max_continuous_high_stringency, current_streak)
            else:
                current_streak = 0

        if max_continuous_high_stringency > 50:
            fatigue_score -= 0.35
            fatigue_concerns.append(
                f"Continuous high-stringency period lasts {max_continuous_high_stringency} days (>50 days), provoking compliance exhaustion."
            )

        fatigue_score = max(0.1, fatigue_score)
        dim_scores["fatigue_risk"] = CriticDimensionScore(
            dimension="Behavioral Fatigue Risk",
            score=round(fatigue_score, 2),
            assessment="LOW_FATIGUE" if fatigue_score >= 0.75 else "HIGH_FATIGUE_EROSION",
            concerns=fatigue_concerns
        )

        overall = float(np.mean([ds.score for ds in dim_scores.values()]))
        approved = overall >= 0.65 and dim_scores["feasibility"].score >= 0.80

        verdict = "Policy package approved with minor equity advisories." if approved else "Policy rejected: critical feasibility or fatigue thresholds violated."

        return PolicyCritique(
            overall_score=round(overall, 3),
            approved=approved,
            dimension_scores=dim_scores,
            summary_verdict=verdict,
            equity_tradeoffs=equity_tradeoffs
        )
