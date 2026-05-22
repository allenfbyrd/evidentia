"""SARIF 2.1.0 export for gap-analysis reports.

v0.10.0. Renders a :class:`GapAnalysisReport` as a SARIF 2.1.0 log so
gap analysis can run as a CI gate — surfaced in GitHub code scanning,
GitLab MR security dashboards, or any SARIF-aware viewer — and as a
standalone, schema-valid artifact.

Each :class:`ControlGap` becomes one SARIF ``result``; each distinct
control becomes one ``rule`` (reportingDescriptor). Results carry a
stable ``partialFingerprints`` entry so SARIF consumers can track a gap
across runs, and both a physical location (the control inventory file)
and a logical location (the control) so the results render in
file-oriented viewers without being misattributed to source code.
"""

from __future__ import annotations

import hashlib
from typing import Any

from evidentia_core.models.common import current_version
from evidentia_core.models.gap import GapAnalysisReport, GapSeverity

_SARIF_VERSION = "2.1.0"
_SARIF_SCHEMA = "https://json.schemastore.org/sarif-2.1.0.json"
_INFORMATION_URI = "https://github.com/Polycentric-Labs/evidentia"

# Evidentia GapSeverity -> SARIF result level. SARIF defines exactly
# error / warning / note / none; critical+high escalate to error.
_SEVERITY_TO_LEVEL: dict[GapSeverity, str] = {
    GapSeverity.CRITICAL: "error",
    GapSeverity.HIGH: "error",
    GapSeverity.MEDIUM: "warning",
    GapSeverity.LOW: "note",
    GapSeverity.INFORMATIONAL: "note",
}


def gap_report_to_sarif(report: GapAnalysisReport) -> dict[str, Any]:
    """Render a gap-analysis report as a SARIF 2.1.0 log dict.

    Returns a plain JSON-ready ``dict`` valid against the SARIF 2.1.0
    schema. The output is a standalone artifact; it is also consumable
    by GitHub code scanning and GitLab security dashboards.
    """
    rules: list[dict[str, Any]] = []
    rule_index: dict[str, int] = {}
    results: list[dict[str, Any]] = []

    # Compliance gaps are not bound to a source-code region; anchor the
    # physical location to the inventory file so viewers have somewhere
    # to attribute the result rather than guessing at source.
    location_uri = report.inventory_source or "evidentia-gap-analysis"

    for gap in report.gaps:
        rule_id = f"{gap.framework}/{gap.control_id}"
        if rule_id not in rule_index:
            rule_index[rule_id] = len(rules)
            rules.append(
                {
                    "id": rule_id,
                    "name": gap.control_id,
                    "shortDescription": {"text": gap.control_title},
                    "fullDescription": {"text": gap.control_description},
                    "properties": {
                        "framework": gap.framework,
                        "controlFamily": gap.control_family or "",
                    },
                }
            )

        message = gap.gap_description
        if gap.remediation_guidance:
            message = f"{message}\n\nRemediation: {gap.remediation_guidance}"

        # Stable across runs: a gap keyed by framework + control id is
        # "the same finding" even if its severity or wording changes.
        fingerprint = hashlib.sha256(rule_id.encode("utf-8")).hexdigest()[:16]

        results.append(
            {
                "ruleId": rule_id,
                "ruleIndex": rule_index[rule_id],
                "level": _SEVERITY_TO_LEVEL.get(gap.gap_severity, "warning"),
                "message": {"text": message},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": location_uri},
                        },
                        "logicalLocations": [
                            {"fullyQualifiedName": rule_id, "kind": "control"},
                        ],
                    }
                ],
                "partialFingerprints": {"evidentiaGapKey/v1": fingerprint},
                "properties": {
                    "gapSeverity": gap.gap_severity,
                    "implementationStatus": gap.implementation_status,
                    "implementationEffort": gap.implementation_effort,
                    "priorityScore": gap.priority_score,
                    "framework": gap.framework,
                    "controlId": gap.control_id,
                },
            }
        )

    return {
        "$schema": _SARIF_SCHEMA,
        "version": _SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "Evidentia",
                        "informationUri": _INFORMATION_URI,
                        "version": current_version(),
                        "rules": rules,
                    }
                },
                "results": results,
            }
        ],
    }
