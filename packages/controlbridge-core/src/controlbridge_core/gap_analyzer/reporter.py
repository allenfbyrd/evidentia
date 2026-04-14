"""Gap analysis report output formatters.

Supports: JSON, CSV, Markdown, OSCAL Assessment Results.
"""

from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path
from typing import Literal

from controlbridge_core.models.gap import GapAnalysisReport

OutputFormat = Literal["json", "csv", "markdown", "oscal-ar"]


def export_report(
    report: GapAnalysisReport,
    output_path: str | Path,
    format: OutputFormat = "json",
) -> Path:
    """Export a gap analysis report in the specified format."""
    path = Path(output_path)

    if format == "json":
        return _export_json(report, path)
    if format == "csv":
        return _export_csv(report, path)
    if format == "markdown":
        return _export_markdown(report, path)
    if format == "oscal-ar":
        return _export_oscal_ar(report, path)

    raise ValueError(f"Unsupported format: {format}")


def _export_json(report: GapAnalysisReport, path: Path) -> Path:
    """Export as JSON."""
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return path


def _export_csv(report: GapAnalysisReport, path: Path) -> Path:
    """Export gaps as CSV (one row per gap)."""
    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "gap_id",
            "framework",
            "control_id",
            "control_title",
            "gap_severity",
            "implementation_status",
            "gap_description",
            "cross_framework_value",
            "remediation_guidance",
            "implementation_effort",
            "priority_score",
            "jira_issue_key",
            "servicenow_ticket_id",
        ]
    )

    for gap in report.gaps:
        writer.writerow(
            [
                gap.id,
                gap.framework,
                gap.control_id,
                gap.control_title,
                gap.gap_severity,
                gap.implementation_status,
                gap.gap_description,
                "; ".join(gap.cross_framework_value),
                gap.remediation_guidance,
                gap.implementation_effort,
                gap.priority_score,
                gap.jira_issue_key or "",
                gap.servicenow_ticket_id or "",
            ]
        )

    path.write_text(output.getvalue(), encoding="utf-8")
    return path


def _export_markdown(report: GapAnalysisReport, path: Path) -> Path:
    """Export as Markdown report."""
    lines: list[str] = []

    lines.append(f"# Gap Analysis Report: {report.organization}")
    lines.append("")
    lines.append(f"**Date:** {report.analyzed_at.isoformat()}")
    lines.append(f"**Frameworks:** {', '.join(report.frameworks_analyzed)}")
    lines.append(f"**ControlBridge Version:** {report.controlbridge_version}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Total Controls Required | {report.total_controls_required} |")
    lines.append(f"| Controls in Inventory | {report.total_controls_in_inventory} |")
    lines.append(f"| Total Gaps | {report.total_gaps} |")
    lines.append(f"| Critical | {report.critical_gaps} |")
    lines.append(f"| High | {report.high_gaps} |")
    lines.append(f"| Medium | {report.medium_gaps} |")
    lines.append(f"| Low | {report.low_gaps} |")
    lines.append(f"| Coverage | {report.coverage_percentage}% |")
    lines.append("")

    lines.append("## Gaps (Prioritized)")
    lines.append("")
    lines.append("| # | Framework | Control | Severity | Status | Effort | Priority | Cross-FW Value |")
    lines.append("|---|---|---|---|---|---|---|---|")

    for i, gap in enumerate(report.gaps, 1):
        cross_fw = len(gap.cross_framework_value)
        lines.append(
            f"| {i} | {gap.framework} | {gap.control_id} — {gap.control_title} | "
            f"{gap.gap_severity} | {gap.implementation_status} | "
            f"{gap.implementation_effort} | {gap.priority_score} | "
            f"{cross_fw} frameworks |"
        )

    if report.efficiency_opportunities:
        lines.append("")
        lines.append("## Efficiency Opportunities")
        lines.append("")
        lines.append("Controls that satisfy 3+ framework requirements simultaneously:")
        lines.append("")
        lines.append("| Control | Title | Frameworks | Gaps Closed | Effort | Value Score |")
        lines.append("|---|---|---|---|---|---|")
        for opp in report.efficiency_opportunities:
            lines.append(
                f"| {opp.control_id} | {opp.control_title} | "
                f"{opp.framework_count} | {opp.total_gaps_closed} | "
                f"{opp.implementation_effort} | {opp.value_score} |"
            )

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _export_oscal_ar(report: GapAnalysisReport, path: Path) -> Path:
    """Export as OSCAL Assessment Results JSON.

    Maps ControlBridge gap report to a minimal OSCAL assessment-results structure.
    """
    from controlbridge_core.oscal.exporter import gap_report_to_oscal_ar

    oscal_ar = gap_report_to_oscal_ar(report)
    path.write_text(json.dumps(oscal_ar, indent=2, default=str), encoding="utf-8")
    return path
