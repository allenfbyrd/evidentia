"""OSCAL exporters for Evidentia models.

Maps Evidentia gap reports to OSCAL Assessment Results (AR) JSON.

OSCAL AR spec: https://pages.nist.gov/OSCAL/concepts/layer/assessment/assessment-results/
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from evidentia_core.models.gap import ControlGap, GapAnalysisReport


def gap_report_to_oscal_ar(report: GapAnalysisReport) -> dict[str, Any]:
    """Convert a Evidentia gap report to an OSCAL Assessment Results dict.

    Produces a minimal but valid OSCAL assessment-results structure with:
    - metadata (title, version, last-modified, parties)
    - results (one result containing findings, observations)
    - findings (one per gap, with severity and remediation)

    The output is a Python dict ready to be serialized as OSCAL JSON.
    """
    now_iso = _now_iso()
    ar_uuid = str(uuid4())
    result_uuid = str(uuid4())

    findings = [_gap_to_finding(gap) for gap in report.gaps]
    observations = [_gap_to_observation(gap) for gap in report.gaps]

    return {
        "assessment-results": {
            "uuid": ar_uuid,
            "metadata": {
                "title": f"Gap Analysis: {report.organization}",
                "last-modified": now_iso,
                "version": report.evidentia_version,
                "oscal-version": "1.1.2",
                "parties": [
                    {
                        "uuid": str(uuid4()),
                        "type": "organization",
                        "name": report.organization,
                    }
                ],
                "props": [
                    {
                        "name": "frameworks-analyzed",
                        "value": ", ".join(report.frameworks_analyzed),
                    },
                    {
                        "name": "coverage-percentage",
                        "value": str(report.coverage_percentage),
                    },
                    {
                        "name": "total-gaps",
                        "value": str(report.total_gaps),
                    },
                ],
            },
            "import-ap": {
                "href": "#assessment-plan-placeholder",
            },
            "results": [
                {
                    "uuid": result_uuid,
                    "title": "Evidentia Gap Analysis Result",
                    "description": (
                        f"Automated gap analysis of {report.organization} "
                        f"against {', '.join(report.frameworks_analyzed)}."
                    ),
                    "start": report.analyzed_at.isoformat(),
                    "end": report.analyzed_at.isoformat(),
                    "reviewed-controls": {
                        "control-selections": [
                            {
                                "description": (
                                    f"Controls from {fw}"
                                ),
                                "include-all": {},
                            }
                            for fw in report.frameworks_analyzed
                        ],
                    },
                    "observations": observations,
                    "findings": findings,
                }
            ],
        }
    }


def _gap_to_finding(gap: ControlGap) -> dict[str, Any]:
    """Map a ControlGap to an OSCAL finding."""
    severity_value = (
        gap.gap_severity.value if hasattr(gap.gap_severity, "value") else gap.gap_severity
    )
    return {
        "uuid": gap.id,
        "title": f"{gap.control_id}: {gap.control_title}",
        "description": gap.gap_description,
        "target": {
            "type": "objective-id",
            "target-id": gap.control_id,
            "status": {
                "state": "not-satisfied",
                "reason": gap.implementation_status,
            },
        },
        "props": [
            {"name": "framework", "value": gap.framework},
            {"name": "severity", "value": severity_value},
            {"name": "priority-score", "value": str(gap.priority_score)},
            {
                "name": "implementation-effort",
                "value": (
                    gap.implementation_effort.value
                    if hasattr(gap.implementation_effort, "value")
                    else gap.implementation_effort
                ),
            },
            {
                "name": "cross-framework-count",
                "value": str(len(gap.cross_framework_value)),
            },
        ],
        "remarks": gap.remediation_guidance,
    }


def _gap_to_observation(gap: ControlGap) -> dict[str, Any]:
    """Map a ControlGap to an OSCAL observation."""
    return {
        "uuid": str(uuid4()),
        "title": f"Observation: {gap.control_id}",
        "description": gap.gap_description,
        "methods": ["EXAMINE"],
        "types": ["finding"],
        "subjects": [
            {
                "subject-uuid": gap.id,
                "type": "component",
            }
        ],
        "collected": _now_iso(),
        "props": [
            {"name": "framework", "value": gap.framework},
            {"name": "control-id", "value": gap.control_id},
        ],
    }


def _now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    from datetime import UTC

    return datetime.now(UTC).isoformat()
