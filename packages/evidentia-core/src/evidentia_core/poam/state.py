"""POA&M lifecycle state transition rules (v0.9.0 P1).

The :class:`evidentia_core.models.gap.POAMState` enum carries five
states; this module enumerates the valid forward transitions + a
predicate :func:`is_valid_transition` that callers (CLI ``update``
verb, REST PATCH handler, OSCAL emit pre-flight) consult before
mutating a milestone's status.

Audit-trail integrity is the design constraint. An auditor reading
the POA&M lifecycle expects monotonic forward progress: a milestone
that was ``COMPLETED`` cannot revert to ``IN_PROGRESS`` via an edit
to the same record — the operator must create a NEW milestone with
a fresh ``target_date`` to capture the re-opened scope. This module
enforces that rule programmatically; the CLI + REST surfaces invoke
:func:`is_valid_transition` and refuse to persist an invalid edit.

The ``OVERDUE`` state has special handling. It is BOTH:

  1. An operator-set state (the CLI's ``milestone update --status overdue``
     verb), captured in the persisted ``Milestone.status`` field; AND
  2. A derived attention signal (computed at query time by
     :func:`derive_overdue` against a reference date), surfaced by
     the OSCAL POA&M emitter + report renderer regardless of the
     persisted status, so an operator who forgot to update a stale
     milestone still sees the auditor-visible flag.

The transition table treats ``OVERDUE`` as a transient state — the
operator can return to ``IN_PROGRESS`` (catching up) or jump straight
to ``COMPLETED`` (finishing the work). The ``OVERDUE`` → ``PLANNED``
transition is forbidden (auditors interpret a planned-after-overdue
record as evidence of timeline mismanagement; the right move is a
NEW milestone with a fresh planned date).
"""

from __future__ import annotations

from datetime import date
from typing import Final

from evidentia_core.models.gap import POAMState

# Forward-only transition table. Maps each state to the set of states
# it can legally transition to. Backward transitions (e.g.,
# COMPLETED -> IN_PROGRESS) are explicitly absent. Self-transitions
# (state == state) are also excluded — re-saving a milestone with
# the same state isn't a "transition" in the audit-trail sense.
_VALID_TRANSITIONS: Final[dict[POAMState, frozenset[POAMState]]] = {
    POAMState.PLANNED: frozenset(
        {
            POAMState.IN_PROGRESS,
            POAMState.OVERDUE,
            POAMState.COMPLETED,
        }
    ),
    POAMState.IN_PROGRESS: frozenset(
        {
            POAMState.OVERDUE,
            POAMState.COMPLETED,
        }
    ),
    POAMState.OVERDUE: frozenset(
        {
            POAMState.IN_PROGRESS,
            POAMState.COMPLETED,
        }
    ),
    POAMState.COMPLETED: frozenset(
        {
            POAMState.VERIFIED,
        }
    ),
    POAMState.VERIFIED: frozenset(),  # Terminal — no further transitions.
}

# Convenience alias: the set of states that have no successor.
TERMINAL_STATES: Final[frozenset[POAMState]] = frozenset({POAMState.VERIFIED})


def valid_next_states(current: POAMState) -> frozenset[POAMState]:
    """Return the set of legal successor states from ``current``.

    Empty frozenset for terminal states (``VERIFIED``). Callers can
    use this for UI hints (e.g., the CLI's ``milestone update --help``
    autocompletion) without re-walking the transition table.
    """
    return _VALID_TRANSITIONS.get(current, frozenset())


def is_valid_transition(current: POAMState, proposed: POAMState) -> bool:
    """Return True if ``current → proposed`` is a legal transition.

    Used by the CLI ``poam milestone update`` verb + the REST PATCH
    handler before persisting a status change. Self-transitions
    (``current == proposed``) return False — re-saving the same
    state isn't a transition; the caller should detect that case
    and skip the audit-event emit. ``current is None`` (i.e.,
    creating a new milestone, not transitioning) returns True for
    any proposed state — the validity check applies only to edits
    of existing records.
    """
    return proposed in _VALID_TRANSITIONS.get(current, frozenset())


def derive_overdue(target_date: date, status: POAMState, today: date) -> bool:
    """Return True if a milestone is overdue relative to ``today``.

    A milestone is *derived overdue* when:

      1. Its ``status`` is ``PLANNED`` or ``IN_PROGRESS`` (work is
         not yet complete); AND
      2. Its ``target_date`` is strictly in the past (``target_date <
         today``).

    Operators can also explicitly set ``status = OVERDUE`` via the
    CLI; this predicate is independent of that — it answers "is
    this milestone late by the calendar's reckoning?" regardless of
    operator state. The OSCAL POA&M emitter (v0.9.0 P2) ORs the
    persisted-status-OVERDUE flag with this derived flag at emit
    time, so an auditor sees the union of both attention signals.

    A ``COMPLETED`` or ``VERIFIED`` milestone is never overdue, even
    if its ``target_date`` is in the past — the work is done. A
    milestone with ``status = OVERDUE`` is trivially overdue
    (returns True regardless of the date check).
    """
    if status == POAMState.OVERDUE:
        return True
    if status in {POAMState.COMPLETED, POAMState.VERIFIED}:
        return False
    return target_date < today


__all__ = [
    "TERMINAL_STATES",
    "derive_overdue",
    "is_valid_transition",
    "valid_next_states",
]
