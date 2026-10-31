"""Exhaustive ground truth policy search and optimizer arm benchmarking (Libin et al. 2020, Spec 12.2).

Enumerates all 2^W binary intervention schedules on the deterministic metapopulation
engine to discover true mathematical global optima, against which heuristic advisors
and Optuna NSGA-II/discrete optimizers are rigorously benchmarked.
"""

from typing import Dict, List, Tuple, Optional, Any
import itertools
import numpy as np
import optuna

from episwarm.engine.meta import MetapopulationEngine, MetaSimResult
from episwarm.packs.scenario import InterventionAction


def _policy_bits_to_interventions(
    bits: Tuple[int, ...],
    measure_type: str = "school_closure",
    stringency: float = 0.8
) -> List[InterventionAction]:
    """Convert weekly binary bits into InterventionAction list."""
    actions: List[InterventionAction] = []
    # Merge consecutive 1s into single continuous action blocks
    current_start = None
    for w, b in enumerate(bits):
        if b == 1 and current_start is None:
            current_start = w * 7
        elif b == 0 and current_start is not None:
            actions.append(InterventionAction(
                name=f"{measure_type}_w{current_start//7}",
                measure_type=measure_type,
                area_id="ALL",
                start_day=current_start,
                end_day=w * 7 - 1,
                stringency=stringency,
                cost_per_day=1.0
            ))
            current_start = None
    if current_start is not None:
        actions.append(InterventionAction(
            name=f"{measure_type}_w{current_start//7}",
            measure_type=measure_type,
            area_id="ALL",
            start_day=current_start,
            end_day=len(bits) * 7 - 1,
            stringency=stringency,
            cost_per_day=1.0
        ))
    return actions


def evaluate_policy_score(
    eng: MetapopulationEngine,
    bits: Tuple[int, ...],
    horizon_days: int = 42,
    attack_rate_weight: float = 1000.0,
    cost_per_closure_week: float = 35.0,
    measure_type: str = "school_closure",
    stringency: float = 0.8
) -> Tuple[float, float, int]:
    """Evaluate objective score = (weight * attack_rate) + (cost * weeks_closed) deterministically."""
    # Enforce deterministic evaluation
    actions = _policy_bits_to_interventions(bits, measure_type=measure_type, stringency=stringency)
    # Clone engine with stochastic=False for ground truth determinism
    det_eng = MetapopulationEngine(
        area_populations=dict(zip(eng.area_ids, eng.N_area.astype(int))),
        contact_matrix=eng.contact_matrix,
        beta=eng.beta,
        latent_period_days=1.0 / eng.zeta,
        infectious_period_days=1.0 / eng.gamma,
        mobility_matrix=eng.Mob,
        area_ids=eng.area_ids,
        mu=eng.mu,
        adult_age_idx=eng.adult_age_idx,
        stochastic=False,
        seed=42
    )
    res = det_eng.run(horizon_days=horizon_days, n_initial_seeds=10, interventions=actions)
    weeks_closed = sum(bits)
    score = float(attack_rate_weight * res.attack_rate + cost_per_closure_week * weeks_closed)
    return score, float(res.attack_rate), weeks_closed


def exhaustive_binary_policy_search(
    eng: MetapopulationEngine,
    n_weeks: int = 6,
    attack_rate_weight: float = 1000.0,
    cost_per_closure_week: float = 35.0,
    measure_type: str = "school_closure",
    stringency: float = 0.8
) -> Dict[str, Any]:
    """Exhaustively enumerate all 2^W policies (Spec 12.2)."""
    horizon_days = n_weeks * 7
    all_bits = list(itertools.product([0, 1], repeat=n_weeks))
    evaluations: List[Dict[str, Any]] = []

    for bits in all_bits:
        score, attack_rate, weeks_closed = evaluate_policy_score(
            eng,
            bits,
            horizon_days=horizon_days,
            attack_rate_weight=attack_rate_weight,
            cost_per_closure_week=cost_per_closure_week,
            measure_type=measure_type,
            stringency=stringency
        )
        evaluations.append({
            "bitstring": "".join(map(str, bits)),
            "bits": bits,
            "score": round(score, 3),
            "attack_rate": round(attack_rate, 4),
            "weeks_closed": weeks_closed
        })

    # Sort ascending by score (lower score is better)
    evaluations.sort(key=lambda x: x["score"])
    best = evaluations[0]
    worst = evaluations[-1]

    all_scores = [e["score"] for e in evaluations]

    return {
        "n_evaluated": len(evaluations),
        "n_weeks": n_weeks,
        "best_policy": best,
        "worst_policy": worst,
        "all_scores": all_scores,
        "all_evaluations": evaluations
    }


def compare_optimizer_against_ground_truth(
    eng: MetapopulationEngine,
    n_weeks: int = 6,
    n_optuna_trials: int = 15,
    attack_rate_weight: float = 1000.0,
    cost_per_closure_week: float = 35.0,
    seed: int = 42
) -> Dict[str, Any]:
    """Benchmark Heuristic Rule vs Optuna NSGA-II/TPE against Exhaustive Ground Truth."""
    # 1. Exhaustive Ground Truth
    gt_res = exhaustive_binary_policy_search(
        eng,
        n_weeks=n_weeks,
        attack_rate_weight=attack_rate_weight,
        cost_per_closure_week=cost_per_closure_week
    )
    best_gt = gt_res["best_policy"]
    best_gt_score = best_gt["score"]
    all_scores = np.array(gt_res["all_scores"])

    horizon_days = n_weeks * 7

    # 2. Arm 1: Heuristic Policy (Reactive: close in middle weeks when wave crests, e.g. weeks 2 & 3)
    # A standard public health rule: trigger closure upon surge for 2 weeks
    heuristic_bits = [0] * n_weeks
    if n_weeks >= 4:
        heuristic_bits[1] = 1
        heuristic_bits[2] = 1
    elif n_weeks >= 2:
        heuristic_bits[1] = 1
    heur_tuple = tuple(heuristic_bits)

    heur_score, heur_ar, heur_wc = evaluate_policy_score(
        eng,
        heur_tuple,
        horizon_days=horizon_days,
        attack_rate_weight=attack_rate_weight,
        cost_per_closure_week=cost_per_closure_week
    )
    heur_rank = int(np.sum(all_scores < heur_score)) + 1
    heur_percentile = round(float(heur_rank / len(all_scores)) * 100.0, 1)

    # 3. Arm 2: Optuna Optimization over binary choices
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    def optuna_obj(trial: optuna.Trial) -> float:
        bits = tuple(trial.suggest_categorical(f"w_{i}", [0, 1]) for i in range(n_weeks))
        score, _, _ = evaluate_policy_score(
            eng,
            bits,
            horizon_days=horizon_days,
            attack_rate_weight=attack_rate_weight,
            cost_per_closure_week=cost_per_closure_week
        )
        return score

    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=seed))
    study.optimize(optuna_obj, n_trials=min(n_optuna_trials, len(all_scores)))

    best_optuna_bits = tuple(study.best_params[f"w_{i}"] for i in range(n_weeks))
    optuna_score, optuna_ar, optuna_wc = evaluate_policy_score(
        eng,
        best_optuna_bits,
        horizon_days=horizon_days,
        attack_rate_weight=attack_rate_weight,
        cost_per_closure_week=cost_per_closure_week
    )
    optuna_rank = int(np.sum(all_scores < optuna_score)) + 1
    optuna_percentile = round(float(optuna_rank / len(all_scores)) * 100.0, 1)

    return {
        "ground_truth_best": {
            "bitstring": best_gt["bitstring"],
            "score": best_gt_score,
            "attack_rate": best_gt["attack_rate"],
            "weeks_closed": best_gt["weeks_closed"],
            "rank": 1,
            "percentile": round(100.0 / len(all_scores), 1)
        },
        "heuristic_arm": {
            "bitstring": "".join(map(str, heur_tuple)),
            "score": round(heur_score, 3),
            "gap_to_optimum": round(heur_score - best_gt_score, 3),
            "attack_rate": round(heur_ar, 4),
            "weeks_closed": heur_wc,
            "rank": heur_rank,
            "percentile": heur_percentile
        },
        "optuna_arm": {
            "bitstring": "".join(map(str, best_optuna_bits)),
            "score": round(optuna_score, 3),
            "gap_to_optimum": round(optuna_score - best_gt_score, 3),
            "attack_rate": round(optuna_ar, 4),
            "weeks_closed": optuna_wc,
            "rank": optuna_rank,
            "percentile": optuna_percentile,
            "trials_used": min(n_optuna_trials, len(all_scores))
        },
        "total_exhaustive_search_space": len(all_scores)
    }
