"""StorageBackend ABC (v0.8.0 P0.4)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator


class StorageBackend[T](ABC):
    """Abstract base class for pluggable storage backends.

    Generic over the record type ``T``. Implementations decide
    how to serialize ``T`` (typically JSON via Pydantic
    ``model_dump_json`` + ``model_validate_json``).

    The contract is intentionally minimal — get/list/save/delete.
    Implementations layer their own concerns (locking, retention,
    WORM semantics, etc.) on top.

    For WORM-specific backends with lock + lifecycle + legal-hold
    semantics, see :class:`evidentia_core.retention.worm.WORMBackend`
    instead. ``StorageBackend`` is for mutable-store use cases.

    Implementations should be thread-safe (Evidentia's REST API
    handlers may invoke methods concurrently).
    """

    @abstractmethod
    def save(self, *, record_id: str, record: T) -> None:
        """Persist a record under the given ID.

        If a record already exists under ``record_id``, it is
        overwritten. Implementations that need
        first-write-wins semantics should layer their own
        precondition check.

        Args:
            record_id: Unique identifier for the record. Must
                be a valid identifier under the backend's
                naming rules (typically alphanumeric + dash +
                underscore; no path separators).
            record: The record to save.

        Raises:
            ValueError: ``record_id`` violates the backend's
                naming rules.
            OSError: Backend-side IO failure (filesystem error,
                network error, etc.).
        """
        raise NotImplementedError

    @abstractmethod
    def load(self, record_id: str) -> T:
        """Load a record by ID.

        Args:
            record_id: The record's identifier.

        Returns:
            The record.

        Raises:
            KeyError: No record exists under ``record_id``.
            ValueError: The record exists but cannot be parsed
                (corrupt; schema mismatch; etc.).
        """
        raise NotImplementedError

    @abstractmethod
    def list_records(self) -> Iterator[str]:
        """Iterate over the IDs of all records in the backend.

        The order is implementation-defined; callers should not
        rely on lexicographic / chronological / any specific
        ordering.

        Yields:
            Record IDs (as strings).
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, record_id: str) -> None:
        """Delete a record by ID.

        Args:
            record_id: The record's identifier.

        Raises:
            KeyError: No record exists under ``record_id``.
        """
        raise NotImplementedError

    @abstractmethod
    def name(self) -> str:
        """Return a short human-readable name for this backend.

        Used in audit logs + admin UI. Examples:
        ``"filesystem"``, ``"s3"``, ``"ipfs"``,
        ``"federated-nfs"``.
        """
        raise NotImplementedError
