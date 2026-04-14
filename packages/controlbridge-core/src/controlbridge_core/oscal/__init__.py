"""OSCAL (Open Security Controls Assessment Language) integration.

Exporters that convert ControlBridge models into NIST OSCAL JSON formats.
"""

from controlbridge_core.oscal.exporter import gap_report_to_oscal_ar

__all__ = ["gap_report_to_oscal_ar"]
