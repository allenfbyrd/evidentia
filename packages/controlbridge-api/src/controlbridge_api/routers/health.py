"""Health + version endpoints — minimal dependencies.

These are used by:
- The Playwright e2e-smoke test (`wait-on http://127.0.0.1:8000/api/health`)
- The React UI on load to verify the backend is reachable
- Deployment health probes
"""

from __future__ import annotations

import sys

from fastapi import APIRouter

from controlbridge_api import __version__ as api_version
from controlbridge_api.schemas import HealthResponse, VersionResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Simple liveness probe — returns 200 when the server is serving requests."""
    return HealthResponse(status="ok", version=api_version)


@router.get("/version", response_model=VersionResponse)
async def version() -> VersionResponse:
    """Return installed ControlBridge component versions + Python info."""
    # Imports deferred so health stays dependency-light when cores fail.
    try:
        from controlbridge_core import __version__ as core_version
    except ImportError:
        core_version = "unknown"
    try:
        from controlbridge_ai import __version__ as ai_version
    except ImportError:
        ai_version = "unknown"

    py = ".".join(str(v) for v in sys.version_info[:3])
    return VersionResponse(
        api_version=api_version,
        core_version=core_version,
        ai_version=ai_version,
        python_version=py,
    )
