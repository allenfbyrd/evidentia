"""Tests for :mod:`evidentia_core.oscal.verify` (v0.7.0).

Covers the digest-checking half of the verifier (the signature half is
covered by ``test_signing.py`` round-trip tests; ``test_verify_ar_file``
here exercises the orchestration that pulls them together).
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

from evidentia_core.models.common import Severity
from evidentia_core.models.finding import SecurityFinding
from evidentia_core.models.gap import (
    ControlGap,
    GapAnalysisReport,
    GapSeverity,
    GapStatus,
    ImplementationEffort,
)
from evidentia_core.oscal.exporter import gap_report_to_oscal_ar
from evidentia_core.oscal.verify import verify_ar_file, verify_digests

# ── fixtures ─────────────────────────────────────────────────────────────


def _make_gap(control_id: str = "AC-2") -> ControlGap:
    return ControlGap(
        framework="nist-800-53-mod",
        control_id=control_id,
        control_title=f"{control_id} title",
        control_description="desc",
        gap_severity=GapSeverity.HIGH,
        implementation_status="missing",
        gap_description="not implemented",
        remediation_guidance="implement",
        implementation_effort=ImplementationEffort.MEDIUM,
        priority_score=1.0,
        status=GapStatus.OPEN,
    )


def _make_finding(control_ids: list[str] | None = None) -> SecurityFinding:
    return SecurityFinding(
        id="22222222-2222-2222-2222-222222222222",
        title="Privileged account lacks MFA",
        description="Root account missing MFA enforcement.",
        severity=Severity.HIGH,
        source_system="aws-config",
        control_ids=control_ids or ["AC-2"],
    )


def _make_report() -> GapAnalysisReport:
    gap = _make_gap("AC-2")
    return GapAnalysisReport(
        organization="TestOrg",
        frameworks_analyzed=["nist-800-53-mod"],
        total_controls_required=1,
        total_controls_in_inventory=0,
        total_gaps=1,
        critical_gaps=0,
        high_gaps=1,
        medium_gaps=0,
        low_gaps=0,
        informational_gaps=0,
        coverage_percentage=0.0,
        gaps=[gap],
        efficiency_opportunities=[],
        prioritized_roadmap=[gap.id],
        inventory_source="test.yaml",
    )


# ── verify_digests ───────────────────────────────────────────────────────


def test_verify_digests_all_pass_for_clean_export() -> None:
    """A fresh export with no tampering should re-hash cleanly."""
    ar_doc = gap_report_to_oscal_ar(_make_report(), findings=[_make_finding()])
    checks = verify_digests(ar_doc)
    assert len(checks) == 1
    assert checks[0].valid is True
    assert checks[0].expected_digest == checks[0].actual_digest


def test_verify_digests_detects_tampered_resource_payload() -> None:
    """Re-encode a different payload under the same hash → integrity fails."""
    ar_doc = gap_report_to_oscal_ar(_make_report(), findings=[_make_finding()])
    resource = ar_doc["assessment-results"]["back-matter"]["resources"][0]

    # Tamper: replace the base64 content with something different, but
    # leave the hash value intact. This is the classic attack the feature
    # is meant to detect.
    tampered_content = b'{"malicious": "payload"}'
    resource["base64"]["value"] = base64.b64encode(tampered_content).decode("ascii")

    checks = verify_digests(ar_doc)
    assert len(checks) == 1
    assert checks[0].valid is False
    assert checks[0].expected_digest != checks[0].actual_digest


def test_verify_digests_flags_resource_with_missing_hash() -> None:
    """Embedded content with no hashes[] entry → invalid (silent pass would
    defeat the chain-of-custody claim)."""
    ar_doc = gap_report_to_oscal_ar(_make_report(), findings=[_make_finding()])
    resource = ar_doc["assessment-results"]["back-matter"]["resources"][0]
    resource["rlinks"] = [{"href": "#whatever"}]  # no hashes[]
    checks = verify_digests(ar_doc)
    assert len(checks) == 1
    assert checks[0].valid is False


def test_verify_digests_skips_external_resources_without_base64() -> None:
    """Resources that point at external files have nothing to re-hash
    locally; they should be silently skipped (not flagged)."""
    ar_doc = {
        "assessment-results": {
            "back-matter": {
                "resources": [
                    {
                        "uuid": "external-uuid",
                        "title": "External evidence",
                        "rlinks": [{"href": "https://example.com/evidence.pdf"}],
                        # No base64 block — pure metadata pointer
                    }
                ]
            }
        }
    }
    checks = verify_digests(ar_doc)
    assert checks == []


def test_verify_digests_returns_empty_when_no_back_matter() -> None:
    """An AR with no evidence resources has nothing to check — return []."""
    ar_doc = gap_report_to_oscal_ar(_make_report())  # no findings
    checks = verify_digests(ar_doc)
    assert checks == []


# ── verify_ar_file ───────────────────────────────────────────────────────


def test_verify_ar_file_passes_on_clean_export(tmp_path: Path) -> None:
    ar_doc = gap_report_to_oscal_ar(_make_report(), findings=[_make_finding()])
    ar_path = tmp_path / "audit.json"
    ar_path.write_text(json.dumps(ar_doc), encoding="utf-8")

    report = verify_ar_file(ar_path)
    assert report.overall_valid is True
    assert report.digests_valid is True
    assert report.signature_valid is None  # no sig on disk, none required


def test_verify_ar_file_fails_on_tampered_content(tmp_path: Path) -> None:
    ar_doc = gap_report_to_oscal_ar(_make_report(), findings=[_make_finding()])

    # Tamper the base64 content before writing to disk.
    resource = ar_doc["assessment-results"]["back-matter"]["resources"][0]
    resource["base64"]["value"] = base64.b64encode(b"tampered").decode("ascii")

    ar_path = tmp_path / "audit.json"
    ar_path.write_text(json.dumps(ar_doc), encoding="utf-8")

    report = verify_ar_file(ar_path)
    assert report.overall_valid is False
    assert report.digests_valid is False


def test_verify_ar_file_missing_file_returns_error(tmp_path: Path) -> None:
    report = verify_ar_file(tmp_path / "does-not-exist.json")
    assert report.overall_valid is False
    assert any("not found" in err for err in report.errors)


def test_verify_ar_file_malformed_json_returns_error(tmp_path: Path) -> None:
    path = tmp_path / "garbage.json"
    path.write_text("this is { not valid json", encoding="utf-8")
    report = verify_ar_file(path)
    assert report.overall_valid is False
    assert any("Malformed JSON" in err for err in report.errors)


def test_verify_ar_file_require_signature_without_sig_fails(
    tmp_path: Path,
) -> None:
    """--require-signature turns a missing .asc into a failure."""
    ar_doc = gap_report_to_oscal_ar(_make_report())
    ar_path = tmp_path / "unsigned.json"
    ar_path.write_text(json.dumps(ar_doc), encoding="utf-8")

    report = verify_ar_file(ar_path, require_signature=True)
    assert report.overall_valid is False
    assert report.signature_valid is False
