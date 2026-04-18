"""Tests for the v0.3.0 gap-diff compute + renderers."""

from __future__ import annotations

from controlbridge_core.gap_diff import (
    compute_gap_diff,
    render_github_annotations,
    render_markdown,
)
from controlbridge_core.models.gap import (
    ControlGap,
    GapAnalysisReport,
    GapSeverity,
    GapStatus,
    ImplementationEffort,
)


def _gap(
    framework: str,
    control_id: str,
    severity: GapSeverity = GapSeverity.HIGH,
    status: GapStatus = GapStatus.OPEN,
    priority: float = 1.5,
) -> ControlGap:
    return ControlGap(
        framework=framework,
        control_id=control_id,
        control_title=f"{control_id} title",
        control_description="desc",
        gap_severity=severity,
        implementation_status="missing",
        gap_description="gap",
        remediation_guidance="fix",
        implementation_effort=ImplementationEffort.MEDIUM,
        priority_score=priority,
        status=status,
    )


def _report(org: str, gaps: list[ControlGap]) -> GapAnalysisReport:
    return GapAnalysisReport(
        organization=org,
        frameworks_analyzed=sorted({g.framework for g in gaps}) or ["fw"],
        total_controls_required=10,
        total_controls_in_inventory=9,
        total_gaps=len(gaps),
        critical_gaps=sum(1 for g in gaps if g.gap_severity == GapSeverity.CRITICAL.value),
        high_gaps=sum(1 for g in gaps if g.gap_severity == GapSeverity.HIGH.value),
        medium_gaps=sum(1 for g in gaps if g.gap_severity == GapSeverity.MEDIUM.value),
        low_gaps=sum(1 for g in gaps if g.gap_severity == GapSeverity.LOW.value),
        informational_gaps=0,
        coverage_percentage=90.0,
        gaps=gaps,
        efficiency_opportunities=[],
        prioritized_roadmap=[g.id for g in gaps],
    )


# -----------------------------------------------------------------------------
# compute_gap_diff — classification
# -----------------------------------------------------------------------------


def test_identical_reports_yield_unchanged_entries() -> None:
    gaps = [_gap("nist", "AC-2"), _gap("nist", "AU-2", GapSeverity.MEDIUM)]
    base = _report("Org", gaps)
    head = _report("Org", list(gaps))  # same identities
    diff = compute_gap_diff(base, head)
    assert diff.summary.unchanged == 2
    assert diff.summary.opened == 0
    assert diff.summary.closed == 0
    assert diff.summary.severity_increased == 0
    assert diff.summary.severity_decreased == 0


def test_opened_gap_detected() -> None:
    base = _report("Org", [_gap("nist", "AC-2")])
    head = _report("Org", [_gap("nist", "AC-2"), _gap("nist", "AC-3")])
    diff = compute_gap_diff(base, head)
    assert diff.summary.opened == 1
    assert diff.summary.is_regression is True
    assert diff.opened_entries[0].control_id == "AC-3"


def test_closed_gap_detected() -> None:
    base = _report("Org", [_gap("nist", "AC-2"), _gap("nist", "AU-2")])
    head = _report("Org", [_gap("nist", "AC-2")])
    diff = compute_gap_diff(base, head)
    assert diff.summary.closed == 1
    assert diff.closed_entries[0].control_id == "AU-2"
    assert diff.summary.is_regression is False


def test_severity_increased() -> None:
    base = _report("Org", [_gap("nist", "AC-2", GapSeverity.LOW)])
    head = _report("Org", [_gap("nist", "AC-2", GapSeverity.CRITICAL)])
    diff = compute_gap_diff(base, head)
    assert diff.summary.severity_increased == 1
    assert diff.severity_increased_entries[0].base_severity == GapSeverity.LOW.value
    assert diff.severity_increased_entries[0].head_severity == GapSeverity.CRITICAL.value
    assert diff.summary.is_regression is True


def test_severity_decreased() -> None:
    base = _report("Org", [_gap("nist", "AC-2", GapSeverity.HIGH)])
    head = _report("Org", [_gap("nist", "AC-2", GapSeverity.LOW)])
    diff = compute_gap_diff(base, head)
    assert diff.summary.severity_decreased == 1
    assert diff.summary.is_regression is False


def test_accepted_status_treated_as_closed() -> None:
    """A gap that's been formally accepted (risk acceptance memo) in base
    should NOT count as 'opened' if it shows up OPEN again in head."""
    base = _report("Org", [_gap("nist", "AC-2", status=GapStatus.ACCEPTED)])
    head = _report("Org", [_gap("nist", "AC-2", status=GapStatus.OPEN)])
    diff = compute_gap_diff(base, head)
    # base: 0 open gaps (the ACCEPTED one doesn't count)
    # head: 1 open gap → appears as 'opened' (a real regression —
    # someone revoked the acceptance)
    assert diff.summary.opened == 1


def test_remediated_gaps_excluded_from_diff() -> None:
    """REMEDIATED gaps aren't counted as 'open' on either side."""
    base = _report("Org", [_gap("nist", "AC-2", status=GapStatus.REMEDIATED)])
    head = _report("Org", [_gap("nist", "AC-2", status=GapStatus.REMEDIATED)])
    diff = compute_gap_diff(base, head)
    assert diff.summary.unchanged == 0
    assert diff.summary.closed == 0
    assert len(diff.entries) == 0


def test_mixed_diff_full_classification() -> None:
    base = _report(
        "Org",
        [
            _gap("nist", "AC-2", GapSeverity.HIGH),
            _gap("nist", "AC-3", GapSeverity.MEDIUM),
            _gap("nist", "AU-2"),
        ],
    )
    head = _report(
        "Org",
        [
            _gap("nist", "AC-2", GapSeverity.MEDIUM),  # sev decreased
            _gap("nist", "AC-3", GapSeverity.CRITICAL),  # sev increased
            # AU-2 closed
            _gap("nist", "AC-4"),  # opened
        ],
    )
    diff = compute_gap_diff(base, head)
    assert diff.summary.opened == 1
    assert diff.summary.closed == 1
    assert diff.summary.severity_increased == 1
    assert diff.summary.severity_decreased == 1


def test_entries_sorted_opened_first() -> None:
    """Opened gaps must appear before other classifications for visibility."""
    base = _report(
        "Org",
        [_gap("nist", "AC-2"), _gap("nist", "AU-2", GapSeverity.LOW)],
    )
    head = _report(
        "Org",
        [_gap("nist", "AC-2"), _gap("nist", "AU-2", GapSeverity.HIGH), _gap("nist", "NEW-1")],
    )
    diff = compute_gap_diff(base, head)
    # First entry must be the opened one
    assert diff.entries[0].status == "opened"


def test_control_id_normalization_matches_across_conventions() -> None:
    """Base uses 'AC-2(1)', head uses 'ac-2.1' — diff should see them as same gap."""
    base = _report("Org", [_gap("nist", "AC-2(1)")])
    head = _report("Org", [_gap("nist", "ac-2.1")])
    diff = compute_gap_diff(base, head)
    # Should be 'unchanged', not (1 closed + 1 opened)
    assert diff.summary.unchanged == 1
    assert diff.summary.opened == 0
    assert diff.summary.closed == 0


def test_framework_union_in_output() -> None:
    base = _report("Org", [_gap("fw-a", "C-1")])
    # need to coerce frameworks_analyzed manually
    head = _report("Org", [_gap("fw-b", "C-2")])
    diff = compute_gap_diff(base, head)
    assert "fw-a" in diff.frameworks_analyzed
    assert "fw-b" in diff.frameworks_analyzed


# -----------------------------------------------------------------------------
# render_markdown
# -----------------------------------------------------------------------------


def test_markdown_renders_summary_table() -> None:
    base = _report("Org", [_gap("nist", "AC-2")])
    head = _report("Org", [_gap("nist", "AC-2"), _gap("nist", "AC-3")])
    diff = compute_gap_diff(base, head)
    md = render_markdown(diff)
    assert "Compliance regression" in md
    assert "Opened" in md
    assert "| 🆕 Opened (regressions) | **1** |" in md
    assert "AC-3" in md


def test_markdown_no_regression_verdict() -> None:
    base = _report("Org", [_gap("nist", "AC-2")])
    head = _report("Org", [])  # all closed
    diff = compute_gap_diff(base, head)
    md = render_markdown(diff)
    assert "No compliance regression" in md or "No regression" in md


# -----------------------------------------------------------------------------
# render_github_annotations
# -----------------------------------------------------------------------------


def test_github_annotations_has_error_per_opened_gap() -> None:
    base = _report("Org", [])
    head = _report("Org", [_gap("nist", "AC-2"), _gap("nist", "AC-3")])
    diff = compute_gap_diff(base, head)
    ann = render_github_annotations(diff)
    lines = ann.strip().split("\n")
    error_lines = [ln for ln in lines if ln.startswith("::error")]
    assert len(error_lines) == 2


def test_github_annotations_has_warning_per_severity_increase() -> None:
    base = _report("Org", [_gap("nist", "AC-2", GapSeverity.LOW)])
    head = _report("Org", [_gap("nist", "AC-2", GapSeverity.CRITICAL)])
    diff = compute_gap_diff(base, head)
    ann = render_github_annotations(diff)
    assert ann.startswith("::warning") or "::warning" in ann


def test_github_annotations_empty_diff_has_notice() -> None:
    """Clean diff → single ::notice:: line (GitHub won't show 'empty' check)."""
    base = _report("Org", [_gap("nist", "AC-2")])
    head = _report("Org", [_gap("nist", "AC-2")])
    diff = compute_gap_diff(base, head)
    ann = render_github_annotations(diff)
    assert "::notice" in ann
