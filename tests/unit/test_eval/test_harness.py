"""Unit tests for the DFAH determinism harness (v0.8.0 P0.1).

Five test classes mirroring the eval module structure:

1. :class:`TestNormalization` — :func:`normalize_for_determinism`
   + :func:`hash_output` round-trip and edge cases.
2. :class:`TestDeterminismScore` — :func:`determinism_score`
   computes correctly for fully-deterministic, partially-
   deterministic, and fully-non-deterministic sample sets.
3. :class:`TestReplayEquivalent` — :func:`replay_equivalent`
   binary outcome.
4. :class:`TestHarnessRun` — :class:`DFAHarness` end-to-end
   against a deterministic stub + against a non-deterministic
   stub. Validates the audit-event emit count + JSON round-trip.
5. :class:`TestEvalCLI` — Typer CliRunner-driven smoke tests of
   ``evidentia eval stub-smoke``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from evidentia.cli.eval import app as eval_cli_app
from evidentia_ai.eval import (
    DFAHarness,
    EvalResult,
    EvalSample,
    determinism_score,
    hash_output,
    normalize_for_determinism,
    replay_equivalent,
)
from evidentia_core.audit.provenance import (
    GenerationContext,
    compute_prompt_hash,
)
from typer.testing import CliRunner

# ── 1. Normalization + hashing ────────────────────────────────────


class TestNormalization:
    def test_strips_leading_trailing_whitespace(self) -> None:
        assert normalize_for_determinism("  hello  ") == "hello"

    def test_collapses_internal_whitespace(self) -> None:
        assert normalize_for_determinism("a  b   c") == "a b c"

    def test_strips_trailing_punctuation(self) -> None:
        assert normalize_for_determinism("Risk found.") == "Risk found"
        assert normalize_for_determinism("Wow!") == "Wow"
        assert normalize_for_determinism("Why?") == "Why"

    def test_preserves_internal_punctuation(self) -> None:
        assert normalize_for_determinism("X.Y.Z") == "X.Y.Z"

    def test_hash_is_64_hex_chars(self) -> None:
        h = hash_output("anything")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_equivalent_inputs_hash_identically(self) -> None:
        a = "Risk found."
        b = "  Risk found  "
        c = "Risk found"
        assert hash_output(a) == hash_output(b) == hash_output(c)

    def test_distinct_inputs_hash_differently(self) -> None:
        assert hash_output("AC-2 risk") != hash_output("AC-3 risk")


# ── 2. Determinism scoring ────────────────────────────────────────


class TestDeterminismScore:
    def test_perfect_determinism(self) -> None:
        result = determinism_score(
            ["x", "x", "x", "x", "x"], prompt_id="p"
        )
        assert result.passed is True
        assert result.determinism_rate == 1.0
        assert result.distinct_outputs == 1
        assert result.modal_count == 5

    def test_all_distinct(self) -> None:
        result = determinism_score(
            ["a", "b", "c", "d"], prompt_id="p"
        )
        assert result.passed is False
        assert result.distinct_outputs == 4
        assert result.modal_count == 1
        assert result.determinism_rate == pytest.approx(0.25)

    def test_partial_determinism(self) -> None:
        # 3 of 5 samples match (the modal output).
        result = determinism_score(
            ["x", "x", "x", "y", "z"], prompt_id="p"
        )
        assert result.passed is False
        assert result.distinct_outputs == 3
        assert result.modal_count == 3
        assert result.determinism_rate == pytest.approx(0.6)

    def test_normalization_collapses_equivalents(self) -> None:
        # "x.", " x ", "x" should all hash to the same bucket.
        result = determinism_score(
            ["x.", " x ", "x"], prompt_id="p"
        )
        assert result.passed is True
        assert result.distinct_outputs == 1

    def test_empty_samples_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one"):
            determinism_score([], prompt_id="p")


# ── 3. Replay equivalence ─────────────────────────────────────────


class TestReplayEquivalent:
    def test_identical_outputs(self) -> None:
        r = replay_equivalent(
            original="Risk", replay="Risk", prompt_id="p"
        )
        assert r.equivalent is True

    def test_normalization_equivalent(self) -> None:
        # Trailing period + extra space should not register as
        # a replay violation.
        r = replay_equivalent(
            original="Risk.", replay="  Risk", prompt_id="p"
        )
        assert r.equivalent is True

    def test_substantively_different(self) -> None:
        r = replay_equivalent(
            original="Risk A",
            replay="Risk B",
            prompt_id="p",
        )
        assert r.equivalent is False


# ── 4. Harness end-to-end ─────────────────────────────────────────


def _det_stub(prompt: str, _ctx: GenerationContext) -> str:
    """Fully-deterministic stub: same prompt → same output."""
    return f"output-for-{prompt}"


class _CounterStub:
    """Stub that returns a different output on every call.

    Used to validate that the harness DETECTS non-determinism
    rather than masking it.
    """

    def __init__(self) -> None:
        self._n = 0

    def __call__(
        self, prompt: str, _ctx: GenerationContext
    ) -> str:
        self._n += 1
        return f"output-{self._n}-for-{prompt}"


def _make_ctx(prompt_id: str) -> GenerationContext:
    return GenerationContext(
        model="test-stub",
        temperature=0.0,
        prompt_hash=compute_prompt_hash("sys", prompt_id),
    )


class TestHarnessRun:
    def test_deterministic_stub_passes(self) -> None:
        harness = DFAHarness(
            generator=_det_stub, sample_count_per_prompt=5
        )
        result = harness.run(
            samples=[
                EvalSample(prompt_id="p1", prompt="A"),
                EvalSample(prompt_id="p2", prompt="B"),
            ],
            context_factory=_make_ctx,
        )
        assert result.overall_determinism_rate == 1.0
        assert result.determinism_violations == []
        assert all(r.passed for r in result.determinism_results)
        assert len(result.determinism_results) == 2

    def test_nondeterministic_stub_caught(self) -> None:
        stub = _CounterStub()
        harness = DFAHarness(
            generator=stub, sample_count_per_prompt=4
        )
        result = harness.run(
            samples=[EvalSample(prompt_id="p1", prompt="A")],
            context_factory=_make_ctx,
        )
        assert result.overall_determinism_rate < 1.0
        assert len(result.determinism_violations) == 1
        det = result.determinism_violations[0]
        assert det.distinct_outputs == 4
        assert det.passed is False

    def test_replay_check_when_deterministic(self) -> None:
        harness = DFAHarness(
            generator=_det_stub, sample_count_per_prompt=3
        )
        result = harness.run(
            samples=[EvalSample(prompt_id="p1", prompt="A")],
            context_factory=_make_ctx,
            check_replay=True,
        )
        assert len(result.replay_results) == 1
        assert result.replay_results[0].equivalent is True

    def test_replay_check_when_nondeterministic(self) -> None:
        stub = _CounterStub()
        harness = DFAHarness(
            generator=stub, sample_count_per_prompt=2
        )
        result = harness.run(
            samples=[EvalSample(prompt_id="p1", prompt="A")],
            context_factory=_make_ctx,
            check_replay=True,
        )
        assert len(result.replay_results) == 1
        assert result.replay_results[0].equivalent is False

    def test_eval_result_serializes_round_trip(self) -> None:
        harness = DFAHarness(
            generator=_det_stub, sample_count_per_prompt=2
        )
        result = harness.run(
            samples=[EvalSample(prompt_id="p1", prompt="A")],
            context_factory=_make_ctx,
        )
        dumped = result.model_dump_json()
        round_tripped = EvalResult.model_validate_json(dumped)
        assert round_tripped.run_id == result.run_id
        assert (
            round_tripped.overall_determinism_rate
            == result.overall_determinism_rate
        )

    def test_invalid_sample_count_raises(self) -> None:
        with pytest.raises(ValueError, match="sample_count_per_prompt"):
            DFAHarness(generator=_det_stub, sample_count_per_prompt=0)


# ── 5. CLI smoke ──────────────────────────────────────────────────


class TestEvalCLI:
    def test_stub_smoke_exits_zero(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            eval_cli_app,
            ["stub-smoke", "--samples-per-prompt", "3"],
        )
        assert result.exit_code == 0, result.stdout
        assert "PASS" in result.stdout
        assert "1.0000" in result.stdout

    def test_stub_smoke_writes_output(
        self, tmp_path: Path
    ) -> None:
        runner = CliRunner()
        out_path = tmp_path / "result.json"
        result = runner.invoke(
            eval_cli_app,
            [
                "stub-smoke",
                "--samples-per-prompt",
                "2",
                "--output",
                str(out_path),
            ],
        )
        assert result.exit_code == 0
        assert out_path.exists()
        loaded = json.loads(out_path.read_text(encoding="utf-8"))
        assert "run_id" in loaded
        assert "determinism_results" in loaded
        # 3 default smoke prompts; harness ran 2 samples each
        assert len(loaded["determinism_results"]) == 3


# ── 6. risk-determinism CLI verb (v0.8.1 P2.1) ───────────────────


class TestRiskDeterminismCLI:
    """Live LLM-driven harness against `RiskStatementGenerator`.

    The verb requires a system-context YAML + gap report JSON
    (the same files `evidentia risk generate` consumes). Tests
    mock `RiskStatementGenerator.generate` so the LLM round-trip
    is replaced with deterministic / non-deterministic stubs.
    """

    def test_risk_determinism_passes_with_deterministic_mock(
        self, tmp_path: Path
    ) -> None:
        """Mock `RiskStatementGenerator.generate` to always return
        the same RiskStatement; harness should report 1.0
        determinism rate.
        """
        from unittest.mock import patch

        from evidentia_core.models.gap import (
            ControlGap,
            GapAnalysisReport,
            GapSeverity,
            ImplementationEffort,
        )
        from evidentia_core.models.risk import (
            ImpactRating,
            LikelihoodRating,
            RiskLevel,
            RiskStatement,
            RiskTreatment,
        )

        # Create a minimal gap report on disk.
        gap = ControlGap(
            framework="nist-800-53-rev5",
            control_id="AC-2",
            control_title="Account Management",
            control_description="Manage accounts",
            gap_severity=GapSeverity.HIGH,
            gap_description="No automated deactivation",
            implementation_status="missing",
            cross_framework_value=[],
            remediation_guidance="Enable IAM Access Analyzer",
            implementation_effort=ImplementationEffort.MEDIUM,
        )
        report = GapAnalysisReport(
            organization="Test Co",
            frameworks_analyzed=["nist-800-53-rev5"],
            analyzed_at=datetime(2026, 5, 5, tzinfo=UTC),
            total_controls_required=10,
            total_controls_in_inventory=5,
            total_gaps=1,
            critical_gaps=0,
            high_gaps=1,
            medium_gaps=0,
            low_gaps=0,
            informational_gaps=0,
            coverage_percentage=50.0,
            gaps=[gap],
            efficiency_opportunities=[],
            prioritized_roadmap=[],
            evidentia_version="0.8.1",
        )
        gaps_file = tmp_path / "gaps.json"
        gaps_file.write_text(report.model_dump_json(), encoding="utf-8")

        # Create a minimal system context YAML on disk.
        ctx_file = tmp_path / "context.yaml"
        ctx_file.write_text(
            "organization: Test Co\n"
            "system_name: Test System\n"
            "system_description: minimal test fixture\n"
            "data_classification: [internal]\n"
            "hosting: cloud\n"
            "components: []\n"
            "threat_actors: []\n"
            "existing_controls: []\n"
            "frameworks: [nist-800-53-rev5]\n",
            encoding="utf-8",
        )

        # Mock the RiskStatement that the LLM "returns" — same
        # object each time.
        canonical_risk = RiskStatement(
            id="determ-test-001",
            asset="user-database",
            threat_source="external-attacker",
            threat_event="unauthorized-access",
            vulnerability="weak-acct-management",
            likelihood=LikelihoodRating.HIGH,
            likelihood_rationale="Dormant accounts.",
            impact=ImpactRating.HIGH,
            impact_rationale="PII exposure.",
            risk_level=RiskLevel.HIGH,
            risk_description="Risk description.",
            recommended_controls=["AC-2"],
            remediation_priority=2,
            treatment=RiskTreatment.MITIGATE,
        )

        # Patch RiskStatementGenerator.generate to return the
        # same RiskStatement on every call. Build a real Generator
        # instance + monkey-patch the `generate` method.
        from evidentia_ai.risk_statements import RiskStatementGenerator

        with patch.object(
            RiskStatementGenerator,
            "generate",
            return_value=canonical_risk,
        ):
            runner = CliRunner()
            out_path = tmp_path / "result.json"
            result = runner.invoke(
                eval_cli_app,
                [
                    "risk-determinism",
                    "--context",
                    str(ctx_file),
                    "--gaps",
                    str(gaps_file),
                    "--samples-per-prompt",
                    "3",
                    "--output",
                    str(out_path),
                    "--model",
                    "test-stub",
                ],
            )
        assert result.exit_code == 0, result.stdout
        assert "PASS" in result.stdout
        assert out_path.exists()
        loaded = json.loads(out_path.read_text(encoding="utf-8"))
        # overall_determinism_rate is a @property on EvalResult,
        # not a field — it doesn't survive model_dump_json. Check
        # via determinism_results directly.
        assert "determinism_results" in loaded
        assert len(loaded["determinism_results"]) == 1
        # 3 samples per prompt, all matching the modal hash
        # (the mocked RiskStatementGenerator.generate returns
        # the same canonical_risk every call).
        assert loaded["determinism_results"][0]["modal_count"] == 3
        assert loaded["determinism_results"][0]["distinct_outputs"] == 1

    def test_risk_determinism_missing_gap_id_exits_2(
        self, tmp_path: Path
    ) -> None:
        from evidentia_core.models.gap import GapAnalysisReport

        report = GapAnalysisReport(
            organization="Test Co",
            frameworks_analyzed=["nist-800-53-rev5"],
            analyzed_at=datetime(2026, 5, 5, tzinfo=UTC),
            total_controls_required=10,
            total_controls_in_inventory=5,
            total_gaps=0,
            critical_gaps=0,
            high_gaps=0,
            medium_gaps=0,
            low_gaps=0,
            informational_gaps=0,
            coverage_percentage=100.0,
            gaps=[],
            efficiency_opportunities=[],
            prioritized_roadmap=[],
            evidentia_version="0.8.1",
        )
        gaps_file = tmp_path / "gaps.json"
        gaps_file.write_text(report.model_dump_json(), encoding="utf-8")
        ctx_file = tmp_path / "context.yaml"
        ctx_file.write_text(
            "organization: Test Co\n"
            "system_name: Test\n"
            "system_description: minimal\n"
            "data_classification: [internal]\n"
            "hosting: cloud\n"
            "components: []\n"
            "threat_actors: []\n"
            "existing_controls: []\n"
            "frameworks: [nist-800-53-rev5]\n",
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(
            eval_cli_app,
            [
                "risk-determinism",
                "--context",
                str(ctx_file),
                "--gaps",
                str(gaps_file),
                "--gap-id",
                "nonexistent",
            ],
        )
        # Empty filtered set → exit 2 (usage error per CLI
        # convention); message tells operator the gap-id wasn't
        # found.
        assert result.exit_code == 2
