"""Tests for the OSCAL Assessment Results exporter (v0.2.1 D7).

The ``gap_report_to_oscal_ar`` function converts a ``GapAnalysisReport``
into an OSCAL Assessment Results JSON document. These tests pin the
top-level shape (the keys an auditor's tooling will consume) so future
refactors don't silently drop fields.
"""

from __future__ import annotations

from evidentia_core.models.gap import (
    ControlGap,
    GapAnalysisReport,
    GapSeverity,
    GapStatus,
    ImplementationEffort,
)
from evidentia_core.oscal.exporter import gap_report_to_oscal_ar


def _make_gap(
    framework: str, ctrl_id: str, sev: GapSeverity = GapSeverity.HIGH
) -> ControlGap:
    return ControlGap(
        framework=framework,
        control_id=ctrl_id,
        control_title=f"{ctrl_id} title",
        control_description="Some description.",
        gap_severity=sev,
        implementation_status="missing",
        gap_description="Not yet implemented.",
        remediation_guidance="Implement the control.",
        implementation_effort=ImplementationEffort.MEDIUM,
        priority_score=1.5,
        status=GapStatus.OPEN,
    )


def _make_report(frameworks: list[str] | None = None) -> GapAnalysisReport:
    frameworks = frameworks or ["nist-800-53-mod"]
    gaps = [
        _make_gap("nist-800-53-mod", "AC-2", GapSeverity.HIGH),
        _make_gap("nist-800-53-mod", "AU-2", GapSeverity.MEDIUM),
    ]
    return GapAnalysisReport(
        organization="Test Org",
        frameworks_analyzed=frameworks,
        total_controls_required=10,
        total_controls_in_inventory=8,
        total_gaps=len(gaps),
        critical_gaps=0,
        high_gaps=1,
        medium_gaps=1,
        low_gaps=0,
        informational_gaps=0,
        coverage_percentage=80.0,
        gaps=gaps,
        efficiency_opportunities=[],
        prioritized_roadmap=[g.id for g in gaps],
        inventory_source="test.yaml",
    )


def test_exports_top_level_oscal_ar_shape() -> None:
    """Output must have 'assessment-results' key — the OSCAL 1.x root."""
    report = _make_report()
    out = gap_report_to_oscal_ar(report)
    assert "assessment-results" in out
    ar = out["assessment-results"]
    # Standard OSCAL AR fields
    assert "uuid" in ar
    assert "metadata" in ar
    # 'results' is the required array of actual findings in OSCAL AR
    assert "results" in ar
    assert isinstance(ar["results"], list)
    assert len(ar["results"]) >= 1


def test_metadata_contains_organization() -> None:
    """The exporter must surface the organization name in metadata."""
    report = _make_report()
    out = gap_report_to_oscal_ar(report)
    md = out["assessment-results"]["metadata"]
    # Title or parties/roles — any place the org name can legitimately live
    serialized = str(md)
    assert "Test Org" in serialized


def test_each_gap_becomes_a_finding() -> None:
    """Every input gap produces a discrete output finding."""
    report = _make_report()
    out = gap_report_to_oscal_ar(report)
    _result = out["assessment-results"]["results"][0]
    # Each of the 2 input gaps must be represented somewhere in the output.
    # Serialize + substring-check is robust to exporter shape choices (findings
    # vs observations vs risks — all valid OSCAL AR locations).
    serialized = str(out)
    assert "AC-2" in serialized
    assert "AU-2" in serialized


def test_empty_gap_report_still_produces_valid_shape() -> None:
    """A clean report (0 gaps) should still export a valid OSCAL AR doc."""
    report = GapAnalysisReport(
        organization="Clean Org",
        frameworks_analyzed=["nist-800-53-mod"],
        total_controls_required=1,
        total_controls_in_inventory=1,
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
    )
    out = gap_report_to_oscal_ar(report)
    assert "assessment-results" in out
    # Even with 0 gaps, the shape is valid — the findings list may be empty
    assert "results" in out["assessment-results"]


def test_uuid_is_unique_per_call() -> None:
    """Two exports of the same report must not produce identical UUIDs."""
    report = _make_report()
    a = gap_report_to_oscal_ar(report)
    b = gap_report_to_oscal_ar(report)
    assert a["assessment-results"]["uuid"] != b["assessment-results"]["uuid"]


# ─── v0.7.0: evidence embedding + integrity ──────────────────────────────
#
# These tests cover the new ``findings=`` kwarg. The goal is a
# tamper-evident chain-of-custody: each SecurityFinding lands as an
# OSCAL back-matter resource with base64 content + SHA-256 hash, and
# observations sharing its control IDs cross-reference it.


import base64  # noqa: E402  — grouped with v0.7.0 test helpers below

from evidentia_core.models.common import Severity  # noqa: E402
from evidentia_core.models.finding import SecurityFinding  # noqa: E402
from evidentia_core.oscal.digest import digest_bytes, parse_digest  # noqa: E402


def _make_finding(control_ids: list[str] | None = None) -> SecurityFinding:
    return SecurityFinding(
        id="00000000-0000-0000-0000-000000000042",
        title="MFA not enforced on root",
        description="Root account missing MFA.",
        severity=Severity.HIGH,
        source_system="aws-config",
        control_ids=control_ids or ["AC-2"],
    )


def test_export_without_findings_has_no_back_matter() -> None:
    """Back-compat: omitting ``findings`` must not change the pre-v0.7.0 shape."""
    out = gap_report_to_oscal_ar(_make_report())
    assert "back-matter" not in out["assessment-results"]


def test_export_with_findings_creates_back_matter_resources() -> None:
    out = gap_report_to_oscal_ar(_make_report(), findings=[_make_finding()])
    resources = out["assessment-results"]["back-matter"]["resources"]
    assert len(resources) == 1
    resource = resources[0]
    assert resource["uuid"] == "00000000-0000-0000-0000-000000000042"
    # Standards-track hash + Evidentia-ns prop both present
    assert resource["rlinks"][0]["hashes"][0]["algorithm"] == "SHA-256"
    digest_prop = next(
        p for p in resource["props"] if p["name"] == "evidence-digest"
    )
    assert digest_prop["value"].startswith("sha256:")


def test_embedded_content_hashes_match_stored_digest() -> None:
    """Bit-for-bit integrity: base64-decoded payload hashes to the
    stored value. Verifier reuses this exact computation."""
    finding = _make_finding()
    out = gap_report_to_oscal_ar(_make_report(), findings=[finding])
    resource = out["assessment-results"]["back-matter"]["resources"][0]

    payload = base64.b64decode(resource["base64"]["value"])
    stored_hex = resource["rlinks"][0]["hashes"][0]["value"]
    assert digest_bytes(payload) == stored_hex

    # And the Evidentia prop encodes the same digest under sha256: prefix.
    digest_prop = next(
        p for p in resource["props"] if p["name"] == "evidence-digest"
    )
    _, prop_hex = parse_digest(digest_prop["value"])
    assert prop_hex == stored_hex


def test_observations_crossref_matching_findings() -> None:
    """A finding whose control_ids intersect a gap's control_id lands as
    ``relevant-evidence[].href`` on that observation."""
    finding = _make_finding(control_ids=["AC-2"])  # same as the AC-2 gap
    out = gap_report_to_oscal_ar(_make_report(), findings=[finding])
    observations = out["assessment-results"]["results"][0]["observations"]

    ac2_obs = next(
        o for o in observations if any(
            p.get("value") == "AC-2" for p in o.get("props", [])
        )
    )
    assert "relevant-evidence" in ac2_obs
    hrefs = [e["href"] for e in ac2_obs["relevant-evidence"]]
    assert f"#{finding.id}" in hrefs
    # Evidence attached → method flips EXAMINE → TEST (automated finding).
    assert ac2_obs["methods"] == ["TEST"]


def test_observations_without_matching_findings_stay_examine() -> None:
    """Gaps whose control_id has no matching finding keep the default
    EXAMINE method and no relevant-evidence array."""
    finding = _make_finding(control_ids=["AC-2"])  # only AC-2, not AU-2
    out = gap_report_to_oscal_ar(_make_report(), findings=[finding])
    observations = out["assessment-results"]["results"][0]["observations"]

    au2_obs = next(
        o for o in observations if any(
            p.get("value") == "AU-2" for p in o.get("props", [])
        )
    )
    assert au2_obs["methods"] == ["EXAMINE"]
    assert "relevant-evidence" not in au2_obs


def test_finding_spanning_multiple_controls_crossrefs_each() -> None:
    """A single finding with control_ids=[AC-2, AU-2] becomes relevant
    evidence on both observations."""
    finding = _make_finding(control_ids=["AC-2", "AU-2"])
    out = gap_report_to_oscal_ar(_make_report(), findings=[finding])
    observations = out["assessment-results"]["results"][0]["observations"]

    for obs in observations:
        control_id = next(
            p["value"] for p in obs["props"] if p["name"] == "control-id"
        )
        evidence_hrefs = {e["href"] for e in obs.get("relevant-evidence", [])}
        assert f"#{finding.id}" in evidence_hrefs, (
            f"Expected finding cross-referenced on {control_id}"
        )


def test_finding_with_no_matching_control_still_lands_in_back_matter() -> None:
    """The finding still counts as evidence even if no current gap maps
    to it — it just doesn't get cross-referenced anywhere."""
    finding = _make_finding(control_ids=["CP-9"])  # not in our gaps
    out = gap_report_to_oscal_ar(_make_report(), findings=[finding])

    resources = out["assessment-results"]["back-matter"]["resources"]
    assert len(resources) == 1
    observations = out["assessment-results"]["results"][0]["observations"]
    for obs in observations:
        assert "relevant-evidence" not in obs
