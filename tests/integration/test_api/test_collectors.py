"""TestClient coverage for /api/collectors/* endpoints.

Smoke coverage only — full collector happy-paths are covered in
``tests/unit/test_collectors/``. Here we verify routing, validation,
and error-code mapping.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestCollectorsStatus:
    def test_reports_packages_and_env(
        self, api_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_should_never_appear_in_response")
        r = api_client.get("/api/collectors/status")
        assert r.status_code == 200
        payload = r.json()
        assert "aws" in payload
        assert "github" in payload
        assert payload["github"]["token_configured"] is True
        assert payload["github"]["token_source"] == "env:GITHUB_TOKEN"
        # Token value must NEVER appear in the response.
        assert "should_never_appear_in_response" not in r.text

    def test_reports_github_unconfigured_when_env_missing(
        self, api_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        r = api_client.get("/api/collectors/status")
        payload = r.json()
        assert payload["github"]["token_configured"] is False
        assert payload["github"]["token_source"] is None


class TestGithubCollectEndpoint:
    def test_rejects_malformed_repo(self, api_client: TestClient) -> None:
        r = api_client.post("/api/collectors/github/collect", json={"repo": "notaformat"})
        assert r.status_code == 422
        assert "owner/repo" in r.json()["detail"]

    def test_missing_repo_returns_422(self, api_client: TestClient) -> None:
        r = api_client.post("/api/collectors/github/collect", json={})
        assert r.status_code == 422
