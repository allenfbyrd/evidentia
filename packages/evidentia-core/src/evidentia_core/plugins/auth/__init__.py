"""AuthProvider plugin contract (v0.8.0 P0.4).

Pluggable authentication backends for ``evidentia serve``. The
default behavior is unchanged (no auth; localhost-bound by
default per the v0.4.0 design). Operators that need
authentication wire up an ``AuthProvider`` implementation.

OSS reference implementation: ``LocalTokenAuthProvider``
(token-file-based; reads a token from a file specified at
runtime; matches a single bearer token in incoming requests).

Out-of-tree implementations could provide OAuth, mTLS,
session-cookie, or custom auth flows.
"""

from __future__ import annotations

from evidentia_core.plugins.auth._base import (
    AuthProvider,
    AuthResult,
)
from evidentia_core.plugins.auth.local_token import (
    LocalTokenAuthProvider,
)

__all__ = [
    "AuthProvider",
    "AuthResult",
    "LocalTokenAuthProvider",
]
