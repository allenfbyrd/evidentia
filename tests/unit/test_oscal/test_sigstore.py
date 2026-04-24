"""Tests for :mod:`evidentia_core.oscal.sigstore` (v0.7.0)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from evidentia_core.oscal.sigstore import (
    SigstoreAirGapError,
    SigstoreError,
    SigstoreNotAvailableError,
    SigstoreSigningError,
    SigstoreVerifyError,
    SigstoreVerifyResult,
    default_bundle_path,
    sign_file,
    sigstore_available,
    verify_file,
)


def test_error_class_hierarchy() -> None:
    assert issubclass(SigstoreNotAvailableError, SigstoreError)
    assert issubclass(SigstoreAirGapError, SigstoreError)
    assert issubclass(SigstoreSigningError, SigstoreError)
    assert issubclass(SigstoreVerifyError, SigstoreError)


def test_verify_result_frozen_dataclass() -> None:
    result = SigstoreVerifyResult(valid=True, signer_identity="x", signer_issuer="y")
    with pytest.raises(AttributeError):
        result.valid = False  # type: ignore[misc]


def test_default_bundle_path_appends_sigstore_json() -> None:
    assert (
        default_bundle_path("audit.oscal-ar.json")
        == Path("audit.oscal-ar.json.sigstore.json")
    )


def test_sigstore_available_returns_bool() -> None:
    assert isinstance(sigstore_available(), bool)


def test_sign_raises_not_available_when_library_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "evidentia_core.oscal.sigstore.sigstore_available", lambda: False
    )
    artifact = tmp_path / "x.json"
    artifact.write_text("{}")
    with pytest.raises(SigstoreNotAvailableError, match="pip install"):
        sign_file(artifact)


def test_verify_raises_not_available_when_library_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "evidentia_core.oscal.sigstore.sigstore_available", lambda: False
    )
    artifact = tmp_path / "x.json"
    artifact.write_text("{}")
    with pytest.raises(SigstoreNotAvailableError):
        verify_file(artifact)


def test_sign_raises_airgap_error_in_offline_mode(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "evidentia_core.oscal.sigstore.sigstore_available", lambda: True
    )
    monkeypatch.setattr(
        "evidentia_core.network_guard.is_offline", lambda: True
    )
    artifact = tmp_path / "x.json"
    artifact.write_text("{}")
    with pytest.raises(SigstoreAirGapError, match=r"[Aa]ir-gap"):
        sign_file(artifact)


def test_verify_raises_airgap_error_in_offline_mode(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "evidentia_core.oscal.sigstore.sigstore_available", lambda: True
    )
    monkeypatch.setattr(
        "evidentia_core.network_guard.is_offline", lambda: True
    )
    artifact = tmp_path / "x.json"
    artifact.write_text("{}")
    with pytest.raises(SigstoreAirGapError):
        verify_file(artifact)


def test_sign_raises_signing_error_for_missing_artifact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "evidentia_core.oscal.sigstore.sigstore_available", lambda: True
    )
    monkeypatch.setattr(
        "evidentia_core.network_guard.is_offline", lambda: False
    )
    with pytest.raises(SigstoreSigningError, match="Artifact not found"):
        sign_file(tmp_path / "does-not-exist.json")


def test_verify_raises_verify_error_for_missing_bundle(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "evidentia_core.oscal.sigstore.sigstore_available", lambda: True
    )
    monkeypatch.setattr(
        "evidentia_core.network_guard.is_offline", lambda: False
    )
    artifact = tmp_path / "x.json"
    artifact.write_text("{}")
    with pytest.raises(SigstoreVerifyError, match="bundle not found"):
        verify_file(artifact)


# ── CI-gated integration tests (Q5=A) ────────────────────────────────────


def _sigstore_integration_ready() -> bool:
    """True when the ambient environment can actually run Sigstore."""
    if not sigstore_available():
        return False
    if os.environ.get("CI", "").lower() != "true":
        return False
    if os.environ.get("RUNNER_OS", "") != "Linux":
        return False
    return bool(os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL"))


sigstore_integration = pytest.mark.skipif(
    not _sigstore_integration_ready(),
    reason=(
        "Sigstore sign/verify integration tests require CI=true, "
        "RUNNER_OS=Linux, and GitHub Actions OIDC token env vars "
        "(ACTIONS_ID_TOKEN_REQUEST_URL). Skipping on local and non-"
        "GitHub-Actions CI runs — see Q5=A gating rule."
    ),
)


@sigstore_integration
def test_sign_then_verify_integration(tmp_path: Path) -> None:
    artifact = tmp_path / "audit.oscal-ar.json"
    artifact.write_text(
        '{"assessment-results": {"test": true}}', encoding="utf-8"
    )

    bundle_path = sign_file(artifact)
    assert bundle_path.is_file()
    assert bundle_path.name.endswith(".sigstore.json")

    result = verify_file(artifact)
    assert result.valid is True


@sigstore_integration
def test_verify_detects_tampered_artifact_integration(tmp_path: Path) -> None:
    artifact = tmp_path / "audit.oscal-ar.json"
    artifact.write_text('{"hello": "world"}', encoding="utf-8")

    sign_file(artifact)
    artifact.write_text('{"hello": "tampered"}', encoding="utf-8")

    result = verify_file(artifact)
    assert result.valid is False
