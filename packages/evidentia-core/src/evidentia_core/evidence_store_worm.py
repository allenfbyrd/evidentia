"""Optional cloud-WORM mirror for the evidence-artifact store (v0.9.6 P2).

The primary :mod:`evidentia_core.evidence_store` enforces append-only
at the application layer (refuses to overwrite ``v<N>.json``). For
**regulator-grade** chain-of-custody (FedRAMP AU-9 / AU-11; HIPAA
§164.312(b); SOX §404), operators ALSO mirror each version to a
cloud-WORM backend (S3 Object Lock / Azure Immutable Blob Storage /
GCS Bucket Lock) that enforces immutability at the storage-platform
layer — not application-removable, not OS-removable for the lifetime
of the retention lock.

This module composes the v0.9.6 evidence_store with the v0.7.11
:class:`evidentia_core.retention.worm.WORMBackend` ABC:

  - Local-fs store remains the primary persistence + retrieval path
    (fast, free, no cloud round-trip on every read).
  - Cloud-WORM mirror is opt-in: operators call :func:`mirror_to_worm`
    alongside :func:`evidentia_core.evidence_store.save_evidence` (or
    in a post-save hook of their own design). The mirror is best-
    effort; failure is surfaced via an exception so callers decide
    fail-loud vs queue-for-retry.

Record-id format: ``<lineage_id>_v<version>``. Underscore-separated
to keep the record_id flat — :class:`evidentia_core.retention.worm.
LocalFilesystemWORM` and the cloud-backed equivalents use the
record_id as filename / object key, and a ``/`` separator would be
rejected by ``validate_within`` as a traversal attempt. The
underscore preserves the version-suffix readability without
introducing a path separator.

Payload format: canonical Pydantic JSON serialization (the same
bytes that :func:`save_evidence` writes locally). Mirroring is
literally "the bytes I just persisted locally, now also stored
remotely with retention metadata."

**Threat-model boundary**: this module does NOT itself provide
WORM enforcement — it COMPOSES with a backend that does. Misuse
case: an operator wires this against
:class:`LocalFilesystemWORM` thinking they get cloud-grade WORM;
:class:`LocalFilesystemWORM` is explicitly documented as
development/testing only. The :func:`mirror_to_worm` docstring
re-emphasizes the backend-selection responsibility.
"""

from __future__ import annotations

import logging

from evidentia_core.models.evidence import EvidenceArtifact
from evidentia_core.retention.metadata import RetentionMetadata
from evidentia_core.retention.worm import WORMBackend, WORMBackendError

logger = logging.getLogger(__name__)


def _worm_record_id(lineage_id: str, version: int) -> str:
    """Compose the WORM-backend record_id for one artifact version.

    Format: ``<lineage_id>_v<version>``. Flat (no path separator)
    so cloud-WORM backends + :class:`LocalFilesystemWORM` can use
    the value as filename / object key without path-traversal
    rejection. Stable + reversible (``split('_v')`` recovers the
    pair) so operator tools can correlate WORM objects back to
    local lineage entries.
    """
    return f"{lineage_id}_v{version}"


def mirror_to_worm(
    artifact: EvidenceArtifact,
    backend: WORMBackend,
    retention_metadata: RetentionMetadata,
) -> str:
    """Mirror one evidence artifact version to a cloud-WORM backend.

    Pre-conditions:

      - The artifact MUST have been persisted via :func:`evidence_
        store.save_evidence` first (this function only mirrors;
        does not validate the local-store invariant). Caller's
        responsibility.
      - The supplied ``backend`` should be a regulator-grade cloud
        backend (S3 Object Lock / Azure Immutable Blob / GCS
        Bucket Lock) for the WORM guarantee to be meaningful.
        :class:`evidentia_core.retention.worm.LocalFilesystemWORM`
        is acceptable for development + testing only.
      - ``retention_metadata`` is caller-supplied so operators set
        the retention period appropriate to the evidence
        classification (SOX 7yr / HIPAA 6yr / FedRAMP 5yr / etc.).

    The mirror is **single-version**: each call writes exactly one
    record. Mirroring an entire lineage is the caller's job (iterate
    :func:`evidence_store.list_lineage` + call this per version).

    Args:
        artifact: The artifact version to mirror.
        backend: A concrete :class:`WORMBackend` subclass instance.
        retention_metadata: The retention policy to attach.

    Returns:
        The cloud-WORM record_id (``<lineage>_v<version>``) so
        callers can persist the reference for later audit-trail
        reconstruction.

    Raises:
        WORMBackendError: If the backend rejects the put (most
            commonly: record_id already exists — would indicate
            the lineage version was previously mirrored).
    """
    record_id = _worm_record_id(artifact.effective_lineage_id, artifact.version)
    payload = artifact.model_dump_json(indent=2).encode("utf-8")
    backend.put(record_id, payload, retention_metadata)
    logger.debug(
        "Mirrored evidence to WORM: %s (size=%d bytes)",
        record_id,
        len(payload),
    )
    return record_id


def fetch_from_worm(
    lineage_id: str,
    version: int,
    backend: WORMBackend,
) -> EvidenceArtifact:
    """Read one mirrored artifact version back from a WORM backend.

    Useful for reconciliation: verify the local-store version
    matches the WORM-mirrored version (tamper detection via
    byte-level diff) or restore a lineage entry from the WORM
    backend after a local-store loss.

    Args:
        lineage_id: The lineage identifier (UUID string).
        version: Sequence number within the chain (>= 1).
        backend: A concrete :class:`WORMBackend` subclass instance.

    Returns:
        The reconstructed :class:`EvidenceArtifact`.

    Raises:
        WORMBackendError: If the record is missing from the backend.
        pydantic.ValidationError: If the persisted bytes don't
            deserialize as a valid :class:`EvidenceArtifact` — a
            tamper indicator that the audit trail should surface.
    """
    record_id = _worm_record_id(lineage_id, version)
    payload = backend.get(record_id)
    return EvidenceArtifact.model_validate_json(payload.decode("utf-8"))


__all__ = [
    "WORMBackendError",
    "fetch_from_worm",
    "mirror_to_worm",
]
