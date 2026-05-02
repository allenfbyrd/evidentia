"""Okta evidence collector for Evidentia (v0.7.7 C1).

Read-only collector that surfaces compliance-relevant evidence
about an Okta org's identity posture and emits NIST-mapped
SecurityFinding objects.

Public surface::

    from evidentia_collectors.okta import OktaCollector

    collector = OktaCollector(
        org_url="https://your-org.okta.com",
        api_token=os.environ["OKTA_API_TOKEN"],
    )
    findings = collector.collect()

Or via context manager::

    with OktaCollector(org_url=..., api_token=...) as c:
        findings, manifest = c.collect_v2()

The API token is sourced from the ``OKTA_API_TOKEN`` env var per
the secret-handling protocol. The token MUST be a read-only
service token (Okta API → Tokens; minimum scope is
``READ_ONLY_ADMIN`` on most resources). The collector emits an
EVIDENTIA-WRITE-PRIV-DETECTED finding (mapped to NIST AC-6) when
the token holder is a member of any role granting write access.

Driver: ``httpx`` (already a core Evidentia dependency — no
optional extra needed for the HTTP client). The ``[okta]`` extra
is retained for users who want the official Okta SDK installed
alongside for their own code; the collector itself uses httpx
directly to avoid the async/sync mismatch the SDK introduces.
"""

from evidentia_collectors.okta.collector import (
    BLIND_SPOTS,
    COLLECTOR_ID,
    OktaCollector,
    OktaCollectorError,
    OktaConnectionError,
    OktaQueryError,
)

__all__ = [
    "BLIND_SPOTS",
    "COLLECTOR_ID",
    "OktaCollector",
    "OktaCollectorError",
    "OktaConnectionError",
    "OktaQueryError",
]
