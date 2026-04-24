"""Per-finding and per-run provenance metadata (v0.7.0).

Implements checklist items H5 (collector metadata on every finding),
H10 (pagination continuation tokens preserved as evidence), and B5
(completeness attestation). Designed to satisfy:

- NIST SP 800-53 Rev 5 AU-2(d) / AU-3 / AU-6(4) — audit records must
  identify the user, process, resource, outcome, and timing of each
  evidence-generating action.
- ISAE 3402 / SSAE 18 AT-C 320 — auditors expect to trace every piece
  of evidence back to the collecting process, credential, and scope.
- FedRAMP CA-7 (Continuous Monitoring) — evidence collection scope
  must be documented and verifiable on demand.

Two public classes:

- :class:`CollectionContext` is embedded on every finding. Redundant
  across findings from the same run, but stays with each finding if
  the payload is split, filtered, or re-exported. Chain-of-custody
  survives transformations.
- :class:`CollectionManifest` is one-per-run, attached to the OSCAL AR
  document's ``metadata.props`` and written as an optional sibling
  file. Captures coverage, filters, record counts, and — crucially —
  explicit empty-set attestations so a reviewer can distinguish
  "no findings" from "collection never ran" or "collection crashed".
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import ulid
from pydantic import Field

from evidentia_core.models.common import EvidentiaModel, current_version, utc_now


def new_run_id() -> str:
    """Generate a fresh collection-run identifier as a ULID string.

    ULID (Universally Unique Lexicographically Sortable Identifier) is
    a 128-bit identifier with a 48-bit timestamp prefix. For audit logs
    that's the property that matters: run_ids sort chronologically by
    their value alone, so ``ORDER BY run_id`` in a log store returns
    collections in the order they started, even across clock-skew
    boundaries or rotation breaks where ``@timestamp`` gets messy.
    """
    return str(ulid.ULID())


class PaginationContext(EvidentiaModel):
    """Pagination state at the moment of finding retrieval.

    Preserving the pagination context lets an auditor prove collection
    completeness (checklist H10). If a collector returned 42 findings
    across 3 pages with no continuation token, the evidence trail shows
    the operator didn't silently stop at the first page.
    """

    page_size: int | None = Field(
        default=None,
        description="Number of records requested per API page",
    )
    page_number: int | None = Field(
        default=None,
        description="1-indexed position of the page this finding appeared in",
    )
    total_pages: int | None = Field(
        default=None,
        description=(
            "Total pages in the result set when computable from API response; "
            "None for cursor-based pagination where total is unknown"
        ),
    )
    continuation_token: str | None = Field(
        default=None,
        description=(
            "Opaque API continuation/next token if pagination was not "
            "fully drained at collection time; None on the final page"
        ),
    )
    is_complete: bool = Field(
        default=True,
        description=(
            "False if collection was truncated (rate limit, time budget "
            "exhausted, explicit limit). Forces CollectionManifest to "
            "mark the run 'incomplete' for auditor visibility."
        ),
    )


class CollectionContext(EvidentiaModel):
    """Per-finding provenance block — who/what/when/where/how.

    Every :class:`~evidentia_core.models.finding.SecurityFinding` in
    v0.7.0+ carries one of these. All six NIST AU-3 content requirements
    are expressed across the SecurityFinding + CollectionContext pair:

    =====================  ==========================================
    AU-3 requirement       Field(s)
    =====================  ==========================================
    Type of event           ``SecurityFinding.title``, ``severity``
    When event occurred     ``collected_at`` (microsecond UTC)
    Where event occurred    ``source_system_id`` + ``filter_applied``
    Source of event         ``collector_id`` + ``collector_version``
    Outcome of event        ``SecurityFinding.status``
    Identity                ``credential_identity``
    =====================  ==========================================
    """

    collector_id: str = Field(
        description=(
            "Stable collector identifier; used for filtering and SIEM "
            "alerting. Examples: 'aws-config', 'aws-security-hub', "
            "'aws-access-analyzer', 'github-branch-protection', "
            "'github-dependabot'."
        ),
    )
    collector_version: str = Field(
        description=(
            "Semver of the evidentia-collectors package that produced "
            "this finding. Resolved from importlib.metadata at collection "
            "time so it always matches the installed wheel."
        ),
    )
    run_id: str = Field(
        description=(
            "ULID of the collection run. Identical across every finding "
            "emitted by the same ``collect`` invocation; also equals the "
            "CollectionManifest.run_id so the two can be joined."
        ),
    )
    collected_at: datetime = Field(
        default_factory=utc_now,
        description=(
            "Exact UTC timestamp when the finding was retrieved from the "
            "source API. Auditor-grade precision (microseconds)."
        ),
    )
    credential_identity: str = Field(
        description=(
            "Authenticated principal that produced the finding. "
            "Format varies by source: AWS IAM ARN, GitHub app installation "
            "id, token subject, service-account email, etc. NOT the secret "
            "itself — the identity that the secret authenticates."
        ),
    )
    source_system_id: str = Field(
        description=(
            "Source system instance identifier. Examples: "
            "'aws-account:123456789012:us-east-1', "
            "'github:org/repo', 'github:enterprise/acme'."
        ),
    )
    filter_applied: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Filter / query parameters used during collection. Auditors "
            "use this to verify the reported scope. Empty dict means "
            "'no filter — full enumeration' (which is itself a claim)."
        ),
    )
    pagination_context: PaginationContext | None = Field(
        default=None,
        description=(
            "Pagination state if the source API requires it. None when "
            "the source API returns the full set in a single response."
        ),
    )
    evidentia_version: str = Field(
        default_factory=current_version,
        description=(
            "Version of evidentia-core orchestrating the collection. "
            "Paired with collector_version, lets auditors verify the "
            "exact release that produced the evidence."
        ),
    )


class CoverageCount(EvidentiaModel):
    """One resource-type's scan/match/collect counts within a run."""

    resource_type: str = Field(
        description=(
            "Source-system resource category. Examples: "
            "'aws-iam-role', 'aws-iam-user', 'github-dependabot-alert'."
        ),
    )
    scanned: int = Field(
        ge=0, description="Total resources enumerated (before filtering)"
    )
    matched_filter: int = Field(
        ge=0, description="Resources passing the collector's filter criteria"
    )
    collected: int = Field(
        ge=0,
        description=(
            "Findings actually produced from this resource type. May be < "
            "matched_filter if some matched resources yielded no findings."
        ),
    )


class CollectionManifest(EvidentiaModel):
    """Per-run manifest attesting to collection scope and completeness.

    Implements checklist item B5 (completeness attestation). One
    manifest per collection run is attached to the OSCAL Assessment
    Results document's ``metadata.props`` and optionally written as a
    sibling ``<output>.manifest.json`` for standalone inspection.

    The manifest is signed using the same signing pipeline as the AR
    itself. A verified manifest establishes:

    1. Which source systems were scanned.
    2. Which filters were applied.
    3. How many resources of each type were examined.
    4. Whether any categories were intentionally empty.
    5. Whether any errors truncated collection (``is_complete=False``).
    """

    run_id: str = Field(
        description=(
            "ULID matching CollectionContext.run_id on every finding "
            "produced by this run. Join key for findings↔manifest."
        ),
    )
    collector_id: str
    collector_version: str
    collection_started_at: datetime = Field(
        description="UTC timestamp when the collector began this run",
    )
    collection_finished_at: datetime | None = Field(
        default=None,
        description=(
            "UTC timestamp when the collector finished. None while "
            "still in progress."
        ),
    )
    source_system_ids: list[str] = Field(
        default_factory=list,
        description="All source_system_ids covered in this run",
    )
    filters_applied: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Run-level filters. Empty dict means 'no filter'."
        ),
    )
    coverage_counts: list[CoverageCount] = Field(
        default_factory=list,
        description="Per-resource-type scan/match/collect counts",
    )
    total_findings: int = Field(
        default=0, ge=0, description="Sum of findings emitted from this run"
    )
    is_complete: bool = Field(
        default=True,
        description=(
            "False if any collection error, truncation, or pagination "
            "abort occurred. Auditors treat incomplete runs as evidence "
            "gaps."
        ),
    )
    incomplete_reason: str | None = Field(
        default=None,
        description=(
            "Human-readable reason the run didn't complete. "
            "MUST be populated when ``is_complete=False``."
        ),
    )
    empty_categories: list[str] = Field(
        default_factory=list,
        description=(
            "Resource types explicitly scanned but yielding zero "
            "findings. Per checklist B5: an auditor cannot distinguish "
            "'no findings' (legitimate) from 'collector skipped' "
            "(evidence gap) without this explicit attestation."
        ),
    )
    warnings: list[str] = Field(
        default_factory=list,
        description=(
            "Non-fatal issues encountered during collection — rate-limit "
            "backoffs, skipped resources, blind-spot disclosures."
        ),
    )
    errors: list[str] = Field(
        default_factory=list,
        description=(
            "Fatal errors that caused specific resources to be skipped "
            "but didn't abort the run. Non-empty plus is_complete=True "
            "means 'partial success'."
        ),
    )
    evidentia_version: str = Field(
        default_factory=current_version,
        description="Version of evidentia-core that wrote this manifest",
    )
