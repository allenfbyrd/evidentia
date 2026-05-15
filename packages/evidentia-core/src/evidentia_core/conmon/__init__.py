"""Continuous Monitoring (CONMON) cycle-calendar primitives (v0.9.0 P3).

Read-only library for surfacing assessment + reporting cycles per
the major federal-compliance frameworks. Operators consume this via:

- :func:`evidentia_core.conmon.calendar.next_due` — compute the next
  cycle's due date from a framework + last-completed-cycle anchor
- :func:`evidentia_core.conmon.calendar.list_cadences` — enumerate
  the bundled cadence rules
- :func:`evidentia_core.conmon.calendar.derive_status` — bucket a
  pending cycle into ``due_soon`` / ``overdue`` / ``current`` at
  query time against a reference date

The `evidentia conmon` CLI (v0.9.0 P2-adjacent; ships in the same
release cycle) wires these primitives into the operator workflow.
No daemon — operators poll. The CONMON live-trigger daemon
(``evidentia conmon watch``) is reserved for v1.0 per §31.1 OUT-of-
scope.

Bundled cadences (v0.9.0 P3 baseline; operator-extensible via
:func:`register_cadence`):

- ``nist-800-53-rev5-ca7``      — monthly (NIST 800-53 CA-7
  Continuous Monitoring)
- ``fedramp-conmon-poam``       — monthly POA&M updates
- ``fedramp-conmon-scans``      — monthly vulnerability scans
- ``fedramp-conmon-annual``     — annual SAR
- ``cmmc-l2-triennial``         — triennial reassessment
- ``dod-rmf-annual``            — annual control assessment
- ``occ-2026-13a-model-risk``   — annual model-risk review

Pure functions; no I/O; no persistence side-effects. Audit-trail
emit (``EventAction.CONMON_CYCLE_DUE`` /
``EventAction.CONMON_CYCLE_OVERDUE``) happens at the CLI
layer when queries identify due/overdue cycles — not in this
library, which only computes the dates.
"""

from __future__ import annotations

from evidentia_core.conmon.calendar import (
    BUNDLED_CADENCES,
    CONMON_FREQUENCIES,
    CadenceFrequency,
    ConmonCadence,
    CycleAttentionState,
    derive_status,
    get_cadence,
    list_cadences,
    next_due,
    register_cadence,
)

__all__ = [
    "BUNDLED_CADENCES",
    "CONMON_FREQUENCIES",
    "CadenceFrequency",
    "ConmonCadence",
    "CycleAttentionState",
    "derive_status",
    "get_cadence",
    "list_cadences",
    "next_due",
    "register_cadence",
]
