"""Collectors router — AWS + GitHub evidence endpoints.

All endpoints are POST-only — running a collector has non-trivial
side-effects (AWS API calls, GitHub rate limits) so a GET shouldn't
trigger them. Response is a list of :class:`SecurityFinding` objects.

Credentials:
- AWS: boto3's standard chain (env, ~/.aws/credentials, instance profile)
- GitHub: $GITHUB_TOKEN environment variable on the server

No credential values ever flow through request/response bodies.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from controlbridge_core.models.finding import SecurityFinding
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/collectors/aws/collect", response_model=list[SecurityFinding])
async def aws_collect(payload: dict[str, Any] | None = None) -> list[SecurityFinding]:
    """Run the AWS collector (Config + Security Hub).

    Request body (optional):

    - ``region``: override region
    - ``profile``: optional AWS profile name
    - ``include_config``: bool (default True)
    - ``include_security_hub``: bool (default True)
    """
    try:
        from controlbridge_collectors.aws import AwsCollector, AwsCollectorError
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=(
                "AWS collector not installed. Run "
                "`pip install 'controlbridge-collectors[aws]'`."
            ),
        ) from e

    body = payload or {}
    region = body.get("region") if isinstance(body.get("region"), str) else None
    profile = body.get("profile") if isinstance(body.get("profile"), str) else None
    include_config = bool(body.get("include_config", True))
    include_security_hub = bool(body.get("include_security_hub", True))

    try:
        collector = AwsCollector(region=region, profile=profile)
        collector.test_connection()
    except AwsCollectorError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    try:
        findings = collector.collect_all(
            include_config=include_config,
            include_security_hub=include_security_hub,
        )
    except Exception as e:
        logger.exception("AWS collector failed")
        raise HTTPException(status_code=500, detail=f"AWS collector failed: {e}") from e

    return findings


@router.post("/collectors/github/collect", response_model=list[SecurityFinding])
async def github_collect(payload: dict[str, Any]) -> list[SecurityFinding]:
    """Run the GitHub collector.

    Request body (required):

    - ``repo``: repository in 'owner/repo' format

    Credentials are sourced from the server's ``$GITHUB_TOKEN`` env var.
    """
    try:
        from controlbridge_collectors.github import (
            GitHubApiError,
            GitHubCollector,
            GitHubCollectorError,
        )
    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"GitHub collector import failed: {e}",
        ) from e

    repo = str(payload.get("repo") or "").strip()
    if "/" not in repo:
        raise HTTPException(
            status_code=422,
            detail="Request body must include 'repo' in 'owner/repo' format.",
        )
    owner, repo_name = repo.split("/", 1)
    token = os.environ.get("GITHUB_TOKEN")

    try:
        with GitHubCollector(
            owner=owner, repo=repo_name, token=token
        ) as collector:
            findings = collector.collect()
    except GitHubCollectorError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except GitHubApiError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    return findings


@router.get("/collectors/status")
async def collectors_status() -> dict[str, Any]:
    """Report which collectors are installed + which credentials are set.

    Never returns token values — only ``configured: bool`` + the env var
    name the token was sourced from.
    """
    aws_installed = False
    github_installed = False
    try:
        import controlbridge_collectors.aws

        aws_installed = True
    except ImportError:
        pass
    try:
        import controlbridge_collectors.github  # noqa: F401

        github_installed = True
    except ImportError:
        pass

    return {
        "aws": {
            "installed": aws_installed,
            "credentials_hint": (
                "boto3 standard chain (env / ~/.aws / instance profile)"
            ),
        },
        "github": {
            "installed": github_installed,
            "token_configured": bool(os.environ.get("GITHUB_TOKEN")),
            "token_source": "env:GITHUB_TOKEN" if os.environ.get("GITHUB_TOKEN") else None,
        },
    }
