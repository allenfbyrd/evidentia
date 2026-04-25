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


# -----------------------------------------------------------------------------
# v0.7.1 — AI generation events
# -----------------------------------------------------------------------------


def test_ai_generation_events_present() -> None:
    """All 9 AI_* entries from the v0.7.1 P0 design + post-review fixes
    land under the ``evidentia.ai.*`` namespace."""
    required = {
        "evidentia.ai.risk_generated",
        "evidentia.ai.risk_failed",
        "evidentia.ai.risk_retry",
        "evidentia.ai.risk_batch_completed",
        "evidentia.ai.explain_generated",
        "evidentia.ai.explain_failed",
        "evidentia.ai.explain_retry",
        "evidentia.ai.explain_cache_hit",
        "evidentia.ai.explain_batch_completed",
    }
    present = {a.value for a in EventAction}
    missing = required - present
    assert not missing, f"Required AI generation events missing: {missing}"


@pytest.mark.parametrize(
    "name,value",
    [
        ("AI_RISK_GENERATED", "evidentia.ai.risk_generated"),
        ("AI_RISK_FAILED", "evidentia.ai.risk_failed"),
        ("AI_RISK_RETRY", "evidentia.ai.risk_retry"),
        ("AI_RISK_BATCH_COMPLETED", "evidentia.ai.risk_batch_completed"),
        ("AI_EXPLAIN_GENERATED", "evidentia.ai.explain_generated"),
        ("AI_EXPLAIN_FAILED", "evidentia.ai.explain_failed"),
        ("AI_EXPLAIN_RETRY", "evidentia.ai.explain_retry"),
        ("AI_EXPLAIN_CACHE_HIT", "evidentia.ai.explain_cache_hit"),
        ("AI_EXPLAIN_BATCH_COMPLETED", "evidentia.ai.explain_batch_completed"),
    ],
)
def test_ai_event_member_to_value_mapping(name: str, value: str) -> None:
    """Pin both the Python member name and string value — downstream SIEM
    queries depend on the string, downstream callers depend on the member."""
    assert EventAction[name].value == value
