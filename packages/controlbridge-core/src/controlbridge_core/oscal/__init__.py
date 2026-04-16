"""OSCAL (Open Security Controls Assessment Language) integration.

Exporters that convert ControlBridge models into NIST OSCAL JSON formats,
plus a profile resolver for turning OSCAL profile + catalog pairs into
resolved baselines.
"""

from controlbridge_core.oscal.exporter import gap_report_to_oscal_ar
from controlbridge_core.oscal.profile import (
    ProfileResolutionError,
    catalog_to_oscal_json,
    resolve_profile,
)

__all__ = [
    "ProfileResolutionError",
    "catalog_to_oscal_json",
    "gap_report_to_oscal_ar",
    "resolve_profile",
]
