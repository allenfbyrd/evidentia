"""Milestone collection helpers — sort, group, time-window slicing.

Used by the v0.9.0 P2 CLI ``poam list`` + ``poam show`` verbs +
the OSCAL POA&M exporter to render milestone lists in canonical
order. Pure functions — no I/O, no persistence side-effects — so
they're safe to invoke at any layer (CLI, REST, OSCAL emit, test
fixtures).

Cycle-diff intent:

The CONMON cycle calendar (v0.9.0 P3) reads "what's coming due in
the next 30 days?" + "what's overdue right now?" off this module's
:func:`upcoming_milestones` + :func:`derive_attention_state` helpers.
Until P3 lands, those questions are answered by the CLI's
``poam list --upcoming N`` flag.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta

from evidentia_core.models.gap import Milestone, POAMState
from evidentia_core.poam.state import derive_overdue


def sort_milestones_by_target_date(
    milestones: Iterable[Milestone],
    *,
    reverse: bool = False,
) -> list[Milestone]:
    """Return ``milestones`` sorted by ``target_date`` ascending.

    Stable sort — milestones with identical target dates retain
    their input order. ``reverse=True`` flips to descending (most
    distant date first); useful for a "long-term roadmap" view.
    """
    return sorted(milestones, key=lambda m: m.target_date, reverse=reverse)


def group_milestones_by_state(
    milestones: Iterable[Milestone],
) -> dict[POAMState, list[Milestone]]:
    """Bucket milestones into a {state: [milestone, ...]} mapping.

    Empty buckets for states with zero milestones are PRESENT in
    the returned dict (with empty list values) so callers can
    iterate ``POAMState`` and render every state row even when
    no milestones are in it. Within each bucket, milestones are
    sorted by ``target_date`` ascending — auditors expect the
    earliest deadline first.
    """
    grouped: dict[POAMState, list[Milestone]] = {state: [] for state in POAMState}
    for milestone in milestones:
        # ``Milestone.status`` round-trips through Pydantic as the
        # raw string (``use_enum_values=True`` on EvidentiaModel) so
        # we cast back through POAMState for the dict key.
        key = POAMState(milestone.status)
        grouped[key].append(milestone)
    for state in grouped:
        grouped[state] = sort_milestones_by_target_date(grouped[state])
    return grouped


def upcoming_milestones(
    milestones: Iterable[Milestone],
    *,
    today: date,
    window_days: int = 30,
) -> list[Milestone]:
    """Return milestones whose ``target_date`` is in [today, today+window_days].

    Excludes:
      - Already-completed milestones (``COMPLETED`` or ``VERIFIED``)
      - Already-overdue milestones (``target_date < today``)

    The window is inclusive on both ends — a milestone with
    ``target_date == today`` IS upcoming (it's due today). The
    output is sorted by ``target_date`` ascending — the operator
    sees the soonest deadline first.

    ``window_days = 0`` returns only milestones due today; negative
    values raise ValueError (the caller probably meant to use
    :func:`overdue_milestones` instead, but that function doesn't
    exist as a separate helper because :func:`derive_attention_state`
    + :func:`group_milestones_by_state` together cover the overdue
    surface).
    """
    if window_days < 0:
        raise ValueError(
            "window_days must be >= 0; for overdue queries use "
            "derive_attention_state() + filter on the 'overdue' bucket."
        )
    horizon = today + timedelta(days=window_days)
    upcoming: list[Milestone] = []
    for milestone in milestones:
        status = POAMState(milestone.status)
        if status in {POAMState.COMPLETED, POAMState.VERIFIED}:
            continue
        if milestone.target_date < today:
            continue
        if milestone.target_date > horizon:
            continue
        upcoming.append(milestone)
    return sort_milestones_by_target_date(upcoming)


def derive_attention_state(
    milestones: Iterable[Milestone],
    *,
    today: date,
) -> dict[str, list[Milestone]]:
    """Bucket milestones into auditor-visible attention buckets.

    Returns a dict with three keys (always present, possibly empty):

    - ``"overdue"`` — milestones with derived-overdue == True. The
      OSCAL POA&M emit + report-renderer surface these as a HIGH
      attention signal regardless of the persisted status field.
    - ``"due_soon"`` — milestones due within 7 days (inclusive)
      that are not yet overdue and not yet completed.
    - ``"closed"`` — milestones in the COMPLETED or VERIFIED state.

    Milestones not in any of those three buckets (PLANNED or
    IN_PROGRESS with target_date > today + 7 days) are not returned
    by this function — those are the "everything else, nothing to
    flag" cohort. Callers that need the full bucketing should use
    :func:`group_milestones_by_state` instead.
    """
    overdue: list[Milestone] = []
    due_soon: list[Milestone] = []
    closed: list[Milestone] = []
    soon_horizon = today + timedelta(days=7)
    for milestone in milestones:
        status = POAMState(milestone.status)
        if status in {POAMState.COMPLETED, POAMState.VERIFIED}:
            closed.append(milestone)
            continue
        if derive_overdue(milestone.target_date, status, today):
            overdue.append(milestone)
            continue
        if today <= milestone.target_date <= soon_horizon:
            due_soon.append(milestone)
    return {
        "overdue": sort_milestones_by_target_date(overdue),
        "due_soon": sort_milestones_by_target_date(due_soon),
        "closed": sort_milestones_by_target_date(closed),
    }


__all__ = [
    "derive_attention_state",
    "group_milestones_by_state",
    "sort_milestones_by_target_date",
    "upcoming_milestones",
]
