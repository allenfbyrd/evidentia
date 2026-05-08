"""Plan-of-Action-and-Milestones (POA&M) capability surface (v0.9.0 P1).

Lives at ``evidentia_core.poam`` — sub-namespace under ``evidentia_core``
mirroring the v0.7.9 ``tprm/`` precedent. Sub-modules:

- :mod:`evidentia_core.poam.state` — :class:`POAMState` lifecycle
  transition rules + ``derive_overdue`` predicate
- :mod:`evidentia_core.poam.milestone` — cycle-diff helpers (sort,
  group-by-status, time-window slicing) for milestone collections

The Pydantic models themselves (:class:`POAMState`,
:class:`Milestone`) live in :mod:`evidentia_core.models.gap` to keep
all gap-related models co-located. This module ships the *behaviour*
(transition validation, derived state, cycle helpers) layered on top
of those models.

Subsequent v0.9.0 sub-slices will land additional surfaces under this
namespace:

- v0.9.0 P2: OSCAL POA&M exporter at
  :mod:`evidentia_core.oscal.poam_exporter` (gap_report → OSCAL POA&M
  1.1.2 emit)
- v0.9.0 P2: ``evidentia poam`` Typer subcommand at
  :mod:`evidentia.cli.poam` (CLI verbs: create / list / show / update
  / milestone add\\|update / export / calendar)
- v0.9.0 P2: ``/api/poam/`` REST router at
  :mod:`evidentia_api.routers.poam` (CRUD + pagination + filter)
- v0.9.0 P3: CONMON cycle-calendar primitives at
  :mod:`evidentia_core.conmon` (read-only library; daemon defers to v1.0)

The persistent JSON file-store lives at the package root
(:mod:`evidentia_core.poam_store`) mirroring the v0.7.9 P0.1.2
``vendor_store`` pattern — atomic-write + UUID-shape-validation +
``platformdirs``-backed default location + ``EVIDENTIA_POAM_STORE_DIR``
env-var override.
"""

from __future__ import annotations

from evidentia_core.poam.milestone import (
    derive_attention_state,
    group_milestones_by_state,
    sort_milestones_by_target_date,
    upcoming_milestones,
)
from evidentia_core.poam.state import (
    TERMINAL_STATES,
    derive_overdue,
    is_valid_transition,
    valid_next_states,
)

__all__ = [
    "TERMINAL_STATES",
    "derive_attention_state",
    "derive_overdue",
    "group_milestones_by_state",
    "is_valid_transition",
    "sort_milestones_by_target_date",
    "upcoming_milestones",
    "valid_next_states",
]
