"""Tests for :mod:`evidentia_core.audit.events` (v0.7.0)."""

from __future__ import annotations

import re

import pytest
from evidentia_core.audit.events import (
    EventAction,
    EventCategory,
    EventOutcome,
    EventType,
)

_ACTION_PATTERN = re.compile(r"^evidentia\.[a-z_]+\.[a-z_]+$")


@pytest.mark.parametrize("action", list(EventAction))
def test_every_action_matches_namespace_pattern(action: EventAction) -> None:
    """Every action value follows ``evidentia.<namespace>.<verb>`` exactly."""
    assert _ACTION_PATTERN.match(action.value), (
        f"{action.name}={action.value!r} breaks the "
        f"'evidentia.<namespace>.<verb>' convention"
    )


def test_action_values_unique() -> None:
    values = [a.value for a in EventAction]
    assert len(values) == len(set(values))


def test_collect_lifecycle_members_present() -> None:
    """Assert the minimum collect.* lifecycle is intact."""
    required = {
        "evidentia.collect.started",
        "evidentia.collect.finding_retrieved",
        "evidentia.collect.completed",
        "evidentia.collect.failed",
        "evidentia.collect.retry",
    }
    present = {a.value for a in EventAction}
    missing = required - present
    assert not missing, f"Required collect.* actions removed: {missing}"


def test_sign_and_verify_pair_symmetry() -> None:
    present = {a.value for a in EventAction}
    assert "evidentia.sign.gpg_signed" in present
    assert "evidentia.verify.signature_passed" in present
    assert "evidentia.sign.sigstore_signed" in present
    assert "evidentia.sign.sigstore_skipped_airgap" in present


def test_event_outcome_matches_ecs_spec() -> None:
    expected = {"success", "failure", "unknown"}
    actual = {o.value for o in EventOutcome}
    assert actual == expected


def test_event_category_values_are_lowercase() -> None:
    for cat in EventCategory:
        assert cat.value.islower()
        assert " " not in cat.value


def test_event_type_covers_minimum_set() -> None:
    present = {t.value for t in EventType}
    assert {"info", "start", "end", "error", "change"}.issubset(present)


def test_event_action_is_string_subclass() -> None:
    """EventAction must be a StrEnum-equivalent for ECS JSON serialization."""
    assert isinstance(EventAction.COLLECT_STARTED, str)
    assert EventAction.COLLECT_STARTED == "evidentia.collect.started"
