"""Behavioral modeling and decision policy package for EpiSwarm."""

from episwarm.behavior.hierarchical import (
    HierarchicalCoefficients,
    compute_individual_probabilities,
    evaluate_agent_diversity
)
from episwarm.behavior.teacher_student import (
    CoMixEmpiricalTeacher,
    VectorizedStudentEvaluator,
    OutOfRangeDetector,
    DataConstrainedTier,
    OutOfRangeWarning,
    TeacherArchetypePrior
)

__all__ = [
    "HierarchicalCoefficients",
    "compute_individual_probabilities",
    "evaluate_agent_diversity",
    "CoMixEmpiricalTeacher",
    "VectorizedStudentEvaluator",
    "OutOfRangeDetector",
    "DataConstrainedTier",
    "OutOfRangeWarning",
    "TeacherArchetypePrior"
]
