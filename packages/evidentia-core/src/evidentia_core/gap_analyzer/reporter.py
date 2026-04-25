"""Gap analysis report output formatters.

Supports: JSON, CSV, Markdown, OSCAL Assessment Results.

v0.7.0: the ``oscal-ar`` format optionally accepts a list of
:class:`SecurityFinding` objects (``findings=``) to embed as hashed
OSCAL resources, and a ``gpg_key_id`` to produce a detached ASCII-armored
signature alongside the JSON. See :mod:`evidentia_core.oscal.verify`
for the corresponding integrity checks.
"""

from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from evidentia_core.models.gap import GapAnalysisReport

if TYPE_CHECKING:
    from evidentia_core.models.finding import SecurityFinding

OutputFormat = Literal["json", "csv", "markdown", "oscal-ar"]


def export_report(
    report: GapAnalysisReport,
    output_path: str | Path,
    format: OutputFormat = "json",
    *,
    findings: list[SecurityFinding] | None = None,
    gpg_key_id: str | None = None,
    gnupghome: str | Path | None = None,
    sign_with_sigstore: bool = False,
    sigstore_bundle_path: str | Path | None = None,
    sigstore_identity_token: str | None = None,
) -> Path:
    """Export a gap analysis report in the specified format.

    Parameters
    ----------
    report:
        The gap analysis to export.
    output_path:
        Destination file path.
    format:
        One of ``json``, ``csv``, ``markdown``, ``oscal-ar``.
    findings:
        Optional :class:`SecurityFinding` list for the ``oscal-ar`` format.
        Each finding becomes a hashed OSCAL back-matter resource and is
        cross-referenced from observations that share a control ID.
        Ignored by non-OSCAL formats.
    gpg_key_id:
        Optional GPG key identifier. When supplied alongside ``format="oscal-ar"``,
        the AR JSON is signed with a detached ASCII-armored signature
        written to ``<output_path>.asc``. Ignored by non-OSCAL formats.
    gnupghome:
        Optional ``GNUPGHOME`` override passed to the GPG subprocess.
    sign_with_sigstore:
        When True (and ``format="oscal-ar"``), produces a Sigstore/Rekor
        keyless-signing bundle alongside the AR JSON. Defaults to
        ``<output_path>.sigstore.json`` unless ``sigstore_bundle_path``
        is supplied. Refused in air-gap mode.
    sigstore_bundle_path:
        Custom Sigstore bundle output path. Defaults to
        ``<output_path>.sigstore.json``. Only used with
        ``sign_with_sigstore=True``.
    sigstore_identity_token:
        Optional explicit OIDC token for Sigstore signing. When omitted,
        sigstore-python's ``detect_credential()`` resolves it from the
        ambient GitHub Actions / GCP / AWS environment.
    """
    path = Path(output_path)

    if format == "json":
        return _export_json(report, path)
    if format == "csv":
        return _export_csv(report, path)
    if format == "markdown":
        return _export_markdown(report, path)
    if format == "oscal-ar":
        return _export_oscal_ar(
            report,
            path,
            findings=findings,
            gpg_key_id=gpg_key_id,
            gnupghome=gnupghome,
            sign_with_sigstore=sign_with_sigstore,
            sigstore_bundle_path=sigstore_bundle_path,
            sigstore_identity_token=sigstore_identity_token,
        )

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
    lines.append(f"**Evidentia Version:** {report.evidentia_version}")
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


def _export_oscal_ar(
    report: GapAnalysisReport,
    path: Path,
    *,
    findings: list[SecurityFinding] | None = None,
    gpg_key_id: str | None = None,
    gnupghome: str | Path | None = None,
    sign_with_sigstore: bool = False,
    sigstore_bundle_path: str | Path | None = None,
    sigstore_identity_token: str | None = None,
) -> Path:
    """Export as OSCAL Assessment Results JSON.

    Maps Evidentia gap report to a minimal OSCAL assessment-results structure.

    v0.7.0: when ``findings`` is provided, each is embedded in the AR's
    ``back-matter.resources[]`` with a SHA-256 digest. When
    ``gpg_key_id`` is provided, a detached ASCII-armored signature is
    written to ``<path>.asc``. When ``sign_with_sigstore=True``, a
    Sigstore bundle is also written to ``<path>.sigstore.json``. GPG
    and Sigstore are independent — both can coexist for defence-in-depth.
    """
    from evidentia_core.oscal.exporter import gap_report_to_oscal_ar

    oscal_ar = gap_report_to_oscal_ar(report, findings=findings)
    path.write_text(json.dumps(oscal_ar, indent=2, default=str), encoding="utf-8")

    if gpg_key_id:
        from evidentia_core.oscal.signing import sign_file

        sign_file(path, key_id=gpg_key_id, gnupghome=gnupghome)

    if sign_with_sigstore:
        from evidentia_core.oscal.sigstore import sign_file as sigstore_sign

        sigstore_sign(
            path,
            bundle_path=sigstore_bundle_path,
            identity_token=sigstore_identity_token,
        )

    return path
