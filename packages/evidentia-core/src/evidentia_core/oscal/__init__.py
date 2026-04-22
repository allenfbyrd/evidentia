"""OSCAL (Open Security Controls Assessment Language) integration.

Exporters that convert Evidentia models into NIST OSCAL JSON formats,
plus a profile resolver for turning OSCAL profile + catalog pairs into
resolved baselines.
"""

from evidentia_core.oscal.exporter import gap_report_to_oscal_ar
from evidentia_core.oscal.profile import (
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
