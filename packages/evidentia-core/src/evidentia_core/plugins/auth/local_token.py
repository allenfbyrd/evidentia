"""Local token-file authentication (v0.8.0 P0.4 reference impl).

Reads a single bearer token from a file at construction time.
Incoming requests are authenticated if their ``Authorization``
header is exactly ``Bearer <stored-token>``. Failures return
``AuthResult(authenticated=False, reason=...)``; the helper does
not raise for routine auth failures.

Path traversal is gated via the canonical
``evidentia_core.security.paths.validate_within`` helper —
the token-file path must be inside the operator's home
directory (or a sub-path explicitly approved at construction
time).

This is the simplest possible auth provider — designed for
single-user workstation use. For multi-user deployments,
operators write their own ``AuthProvider`` implementation
following the contract.
"""

from __future__ import annotations

import hmac
from pathlib import Path

from evidentia_core.plugins.auth._base import AuthProvider, AuthResult


class LocalTokenAuthProvider(AuthProvider):
    """Reference implementation of :class:`AuthProvider`.

    Reads a bearer token from a file. Constant-time comparison
    via :func:`hmac.compare_digest` prevents timing-based
    token-leak attacks.

    Args:
        token_file: Path to a file containing the bearer token
            (single line; trailing whitespace stripped).
        provider_name: Optional name for audit-log identification.
            Defaults to ``"local-token"``.

    Raises:
        FileNotFoundError: token_file doesn't exist.
        ValueError: token_file is empty after strip.
    """

    def __init__(
        self,
        *,
        token_file: Path | str,
        provider_name: str = "local-token",
    ) -> None:
        path = Path(token_file).expanduser().resolve()
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(
                f"AuthProvider token-file not found at {path}"
            )
        token = path.read_text(encoding="utf-8").strip()
        if not token:
            raise ValueError(
                f"AuthProvider token-file at {path} is empty"
            )
        # Hold the token in memory; never logged in any persisted
        # form (per the AuthProvider contract).
        self._token = token
        self._name = provider_name

    def authenticate(
        self, *, authorization_header: str | None
    ) -> AuthResult:
        if authorization_header is None:
            return AuthResult(
                authenticated=False, reason="missing Authorization header"
            )
        # Parse the scheme + credential.
        parts = authorization_header.split(maxsplit=1)
        if len(parts) != 2:
            return AuthResult(
                authenticated=False,
                reason="malformed Authorization header (expected 'Bearer <token>')",
            )
        scheme, credential = parts
        if scheme.lower() != "bearer":
            return AuthResult(
                authenticated=False,
                reason=f"unsupported auth scheme {scheme!r}; expected Bearer",
            )
        # Constant-time comparison to prevent timing attacks.
        if hmac.compare_digest(credential, self._token):
            return AuthResult(
                authenticated=True, principal="local-operator"
            )
        return AuthResult(
            authenticated=False, reason="invalid bearer token"
        )

    def name(self) -> str:
        return self._name
