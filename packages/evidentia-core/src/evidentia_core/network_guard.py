"""Air-gapped mode — network-call guard for v0.4.0's ``--offline`` flag.

Positioning: *"The only open-source GRC tool that runs entirely on your
infrastructure."* This module enforces that claim — when offline mode is
on, any attempted outbound network call that isn't loopback or RFC-1918
raises :class:`OfflineViolationError` **before** the network IO is
issued. The error is structured so the CLI and the GUI can render a
clear explanation (subsystem, target host, remediation).

The guard is consulted from three subsystems:

1. :mod:`evidentia_ai.client` — every LLM completion call checks the
   configured model prefix + ``api_base`` kwarg. Only Ollama-style prefixes
   and custom endpoints pointing at loopback/private IPs are allowed.
2. :mod:`evidentia_core.catalogs.loader` — ``catalog import --from-url``
   refuses non-loopback URLs.
3. :mod:`evidentia.cli.doctor` — ``evidentia doctor --check-air-gap``
   exercises every subsystem and reports its offline posture.

The enabling surface is tiny on purpose. Call :func:`set_offline(True)`
once at process start (the CLI's global callback does this when
``--offline`` is set; the FastAPI app factory does it from
``app.state.offline``) and every subsystem's guard checks become active.
Use :func:`offline_mode()` as a context manager for test fixtures that
need per-block enablement.

Design note: a module-level flag rather than contextvars. Evidentia's
CLI is single-process and the FastAPI server's handlers read request
state at call time, so the flag's lack of per-request isolation doesn't
matter in practice. If a future release adds worker pools with mixed
offline/online tenants, revisit.
"""

from __future__ import annotations

import ipaddress
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

__all__ = [
    "LOCAL_LLM_PREFIXES",
    "OfflineViolationError",
    "check_llm_model",
    "check_url",
    "is_loopback_or_private",
    "is_offline",
    "offline_mode",
    "set_offline",
]

# ── Module-level state ────────────────────────────────────────────────────

_offline_enabled: bool = False
"""When True, all guard checks raise on non-loopback/RFC-1918 targets."""


def is_offline() -> bool:
    """Return True if offline mode is currently enabled for this process."""
    return _offline_enabled


def set_offline(enabled: bool) -> None:
    """Toggle offline mode process-wide.

    Called exactly once at CLI startup (in the global ``--offline`` flag
    handler) or at FastAPI app creation time (when ``--offline`` was passed
    to ``evidentia serve``). Explicit enable/disable avoids the subtle
    bugs you get from "remember to reset" patterns in tests.
    """
    global _offline_enabled
    _offline_enabled = bool(enabled)
    if _offline_enabled:
        logger.info(
            "Air-gapped mode ENABLED — outbound network calls to non-loopback "
            "hosts will raise OfflineViolationError."
        )


@contextmanager
def offline_mode(enabled: bool = True) -> Iterator[None]:
    """Context manager that toggles offline mode for the duration of a block.

    Useful for test fixtures and short-lived subsystems that need offline
    enforcement without leaking into the rest of the process::

        with offline_mode():
            # guarded region
            ...

    Restores the prior offline state on exit even if an exception fires.
    """
    previous = _offline_enabled
    set_offline(enabled)
    try:
        yield
    finally:
        set_offline(previous)


# ── Exception ─────────────────────────────────────────────────────────────


class OfflineViolationError(Exception):
    """Raised when offline mode is on and a disallowed network target is detected.

    Attributes
    ----------
    subsystem
        Which Evidentia module flagged the violation
        (``'llm_client'``, ``'catalog_loader'``, etc.).
    target
        The host / URL / model string that would have leaked.
    remediation
        One-line hint for the user; rendered in the CLI error path and
        surfaced to the GUI via the /api/*/error response body.
    """

    def __init__(
        self, *, subsystem: str, target: str, remediation: str = ""
    ) -> None:
        self.subsystem = subsystem
        self.target = target
        self.remediation = remediation
        message = (
            f"Air-gapped mode refuses network call from {subsystem}: "
            f"target={target!r}"
        )
        if remediation:
            message += f" -- {remediation}"
        super().__init__(message)


# ── Host allowlisting ─────────────────────────────────────────────────────

# Hostnames that always resolve to loopback; we skip IP resolution for these
# to avoid a DNS round-trip on every guarded call.
_LOOPBACK_HOSTNAMES = frozenset({"localhost", "localhost.localdomain"})


def is_loopback_or_private(host: str) -> bool:
    """Return True if ``host`` is a loopback, link-local, or RFC-1918 address.

    Accepts both hostnames (``localhost``, ``localhost.localdomain``) and
    IP addresses (``127.0.0.1``, ``10.0.0.5``, ``192.168.1.7``, ``::1``,
    ``fd00::1``, etc.). Hostnames that aren't in the reserved-loopback
    set and don't parse as IPs return False — callers should not
    DNS-resolve arbitrary hostnames in offline mode (the DNS query itself
    is a leak).

    Allowed ranges:
    - IPv4 loopback (``127.0.0.0/8``)
    - IPv4 link-local (``169.254.0.0/16``)
    - IPv4 private (RFC-1918): ``10.0.0.0/8``, ``172.16.0.0/12``, ``192.168.0.0/16``
    - IPv6 loopback (``::1``)
    - IPv6 link-local (``fe80::/10``)
    - IPv6 unique-local (``fc00::/7`` — RFC-4193)
    """
    if not host:
        return False

    host_lower = host.lower().strip()
    if host_lower in _LOOPBACK_HOSTNAMES:
        return True

    # Strip IPv6 brackets if present (urlparse gives us "[::1]" hosts).
    if host_lower.startswith("[") and host_lower.endswith("]"):
        host_lower = host_lower[1:-1]

    try:
        ip = ipaddress.ip_address(host_lower)
    except ValueError:
        return False

    return bool(ip.is_loopback or ip.is_private or ip.is_link_local)


# ── URL + LLM guards ──────────────────────────────────────────────────────


def check_url(url: str, *, subsystem: str, remediation: str = "") -> None:
    """Raise :class:`OfflineViolationError` if offline mode is on and URL is external.

    No-op when offline mode is off. When on, parses ``url`` and consults
    :func:`is_loopback_or_private` on the host component.

    Parameters
    ----------
    url
        The full URL about to be fetched (any scheme).
    subsystem
        Human-readable caller label for the error; used for diagnostics.
    remediation
        Optional one-line hint to surface to the user.
    """
    if not _offline_enabled:
        return

    parsed = urlparse(url)
    host = parsed.hostname or ""
    if is_loopback_or_private(host):
        return

    raise OfflineViolationError(
        subsystem=subsystem,
        target=url,
        remediation=remediation
        or "Configure a local endpoint (Ollama, vLLM, mirror proxy) or disable --offline.",
    )


# LLM model prefixes that are always offline-safe — they either route to
# localhost (Ollama) or require explicit api_base (vLLM + custom OpenAI-
# compatible endpoints) which is checked separately.
LOCAL_LLM_PREFIXES: tuple[str, ...] = (
    "ollama/",
    "ollama_chat/",
    "vllm/",
    "text-completion-openai/",  # Aliased route LiteLLM uses for OpenAI-compatible
)


def check_llm_model(
    model: str,
    *,
    api_base: str | None = None,
    subsystem: str = "llm_client",
) -> None:
    """Raise :class:`OfflineViolationError` if offline mode rejects this LLM config.

    Allowed in offline mode:
    - Any model whose prefix is in :data:`LOCAL_LLM_PREFIXES`
      (``ollama/...``, ``vllm/...``, etc.)
    - Any model with an explicit ``api_base`` pointing at a loopback or
      RFC-1918 address (covers self-hosted OpenAI-compatible endpoints).

    Everything else raises. This is intentionally conservative — we'd
    rather fail closed than let a cloud LLM sneak through on a model
    string we don't recognize.
    """
    if not _offline_enabled:
        return

    # If the caller provided a custom api_base, its host determines allowlisting
    # regardless of the model string.
    if api_base:
        parsed = urlparse(api_base)
        host = parsed.hostname or ""
        if is_loopback_or_private(host):
            return
        raise OfflineViolationError(
            subsystem=subsystem,
            target=f"{model} @ {api_base}",
            remediation=(
                "api_base points at a non-loopback host. Use localhost / "
                "RFC-1918 or switch to an ollama/* model."
            ),
        )

    # Without api_base, rely on the model prefix whitelist.
    model_lower = model.lower()
    for prefix in LOCAL_LLM_PREFIXES:
        if model_lower.startswith(prefix):
            return

    raise OfflineViolationError(
        subsystem=subsystem,
        target=model,
        remediation=(
            "Cloud LLM models are refused in air-gapped mode. Switch to "
            "ollama/llama3 (or similar) or set api_base to a local "
            "OpenAI-compatible endpoint."
        ),
    )
