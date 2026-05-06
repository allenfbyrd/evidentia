"""Unit tests for v0.8.2 §25.2 P3.2 first-class Sigstore signing.

Covers the eval-output signing path:

1. **JSON written before signing** — the EvalResult JSON lands
   on disk regardless of whether Sigstore signing succeeds. An
   operator running locally without an OIDC credential still
   gets the eval output; they can sign later in CI when
   credentials are available.
2. **Bundle path defaulting** — when ``bundle_path`` is None,
   the bundle lands at ``<output>.sigstore.json``.
3. **Audit event** — successful signing fires
   ``EventAction.AI_EVAL_OUTPUT_SIGNED``.
4. **Verify roundtrip** — verify_eval_result delegates to the
   canonical OSCAL Sigstore verifier.
5. **Missing parent directory** — sign_eval_result raises
   FileNotFoundError when the output's parent doesn't exist.

Sigstore signing requires a network round-trip to Fulcio + Rekor
+ an OIDC credential. The tests mock those out — exercising the
control flow without hitting the real services.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

import pytest
from evidentia_ai.eval.harness import EvalResult
from evidentia_ai.eval.signing import (
    sign_eval_result,
    verify_eval_result,
)


def _make_eval_result() -> EvalResult:
    """Return a minimal EvalResult fixture for signing tests."""
    now = datetime(2026, 5, 6, 12, 0, 0, tzinfo=UTC)
    return EvalResult(
        run_id="01HXYZ0000000000000000000A",
        started_at=now,
        completed_at=now,
        evidentia_version="0.8.2",
        sample_count_per_prompt=1,
        samples=[],
        determinism_results=[],
        replay_results=[],
    )


class TestSignEvalResult:
    def test_json_written_to_output_path(
        self, tmp_path: Path
    ) -> None:
        """The EvalResult JSON lands on disk before signing fires."""
        output = tmp_path / "eval-result.json"
        result = _make_eval_result()
        # Mock the Sigstore signer so the test runs without OIDC.
        with mock.patch(
            "evidentia_ai.eval.signing.sign_file"
        ) as mock_sign:
            mock_sign.return_value = output.with_suffix(
                ".json.sigstore.json"
            )
            out_path, _bundle_path = sign_eval_result(result, output)

        assert out_path == output
        assert output.is_file()
        # Verify the file content is the serialized EvalResult.
        body = output.read_text(encoding="utf-8")
        assert "01HXYZ0000000000000000000A" in body  # run_id
        assert "0.8.2" in body  # evidentia_version
        # Sigstore signer was called once.
        mock_sign.assert_called_once()

    def test_default_bundle_path_appended(
        self, tmp_path: Path
    ) -> None:
        """When bundle_path is None, defaults to <output>.sigstore.json."""
        output = tmp_path / "eval.json"
        result = _make_eval_result()
        expected_bundle = output.with_suffix(".json.sigstore.json")

        with mock.patch(
            "evidentia_ai.eval.signing.sign_file"
        ) as mock_sign:
            mock_sign.return_value = expected_bundle
            _out, bundle_path = sign_eval_result(result, output)

        # The function returns the resolved bundle path (which
        # matches default_bundle_path semantics from oscal.sigstore).
        assert bundle_path == expected_bundle
        # sign_file was called with bundle_path matching the default.
        kwargs = mock_sign.call_args.kwargs
        assert kwargs.get("bundle_path") == expected_bundle

    def test_explicit_bundle_path_honored(self, tmp_path: Path) -> None:
        """Caller-supplied bundle_path overrides the default."""
        output = tmp_path / "eval.json"
        explicit_bundle = tmp_path / "custom-bundle.sig"
        result = _make_eval_result()

        with mock.patch(
            "evidentia_ai.eval.signing.sign_file"
        ) as mock_sign:
            mock_sign.return_value = explicit_bundle
            _out, bundle_path = sign_eval_result(
                result, output, bundle_path=explicit_bundle
            )

        assert bundle_path == explicit_bundle

    def test_missing_parent_dir_raises_filenotfound(
        self, tmp_path: Path
    ) -> None:
        """Output path with non-existent parent → FileNotFoundError."""
        nonexistent_parent = tmp_path / "no" / "such" / "dir"
        output = nonexistent_parent / "eval.json"
        result = _make_eval_result()

        with pytest.raises(FileNotFoundError):
            sign_eval_result(result, output)

    def test_audit_event_fires(self, tmp_path: Path) -> None:
        """Successful signing emits AI_EVAL_OUTPUT_SIGNED."""
        output = tmp_path / "eval-audit.json"
        result = _make_eval_result()

        with mock.patch(
            "evidentia_ai.eval.signing.sign_file"
        ) as mock_sign:
            mock_sign.return_value = output.with_suffix(
                ".json.sigstore.json"
            )
            with mock.patch(
                "evidentia_ai.eval.signing._log"
            ) as mock_log:
                sign_eval_result(result, output)

        # _log.info was called at least once with action=AI_EVAL_OUTPUT_SIGNED.
        action_args = [
            call.kwargs.get("action")
            for call in mock_log.info.call_args_list
        ]
        # Compare via the enum value (str enum) for robustness across
        # mypy-strict + runtime contexts.
        assert any(
            getattr(a, "value", a)
            == "evidentia.ai.eval_output_signed"
            for a in action_args
        )


class TestVerifyEvalResult:
    def test_verify_delegates_to_canonical(self, tmp_path: Path) -> None:
        """verify_eval_result delegates to oscal.sigstore.verify_file."""
        output = tmp_path / "eval.json"
        output.write_text("{}", encoding="utf-8")

        with mock.patch(
            "evidentia_ai.eval.signing.verify_file"
        ) as mock_verify:
            sentinel = mock.MagicMock(valid=True)
            mock_verify.return_value = sentinel
            result = verify_eval_result(output)

        # The wrapper passes through the result unchanged.
        assert result is sentinel
        mock_verify.assert_called_once_with(
            output,
            bundle_path=None,
            expected_identity=None,
            expected_issuer=None,
        )

    def test_verify_passes_through_kwargs(
        self, tmp_path: Path
    ) -> None:
        """Identity/issuer/bundle kwargs flow to the canonical verifier."""
        output = tmp_path / "eval.json"
        output.write_text("{}", encoding="utf-8")
        bundle = tmp_path / "custom.sig"

        with mock.patch(
            "evidentia_ai.eval.signing.verify_file"
        ) as mock_verify:
            mock_verify.return_value = mock.MagicMock(valid=True)
            verify_eval_result(
                output,
                bundle_path=bundle,
                expected_identity="https://example.com/foo",
                expected_issuer="https://example.com/issuer",
            )

        mock_verify.assert_called_once_with(
            output,
            bundle_path=bundle,
            expected_identity="https://example.com/foo",
            expected_issuer="https://example.com/issuer",
        )
