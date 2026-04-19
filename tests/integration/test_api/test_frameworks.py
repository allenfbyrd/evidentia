"""TestClient coverage for the /api/frameworks/* endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestListFrameworks:
    def test_lists_all_bundled(self, api_client: TestClient) -> None:
        r = api_client.get("/api/frameworks")
        assert r.status_code == 200
        payload = r.json()
        assert payload["total"] > 0
        # 82 is the current v0.3.1/v0.4.0 bundled count.
        assert payload["total"] >= 80
        # Entries carry the manifest shape.
        fw = payload["frameworks"][0]
        assert set(fw.keys()) >= {"id", "name", "version", "tier", "category"}

    def test_filter_by_tier(self, api_client: TestClient) -> None:
        r = api_client.get("/api/frameworks", params={"tier": "A"})
        assert r.status_code == 200
        for fw in r.json()["frameworks"]:
            assert fw["tier"] == "A"

    def test_filter_by_category(self, api_client: TestClient) -> None:
        r = api_client.get("/api/frameworks", params={"category": "control"})
        assert r.status_code == 200
        for fw in r.json()["frameworks"]:
            assert fw["category"] == "control"

    def test_filter_by_unknown_tier_returns_empty_list(
        self, api_client: TestClient
    ) -> None:
        r = api_client.get("/api/frameworks", params={"tier": "Z"})
        assert r.status_code == 200
        assert r.json()["frameworks"] == []
        assert r.json()["total"] == 0


class TestGetFramework:
    def test_known_framework_returns_catalog(self, api_client: TestClient) -> None:
        # NIST 800-53 sample is one of the most-loaded bundled catalogs.
        r = api_client.get("/api/frameworks/nist-800-53-mod")
        assert r.status_code == 200
        payload = r.json()
        assert payload["framework_id"] == "nist-800-53-mod"
        assert isinstance(payload["controls"], list)
        assert len(payload["controls"]) > 0

    def test_unknown_framework_returns_404(self, api_client: TestClient) -> None:
        r = api_client.get("/api/frameworks/does-not-exist-xyz")
        assert r.status_code == 404


class TestGetControl:
    def test_known_control_returns_detail(self, api_client: TestClient) -> None:
        # AC-2 is ubiquitous across NIST catalogs.
        r = api_client.get("/api/frameworks/nist-800-53-mod/controls/AC-2")
        assert r.status_code == 200
        payload = r.json()
        assert payload["id"].upper().startswith("AC-2")
        assert "title" in payload

    def test_unknown_control_returns_404(self, api_client: TestClient) -> None:
        r = api_client.get("/api/frameworks/nist-800-53-mod/controls/NOPE-999")
        assert r.status_code == 404
        assert "not found" in r.json()["detail"].lower()
