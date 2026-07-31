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
from .resonance import (
    DEFAULT_SLOPE_THRESHOLD,
    ResonanceGuardReport,
    check_energy_continuity,
    stored_electric_energy,
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
    "DEFAULT_SLOPE_THRESHOLD",
    "ResonanceGuardReport",
    "check_energy_continuity",
    "stored_electric_energy",
    "HomogeneousMaterial",
    "TimeHarmonicBoundaryCondition",
    "TimeHarmonicFields",
    "TimeHarmonicProblem",
    "TimeHarmonicSolver",
    "build_material_fields",
    "normalize_boundary_condition",
]
