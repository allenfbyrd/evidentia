"""Unit tests for v0.8.2 §25.2 P3.1 DFAH faithfulness scoring.

Covers the three intrinsic invariants of
:func:`evidentia_ai.eval.faithfulness.faithfulness_score`:

1. **Score range** — output ``score`` always in ``[0.0, 1.0]``.
2. **Empty source** — empty ``source_clauses`` produces score
   0.0 + empty evidence list (never raises).
3. **Top-3 evidence** — returned ``evidence_clauses`` are at
   most 3, sorted descending by similarity.
4. **Threshold validation** — out-of-range threshold raises
   ``ValueError``.
5. **Faithful claim** — a claim with high token overlap to a
   source clause scores high + passes the default threshold.
6. **Hallucinated claim** — a claim with no token overlap
   scores 0 + fails the threshold.
"""

from __future__ import annotations

import pytest
from evidentia_ai.eval.faithfulness import (
    DEFAULT_FAITHFULNESS_THRESHOLD,
    FaithfulnessResult,
    faithfulness_score,
)


class TestFaithfulnessScore:
    def test_score_in_unit_interval(self) -> None:
        result = faithfulness_score(
            "The system enforces account management",
            ["AC-2 requires account management procedures"],
        )
        assert 0.0 <= result.score <= 1.0

    def test_empty_source_clauses_returns_zero_score(self) -> None:
        """No source → score 0.0, no evidence, no raise."""
        result = faithfulness_score("Some claim", [])
        assert result.score == 0.0
        assert result.evidence_clauses == []
        # score < default threshold → fails (correct: hallucination
        # signal when there's no source to anchor against).
        assert not result.passed

    def test_top_3_evidence_clauses(self) -> None:
        """``evidence_clauses`` capped at 3 + sorted descending."""
        clauses = [
            "Account management policies enforce least privilege",
            "Configuration management baselines maintained",
            "Information system inventory documented",
            "Auditor access controls reviewed quarterly",
            "Change management workflow approves all changes",
        ]
        result = faithfulness_score(
            "Account management policies enforce least privilege",
            clauses,
        )
        assert len(result.evidence_clauses) <= 3
        # The verbatim-match clause MUST be the first evidence entry.
        assert result.evidence_clauses[0] == clauses[0]

    def test_invalid_threshold_raises(self) -> None:
        """Threshold outside [0, 1] is a ValueError."""
        with pytest.raises(ValueError, match="threshold"):
            faithfulness_score("c", ["x"], threshold=1.5)
        with pytest.raises(ValueError, match="threshold"):
            faithfulness_score("c", ["x"], threshold=-0.1)

    def test_high_overlap_claim_scores_high(self) -> None:
        """A claim that's a near-verbatim copy of a clause scores ~1."""
        clause = "Configuration management baselines documented quarterly"
        result = faithfulness_score(clause, [clause])
        # Identical token sets → Jaccard 1.0.
        assert result.score == 1.0
        assert result.passed
        assert result.evidence_clauses[0] == clause

    def test_zero_overlap_claim_fails_threshold(self) -> None:
        """A claim with no token overlap to any clause scores 0."""
        result = faithfulness_score(
            "The quick brown fox jumps over",
            [
                "Account management procedures enforce least privilege",
                "Information system inventory documented",
            ],
        )
        # Zero token overlap (after lowercase normalization).
        assert result.score == 0.0
        assert not result.passed

    def test_threshold_stored_on_result(self) -> None:
        """``FaithfulnessResult.threshold`` reflects the input threshold."""
        result = faithfulness_score(
            "claim", ["clause"], threshold=0.5
        )
        assert result.threshold == 0.5

    def test_default_threshold_constant(self) -> None:
        """The default threshold is exposed as a module-level constant."""
        assert 0.0 <= DEFAULT_FAITHFULNESS_THRESHOLD <= 1.0
        # When no threshold passed, the constant is what's stored.
        result = faithfulness_score("c", ["x"])
        assert result.threshold == DEFAULT_FAITHFULNESS_THRESHOLD

    def test_method_field_identifies_stdlib_baseline(self) -> None:
        """The ``method`` field distinguishes stdlib from semantic paths."""
        result = faithfulness_score("c", ["x"])
        assert result.method == "jaccard-stdlib"

    def test_result_is_serializable(self) -> None:
        """The result model is Sigstore-signable as part of the
        wider eval output — JSON-roundtrips cleanly."""
        result = faithfulness_score(
            "Account management is enforced",
            ["AC-2 requires account management"],
        )
        json_str = result.model_dump_json()
        # Parse back and verify the canonical fields present.
        roundtripped = FaithfulnessResult.model_validate_json(json_str)
        assert roundtripped.claim == result.claim
        assert roundtripped.score == result.score
        assert roundtripped.method == result.method
