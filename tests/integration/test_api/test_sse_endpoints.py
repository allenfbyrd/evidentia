"""Smoke coverage for the SSE endpoints (/api/risk/generate, /api/explain/...).

These endpoints call the LLM, so full happy-path tests require a live API
key. Here we cover the validation + 404 paths + structural response shape
so regressions in the router wiring are caught in CI without making
actual LLM calls.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestRiskGenerateValidation:
    def test_missing_report_returns_404(self, api_client: TestClient) -> None:
        r = api_client.post(
            "/api/risk/generate",
            json={"report_key": "0123456789abcdef", "top_n": 1},
        )
        # SSE endpoints are queried via POST; FastAPI still returns 404 JSON
        # for missing upstream resources (the handler raises HTTPException
        # before starting the stream).
        assert r.status_code == 404

    def test_invalid_key_returns_422(self, api_client: TestClient) -> None:
        r = api_client.post(
            "/api/risk/generate",
            json={"report_key": "not-hex", "top_n": 1},
        )
        assert r.status_code == 422

    def test_top_n_out_of_range(self, api_client: TestClient) -> None:
        r = api_client.post(
            "/api/risk/generate",
            json={"report_key": "0123456789abcdef", "top_n": 99},
        )
        # Pydantic Field(le=50) should reject top_n>50.
        assert r.status_code == 422


class TestExplainValidation:
    def test_unknown_framework_returns_404(self, api_client: TestClient) -> None:
        r = api_client.post("/api/explain/does-not-exist/AC-2")
        assert r.status_code == 404

    def test_unknown_control_returns_404(self, api_client: TestClient) -> None:
        r = api_client.post("/api/explain/nist-800-53-mod/NOPE-999")
        assert r.status_code == 404


class TestOpenApi:
    def test_openapi_schema_includes_all_routers(
        self, api_client: TestClient
    ) -> None:
        r = api_client.get("/api/openapi.json")
        assert r.status_code == 200
        paths = r.json()["paths"]
        # Spot-check that every router we register is reachable.
        assert "/api/health" in paths
        assert "/api/version" in paths
        assert "/api/config" in paths
        assert "/api/doctor" in paths
        assert "/api/doctor/check-air-gap" in paths
        assert "/api/llm-status" in paths
        assert "/api/frameworks" in paths
        assert "/api/gap/analyze" in paths
        assert "/api/gap/reports" in paths
        assert "/api/gap/diff" in paths
        assert "/api/risk/generate" in paths
        assert "/api/init/wizard" in paths
