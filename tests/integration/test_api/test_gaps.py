"""TestClient coverage for /api/gap/* endpoints.

Uses the Meridian v2 sample inventory from the examples/ directory as
a realistic fixture. No LLM calls; pure gap-arithmetic pipeline.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[3]
MERIDIAN_V2 = REPO_ROOT / "examples" / "meridian-fintech-v2"


@pytest.fixture
def meridian_inventory() -> str:
    """Return the Meridian v2 baseline inventory YAML as a string."""
    return (MERIDIAN_V2 / "my-controls.yaml").read_text(encoding="utf-8")


class TestGapAnalyze:
    def test_rejects_empty_body(self, api_client: TestClient) -> None:
        r = api_client.post("/api/gap/analyze", json={})
        assert r.status_code == 422

    def test_requires_inventory(self, api_client: TestClient) -> None:
        r = api_client.post(
            "/api/gap/analyze",
            json={"frameworks": ["soc2-tsc"]},
        )
        assert r.status_code == 422

    def test_runs_with_inline_content(
        self, api_client: TestClient, meridian_inventory: str
    ) -> None:
        r = api_client.post(
            "/api/gap/analyze",
            json={
                "frameworks": ["soc2-tsc"],
                "inventory_content": meridian_inventory,
                "inventory_format": "yaml",
            },
        )
        assert r.status_code == 200, r.text
        report = r.json()
        assert report["total_gaps"] >= 0
        assert "soc2-tsc" in report["frameworks_analyzed"]
        # Organization from the inventory propagates.
        assert report["organization"]

    def test_organization_override_propagates(
        self, api_client: TestClient, meridian_inventory: str
    ) -> None:
        r = api_client.post(
            "/api/gap/analyze",
            json={
                "frameworks": ["soc2-tsc"],
                "inventory_content": meridian_inventory,
                "organization": "Overridden Org, Inc.",
            },
        )
        assert r.status_code == 200
        assert r.json()["organization"] == "Overridden Org, Inc."


class TestGapReports:
    def test_empty_store_returns_empty_list(self, api_client: TestClient) -> None:
        r = api_client.get("/api/gap/reports")
        assert r.status_code == 200
        assert r.json()["total"] == 0
        assert r.json()["reports"] == []

    def test_analyze_then_list_shows_report(
        self, api_client: TestClient, meridian_inventory: str
    ) -> None:
        # Analyze once so the gap store has something.
        api_client.post(
            "/api/gap/analyze",
            json={
                "frameworks": ["soc2-tsc"],
                "inventory_content": meridian_inventory,
            },
        )
        r = api_client.get("/api/gap/reports")
        assert r.status_code == 200
        payload = r.json()
        assert payload["total"] >= 1
        report_meta = payload["reports"][0]
        assert set(report_meta.keys()) >= {
            "key",
            "mtime_iso",
            "size_bytes",
            "organization",
            "frameworks_analyzed",
        }
        assert report_meta["organization"]


class TestGapDiff:
    def test_rejects_invalid_key(self, api_client: TestClient) -> None:
        r = api_client.post(
            "/api/gap/diff",
            json={"base_key": "not-a-hex-key", "head_key": "also-bad"},
        )
        assert r.status_code == 422

    def test_missing_report_returns_404(
        self, api_client: TestClient
    ) -> None:
        r = api_client.post(
            "/api/gap/diff",
            json={
                "base_key": "0123456789abcdef",
                "head_key": "fedcba9876543210",
            },
        )
        assert r.status_code == 404

    def test_diff_between_same_report_has_all_unchanged(
        self, api_client: TestClient, meridian_inventory: str
    ) -> None:
        # Analyze once -> one report in store. Diff it against itself.
        r1 = api_client.post(
            "/api/gap/analyze",
            json={
                "frameworks": ["soc2-tsc"],
                "inventory_content": meridian_inventory,
            },
        )
        assert r1.status_code == 200
        reports = api_client.get("/api/gap/reports").json()["reports"]
        key = reports[0]["key"]
        r2 = api_client.post(
            "/api/gap/diff",
            json={"base_key": key, "head_key": key},
        )
        assert r2.status_code == 200
        diff = r2.json()
        # Self-diff: no opened/closed/changed; all unchanged (or zero gaps).
        summary = diff["summary"]
        assert summary["opened"] == 0
        assert summary["closed"] == 0
        assert summary["severity_increased"] == 0
        assert summary["severity_decreased"] == 0
