"""Tests for :class:`evidentia_core.audit.provenance.GenerationContext` (v0.7.1).

The AI sibling of :class:`CollectionContext`. These tests assert the
shape, defaults, and serialization invariants that the
``evidentia-ai`` risk-statement and explain generators rely on.
"""

from __future__ import annotations

import pytest
from evidentia_core import __version__ as evidentia_version
from evidentia_core.audit.provenance import (
    GenerationContext,
    compute_prompt_hash,
    new_run_id,
)

# -----------------------------------------------------------------------------
# compute_prompt_hash
# -----------------------------------------------------------------------------


def test_compute_prompt_hash_is_deterministic() -> None:
    a = compute_prompt_hash("system prompt", "user prompt")
    b = compute_prompt_hash("system prompt", "user prompt")
    assert a == b


def test_compute_prompt_hash_differs_when_system_changes() -> None:
    a = compute_prompt_hash("system A", "user prompt")
    b = compute_prompt_hash("system B", "user prompt")
    assert a != b


def test_compute_prompt_hash_differs_when_user_changes() -> None:
    a = compute_prompt_hash("system prompt", "user A")
    b = compute_prompt_hash("system prompt", "user B")
    assert a != b


def test_compute_prompt_hash_separator_prevents_collisions() -> None:
    """Concatenation without the fixed separator would let two distinct
    prompt pairs collide. The fixed ``\\n---\\n`` separator prevents that."""
    # Without separator, ("ab", "c") and ("a", "bc") would collide as "abc".
    # With separator, they hash to "ab\n---\nc" vs "a\n---\nbc" → distinct.
    h1 = compute_prompt_hash("ab", "c")
    h2 = compute_prompt_hash("a", "bc")
    assert h1 != h2


def test_compute_prompt_hash_is_lowercase_hex_64() -> None:
    h = compute_prompt_hash("system", "user")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


# -----------------------------------------------------------------------------
# GenerationContext — required + default fields
# -----------------------------------------------------------------------------


def _minimal(**overrides: object) -> GenerationContext:
    """Build a GenerationContext with the minimum required fields populated."""
    defaults: dict[str, object] = {
        "model": "claude-sonnet-4",
        "temperature": 0.2,
        "prompt_hash": compute_prompt_hash("sys", "user"),
    }
    defaults.update(overrides)
    return GenerationContext(**defaults)


def test_minimal_construction_sets_defaults() -> None:
    ctx = _minimal()
    assert ctx.model == "claude-sonnet-4"
    assert ctx.temperature == 0.2
    assert ctx.attempts == 1
    assert ctx.instructor_max_retries == 3
    assert ctx.evidentia_version == evidentia_version


def test_run_id_default_factory_generates_ulid() -> None:
    ctx = _minimal()
    assert len(ctx.run_id) == 26
    assert set(ctx.run_id).issubset(set("0123456789ABCDEFGHJKMNPQRSTVWXYZ"))


def test_run_id_can_be_overridden_for_batch_grouping() -> None:
    """A batch caller mints one run_id and threads it through every output."""
    shared = new_run_id()
    a = _minimal(run_id=shared)
    b = _minimal(run_id=shared)
    assert a.run_id == b.run_id == shared


def test_generated_at_default_is_utc() -> None:
    ctx = _minimal()
    assert ctx.generated_at.tzinfo is not None


# -----------------------------------------------------------------------------
# Validation
# -----------------------------------------------------------------------------


def test_temperature_below_zero_rejected() -> None:
    with pytest.raises(ValueError):
        _minimal(temperature=-0.1)


def test_temperature_above_two_rejected() -> None:
    with pytest.raises(ValueError):
        _minimal(temperature=2.1)


def test_attempts_below_one_rejected() -> None:
    with pytest.raises(ValueError):
        _minimal(attempts=0)


def test_instructor_max_retries_below_zero_rejected() -> None:
    with pytest.raises(ValueError):
        _minimal(instructor_max_retries=-1)


def test_prompt_hash_wrong_length_rejected() -> None:
    with pytest.raises(ValueError):
        _minimal(prompt_hash="too-short")


def test_extra_fields_rejected() -> None:
    """EvidentiaModel sets extra='forbid' — guard against silent typos."""
    with pytest.raises(ValueError):
        GenerationContext(  # type: ignore[call-arg]
            model="claude-sonnet-4",
            temperature=0.2,
            prompt_hash=compute_prompt_hash("s", "u"),
            bogus_field="should fail",
        )


def test_required_field_missing_raises() -> None:
    with pytest.raises(ValueError):
        GenerationContext(  # type: ignore[call-arg]
            temperature=0.2,
            prompt_hash=compute_prompt_hash("s", "u"),
        )


# -----------------------------------------------------------------------------
# Serialization
# -----------------------------------------------------------------------------


def test_serializes_roundtrip() -> None:
    ctx = _minimal(attempts=3, instructor_max_retries=5)
    dumped = ctx.model_dump(mode="json")
    restored = GenerationContext.model_validate(dumped)
    assert restored == ctx


def test_serialized_form_has_iso_timestamp() -> None:
    ctx = _minimal()
    dumped = ctx.model_dump(mode="json")
    # ISO 8601 with timezone — should end in '+00:00' or 'Z'
    assert "T" in dumped["generated_at"]
    assert dumped["generated_at"].endswith(("+00:00", "Z"))


def test_attempts_and_instructor_max_retries_are_independent() -> None:
    """The two retry-tracking fields capture different layers; assert they
    can hold distinct values without coupling."""
    ctx = _minimal(attempts=2, instructor_max_retries=5)
    assert ctx.attempts == 2
    assert ctx.instructor_max_retries == 5


# -----------------------------------------------------------------------------
# credential_identity (v0.7.1 post-review HIGH fix H3)
# -----------------------------------------------------------------------------


def test_credential_identity_defaults_to_none() -> None:
    """Optional field for backward compat; populated by callers."""
    ctx = _minimal()
    assert ctx.credential_identity is None


def test_credential_identity_round_trips() -> None:
    ctx = _minimal(credential_identity="alice@acme.com")
    dumped = ctx.model_dump(mode="json")
    assert dumped["credential_identity"] == "alice@acme.com"
    restored = GenerationContext.model_validate(dumped)
    assert restored.credential_identity == "alice@acme.com"
