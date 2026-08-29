"""Post-processing and analysis."""

from .consistency import compute_field_consistency_diagnostics
from .faraday import b1_plus, magnetic_flux_density_from_e
from .evaluation import evaluate_vector_field_parallel
from .current_divergence import current_divergence_residual
from .power_balance import poynting_power_balance
from .sar import mean_sar, uniform_sphere_sar_closed_form
from .phantom_fields import (
    compute_phantom_eb_metrics_and_export,
    compute_tagged_vector_magnitude_stats,
    export_tagged_field_samples_csv,
)
from .quicklook import (
    build_phantom_quicklook_report,
    format_phantom_quicklook_report,
    write_phantom_quicklook_report,
)

__all__ = [
    "compute_field_consistency_diagnostics",
    "magnetic_flux_density_from_e",
    "b1_plus",
    "evaluate_vector_field_parallel",
    "poynting_power_balance",
    "mean_sar",
    "uniform_sphere_sar_closed_form",
    "current_divergence_residual",
    "compute_tagged_vector_magnitude_stats",
    "export_tagged_field_samples_csv",
    "compute_phantom_eb_metrics_and_export",
    "build_phantom_quicklook_report",
    "format_phantom_quicklook_report",
    "write_phantom_quicklook_report",
]
