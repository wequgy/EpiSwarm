"""Unit and integration tests for Behavior System v3 (Stage A4)."""

import numpy as np
import pytest
from episwarm.population.build import build_synthetic_population
from episwarm.behavior.teacher_student import (
    CoMixEmpiricalTeacher,
    VectorizedStudentEvaluator,
    OutOfRangeDetector,
    DataConstrainedTier,
    POLYMOD_BASELINE_CONTACTS
)


@pytest.fixture(scope="module")
def sample_population():
    return build_synthetic_population("regions/example_synthetic", scale_agents=3000, random_seed=42)


def test_comix_empirical_teacher():
    teacher = CoMixEmpiricalTeacher()
    # Test age monotonicity: higher age -> higher vulnerability -> higher compliance prior
    p_young, _ = teacher.get_macro_prior("limit_social_contacts", age=20, policy_stringency=0.85)
    p_old, _ = teacher.get_macro_prior("limit_social_contacts", age=75, policy_stringency=0.85)
    assert p_old > p_young, f"Expected p_old ({p_old}) > p_young ({p_young})"

    # Test stringency monotonicity
    p_low, _ = teacher.get_macro_prior("limit_social_contacts", age=45, policy_stringency=0.35)
    p_high, _ = teacher.get_macro_prior("limit_social_contacts", age=45, policy_stringency=0.85)
    assert p_high > p_low, f"Expected p_high ({p_high}) > p_low ({p_low})"


def test_vectorized_student_evaluator(sample_population):
    pop = sample_population
    student = VectorizedStudentEvaluator()

    base_priors = np.full(pop.n_agents, 0.70, dtype=np.float32)
    peer_norm = np.clip(pop.compliance, 0.0, 1.0)
    fatigue = np.full(pop.n_agents, 0.20, dtype=np.float32)

    probs = student.evaluate_vectorized(
        pop=pop,
        base_priors=base_priors,
        question_id="limit_social_contacts",
        peer_social_norm=peer_norm,
        fatigue_array=fatigue
    )

    # Output guarantees
    assert len(probs) == pop.n_agents
    assert np.all(probs >= 0.01) and np.all(probs <= 0.99)
    assert np.var(probs) > 0.001, "Probabilities must exhibit heterogeneous individual variance"
    # Ensure high number of distinct values (no block-quantization)
    n_unique = len(np.unique(np.round(probs, 4)))
    assert n_unique > 500, f"Expected rich individual diversity, got {n_unique} unique values"


def test_out_of_range_detector():
    detector = OutOfRangeDetector()
    # In-range nominal parameters
    w_normal = detector.check_conditions(
        policy_stringency=0.75,
        fatigue_level=0.30,
        mean_compliance_prior=0.70,
        agent_ages=np.array([25, 40, 55, 70])
    )
    assert len(w_normal) == 0, f"Expected 0 warnings for nominal setup, got {len(w_normal)}"

    # Out-of-range excessive stringency and zero fatigue
    w_extreme = detector.check_conditions(
        policy_stringency=0.98,
        fatigue_level=0.005,
        mean_compliance_prior=0.95
    )
    conds = [w.condition for w in w_extreme]
    assert "POLICY_STRINGENCY_OUT_OF_BOUNDS" in conds
    assert "UNREALISTIC_FATIGUE_ASSUMPTION" in conds


def test_data_constrained_tier():
    constrained = DataConstrainedTier(uncertainty_multiplier=2.5)
    base_p = np.array([0.40, 0.60, 0.80], dtype=np.float32)
    _, lower, upper = constrained.apply_uncertainty_inflation(base_p, std_error=0.05)

    # 1.96 * 0.05 * 2.5 = 0.245
    expected_delta = 1.96 * 0.05 * 2.5
    assert np.all(lower < base_p)
    assert np.all(upper > base_p)
    assert pytest.approx(upper[1] - base_p[1], abs=1e-3) == expected_delta
