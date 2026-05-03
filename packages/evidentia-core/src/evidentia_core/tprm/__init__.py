"""Third-Party Risk Management capability surface (v0.7.9).

Lives at `evidentia_core.tprm` rather than as a separate workspace
package per the plan §P0 design choice — sub-namespace mirrors the
existing `gap_analyzer` / `audit` / `oscal` pattern. Sub-modules:

- `concentration` — v0.7.9 P0.3 concentration-risk reporting

Subsequent v0.7.9 sub-slices (P0.2 questionnaire generator, P0.4
vendor-risk collectors, P0.5 OSCAL TPRM emit) will land additional
modules under this namespace.
"""

from evidentia_core.tprm.concentration import (
    SUPPORTED_DIMENSIONS,
    ConcentrationReport,
    DimensionAnalysis,
    ValueCount,
    compute_concentration,
    render_csv_report,
    render_html_report,
)

__all__ = [
    "SUPPORTED_DIMENSIONS",
    "ConcentrationReport",
    "DimensionAnalysis",
    "ValueCount",
    "compute_concentration",
    "render_csv_report",
    "render_html_report",
]
