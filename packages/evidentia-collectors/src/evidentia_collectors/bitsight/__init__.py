"""BitSight evidence collector for Evidentia (v0.7.9 P0.4 third slice).

Read-only collector that pulls a BitSight Security Ratings portfolio
via the BitSight API (https://api.bitsighttech.com) and emits
NIST 800-53 + OCC Bulletin 2013-29 + FRB SR 13-19 + FFIEC IT
Examination Handbook Outsourcing booklet mapped SecurityFinding
objects.

BitSight is shape-different from Vanta / Drata:

- BitSight is a security-ratings provider, not a TPRM-management
  platform. Operators import vendor companies INTO their BitSight
  portfolio; BitSight rates each company's external security
  posture on a 250-900 scale (A: 740-900, B: 670-739, C: 600-669,
  D: 530-599, F: <530).
- The Evidentia integration surfaces each portfolio company as a
  vendor-inventory finding (NIST SR-2 / SR-3 / SR-6 + OCC + FRB +
  FFIEC mappings), AND emits an additional MEDIUM-severity
  finding when the company's BitSight rating falls below the
  operator-configured threshold (default 700).

Public surface::

    from evidentia_collectors.bitsight import BitSightCollector

    with BitSightCollector(api_token=os.environ["BITSIGHT_API_TOKEN"]) as c:
        findings, manifest = c.collect_v2()

Or the legacy ``collect()`` shortcut returning just findings::

    findings = BitSightCollector(api_token="...").collect()

The API token is sourced from the ``BITSIGHT_API_TOKEN`` env var per
the secret-handling protocol — BitSight uses HTTP Basic auth with
the API token as the username and an empty password
(``Authorization: Basic <base64(token:)>``). The collector
constructs the header internally; the token never appears in URLs
or query params.

Token scope: read-only access to the BitSight portfolio surface.

This module ships in v0.7.9 P0.4 third slice; subsequent slices add
finding-level details (factor scores per company), historical
ratings, and the SecurityScorecard counterpart.

No new pyproject extra is needed — the only runtime dep is
``httpx>=0.27`` which is already a base dependency of
``evidentia-collectors``.

Typed exceptions:

- :class:`BitSightCollectorError` — base
- :class:`BitSightAuthError` — 401 / 403 / token rejection
- :class:`BitSightConnectionError` — network / TLS / timeout
- :class:`BitSightQueryError` — per-endpoint failure (4xx / 5xx)
"""

from __future__ import annotations

from evidentia_collectors.bitsight.collector import (
    BLIND_SPOTS,
    COLLECTOR_ID,
    BitSightAuthError,
    BitSightCollector,
    BitSightCollectorError,
    BitSightConnectionError,
    BitSightQueryError,
)

# v0.7.10 P3 closure of v0.7.9 L-7: re-export BLIND_SPOTS +
# COLLECTOR_ID at the package level.
__all__ = [
    "BLIND_SPOTS",
    "COLLECTOR_ID",
    "BitSightAuthError",
    "BitSightCollector",
    "BitSightCollectorError",
    "BitSightConnectionError",
    "BitSightQueryError",
]
