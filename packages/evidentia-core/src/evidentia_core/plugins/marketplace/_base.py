"""MarketplaceProvider ABC (v0.8.0 P0.4)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CatalogManifest:
    """Lightweight metadata about a catalog available from a provider.

    Designed to be cheap to enumerate (no full-catalog-content
    fetch required). Callers ``list_catalogs()`` first to see
    what's available, then ``fetch_catalog()`` to pull specific
    ones.

    Attributes:
        catalog_id: Stable identifier (e.g., ``"nist-800-53-rev5-moderate"``).
            Conventional format: lowercase + dash-separated.
        title: Human-readable name (e.g., ``"NIST SP 800-53 Rev 5 (Moderate baseline)"``).
        version: Catalog version / publication date.
        provider: Short identifier of the provider serving this
            manifest (e.g., ``"local-directory"`` or
            ``"community-cdn"``).
        license: SPDX license identifier or descriptive string
            (e.g., ``"public-domain"`` or ``"CC-BY-4.0"``).
        size_bytes: Approximate size of the full catalog JSON
            in bytes; ``None`` if unknown without fetch.
        provider_metadata: Provider-specific extra metadata (e.g.,
            URL, signing keys, last-modified timestamp). Opaque
            to consumers; provider-defined.
    """

    catalog_id: str
    title: str
    version: str
    provider: str
    license: str | None = None
    size_bytes: int | None = None
    provider_metadata: dict[str, Any] | None = None


class MarketplaceProvider(ABC):
    """Abstract base class for OSCAL catalog providers.

    Implementations expose two operations:

    1. :meth:`list_catalogs` — enumerate what's available
       (returns lightweight manifests; cheap to call)
    2. :meth:`fetch_catalog` — pull full catalog content by ID
       (expensive; may involve network IO)

    Implementations should be thread-safe (multiple consumers
    may call concurrently).

    Implementations should NOT mutate Evidentia's bundled
    catalogs. The bundled set is shipped read-only in the
    package wheel.
    """

    @abstractmethod
    def list_catalogs(self) -> Iterator[CatalogManifest]:
        """Iterate over the catalogs this provider offers.

        Yields:
            One :class:`CatalogManifest` per available catalog.

        The order is implementation-defined; callers should
        not rely on lexicographic / version / any specific
        ordering.

        Implementations SHOULD make this cheap to call (no
        full-content fetch); a consumer typically iterates
        all manifests once at startup to populate a UI.
        """
        raise NotImplementedError

    @abstractmethod
    def fetch_catalog(self, catalog_id: str) -> dict[str, Any]:
        """Fetch the full OSCAL catalog content by ID.

        Args:
            catalog_id: Identifier from a previous
                :meth:`list_catalogs` manifest.

        Returns:
            The full OSCAL catalog as a parsed JSON dict.
            Conformant to OSCAL Catalog Model schema.

        Raises:
            KeyError: No catalog matches ``catalog_id``.
            ValueError: The catalog content cannot be parsed
                (corrupt; schema mismatch).
        """
        raise NotImplementedError

    @abstractmethod
    def name(self) -> str:
        """Return a short human-readable name for this provider.

        Used in audit logs + admin UI. Examples:
        ``"local-directory"``, ``"community-cdn"``,
        ``"trestle-registry"``.
        """
        raise NotImplementedError
