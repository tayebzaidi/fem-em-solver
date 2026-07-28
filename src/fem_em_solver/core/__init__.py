"""Core FEM formulations and solvers."""

from .solvers import (
    DEFAULT_GAUGE_PENALTY,
    GaugeContaminationWarning,
    GaugeMethod,
    LinearSolveDiagnostics,
    MagnetostaticProblem,
    MagnetostaticSolver,
    classify_residual_trend,
)
from .time_harmonic import (
    HomogeneousMaterial,
    TimeHarmonicBoundaryCondition,
    TimeHarmonicFields,
    TimeHarmonicProblem,
    TimeHarmonicSolver,
    build_material_fields,
    normalize_boundary_condition,
)

__all__ = [
    "DEFAULT_GAUGE_PENALTY",
    "GaugeContaminationWarning",
    "GaugeMethod",
    "LinearSolveDiagnostics",
    "MagnetostaticProblem",
    "MagnetostaticSolver",
    "classify_residual_trend",
    "HomogeneousMaterial",
    "TimeHarmonicBoundaryCondition",
    "TimeHarmonicFields",
    "TimeHarmonicProblem",
    "TimeHarmonicSolver",
    "build_material_fields",
    "normalize_boundary_condition",
]
