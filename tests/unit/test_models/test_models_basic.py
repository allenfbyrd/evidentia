"""Basic Pydantic model smoke tests."""

from __future__ import annotations

from evidentia_core.models.control import (
    ControlImplementation,
    ControlInventory,
    ControlStatus,
)
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
)


def test_control_implementation_roundtrip():
    impl = ControlImplementation(
        id="AC-2",
        title="Account Management",
        status=ControlStatus.IMPLEMENTED,
    )
    # use_enum_values stores the string value, not the enum
    assert impl.status == ControlStatus.IMPLEMENTED.value
    data = impl.model_dump()
    restored = ControlImplementation.model_validate(data)
    assert restored.id == impl.id
    assert restored.status == impl.status


def test_control_inventory_get_control_case_insensitive():
    inv = ControlInventory(
        organization="Test Co",
        controls=[
            ControlImplementation(id="AC-2", status=ControlStatus.IMPLEMENTED),
            ControlImplementation(id="cc6.1", status=ControlStatus.IMPLEMENTED),
        ],
    )
    assert inv.get_control("ac-2") is not None
    assert inv.get_control("AC-2") is not None
    assert inv.get_control("CC6.1") is not None


def test_gap_serializes_cleanly():
    gap = ControlGap(
        framework="nist-800-53-mod",
        control_id="AC-2",
        control_title="Account Management",
        control_description="Manage accounts.",
        gap_severity=GapSeverity.CRITICAL,
        implementation_status="missing",
        gap_description="No account management process.",
        remediation_guidance="Implement Okta or similar.",
        implementation_effort=ImplementationEffort.MEDIUM,
    )
    data = gap.model_dump_json()
    assert "AC-2" in data
    assert "critical" in data
    assert "medium" in data


def test_risk_statement_validates_priority_range():
    risk = RiskStatement(
        asset="Customer DB",
        threat_source="External attacker",
        threat_event="Exfiltration of PII",
        vulnerability="Missing access logging (AC-2 gap)",
        likelihood=LikelihoodRating.MODERATE,
        likelihood_rationale="No active monitoring",
        impact=ImpactRating.HIGH,
        impact_rationale="50K customer PII records",
        risk_level=RiskLevel.HIGH,
        risk_description="Risk of PII exfiltration due to missing controls.",
        recommended_controls=["AC-2", "AU-2"],
        remediation_priority=2,
    )
    assert risk.remediation_priority == 2
    assert risk.risk_level == RiskLevel.HIGH.value


def test_gap_report_summary_fields():
    report = GapAnalysisReport(
        organization="Acme",
        frameworks_analyzed=["nist-800-53-mod"],
        total_controls_required=10,
        total_controls_in_inventory=5,
        total_gaps=5,
        critical_gaps=2,
        high_gaps=2,
        medium_gaps=1,
        low_gaps=0,
        coverage_percentage=50.0,
        gaps=[],
    )
    assert report.total_gaps == 5
    assert report.coverage_percentage == 50.0
