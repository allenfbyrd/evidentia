"""FastAPI AuthProvider middleware integration (v0.8.1 P3.3).

Wires the v0.8.0 P0.4 :class:`AuthProvider` plugin contract
into FastAPI's dependency-injection stack. Operators construct
an ``AuthProvider`` (e.g.,
:class:`evidentia_core.plugins.auth.local_token.LocalTokenAuthProvider`)
and pass it via :func:`create_app(auth_provider=...)`. When
present, every request is gated through the provider's
:meth:`authenticate` method before any router handler runs.

Closes the v0.8.0 review F-V08-S3 MEDIUM finding (``/api/metrics``
not auth-gated). Once wired, ``/api/metrics`` + ``/api/risks``
+ all other ``/api/*`` routes inherit the same auth requirement.

The middleware honors a small ``UNAUTHENTICATED_PATHS``
allowlist for liveness probes (``/api/health``,
``/api/version``) — these surfaces are public-by-design + must
remain reachable without a token for Kubernetes / load-balancer
readiness checks.

Design note: this is FastAPI middleware (``BaseHTTPMiddleware``
subclass), not a per-route dependency. Middleware runs for
EVERY request including non-router paths (``/api/openapi.json``,
``/api/docs``, the SPA static mount). The allowlist gates
which surfaces are public.

Operator wiring:

    from evidentia_api.app import create_app
    from evidentia_core.plugins.auth.local_token import (
        LocalTokenAuthProvider,
    )

    app = create_app(
        auth_provider=LocalTokenAuthProvider(
            token_file="/etc/evidentia/api-token",
        ),
        bind_host="0.0.0.0",  # auth required when non-loopback
    )

When ``auth_provider`` is None (the default, matching v0.8.0
behavior), no auth gating fires — preserves backward compat
for localhost-only deployments. When non-None, the middleware
is attached + requests without a valid Bearer token return
401.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from evidentia_core.plugins.auth import AuthProvider
    from starlette.responses import Response

# v0.8.1 P3.3: paths that MUST remain reachable without auth.
# Liveness/readiness probes + the OpenAPI spec (which advertises
# the auth scheme) are public-by-convention. Static SPA assets
# fall through to the FastAPI static mount which is also public
# (the SPA itself enforces auth in the browser via Clerk or
# equivalent — the API gates the data-bearing routes).
UNAUTHENTICATED_PATHS: frozenset[str] = frozenset(
    {
        "/api/health",
        "/api/version",
        "/api/openapi.json",
        "/api/docs",
        "/api/redoc",
    }
)


class AuthProviderMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that gates requests on an AuthProvider.

    Per-request flow:

    1. Request arrives.
    2. If the request path is in :data:`UNAUTHENTICATED_PATHS`,
       skip auth + dispatch the request directly.
    3. Otherwise, extract the ``Authorization`` header and pass
       it to ``self._provider.authenticate(...)``.
    4. On ``AuthResult(authenticated=True)``: attach the
       principal to ``request.state.auth_principal`` and
       dispatch the request.
    5. On ``AuthResult(authenticated=False)``: return 401 with
       a JSON body carrying the provider's ``reason``.

    The middleware never blocks on the AuthProvider's I/O —
    LocalTokenAuthProvider reads its token at construction
    time, so the per-request cost is a constant-time hmac
    comparison. Custom AuthProviders that hit a remote service
    on every request inherit that latency on every API call;
    operators should cache verifiable tokens at the AuthProvider
    layer.
    """

    def __init__(
        self, app: object, *, provider: AuthProvider
    ) -> None:
        # Match the SecurityHeadersMiddleware pattern: take
        # `app: object` + type-ignore the super() call to
        # satisfy Starlette's overly-strict middleware factory
        # protocol.
        super().__init__(app)  # type: ignore[arg-type]
        self._provider = provider

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # Public paths bypass auth entirely (probes + spec).
        if request.url.path in UNAUTHENTICATED_PATHS:
            return await call_next(request)
        # Static SPA mount: any path that doesn't start with /api/
        # falls through to the static assets. These are public-by-
        # design — the SPA itself enforces auth in the browser.
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        result = self._provider.authenticate(
            authorization_header=auth_header
        )
        if not result.authenticated:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Authentication required",
                    "reason": result.reason,
                    "provider": self._provider.name(),
                },
                headers={
                    # Hint the client which scheme to use. RFC 7235
                    # §4.1 — WWW-Authenticate on 401 responses.
                    "WWW-Authenticate": 'Bearer realm="evidentia"',
                },
            )
        # Attach the authenticated principal to request state so
        # downstream handlers can introspect it (e.g., for per-
        # principal audit events). Standard FastAPI pattern.
        request.state.auth_principal = result.principal
        return await call_next(request)
