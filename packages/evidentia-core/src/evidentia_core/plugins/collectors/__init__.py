"""SaaS-collector plugin contract (v0.8.0 P0.4 + M-4 closure).

Common scaffolding for SaaS API collectors that follow the
v0.7.9 vendor-risk pattern (Vanta / Drata / BitSight /
SecurityScorecard). Closes the v0.7.13-cycle M-4 follow-up:

  > A shared BaseSaaSCollector ABC consolidating the
  > _ensure_client / _get / pagination / error-translation
  > scaffolding would reduce LOC and make future SaaS-collector
  > additions mechanical.

The v0.7.9 collectors copy-pasted ~150 LOC each of identical
scaffolding (token-stripping, httpx.Client lifecycle, GET +
auth/connection/query error normalization). This contract
extracts the common parts into a base class; subclasses
provide:

- Their COLLECTOR_ID
- Their default base URL
- Their token env-var name (for error messages)
- Their subclass-specific exception classes (typed inheritance
  from the generic SaaSCollectorError hierarchy)

Subclasses do NOT need to override _ensure_client or _get —
the base class handles those.

Out-of-tree authors writing custom SaaS collectors can inherit
from BaseSaaSCollector instead of copy-pasting the v0.7.9
scaffolding.
"""

from __future__ import annotations

from evidentia_core.plugins.collectors._base import (
    BaseSaaSCollector,
    SaaSAuthError,
    SaaSCollectorError,
    SaaSConnectionError,
    SaaSQueryError,
)

__all__ = [
    "BaseSaaSCollector",
    "SaaSAuthError",
    "SaaSCollectorError",
    "SaaSConnectionError",
    "SaaSQueryError",
]
