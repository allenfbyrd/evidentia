"""Audit chain-of-custody primitives (v0.7.11 P0).

Brings retention-metadata + WORM-backend abstraction to Evidentia
so collected evidence can carry per-record retention policies that
satisfy regulator expectations (SEC Rule 17a-4 / FINRA Regulatory
Notice 17-21 for broker-dealer records, IRS 1.6001-1 for tax
records, Sarbanes-Oxley §404 for SOX evidence, OCC §12 CFR 30
Appendix B for bank records).

Public surface:

  - :class:`RetentionClassification` — canonical regulator-aligned
    record classes (sox / glba / hipaa / pci / gdpr / sec-17a-4 /
    finra-3110 / model-risk / generic)
  - :class:`RetentionMetadata` — per-record metadata: retention
    period + classification + lifecycle stage + lock-until-date
  - :class:`RetentionLifecycleStage` — lifecycle state machine
    (active → preserved → expired → purged)
  - :func:`is_locked` — predicate to check if a record is currently
    inside its mandatory retention window
  - :func:`generate_retention_report` — Markdown audit report
    showing the operator's retention posture across an evidence
    inventory

  - :class:`WORMBackend` — abstract base for Write-Once-Read-Many
    storage backends. Concrete S3 Object Lock + Azure Immutable
    Blob + GCS Bucket Lock implementations land in v0.7.12; this
    file documents the contract.
"""

from __future__ import annotations

from evidentia_core.retention.metadata import (
    RetentionClassification,
    RetentionLifecycleStage,
    RetentionMetadata,
    RetentionPolicy,
    generate_retention_report,
    is_locked,
    transition_lifecycle,
)
from evidentia_core.retention.worm import (
    LocalFilesystemWORM,
    WORMBackend,
    WORMBackendError,
)

__all__ = [
    "LocalFilesystemWORM",
    "RetentionClassification",
    "RetentionLifecycleStage",
    "RetentionMetadata",
    "RetentionPolicy",
    "WORMBackend",
    "WORMBackendError",
    "generate_retention_report",
    "is_locked",
    "transition_lifecycle",
]
