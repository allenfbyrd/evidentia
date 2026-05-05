"""AuthProvider ABC (v0.8.0 P0.4)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class AuthResult:
    """Result of an authentication attempt.

    Attributes:
        authenticated: True if the request carried a valid
            credential. False if anonymous or invalid.
        principal: A short string identifying the authenticated
            principal (typically a username, email, or service
            identifier). None if ``authenticated`` is False.
        reason: Optional human-readable reason for an
            authentication failure (e.g., "missing Authorization
            header", "invalid token format"). Logged but not
            surfaced to the client by default.
    """

    authenticated: bool
    principal: str | None = None
    reason: str | None = None


class AuthProvider(ABC):
    """Abstract base class for authentication backends.

    Implementations parse incoming-request credentials (typically
    a bearer token in the ``Authorization`` header) and return
    an :class:`AuthResult`.

    Implementations should be thread-safe (FastAPI dependencies
    are evaluated per-request and may run concurrently).

    Implementations should NOT raise exceptions for routine
    auth failures (missing/invalid credential); they should
    return ``AuthResult(authenticated=False, reason=...)``
    instead. Exceptions should be reserved for backend
    failures (e.g., the auth-provider service itself is
    unreachable).
    """

    @abstractmethod
    def authenticate(self, *, authorization_header: str | None) -> AuthResult:
        """Authenticate a request based on its Authorization header.

        Args:
            authorization_header: The full value of the request's
                ``Authorization`` header, or None if absent. The
                provider is responsible for parsing the scheme
                (``Bearer``, ``Basic``, etc.) and credential.

        Returns:
            :class:`AuthResult` indicating success/failure +
            principal identity (on success) or reason (on
            failure).

        Implementations MUST:
            - Be thread-safe (called per-request; may run
              concurrently)
            - NOT raise on routine auth failures (return
              ``authenticated=False`` instead)
            - NOT log secret material (the bearer token itself,
              passwords, etc.) in any persisted form
        """
        raise NotImplementedError

    @abstractmethod
    def name(self) -> str:
        """Return a short human-readable name for this provider.

        Used in audit logs + admin UI. Examples: ``"local-token"``,
        ``"oauth2-google"``, ``"mtls-system-ca"``.
        """
        raise NotImplementedError
