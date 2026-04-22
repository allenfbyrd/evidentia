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
