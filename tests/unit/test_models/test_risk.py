"""Model-level tests for :class:`evidentia_core.models.risk.RiskStatement`.

These tests cover the v0.7.1 ``generation_context`` field at the model
layer (independent of the AI generator path covered in
``tests/unit/test_ai/test_risk_statements.py``). They guard backward
compatibility (v0.7.0 JSON deserializes cleanly) and the round-trip
shape of the new field.
"""

from __future__ import annotations

import pytest
from evidentia_core.audit.provenance import (
    GenerationContext,
    compute_prompt_hash,
    new_run_id,
)
from evidentia_core.models.risk import (
    ImpactRating,
    LikelihoodRating,
    RiskLevel,
    RiskStatement,
    RiskTreatment,
)


def _minimal_kwargs() -> dict[str, object]:
    """Smallest set of fields needed to construct a RiskStatement."""
    return {
        "asset": "Customer Portal",
        "threat_source": "External attacker",
        "threat_event": "Credential stuffing",
        "vulnerability": "No automated deactivation",
        "likelihood": LikelihoodRating.HIGH,
        "likelihood_rationale": "Dormant accounts known attack vector",
        "impact": ImpactRating.HIGH,
        "impact_rationale": "PII exposure carries penalties",
        "risk_level": RiskLevel.HIGH,
        "risk_description": "Attackers could compromise dormant accounts",
        "recommended_controls": ["AC-2(3)"],
        "remediation_priority": 2,
        "treatment": RiskTreatment.MITIGATE,
    }


def _sample_generation_context() -> GenerationContext:
    return GenerationContext(
        model="claude-sonnet-4",
        temperature=0.2,
        prompt_hash=compute_prompt_hash("sys", "user"),
        run_id=new_run_id(),
        attempts=1,
        instructor_max_retries=3,
        credential_identity="ci-runner@evidentia",
    )


# -----------------------------------------------------------------------------
# generation_context default + optionality
# -----------------------------------------------------------------------------


def test_risk_statement_constructs_without_generation_context() -> None:
    """Field is optional with default None \u2014 backward compat with v0.7.0
    callers that don't yet supply the provenance block."""
    risk = RiskStatement(**_minimal_kwargs())
    assert risk.generation_context is None


def test_risk_statement_accepts_generation_context_object() -> None:
    risk = RiskStatement(
        **_minimal_kwargs(),
        generation_context=_sample_generation_context(),
    )
    assert risk.generation_context is not None
    assert risk.generation_context.model == "claude-sonnet-4"


# -----------------------------------------------------------------------------
# Backward compat: v0.7.0 JSON (no generation_context) deserializes cleanly
# -----------------------------------------------------------------------------


def test_v070_json_deserializes_into_v071_model() -> None:
    """A v0.7.0 RiskStatement dump (no generation_context key) must
    round-trip through the v0.7.1 model with generation_context=None."""
    v070_payload: dict[str, object] = {
        "asset": "X",
        "threat_source": "Y",
        "threat_event": "Z",
        "vulnerability": "W",
        "likelihood": "high",
        "likelihood_rationale": "..",
        "impact": "high",
        "impact_rationale": "..",
        "risk_level": "high",
        "risk_description": "..",
        "recommended_controls": ["AC-2"],
        "remediation_priority": 2,
    }
    risk = RiskStatement.model_validate(v070_payload)
    assert risk.generation_context is None


# -----------------------------------------------------------------------------
# Round-trip serialization
# -----------------------------------------------------------------------------


def test_risk_statement_with_generation_context_round_trips_through_json() -> None:
    """JSON round-trip preserves the entire generation_context block."""
    original = RiskStatement(
        **_minimal_kwargs(),
        generation_context=_sample_generation_context(),
    )
    dumped = original.model_dump(mode="json")
    restored = RiskStatement.model_validate(dumped)
    assert restored.generation_context == original.generation_context


def test_risk_statement_without_generation_context_round_trips() -> None:
    original = RiskStatement(**_minimal_kwargs())
    dumped = original.model_dump(mode="json")
    restored = RiskStatement.model_validate(dumped)
    assert restored.generation_context is None


# -----------------------------------------------------------------------------
# Field is properly nested in serialized output
# -----------------------------------------------------------------------------


def test_serialized_generation_context_is_nested_object() -> None:
    """JSON shape: generation_context is a nested object (not a string),
    so SIEM tools can index into ``generation_context.run_id``,
    ``generation_context.model``, etc."""
    risk = RiskStatement(
        **_minimal_kwargs(),
        generation_context=_sample_generation_context(),
    )
    dumped = risk.model_dump(mode="json")
    assert isinstance(dumped["generation_context"], dict)
    assert "run_id" in dumped["generation_context"]
    assert "credential_identity" in dumped["generation_context"]


def test_extra_fields_on_risk_statement_still_rejected() -> None:
    """Adding generation_context did not weaken extra='forbid'."""
    with pytest.raises(ValueError):
        RiskStatement(  # type: ignore[call-arg]
            **_minimal_kwargs(),
            bogus_field="should fail",
        )
