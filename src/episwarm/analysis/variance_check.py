"""Variance checks and ablation harness for behavioral decision models."""

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from episwarm.packs.behavior import DecisionQuestion, QuestionType
from episwarm.behavior.buckets import AgentBucket, SituationBucket
from episwarm.behavior.policy_base import DecisionPolicy
from episwarm.behavior.policy_rules import RulePolicy


def generate_benchmark_archetypes() -> List[Tuple[SituationBucket, AgentBucket]]:
    """Create representative test grid of (situation, agent_bucket) pairs."""
    archetypes = []
    age_bands = ["5-18", "19-64", "65+"]
    occupations = ["service", "manufacturing"]
    trust_levels = ["low", "high"]
    risk_levels = ["low", "critical"]

    for age in age_bands:
        for occ in occupations:
            for trust in trust_levels:
                for r_lvl in risk_levels:
                    bucket = AgentBucket(
                        age_band=age,
                        occupation_class=occ,
                        has_comorbidity=(age == "65+"),
                        trust_band=trust,
                        risk_tolerance_band="low" if age == "65+" else "high"
                    )
                    situation = SituationBucket(
                        health_state_group="symptomatic" if r_lvl == "critical" else "susceptible",
                        local_risk_level=r_lvl,
                        active_measures="curfew" if r_lvl == "critical" else "none",
                        household_member_sick=(r_lvl == "critical")
                    )
                    archetypes.append((situation, bucket))

    return archetypes


def evaluate_policy_variance(
    policy: DecisionPolicy,
    question: DecisionQuestion,
    archetypes: List[Tuple[SituationBucket, AgentBucket]]
) -> Dict[str, float]:
    """Compute variance and diversity of policy responses across archetypes."""
    prob_vectors = []
    for sit, buck in archetypes:
        probs = policy.decide(question, sit, buck)
        prob_vectors.append([probs[opt] for opt in question.options])

    prob_matrix = np.array(prob_vectors, dtype=np.float64)  # (n_archetypes, n_options)
    # Variance across archetypes for each option
    option_variances = np.var(prob_matrix, axis=0)
    mean_variance = float(np.mean(option_variances))

    return {
        "mean_variance": round(mean_variance, 5),
        "min_variance": round(float(np.min(option_variances)), 5),
        "max_variance": round(float(np.max(option_variances)), 5),
        "fallback_rate": round(policy.fallback_rate, 3)
    }


def run_behavior_ablation(
    policies: Dict[str, DecisionPolicy],
    question: DecisionQuestion,
    archetypes: Optional[List[Tuple[SituationBucket, AgentBucket]]] = None
) -> pd.DataFrame:
    """Run comparative ablation of RulePolicy vs LLM policy on identical situations."""
    archetypes = archetypes or generate_benchmark_archetypes()
    rows = []

    for name, pol in policies.items():
        var_stats = evaluate_policy_variance(pol, question, archetypes)
        rows.append({
            "policy": name,
            "mean_variance": var_stats["mean_variance"],
            "fallback_rate": var_stats["fallback_rate"],
            "total_queries": pol.total_queries
        })

    return pd.DataFrame(rows)
