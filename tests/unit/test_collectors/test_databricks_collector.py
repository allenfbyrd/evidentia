"""Unit tests for the Databricks evidence collector (v0.7.8 P0.1).

Mocks the Databricks SDK's WorkspaceClient — no real Databricks
workspace required. Integration tests against a real workspace would
require workspace credentials + a non-trivial fixture; deferred to a
future v0.7.8 P0.x bucket as a follow-up to this scaffolding commit.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from evidentia_collectors.databricks import (
    BLIND_SPOTS,
    COLLECTOR_ID,
    DatabricksAuthError,
    DatabricksCollector,
    DatabricksCollectorError,
    DatabricksPermissionError,
)
from evidentia_core.models.common import Severity
from evidentia_core.models.finding import FindingStatus

# ── Mock SDK infrastructure ─────────────────────────────────────────


def _make_mock_pat(
    *,
    token_id: str,
    owner_id: str = "user-42",
    comment: str = "CI-build token",
    creation_time: int | None = 1700000000000,  # 2023-11-14
    expiry_time: int | None = 1707776000000,  # ~90 days later
) -> Any:
    """Build a minimal SDK-shaped TokenInfo stand-in."""
    tok = MagicMock()
    tok.token_id = token_id
    tok.owner_id = owner_id
    tok.comment = comment
    tok.creation_time = creation_time
    tok.expiry_time = expiry_time
    return tok


def _make_mock_client(
    *,
    user_name: str = "alice@example.com",
    pats: list[Any] | None = None,
    pat_list_raises: Exception | None = None,
) -> Any:
    """Build a minimal WorkspaceClient stand-in.

    The collector calls `client.current_user.me()` (auth probe) and
    `client.token_management.list()` (PAT inventory). Other surfaces
    not yet wired in v0.7.8 P0.1 first slice.
    """
    client = MagicMock()
    client.current_user.me.return_value = MagicMock(user_name=user_name)
    client.config = MagicMock(host="https://test.cloud.databricks.com")
    if pat_list_raises is not None:
        client.token_management.list.side_effect = pat_list_raises
    else:
        client.token_management.list.return_value = pats or []
    return client


# ── Construction tests ─────────────────────────────────────────────


class TestConstruction:
    def test_requires_host_or_client(self) -> None:
        with pytest.raises(
            DatabricksCollectorError, match="requires either host"
        ):
            DatabricksCollector()

    def test_accepts_injected_client(self) -> None:
        c = DatabricksCollector(client=_make_mock_client())
        assert c is not None

    def test_accepts_host_only(self) -> None:
        # Host-only (no client) is valid — SDK is constructed lazily
        # in test_connection() / collect_v2() so this should not
        # raise here even if databricks-sdk isn't installed.
        c = DatabricksCollector(host="https://test.databricks.com")
        assert c is not None


# ── Public-surface tests ───────────────────────────────────────────


class TestPublicSurface:
    def test_collector_id_constant(self) -> None:
        assert COLLECTOR_ID == "databricks-scan"

    def test_blind_spots_documented(self) -> None:
        # v0.7.8 P0.1 ships 7 BLIND_SPOTS entries covering the
        # account-vs-workspace split, UC system-table grants, PAT
        # management permission, init-script content, notebook
        # source content, DLT internals, and cloud-IAM scope.
        assert len(BLIND_SPOTS) == 7
        for entry in BLIND_SPOTS:
            assert {"id", "title", "description"} <= set(entry.keys())
            assert entry["id"].startswith("EVIDENTIA-DATABRICKS-")
            assert len(entry["description"]) > 100  # substantive prose

    def test_exception_hierarchy(self) -> None:
        assert issubclass(DatabricksAuthError, DatabricksCollectorError)
        assert issubclass(
            DatabricksPermissionError, DatabricksCollectorError
        )


# ── PAT inventory sub-check tests ──────────────────────────────────


class TestPATInventory:
    def test_emits_one_inventory_finding_per_pat(self) -> None:
        pats = [
            _make_mock_pat(token_id="tok-1"),
            _make_mock_pat(token_id="tok-2"),
            _make_mock_pat(token_id="tok-3"),
        ]
        client = _make_mock_client(pats=pats)
        with DatabricksCollector(client=client) as c:
            findings, _manifest = c.collect_v2()

        # 3 inventory findings (one per PAT). The mock PATs all have
        # creation/expiry within the 90-day window so no long-lived
        # findings emit.
        inventory_findings = [
            f for f in findings if f.title.startswith("Databricks PAT ")
            and "lifetime" not in f.title and "no expiry" not in f.title
        ]
        assert len(inventory_findings) == 3
        for f in inventory_findings:
            # Inventory findings are RESOLVED status (informational —
            # they're enumerations, not problems).
            assert f.status == FindingStatus.RESOLVED
            assert f.severity == Severity.INFORMATIONAL
            assert f.resource_type == "Databricks::PAT"

    def test_long_lived_pat_emits_active_finding(self) -> None:
        # 180-day lifetime: creation = 0ms, expiry = 180 days * msPerDay.
        ms_per_day = 1000 * 60 * 60 * 24
        pat = _make_mock_pat(
            token_id="tok-longlived",
            creation_time=0,
            expiry_time=180 * ms_per_day,
        )
        client = _make_mock_client(pats=[pat])
        with DatabricksCollector(client=client) as c:
            findings, _manifest = c.collect_v2()

        long_lived = [f for f in findings if "lifetime" in f.title]
        assert len(long_lived) == 1
        f = long_lived[0]
        assert f.severity == Severity.MEDIUM
        assert f.status == FindingStatus.ACTIVE
        assert f.raw_data["lifetime_days"] == 180.0
        assert f.raw_data["threshold_days"] == 90

    def test_never_expires_pat_emits_high_finding(self) -> None:
        # SDK can return None or 0 or -1 for "no expiry"; cover the
        # None case here.
        pat = _make_mock_pat(
            token_id="tok-permanent",
            expiry_time=None,
        )
        client = _make_mock_client(pats=[pat])
        with DatabricksCollector(client=client) as c:
            findings, _manifest = c.collect_v2()

        no_expiry = [f for f in findings if "no expiry" in f.title]
        assert len(no_expiry) == 1
        f = no_expiry[0]
        assert f.severity == Severity.HIGH
        assert f.status == FindingStatus.ACTIVE

    def test_zero_pats_yields_no_findings(self) -> None:
        client = _make_mock_client(pats=[])
        with DatabricksCollector(client=client) as c:
            findings, manifest = c.collect_v2()

        assert findings == []
        assert manifest.is_complete is True
        assert manifest.errors == []

    def test_permission_denied_recorded_in_manifest(self) -> None:
        # Simulate the SDK raising a permission-denied error —
        # the collector heuristic-detects this from the message and
        # records it in manifest.errors[] without aborting the run.
        pat_err = RuntimeError(
            "PERMISSION_DENIED: token_management permission required"
        )
        client = _make_mock_client(pat_list_raises=pat_err)
        with DatabricksCollector(client=client) as c:
            findings, manifest = c.collect_v2()

        assert findings == []
        assert manifest.is_complete is False
        assert any(
            "permission" in err.lower() for err in manifest.errors
        )


# ── Manifest tests ────────────────────────────────────────────────


class TestManifest:
    def test_manifest_lists_pat_resource_type(self) -> None:
        client = _make_mock_client(
            pats=[_make_mock_pat(token_id="tok-x")]
        )
        with DatabricksCollector(client=client) as c:
            _findings, manifest = c.collect_v2()

        assert manifest.collector_id == COLLECTOR_ID
        resource_types = [
            cc.resource_type for cc in manifest.coverage_counts
        ]
        assert "databricks-pat" in resource_types

    def test_manifest_flags_other_sub_checks_as_empty(self) -> None:
        # v0.7.8 P0.1 first slice: only PAT inventory is implemented.
        # The other 6 evidence sources (workspace audit log, table
        # lineage, cluster compliance, network policy, service
        # principal, secret scope) are listed in
        # manifest.empty_categories so consumers know this is
        # PARTIAL evidence.
        client = _make_mock_client(pats=[])
        with DatabricksCollector(client=client) as c:
            _findings, manifest = c.collect_v2()

        expected_pending = {
            "workspace_audit_log",
            "table_lineage",
            "cluster_compliance",
            "network_policy",
            "service_principal",
            "secret_scope",
        }
        assert expected_pending <= set(manifest.empty_categories)


# ── Lifecycle tests ───────────────────────────────────────────────


class TestLifecycle:
    def test_context_manager_lifecycle(self) -> None:
        client = _make_mock_client()
        with DatabricksCollector(client=client) as c:
            assert c is not None
        # SDK client is stateless — close() is a no-op for injected
        # clients (since _owns_client is False), but it must not
        # raise.

    def test_dry_run_yields_empty_findings(self) -> None:
        client = _make_mock_client(
            pats=[_make_mock_pat(token_id="tok-x")]
        )
        c = DatabricksCollector(client=client)
        findings = c.collect(dry_run=True)
        assert findings == []
        # SDK should NOT have been called in dry-run mode.
        assert not client.current_user.me.called
        assert not client.token_management.list.called

    def test_test_connection_caches_user(self) -> None:
        client = _make_mock_client(user_name="bob@example.com")
        c = DatabricksCollector(client=client)
        info = c.test_connection()
        assert info["user_name"] == "bob@example.com"
        # Idempotent — second call doesn't re-probe (we cached).
        info2 = c.test_connection()
        assert info2["user_name"] == info["user_name"]
