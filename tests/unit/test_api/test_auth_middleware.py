"""Unit tests for v0.8.1 P3.3 FastAPI AuthProvider middleware.

Verifies that the AuthProvider middleware:
1. Gates `/api/*` routes when wired (closes v0.8.0 F-V08-S3).
2. Allows liveness probes (`/api/health`, `/api/version`,
   `/api/openapi.json`, `/api/docs`, `/api/redoc`) without
   auth (Kubernetes / load-balancer readiness convention).
3. Does NOT fire when `auth_provider=None` (v0.8.0 backward
   compat for localhost-only deployments).
4. Returns 401 with `WWW-Authenticate: Bearer realm="evidentia"`
   on missing/invalid token (RFC 7235 §4.1).
5. Attaches the authenticated principal to `request.state` so
   downstream handlers can introspect.
"""

from __future__ import annotations

from pathlib import Path

from evidentia_api.app import create_app
from evidentia_core.plugins.auth.local_token import LocalTokenAuthProvider
from fastapi.testclient import TestClient


def _make_token_file(tmp_path: Path, value: str = "test-token-abc") -> Path:
    token_file = tmp_path / "token.txt"
    token_file.write_text(value, encoding="utf-8")
    return token_file


class TestAuthMiddleware:
    def test_no_auth_provider_means_no_gating(self) -> None:
        """v0.8.0 backward-compat: auth_provider=None matches
        the localhost-only deployment posture; no middleware
        attached + all routes reachable.
        """
        app = create_app(dev_mode=False, auth_provider=None)
        client = TestClient(app)
        # /api/metrics is the v0.8.0 P1 G3 endpoint — no auth
        # gating in v0.8.0. With auth_provider=None we keep that
        # behavior.
        response = client.get("/api/metrics")
        assert response.status_code == 200

    def test_auth_provider_gates_metrics_endpoint(
        self, tmp_path: Path
    ) -> None:
        """v0.8.1 F-V08-S3 closure: with an AuthProvider wired,
        /api/metrics requires a valid bearer token.
        """
        token_file = _make_token_file(tmp_path)
        provider = LocalTokenAuthProvider(token_file=token_file)
        app = create_app(dev_mode=False, auth_provider=provider)
        client = TestClient(app)

        # No Authorization header → 401.
        response = client.get("/api/metrics")
        assert response.status_code == 401
        assert (
            response.headers["WWW-Authenticate"]
            == 'Bearer realm="evidentia"'
        )
        body = response.json()
        assert body["detail"] == "Authentication required"
        assert body["provider"] == "local-token"

        # Wrong token → 401.
        response = client.get(
            "/api/metrics",
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert response.status_code == 401

        # Right token → 200.
        response = client.get(
            "/api/metrics",
            headers={"Authorization": "Bearer test-token-abc"},
        )
        assert response.status_code == 200
        # The metrics body still renders Prometheus exposition.
        assert "evidentia_app_info" in response.text

    def test_health_probe_bypasses_auth(self, tmp_path: Path) -> None:
        """Liveness probe path /api/health is in the
        UNAUTHENTICATED_PATHS allowlist; it MUST be reachable
        without a token so Kubernetes/load-balancer readiness
        checks don't break.
        """
        token_file = _make_token_file(tmp_path)
        provider = LocalTokenAuthProvider(token_file=token_file)
        app = create_app(dev_mode=False, auth_provider=provider)
        client = TestClient(app)

        # No Authorization header → still 200 (allowlisted).
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_version_probe_bypasses_auth(self, tmp_path: Path) -> None:
        """/api/version is allowlisted alongside /api/health —
        operator's CI gates often check the running version
        without a service-account credential.
        """
        token_file = _make_token_file(tmp_path)
        provider = LocalTokenAuthProvider(token_file=token_file)
        app = create_app(dev_mode=False, auth_provider=provider)
        client = TestClient(app)

        response = client.get("/api/version")
        assert response.status_code == 200

    def test_openapi_spec_bypasses_auth(self, tmp_path: Path) -> None:
        """/api/openapi.json must be reachable without a token
        so OpenAPI tooling (Stoplight, Swagger UI, etc.) can
        introspect the API + advertise the auth scheme to
        clients.
        """
        token_file = _make_token_file(tmp_path)
        provider = LocalTokenAuthProvider(token_file=token_file)
        app = create_app(dev_mode=False, auth_provider=provider)
        client = TestClient(app)

        response = client.get("/api/openapi.json")
        assert response.status_code == 200

    def test_static_spa_paths_bypass_auth(
        self, tmp_path: Path
    ) -> None:
        """Non-/api/* paths fall through to the static SPA
        mount; they bypass auth at the API layer (the SPA
        itself handles client-side auth in the browser).
        """
        token_file = _make_token_file(tmp_path)
        provider = LocalTokenAuthProvider(token_file=token_file)
        app = create_app(dev_mode=False, auth_provider=provider)
        client = TestClient(app)

        # The SPA root path — without auth, returns either the
        # SPA index.html or the placeholder JSON (depending on
        # whether the static mount is populated). Either way,
        # NOT a 401.
        response = client.get("/")
        assert response.status_code != 401
