"""Process-lifetime RBAC policy + identity resolution (v0.9.6 P1.3).

The CLI mirrors the FastAPI ``app.state.rbac_policy`` pattern at the
process layer: one policy load per process, kept in module-level
state, cleared only by tests via :func:`_reset_rbac_cache`. Reloading
on the running process is intentionally not supported — operators
restart the CLI to pick up policy changes (matches the FastAPI
``startup`` semantic from v0.9.5).

Identity arrives from the ``EVIDENTIA_RBAC_IDENTITY`` env var. The
FastAPI side draws identity from the v0.8.1 :class:`AuthProvider`'s
authentication result on the request; the CLI has no equivalent
authentication step, so the operator (or wrapping CI job) supplies
the identity directly via env.

Threat-model note: a CLI invocation that wants to spoof an identity
can simply set ``EVIDENTIA_RBAC_IDENTITY=alice@example.com``. RBAC at
the CLI layer is therefore an **authorization** model that assumes
the surrounding environment (OS user, sudo policy, file
permissions on the policy file) authenticates the operator. The
policy file SHOULD be ``chmod 0600`` and owned by a service user,
per the v0.9.5 F-V95-rbac-trust finding.
"""

from __future__ import annotations

import os
from pathlib import Path

from evidentia_core.rbac import (
    DEFAULT_POLICY,
    RBACPolicy,
    load_policy_from_file,
)

ENV_RBAC_POLICY_FILE = "EVIDENTIA_RBAC_POLICY_FILE"
"""Env var holding an absolute path to a YAML/JSON policy file."""

ENV_RBAC_IDENTITY = "EVIDENTIA_RBAC_IDENTITY"
"""Env var holding the identity string for the current invocation."""

_CACHED_POLICY: RBACPolicy | None = None
"""Process-lifetime cache. Set on first :func:`get_rbac_policy` call."""

_CACHED_POLICY_LOADED: bool = False
"""Sentinel so a deliberately-loaded ``DEFAULT_POLICY`` (no env var
set) is not re-resolved on every call. Distinct from ``None`` so
tests can distinguish "never loaded" from "loaded the default"."""

_OVERRIDE_IDENTITY: str | None = None
"""Optional override set by the CLI ``--rbac-identity`` global
flag. Takes precedence over :data:`ENV_RBAC_IDENTITY` so operators
can override per-invocation without re-exporting the env var."""


def get_rbac_policy() -> RBACPolicy:
    """Return the RBAC policy for this process.

    Loaded from :data:`ENV_RBAC_POLICY_FILE` on the first call;
    cached for the process lifetime. Returns :data:`DEFAULT_POLICY`
    (permissive single-tenant) when the env var is unset.

    Raises:
        FileNotFoundError: If the env var is set but the path does
            not exist. Surfaces as a CLI startup error rather than
            silently falling back to the permissive default — an
            operator who set the var expects it to be honored.
        ValueError: If the file contents are not valid YAML/JSON OR
            don't match the policy schema. Propagated from
            :func:`evidentia_core.rbac.load_policy_from_file`.
    """
    global _CACHED_POLICY, _CACHED_POLICY_LOADED
    if _CACHED_POLICY_LOADED:
        assert _CACHED_POLICY is not None  # invariant; load sets both
        return _CACHED_POLICY
    policy_path = os.environ.get(ENV_RBAC_POLICY_FILE)
    _CACHED_POLICY = (
        load_policy_from_file(Path(policy_path))
        if policy_path
        else DEFAULT_POLICY
    )
    _CACHED_POLICY_LOADED = True
    return _CACHED_POLICY


def get_rbac_identity() -> str | None:
    """Return the identity for the current invocation.

    Precedence:

    1. ``--rbac-identity`` global CLI flag (set via
       :func:`set_rbac_identity_override`).
    2. :data:`ENV_RBAC_IDENTITY` env var.
    3. ``None`` (anonymous; resolves to ``policy.default_role``).
    """
    if _OVERRIDE_IDENTITY is not None:
        return _OVERRIDE_IDENTITY
    return os.environ.get(ENV_RBAC_IDENTITY) or None


def set_rbac_identity_override(identity: str | None) -> None:
    """Set the per-invocation identity override (CLI callback path).

    The ``@app.callback()`` in :mod:`evidentia.cli.main` wires the
    global ``--rbac-identity`` flag through this setter. Tests use
    it to inject an identity without mutating ``os.environ``.

    Passing ``None`` clears the override (the env-var fallback then
    applies). The override is process-lifetime; it does NOT reset
    automatically between Typer invocations within the same Python
    process (tests should call this with ``None`` in teardown if
    they set it in setup).
    """
    global _OVERRIDE_IDENTITY
    _OVERRIDE_IDENTITY = identity


def _reset_rbac_cache() -> None:
    """Clear the policy cache + identity override (test-only helper).

    Public-but-underscored: production code MUST NOT call this. Tests
    invoke it in fixtures so each test sees a clean cache. Future
    runtime-reload features (if any) would land as a new public
    function with explicit operator-facing ergonomics.
    """
    global _CACHED_POLICY, _CACHED_POLICY_LOADED, _OVERRIDE_IDENTITY
    _CACHED_POLICY = None
    _CACHED_POLICY_LOADED = False
    _OVERRIDE_IDENTITY = None
