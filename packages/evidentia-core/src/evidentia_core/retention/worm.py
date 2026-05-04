"""WORM (Write-Once-Read-Many) backend abstraction (v0.7.11 P0).

Defines the contract that concrete WORM-storage backends (S3
Object Lock, Azure Immutable Blob Storage, GCS Bucket Lock)
implement. Concrete cloud implementations land in v0.7.12 with
their respective extras (`evidentia[worm-s3]` /
`evidentia[worm-azure]` / `evidentia[worm-gcs]`).

This file ships the abstract base class + a reference local-
filesystem implementation suitable for development + testing.
The local-filesystem implementation does NOT enforce hardware-
level WORM semantics — it only enforces them via the metadata
+ application-level checks. Real cloud-backed WORM semantics
(S3 Object Lock retention modes, Azure Immutable Blob policies,
GCS bucket retention locks) are required for regulator-grade
chain-of-custody.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path

from evidentia_core.retention.metadata import (
    RetentionMetadata,
    is_locked,
)
from evidentia_core.security.paths import (
    PathTraversalError,
    validate_within,
)


class WORMBackendError(RuntimeError):
    """Raised when a WORM-backend operation violates the WORM contract."""


class WORMBackend(ABC):
    """Abstract base for Write-Once-Read-Many storage backends.

    Concrete subclasses (in v0.7.12: ``S3ObjectLockWORM``,
    ``AzureImmutableBlobWORM``, ``GCSBucketLockWORM``) provide the
    cloud-side enforcement. The contract:

      - :meth:`put` writes a record + retention metadata. Once
        stored, the record is immutable until ``lock_until``.
      - :meth:`get` reads the record by ID.
      - :meth:`get_metadata` returns the retention metadata.
      - :meth:`delete` is allowed ONLY if the retention metadata
        indicates the record is purgeable (lifecycle EXPIRED + not
        under legal hold). On any violation, raises
        :class:`WORMBackendError`.
      - :meth:`extend_retention` extends ``lock_until`` (operator
        deliberately holds the record longer; legal-hold pattern).
        Cannot SHORTEN retention — that would violate WORM.

    All subclasses MUST raise :class:`WORMBackendError` on any
    contract violation rather than silently accepting non-WORM
    operations.
    """

    @abstractmethod
    def put(
        self,
        record_id: str,
        payload: bytes,
        metadata: RetentionMetadata,
    ) -> None:
        """Write a new record + its retention metadata."""
        ...

    @abstractmethod
    def get(self, record_id: str) -> bytes:
        """Read a record by ID. Raises if missing."""
        ...

    @abstractmethod
    def get_metadata(self, record_id: str) -> RetentionMetadata:
        """Read a record's retention metadata."""
        ...

    @abstractmethod
    def delete(self, record_id: str, today: date | None = None) -> None:
        """Delete a record IF retention permits.

        Raises :class:`WORMBackendError` when:
          - The record is still inside its lock window
          - The record is under legal hold
          - The record's lifecycle stage is not EXPIRED
        """
        ...

    @abstractmethod
    def extend_retention(
        self, record_id: str, new_lock_until: date
    ) -> RetentionMetadata:
        """Extend the lock-until date (cannot shorten).

        Raises :class:`WORMBackendError` if ``new_lock_until`` is
        earlier than the current ``lock_until``.
        """
        ...


class LocalFilesystemWORM(WORMBackend):
    """Reference local-filesystem WORM implementation.

    Stores records as ``<root>/<record_id>.bin`` with a sibling
    ``<record_id>.meta.json`` for retention metadata. Enforces
    WORM semantics via application-level checks against the
    metadata; the underlying filesystem provides NO hardware-level
    WORM guarantee. Suitable for development + testing; for
    regulator-grade chain-of-custody, operators must use a
    cloud-backed WORM backend (S3 Object Lock / Azure Immutable
    Blob / GCS Bucket Lock).

    Use:
      ```
      backend = LocalFilesystemWORM(root="/var/evidentia/worm")
      backend.put(record_id, payload, metadata)
      ```
    """

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root).expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _record_path(self, record_id: str) -> tuple[Path, Path]:
        """Return ``(payload_path, meta_path)`` validated within root."""
        candidate_payload = self._root / f"{record_id}.bin"
        candidate_meta = self._root / f"{record_id}.meta.json"
        try:
            payload_path = validate_within(candidate_payload, self._root)
            meta_path = validate_within(candidate_meta, self._root)
        except PathTraversalError as e:
            raise WORMBackendError(
                f"record_id {record_id!r} would escape store root"
            ) from e
        return payload_path, meta_path

    def put(
        self,
        record_id: str,
        payload: bytes,
        metadata: RetentionMetadata,
    ) -> None:
        payload_path, meta_path = self._record_path(record_id)
        if payload_path.exists():
            raise WORMBackendError(
                f"record {record_id!r} already exists; WORM forbids overwrite"
            )
        # Atomic write of payload + metadata
        tmp_payload = payload_path.with_suffix(".bin.tmp")
        tmp_payload.write_bytes(payload)
        tmp_meta = meta_path.with_suffix(".meta.tmp")
        tmp_meta.write_text(metadata.model_dump_json(indent=2), encoding="utf-8")
        # os.replace is atomic on both POSIX and Windows
        os.replace(tmp_payload, payload_path)
        os.replace(tmp_meta, meta_path)

    def get(self, record_id: str) -> bytes:
        payload_path, _ = self._record_path(record_id)
        if not payload_path.exists():
            raise WORMBackendError(f"record {record_id!r} not found")
        return payload_path.read_bytes()

    def get_metadata(self, record_id: str) -> RetentionMetadata:
        _, meta_path = self._record_path(record_id)
        if not meta_path.exists():
            raise WORMBackendError(
                f"metadata for record {record_id!r} not found"
            )
        return RetentionMetadata.model_validate_json(
            meta_path.read_text(encoding="utf-8")
        )

    def delete(self, record_id: str, today: date | None = None) -> None:
        from evidentia_core.retention.metadata import RetentionLifecycleStage

        payload_path, meta_path = self._record_path(record_id)
        if not payload_path.exists() or not meta_path.exists():
            raise WORMBackendError(f"record {record_id!r} not found")
        metadata = self.get_metadata(record_id)
        if metadata.legal_hold:
            raise WORMBackendError(
                f"record {record_id!r} is under legal hold; cannot delete"
            )
        if is_locked(metadata, today=today):
            raise WORMBackendError(
                f"record {record_id!r} is still inside its retention "
                f"window (lock_until={metadata.lock_until}); cannot delete"
            )
        if metadata.lifecycle_stage != RetentionLifecycleStage.EXPIRED.value:
            raise WORMBackendError(
                f"record {record_id!r} lifecycle is "
                f"{metadata.lifecycle_stage}; only EXPIRED records can "
                f"be deleted"
            )
        payload_path.unlink()
        meta_path.unlink()

    def extend_retention(
        self, record_id: str, new_lock_until: date
    ) -> RetentionMetadata:
        metadata = self.get_metadata(record_id)
        if metadata.lock_until is not None and new_lock_until < metadata.lock_until:
            raise WORMBackendError(
                f"WORM forbids shortening retention: current lock_until="
                f"{metadata.lock_until}, attempted={new_lock_until}"
            )
        from evidentia_core.models.common import utc_now

        new_metadata = metadata.model_copy(
            update={
                "lock_until": new_lock_until,
                "updated_at": utc_now(),
            }
        )
        _, meta_path = self._record_path(record_id)
        # Overwriting metadata is permitted (it's tracking only, not
        # the underlying record). Atomic write.
        tmp = meta_path.with_suffix(".meta.tmp")
        tmp.write_text(
            new_metadata.model_dump_json(indent=2), encoding="utf-8"
        )
        os.replace(tmp, meta_path)
        return new_metadata

    def root(self) -> Path:
        """Return the resolved root directory (for inspection / tests)."""
        return self._root

    def __repr__(self) -> str:
        return f"LocalFilesystemWORM(root={self._root!r})"
