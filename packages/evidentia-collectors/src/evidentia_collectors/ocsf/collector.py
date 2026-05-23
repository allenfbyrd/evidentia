"""OCSF JSON ingestion: file + URL modes.

v0.10.1. Dispatches OCSF input by ``class_uid`` — Compliance Finding
(2003) goes through :func:`evidentia_core.ocsf.finding_from_ocsf`
with ``trust_unmapped=False``; Detection Finding (2004) goes through
:func:`evidentia_core.ocsf.finding_from_ocsf_detection`. Anything
else raises :class:`OCSFIngestError`.

URL mode is intentionally conservative — third-party OCSF endpoints
are an SSRF / DoS surface. Defaults: HTTPS-only, no redirects, 10s
connect/read timeout, 50 MB body cap. Operators with stricter or
looser policies pass explicit values.
"""

from __future__ import annotations

import ipaddress
import json
import socket
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from evidentia_core.models.finding import SecurityFinding
from evidentia_core.ocsf import (
    OCSFMappingError,
    finding_from_ocsf,
    finding_from_ocsf_detection,
)

__all__ = [
    "OCSFIngestError",
    "collect_ocsf_file",
    "collect_ocsf_url",
]

# OCSF Findings-category class identifiers (mirror of
# evidentia_core.ocsf.finding_mapping; duplicated here to keep this
# collector free of private-module imports).
_CLASS_UID_COMPLIANCE = 2003
_CLASS_UID_DETECTION = 2004

# Default URL-fetch limits.
_DEFAULT_TIMEOUT_S = 10.0
_DEFAULT_MAX_BYTES = 50 * 1024 * 1024  # 50 MB


class OCSFIngestError(RuntimeError):
    """Raised when OCSF ingestion cannot proceed.

    Common causes: malformed JSON, unsupported OCSF class_uid (only
    Compliance Finding 2003 and Detection Finding 2004 are supported),
    URL-fetch policy violation (non-HTTPS, oversized body, redirect),
    or a wrapped :class:`OCSFMappingError` from the underlying
    mapping functions.
    """


def collect_ocsf_file(path: str | Path) -> list[SecurityFinding]:
    """Read OCSF JSON from a local file and convert to SecurityFinding[].

    The file may contain either a single OCSF finding object or a JSON
    list of them. Each finding's ``class_uid`` decides the conversion
    path (Compliance Finding 2003 vs Detection Finding 2004).
    """
    file_path = Path(path)
    try:
        raw = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise OCSFIngestError(f"could not read OCSF file {file_path}: {exc}") from exc
    return _convert_ocsf_payload(raw, source=str(file_path))


def collect_ocsf_url(
    url: str,
    *,
    timeout: float = _DEFAULT_TIMEOUT_S,
    max_bytes: int = _DEFAULT_MAX_BYTES,
    block_private_ips: bool = True,
) -> list[SecurityFinding]:
    """Read OCSF JSON from an HTTPS URL.

    Policy:

    - HTTPS-only — ``http://`` URLs are rejected (no plaintext).
    - No redirects — the URL must serve the body directly.
    - ``timeout`` (default 10s) is enforced on both connect and read.
    - ``max_bytes`` (default 50 MB) caps the response body; anything
      larger raises :class:`OCSFIngestError` mid-stream.
    - **``block_private_ips`` (default True, v0.10.2 F-V101-L1
      close-out)** — pre-resolves the URL's host and rejects RFC1918
      (10/8, 172.16/12, 192.168/16), link-local (169.254/16 — covers
      AWS / GCP / Azure instance-metadata endpoints), loopback
      (127/8 + ::1), multicast, reserved, and unspecified ranges
      BEFORE opening the socket. Operators ingesting from trusted
      internal endpoints can flip to ``False`` (also via the
      ``--allow-private-ips`` CLI flag).

    Prefer :func:`collect_ocsf_file` whenever the OCSF output can be
    written to disk first — URL mode carries a real SSRF / DoS
    surface and is best reserved for trusted endpoints.
    """
    if not url.lower().startswith("https://"):
        raise OCSFIngestError(
            f"OCSF URL ingest is HTTPS-only; got: {url[:60]}"
        )

    if block_private_ips:
        _refuse_private_host(url)

    # NoRedirectHandler refuses every 3xx — see the policy note above.
    opener = urllib.request.build_opener(_NoRedirectHandler())
    request = urllib.request.Request(url, headers={"Accept": "application/json"})

    try:
        with opener.open(request, timeout=timeout) as response:
            body = _read_capped(response, max_bytes)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise OCSFIngestError(f"OCSF URL fetch failed: {exc}") from exc

    raw = body.decode("utf-8", errors="strict")
    return _convert_ocsf_payload(raw, source=url)


def _refuse_private_host(url: str) -> None:
    """Refuse the request if the URL's host resolves to a private IP.

    Closes F-V101-L1 (v0.10.2). Resolves the hostname via
    :func:`socket.getaddrinfo` (covers IPv4 + IPv6 + literal IPs +
    DNS-based bypass attempts that return private-range addresses),
    walks every returned address, and raises if ANY of them falls
    into a non-public range. The "any address" check matters because
    a malicious DNS record can return multiple addresses and rely on
    the client picking the public one — we reject the entire host
    if any record points internal.

    Ranges considered non-public: ``is_private`` (RFC1918), ``is_loopback``,
    ``is_link_local`` (covers cloud-provider metadata services),
    ``is_multicast``, ``is_reserved``, ``is_unspecified``.
    """
    host = urlparse(url).hostname
    if not host:
        raise OCSFIngestError(f"OCSF URL missing hostname: {url[:60]}")
    try:
        addrinfos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise OCSFIngestError(
            f"OCSF URL hostname resolution failed for {host!r}: {exc}"
        ) from exc
    for _family, _type, _proto, _canon, sockaddr in addrinfos:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise OCSFIngestError(
                f"OCSF URL host {host!r} resolves to {ip_str} — "
                "private / loopback / link-local / multicast / reserved / "
                "unspecified address rejected per SSRF policy. Pass "
                "--allow-private-ips (CLI) or block_private_ips=False "
                "(library) to override for trusted internal endpoints."
            )


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Refuse every redirect — protects against open-redirect → SSRF."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request:
        raise OCSFIngestError(
            f"OCSF URL ingest refused {code} redirect to {newurl[:60]}"
        )


def _read_capped(response: Any, max_bytes: int) -> bytes:
    """Read at most ``max_bytes`` from an HTTP response."""
    buffer = bytearray()
    while True:
        chunk = response.read(min(65536, max_bytes - len(buffer) + 1))
        if not chunk:
            break
        buffer.extend(chunk)
        if len(buffer) > max_bytes:
            raise OCSFIngestError(
                f"OCSF response exceeds {max_bytes}-byte cap"
            )
    return bytes(buffer)


def _convert_ocsf_payload(raw: str, *, source: str) -> list[SecurityFinding]:
    """Parse a JSON string + dispatch by class_uid. Returns findings."""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OCSFIngestError(f"{source} is not valid JSON: {exc}") from exc

    items: list[dict[str, Any]]
    if isinstance(payload, dict):
        items = [payload]
    elif isinstance(payload, list):
        items = [item for item in payload if isinstance(item, dict)]
        if len(items) != len(payload):
            raise OCSFIngestError(
                f"{source} contains non-object entries in its JSON list"
            )
    else:
        raise OCSFIngestError(
            f"{source} JSON root must be an object or a list of objects"
        )

    findings: list[SecurityFinding] = []
    for index, item in enumerate(items):
        try:
            findings.append(_dispatch_one(item))
        except OCSFMappingError as exc:
            raise OCSFIngestError(
                f"{source}[{index}] failed OCSF conversion: {exc}"
            ) from exc
    return findings


def _dispatch_one(item: dict[str, Any]) -> SecurityFinding:
    """Route a single OCSF dict to the right mapping function."""
    class_uid = item.get("class_uid")
    if class_uid == _CLASS_UID_COMPLIANCE:
        # Third-party ingestion -> never trust the unmapped block.
        return finding_from_ocsf(item, trust_unmapped=False)
    if class_uid == _CLASS_UID_DETECTION:
        return finding_from_ocsf_detection(item, trust_unmapped=False)
    raise OCSFIngestError(
        f"unsupported OCSF class_uid {class_uid!r}; expected "
        f"{_CLASS_UID_COMPLIANCE} (Compliance Finding) or "
        f"{_CLASS_UID_DETECTION} (Detection Finding)"
    )
