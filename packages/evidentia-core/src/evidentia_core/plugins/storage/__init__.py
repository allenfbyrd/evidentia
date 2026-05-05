"""StorageBackend plugin contract (v0.8.0 P0.4).

Pluggable persistence for gap reports, collector findings, and
audit-relevant records.

The default behavior is unchanged: Evidentia uses filesystem-
based stores (``gap_store``, ``vendor_store``, ``model_risk_store``,
etc.) that write JSON files under platformdirs-resolved
locations. The new plugin contract lets out-of-tree authors
ship custom backends (S3, IPFS, cloud-WORM, federated NFS,
etc.) that conform to the same get/list/save/delete interface.

OSS reference implementation: ``FilesystemStorageBackend``
(filesystem-based; closest match to the existing in-tree
stores; intended as a copy-and-modify starting point for
custom backends).

Note: the v0.7.11 ``WORMBackend`` ABC (in
``evidentia_core.retention.worm``) is a SEPARATE contract for
WORM-specific semantics (lock + lifecycle + legal hold). The
``StorageBackend`` contract here is a more general
mutable-store interface without WORM constraints.
"""

from __future__ import annotations

from evidentia_core.plugins.storage._base import StorageBackend
from evidentia_core.plugins.storage.file_backend import (
    FilesystemStorageBackend,
)

__all__ = [
    "FilesystemStorageBackend",
    "StorageBackend",
]
