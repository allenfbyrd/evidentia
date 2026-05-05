"""MarketplaceProvider plugin contract (v0.8.0 P0.4).

Pluggable OSCAL catalog providers. The default behavior is
unchanged: Evidentia ships 89 bundled catalogs in
``evidentia_core.catalogs`` (NIST 800-53 / OWASP / CIS / SOC 2 /
FFIEC IT Handbook / OCC SR 11-7 / etc.). The new plugin contract
lets out-of-tree authors ship custom catalog providers that pull
from local directories, community CDN mirrors, IBM
compliance-trestle registries, or organization-private
catalog hosts.

OSS reference implementation:
``LocalDirectoryMarketplaceProvider`` (filesystem-based;
loads OSCAL catalogs from a local directory tree).

Out-of-tree implementations could provide:
- Community CDN mirror (HTTPS-backed; Sigstore-verified
  catalog manifests)
- IBM compliance-trestle registry passthrough
- Organization-private catalog registries (gated by
  AuthProvider)
- Local-language catalog sets (e.g., a community-maintained
  Spanish-language NIST 800-53 translation)
"""

from __future__ import annotations

from evidentia_core.plugins.marketplace._base import (
    CatalogManifest,
    MarketplaceProvider,
)
from evidentia_core.plugins.marketplace.local_directory import (
    LocalDirectoryMarketplaceProvider,
)

__all__ = [
    "CatalogManifest",
    "LocalDirectoryMarketplaceProvider",
    "MarketplaceProvider",
]
