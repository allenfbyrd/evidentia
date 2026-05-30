"""Unit tests for evidentia_core.poam.milestone.resolve_milestone_id.

The CLI (`evidentia poam milestone add` / `poam show` / `poam
calendar`) DISPLAYS an 8-char milestone-ID prefix, e.g. ``(3f70eae3)``.
Operators copy that prefix and pass it back to ``poam milestone
update``. The resolver lets a UNIQUE prefix resolve to the full
milestone UUID so the round-trip works.

Resolution contract:
  - Exact full-UUID match wins (unchanged behaviour).
  - A prefix matching EXACTLY ONE milestone resolves to that UUID.
  - A prefix matching MULTIPLE milestones raises
    :class:`AmbiguousMilestoneIdError`.
  - A prefix matching NONE raises :class:`MilestoneNotFoundError`.
"""

from __future__ import annotations

from datetime import date

import pytest
from evidentia_core.models.gap import (
    ControlGap,
    GapSeverity,
    ImplementationEffort,
    Milestone,
    POAMState,
)
from evidentia_core.poam.milestone import (
    AmbiguousMilestoneIdError,
    MilestoneNotFoundError,
    resolve_milestone_id,
)


def _gap_with_milestones(*milestones: Milestone) -> ControlGap:
    gap = ControlGap(
        framework="nist-800-53-rev5",
        control_id="AC-2",
        control_title="Account Management",
        control_description="Manage system accounts.",
        gap_severity=GapSeverity.HIGH,
        implementation_status="missing",
        gap_description="No automated lifecycle process.",
        remediation_guidance="Implement Okta lifecycle.",
        implementation_effort=ImplementationEffort.MEDIUM,
    )
    gap.poam_milestones.extend(milestones)
    return gap


def _ms(uuid: str, description: str = "phase") -> Milestone:
    return Milestone(
        id=uuid,
        target_date=date(2026, 6, 30),
        description=description,
        status=POAMState.PLANNED,
    )


class TestResolveMilestoneId:
    def test_full_uuid_resolves_unchanged(self) -> None:
        full = "3f70eae3-0000-4000-8000-000000000001"
        gap = _gap_with_milestones(_ms(full))
        assert resolve_milestone_id(gap, full) == full

    def test_eight_char_prefix_resolves_to_full_uuid(self) -> None:
        full = "3f70eae3-0000-4000-8000-000000000001"
        gap = _gap_with_milestones(_ms(full))
        # The 8-char prefix the CLI displays in `(3f70eae3)`.
        assert resolve_milestone_id(gap, "3f70eae3") == full

    def test_prefix_resolves_to_the_right_milestone(self) -> None:
        a = "3f70eae3-0000-4000-8000-000000000001"
        b = "a1b2c3d4-0000-4000-8000-000000000002"
        gap = _gap_with_milestones(_ms(a, "first"), _ms(b, "second"))
        assert resolve_milestone_id(gap, "a1b2c3d4") == b
        assert resolve_milestone_id(gap, "3f70eae3") == a

    def test_ambiguous_prefix_raises(self) -> None:
        a = "3f70eae3-0000-4000-8000-000000000001"
        b = "3f70eae3-1111-4000-8000-000000000002"
        gap = _gap_with_milestones(_ms(a), _ms(b))
        with pytest.raises(
            AmbiguousMilestoneIdError,
            match=r"ambiguous milestone id '3f70eae3' matches 2 milestones",
        ):
            resolve_milestone_id(gap, "3f70eae3")

    def test_unknown_prefix_raises_not_found(self) -> None:
        full = "3f70eae3-0000-4000-8000-000000000001"
        gap = _gap_with_milestones(_ms(full))
        with pytest.raises(MilestoneNotFoundError, match="deadbeef"):
            resolve_milestone_id(gap, "deadbeef")

    def test_no_milestones_raises_not_found(self) -> None:
        gap = _gap_with_milestones()
        with pytest.raises(MilestoneNotFoundError):
            resolve_milestone_id(gap, "3f70eae3")

    def test_exact_full_uuid_wins_over_prefix_ambiguity(self) -> None:
        # A full UUID that is also a strict prefix of another
        # milestone's UUID must resolve to the exact match, not raise
        # ambiguity. (Defensive: UUIDs are fixed-length so this can't
        # actually happen, but the exact-match-first ordering is the
        # contract.)
        a = "3f70eae3-0000-4000-8000-000000000001"
        b = "3f70eae3-0000-4000-8000-000000000002"
        gap = _gap_with_milestones(_ms(a), _ms(b))
        assert resolve_milestone_id(gap, a) == a

    def test_errors_are_value_error_subclasses(self) -> None:
        # Mirrors the InvalidPoamIdError(ValueError) idiom so existing
        # `except ValueError` handlers keep working.
        assert issubclass(AmbiguousMilestoneIdError, ValueError)
        assert issubclass(MilestoneNotFoundError, ValueError)
