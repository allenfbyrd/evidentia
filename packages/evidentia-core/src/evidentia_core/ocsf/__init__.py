"""OCSF (Open Cybersecurity Schema Framework) interoperability.

v0.10.0. Converts Evidentia findings to and from OCSF Compliance
Finding objects. See :mod:`evidentia_core.ocsf.finding_mapping`.

Importing this package does NOT require the optional ``ocsf`` extra —
``py-ocsf-models`` is imported lazily, only when a mapping function is
actually called.
"""

from evidentia_core.ocsf.finding_mapping import (
    OCSFMappingError,
    finding_from_ocsf,
    finding_to_ocsf,
)

__all__ = ["OCSFMappingError", "finding_from_ocsf", "finding_to_ocsf"]
