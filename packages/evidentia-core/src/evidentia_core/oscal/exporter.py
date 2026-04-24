"""OSCAL exporters for Evidentia models.

Maps Evidentia gap reports to OSCAL Assessment Results (AR) JSON.

OSCAL AR spec: https://pages.nist.gov/OSCAL/concepts/layer/assessment/assessment-results/

v0.7.0: optional evidence embedding. When a list of
:class:`SecurityFinding` objects is provided alongside the gap report,
each finding is:

1. Added to ``back-matter.resources[]`` as a standalone OSCAL resource
   with its canonical JSON base64-encoded in ``base64.value`` and a
   SHA-256 hash in ``rlinks[].hashes[]`` (both OSCAL-standard fields).
2. Cross-referenced from each matching observation via
   ``relevant-evidence[].href: "#<resource-uuid>"``. A finding matches
   an observation when they share a control ID.

The digest is computed from the finding's canonical JSON serialization
(``model_dump(mode="json")`` → ``json.dumps(sort_keys=True, separators=(",", ":"))``)
so :mod:`evidentia_core.oscal.verify` can recompute it deterministically
for a chain-of-custody integrity check.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from evidentia_core.models.gap import ControlGap, GapAnalysisReport
from evidentia_core.oscal.digest import digest_bytes, format_digest

if TYPE_CHECKING:
    from evidentia_core.models.finding import SecurityFinding


# v0.7.0 namespace for Evidentia-specific OSCAL prop extensions. Downstream
# tools that don't recognize this namespace will ignore the props (per
# OSCAL's extension rules) rather than rejecting the document.
EVIDENTIA_OSCAL_NS = "https://evidentia.dev/oscal"


def gap_report_to_oscal_ar(
    report: GapAnalysisReport,
    *,
    findings: list[SecurityFinding] | None = None,
    blind_spots: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Convert a Evidentia gap report to an OSCAL Assessment Results dict.

    Produces a minimal but valid OSCAL assessment-results structure with:

    - metadata (title, version, last-modified, parties)
    - results (one result containing findings, observations)
    - findings (one per gap, with severity and remediation)
    - back-matter.resources (v0.7.0: one per :class:`SecurityFinding` with
      SHA-256 digest; only emitted when ``findings`` or ``blind_spots`` is
      non-empty)

    Parameters
    ----------
    report:
        The gap analysis result to export.
    findings:
        Optional collector output. When provided, each finding becomes
        a hashed OSCAL back-matter resource cross-referenced from
        observations sharing a control ID. Enables end-to-end evidence
        chain of custody: tampering with an embedded finding changes
        its hash and fails :func:`evidentia_core.oscal.verify.verify_ar_file`.
    blind_spots:
        Optional list of collector blind-spot disclosures (v0.7.0).
        Each entry must have ``id``, ``title``, and ``description`` keys
        (matching :data:`evidentia_collectors.aws.access_analyzer.BLIND_SPOTS`
        shape). Each becomes a back-matter resource with
        ``class="blind-spot"`` and Evidentia-namespaced props so auditors
        see the explicit limits of automated coverage inline alongside
        the AR. Auditor expectation: every collector documents what it
        does NOT cover, surfaced in the same artifact as the findings.

    The output is a Python dict ready to be serialized as OSCAL JSON.
    """
    now_iso = _now_iso()
    ar_uuid = str(uuid4())
    result_uuid = str(uuid4())

    # v0.7.0: build evidence resources first so observations can reference
    # them by UUID. One resource per finding; indexed by control_id for
    # cross-referencing below.
    resource_by_control: dict[str, list[dict[str, Any]]] = {}
    back_matter_resources: list[dict[str, Any]] = []
    if findings:
        for finding in findings:
            resource = _finding_to_oscal_resource(finding)
            back_matter_resources.append(resource)
            for control_id in finding.control_ids:
                resource_by_control.setdefault(control_id, []).append(resource)

    # v0.7.0: blind-spot disclosures. Standalone back-matter resources
    # (no observation cross-references — they're scope-limit declarations,
    # not findings). Auditor-grade transparency: every collector documents
    # what it does NOT cover, surfaced in the same artifact as the findings.
    if blind_spots:
        for bs in blind_spots:
            back_matter_resources.append(_blind_spot_to_oscal_resource(bs))

    findings_output = [_gap_to_finding(gap) for gap in report.gaps]
    observations = [_gap_to_observation(gap, resource_by_control) for gap in report.gaps]

    ar_doc: dict[str, Any] = {
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
                                "description": (f"Controls from {fw}"),
                                "include-all": {},
                            }
                            for fw in report.frameworks_analyzed
                        ],
                    },
                    "observations": observations,
                    "findings": findings_output,
                }
            ],
        }
    }

    # OSCAL 1.1.2 allows an optional top-level ``back-matter`` alongside
    # ``results``. Only emit it when there are resources to attach —
    # empty arrays are valid OSCAL but add noise to the diff.
    if back_matter_resources:
        ar_doc["assessment-results"]["back-matter"] = {
            "resources": back_matter_resources,
        }

    return ar_doc


def _blind_spot_to_oscal_resource(bs: dict[str, str]) -> dict[str, Any]:
    """Convert a collector blind-spot disclosure to an OSCAL back-matter resource.

    Blind-spots are scope-limit declarations, not findings. They tell
    auditors what the automated collector explicitly does NOT cover, so
    that the gap-analysis result is honest about its boundaries.

    Required keys in ``bs``: ``id`` (stable identifier),
    ``title`` (human-readable summary), ``description`` (what's not
    covered + recommended supplementary control). Matches the shape of
    ``evidentia_collectors.aws.access_analyzer.BLIND_SPOTS``.
    """
    return {
        "uuid": str(uuid4()),
        "title": bs["title"],
        "description": bs["description"],
        "props": [
            {
                "name": "blind-spot-id",
                "ns": EVIDENTIA_OSCAL_NS,
                "value": bs["id"],
                "class": "blind-spot",
            },
        ],
    }


def _finding_to_oscal_resource(finding: SecurityFinding) -> dict[str, Any]:
    """Convert a SecurityFinding to an OSCAL back-matter resource.

    The resource embeds:

    - ``base64.value`` — canonical JSON of the finding, base64-encoded.
      Makes the AR self-contained: no external files needed to verify.
    - ``rlinks[].hashes[]`` — SHA-256 of the *decoded* base64 payload.
      Standard OSCAL integrity mechanism.
    - ``props[]`` — Evidentia-namespaced metadata (source system,
      severity) so downstream filters can triage without decoding.
    """
    # Canonical JSON → same serialization the verifier re-computes from.
    canonical = _finding_canonical_json(finding)
    hex_digest = digest_bytes(canonical)

    # OSCAL resource UUID must be stable per-finding so reruns produce
    # reviewable diffs. Derive from finding.id (already a UUID v4).
    resource_uuid = finding.id

    severity_value = finding.severity.value if hasattr(finding.severity, "value") else str(finding.severity)

    return {
        "uuid": resource_uuid,
        "title": finding.title,
        "description": finding.description,
        "props": [
            {
                "name": "source-system",
                "ns": EVIDENTIA_OSCAL_NS,
                "value": finding.source_system,
            },
            {
                "name": "severity",
                "ns": EVIDENTIA_OSCAL_NS,
                "value": severity_value,
            },
            {
                "name": "evidence-digest",
                "ns": EVIDENTIA_OSCAL_NS,
                "value": format_digest(hex_digest),
                "class": "integrity",
            },
        ],
        # OSCAL rlinks[] with hashes[] is the standards-track integrity
        # mechanism. Tools that don't speak the Evidentia ns above will
        # still find the hash here. ``href: "#<uuid>"`` is a self-reference.
        "rlinks": [
            {
                "href": f"#{resource_uuid}",
                "media-type": "application/json",
                "hashes": [
                    {
                        "algorithm": "SHA-256",
                        "value": hex_digest,
                    }
                ],
            }
        ],
        "base64": {
            "filename": f"{finding.id}.json",
            "media-type": "application/json",
            "value": base64.b64encode(canonical).decode("ascii"),
        },
    }


def _finding_canonical_json(finding: SecurityFinding) -> bytes:
    """Serialize a SecurityFinding to deterministic canonical JSON bytes.

    Identical to :func:`evidentia_core.oscal.digest.digest_model`'s input
    transform — same sort_keys + separators. Verifier reuses this same
    function, so both sides of the hash agree bit-for-bit.
    """
    payload = finding.model_dump(mode="json")
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _gap_to_finding(gap: ControlGap) -> dict[str, Any]:
    """Map a ControlGap to an OSCAL finding."""
    severity_value = gap.gap_severity.value if hasattr(gap.gap_severity, "value") else gap.gap_severity
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


def _gap_to_observation(
    gap: ControlGap,
    resource_by_control: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Map a ControlGap to an OSCAL observation.

    When ``resource_by_control`` is provided (v0.7.0+), any evidence
    resources matching this gap's control ID are attached as
    ``relevant-evidence[]`` cross-references. The observation's ``methods``
    becomes ``["TEST"]`` instead of ``["EXAMINE"]`` when evidence is
    attached, since automated findings are closer to a test result
    than a manual examination.
    """
    observation: dict[str, Any] = {
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

    if resource_by_control:
        linked_resources = resource_by_control.get(gap.control_id, [])
        if linked_resources:
            observation["methods"] = ["TEST"]
            observation["relevant-evidence"] = [
                {
                    "href": f"#{resource['uuid']}",
                    "description": resource["title"],
                }
                for resource in linked_resources
            ]

    return observation


def _now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    from datetime import UTC

    return datetime.now(UTC).isoformat()
