"""Unit tests for the Okta evidence collector (v0.7.7 C1).

Uses httpx.MockTransport to stub the Okta REST API. No live Okta
required.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from evidentia_collectors.okta import (
    BLIND_SPOTS,
    COLLECTOR_ID,
    OktaCollector,
    OktaCollectorError,
)
from evidentia_core.models.finding import FindingStatus, Severity

# ── Mock-transport infrastructure ──────────────────────────────────


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _ago_iso(days: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).strftime(
        "%Y-%m-%dT%H:%M:%S.000Z"
    )


def _baseline_responses() -> dict[str, Any]:
    """Return a mapping path -> JSON body for a typical hardened
    org with high MFA enrollment + reasonable user count.
    """
    return {
        "/api/v1/org": {
            "subdomain": "test-org",
            "companyName": "Test Org Inc.",
            "status": "ACTIVE",
        },
        "/api/v1/users": [
            {
                "id": "u01",
                "status": "ACTIVE",
                "lastLogin": _ago_iso(2),
                "profile": {"login": "alice@example.com"},
            },
            {
                "id": "u02",
                "status": "ACTIVE",
                "lastLogin": _ago_iso(120),  # > 90d threshold
                "profile": {"login": "bob@example.com"},
            },
            {
                "id": "u03",
                "status": "SUSPENDED",
                "lastLogin": _ago_iso(200),
                "profile": {"login": "carol@example.com"},
            },
            {
                "id": "u04",
                "status": "DEPROVISIONED",
                "lastLogin": _ago_iso(400),
                "profile": {"login": "dave@example.com"},
            },
        ],
        "/api/v1/iam/assignees/users": [
            {"id": "u01", "status": "ACTIVE"},
            {"id": "admin1", "status": "ACTIVE"},
        ],
        "/api/v1/users/u01/factors": [
            {"id": "f01", "factorType": "push", "status": "ACTIVE"}
        ],
        "/api/v1/users/u02/factors": [],  # user has no MFA
        "/api/v1/users/u03/factors": [],
        "/api/v1/users/u04/factors": [],
        "/api/v1/policies": {
            "PASSWORD": [
                {
                    "id": "p01",
                    "status": "ACTIVE",
                    "settings": {
                        "password": {
                            "complexity": {"minLength": 12},
                            "age": {"maxAgeDays": 90},
                            "lockout": {"maxAttempts": 5},
                        }
                    },
                }
            ],
            "OKTA_SIGN_ON": [
                {
                    "id": "p02",
                    "status": "ACTIVE",
                    "rules": [
                        {
                            "id": "r01",
                            "actions": {
                                "signon": {
                                    "factorPromptMode": "ALWAYS"
                                }
                            },
                        }
                    ],
                }
            ],
        },
    }


def _make_handler(
    responses: dict[str, Any],
) -> tuple[httpx.MockTransport, list[httpx.Request]]:
    """Build a MockTransport that routes by URL path."""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        path = request.url.path
        # /api/v1/policies behaves differently — route on type param
        if path == "/api/v1/policies":
            params = parse_qs(urlparse(str(request.url)).query)
            policy_type = (params.get("type") or [""])[0]
            policies = responses["/api/v1/policies"].get(
                policy_type, []
            )
            return httpx.Response(200, json=policies)
        if path in responses:
            return httpx.Response(200, json=responses[path])
        return httpx.Response(
            404, json={"error": f"path {path!r} not stubbed"}
        )

    return httpx.MockTransport(handler), captured


def _make_collector(
    responses: dict[str, Any] | None = None,
    **kwargs: Any,
) -> tuple[OktaCollector, list[httpx.Request]]:
    transport, captured = _make_handler(
        responses or _baseline_responses()
    )
    client = httpx.Client(
        transport=transport,
        base_url="https://test-org.okta.com",
        headers={"Authorization": "SSWS test-token"},
    )
    coll = OktaCollector(client=client, **kwargs)
    return coll, captured


# ── Constants ────────────────────────────────────────────────────────


def test_collector_id_constant() -> None:
    assert COLLECTOR_ID == "okta-scan"


def test_blind_spots_documented() -> None:
    assert len(BLIND_SPOTS) == 3
    ids = [bs["id"] for bs in BLIND_SPOTS]
    assert "EVIDENTIA-OKTA-WORKFLOWS-COVERAGE" in ids
    assert "EVIDENTIA-OKTA-RATE-LIMIT-PARTIAL" in ids
    assert "EVIDENTIA-OKTA-USER-MFA-FACTOR-LIFECYCLE" in ids


# ── Construction validation ─────────────────────────────────────────


def test_constructor_requires_url_or_client() -> None:
    with pytest.raises(OktaCollectorError, match="requires either"):
        OktaCollector()


def test_constructor_rejects_http_scheme() -> None:
    with pytest.raises(OktaCollectorError, match="must use https"):
        OktaCollector(
            org_url="http://insecure.example.com",
            api_token="t",
        )


def test_constructor_strips_trailing_slash() -> None:
    coll = OktaCollector(
        org_url="https://test-org.okta.com/",
        api_token="t",
    )
    assert coll._org_url == "https://test-org.okta.com"


# ── test_connection ─────────────────────────────────────────────────


def test_test_connection_returns_org_metadata() -> None:
    coll, _ = _make_collector()
    info = coll.test_connection()
    assert info["subdomain"] == "test-org"
    assert info["company_name"] == "Test Org Inc."
    assert info["status"] == "ACTIVE"


# ── Sub-checks ──────────────────────────────────────────────────────


def test_user_inventory_finding() -> None:
    coll, _ = _make_collector()
    findings = coll.collect()
    inventory = [f for f in findings if "user inventory" in f.title]
    assert len(inventory) == 1
    f = inventory[0]
    assert f.raw_data["total_users"] == 4
    assert f.raw_data["active_count"] == 2
    assert f.raw_data["suspended_count"] == 1
    assert f.raw_data["deprovisioned_count"] == 1


def test_inactive_account_finding_fires() -> None:
    coll, _ = _make_collector()
    findings = coll.collect()
    inactive = [f for f in findings if "inactive accounts" in f.title]
    assert len(inactive) == 1
    f = inactive[0]
    assert f.raw_data["inactive_count"] == 1  # u02 only
    assert f.raw_data["threshold_days"] == 90


def test_inactive_account_finding_with_custom_threshold() -> None:
    coll, _ = _make_collector(inactive_threshold_days=180)
    findings = coll.collect()
    inactive = [f for f in findings if "inactive accounts" in f.title]
    # u02 is 120 days inactive — under 180-day threshold, no finding
    assert inactive == []


def test_inactive_account_severity_high_for_many_inactives() -> None:
    responses = _baseline_responses()
    # Inflate the inactive list past 50
    responses["/api/v1/users"] = [
        {
            "id": f"u{i:03d}",
            "status": "ACTIVE",
            "lastLogin": _ago_iso(120),
            "profile": {"login": f"user{i}@example.com"},
        }
        for i in range(60)
    ]
    coll, _ = _make_collector(responses)
    findings = coll.collect()
    inactive = [f for f in findings if "inactive accounts" in f.title]
    assert len(inactive) == 1
    assert inactive[0].severity == Severity.HIGH


def test_privileged_account_finding() -> None:
    coll, _ = _make_collector()
    findings = coll.collect()
    admin = [f for f in findings if "admin accounts" in f.title]
    assert len(admin) == 1
    f = admin[0]
    assert f.raw_data["admin_count"] == 2
    assert f.status == FindingStatus.RESOLVED  # 2 <= 5


def test_privileged_account_finding_high_severity() -> None:
    responses = _baseline_responses()
    responses["/api/v1/iam/assignees/users"] = [
        {"id": f"admin{i}"} for i in range(15)
    ]
    coll, _ = _make_collector(responses)
    findings = coll.collect()
    admin = [f for f in findings if "admin accounts" in f.title]
    f = admin[0]
    assert f.severity == Severity.HIGH
    assert f.status == FindingStatus.ACTIVE


def test_mfa_enrollment_finding_low_coverage() -> None:
    coll, _ = _make_collector()
    findings = coll.collect()
    mfa = [f for f in findings if "MFA enrollment" in f.title]
    assert len(mfa) == 1
    f = mfa[0]
    # 1 of 2 active users has factors -> 0.5 enrollment rate
    assert f.raw_data["users_with_factors"] == 1
    assert f.raw_data["sample_size"] == 2
    assert f.severity == Severity.HIGH  # < 0.80
    assert f.status == FindingStatus.ACTIVE


def test_mfa_enrollment_finding_full_coverage() -> None:
    responses = _baseline_responses()
    # Make every active user MFA-enrolled
    responses["/api/v1/users/u02/factors"] = [
        {"id": "f02", "factorType": "push", "status": "ACTIVE"}
    ]
    coll, _ = _make_collector(responses)
    findings = coll.collect()
    mfa = [f for f in findings if "MFA enrollment" in f.title]
    f = mfa[0]
    assert f.raw_data["enrollment_rate"] == 1.0
    assert f.status == FindingStatus.RESOLVED


def test_password_policy_finding_strong() -> None:
    coll, _ = _make_collector()
    findings = coll.collect()
    pp = [f for f in findings if "password policy" in f.title]
    assert len(pp) == 1
    f = pp[0]
    assert f.status == FindingStatus.RESOLVED
    assert f.raw_data["min_length"] == 12


def test_password_policy_finding_weak() -> None:
    responses = _baseline_responses()
    responses["/api/v1/policies"]["PASSWORD"][0]["settings"][
        "password"
    ]["complexity"]["minLength"] = 8
    coll, _ = _make_collector(responses)
    findings = coll.collect()
    pp = [f for f in findings if "password policy" in f.title]
    f = pp[0]
    assert f.status == FindingStatus.ACTIVE
    assert f.severity == Severity.MEDIUM


def test_sign_on_policy_finding() -> None:
    coll, _ = _make_collector()
    findings = coll.collect()
    sop = [f for f in findings if "sign-on policies" in f.title]
    assert len(sop) == 1
    f = sop[0]
    assert f.raw_data["rules_with_mfa"] == 1
    assert f.raw_data["total_rules"] == 1
    assert f.status == FindingStatus.RESOLVED


# ── End-to-end manifest ─────────────────────────────────────────────


def test_collect_v2_emits_manifest() -> None:
    coll, _ = _make_collector()
    findings, manifest = coll.collect_v2()

    assert manifest.collector_id == COLLECTOR_ID
    assert manifest.is_complete
    assert manifest.total_findings == len(findings)
    assert "okta:test-org" in manifest.source_system_ids[0]


def test_dry_run_returns_empty_list() -> None:
    coll, captured = _make_collector()
    findings = coll.collect(dry_run=True)
    assert findings == []
    # No API calls should have happened
    assert captured == []


def test_user_agent_header_set() -> None:
    """The collector identifies itself in the UA header for
    operator-side correlation in Okta system-log audit."""
    coll = OktaCollector(
        org_url="https://test-org.okta.com",
        api_token="t",
    )
    client = coll._ensure_client()
    ua = client.headers.get("User-Agent")
    assert ua and "evidentia-collectors" in ua
    coll.close()
